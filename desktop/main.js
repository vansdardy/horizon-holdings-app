'use strict';
/**
 * Desktop shell for the Horizon Holdings portfolio service.
 *
 * All of the application logic lives in the Python backend; this process only
 * supervises it. The responsibilities, ordered by how much trouble each causes
 * when skipped:
 *
 *   1. Keep exactly ONE backend alive. Two would both fire the 18:00 scheduled
 *      fetch against the same database on the same day.
 *   2. Tear the backend down on quit. On Windows a dying parent does not take
 *      its children with it, so an orphan keeps holding the port and the
 *      SQLite file until the user finds it in Task Manager.
 *   3. Keep the database OUT of the install directory, which is read-only and
 *      gets replaced wholesale on update.
 */

const { app, BrowserWindow, Tray, Menu, dialog, shell, nativeImage, Notification, ipcMain } = require('electron');
const { spawn, execFile } = require('child_process');
const http = require('http');
const net = require('net');
const path = require('path');
const fs = require('fs');

const REPO = path.join(__dirname, '..');
const ICON = path.join(__dirname, 'build', 'icon.png');

let mainWindow = null;
let guideWindow = null;
let tray = null;
let backend = null;
let backendPort = null;
let logStream = null;
let isQuitting = false;
let isRestarting = false;   // suppresses the "backend died" alarm during a deliberate restart
const backendLog = [];   // tail kept in memory so a startup failure can be shown

// ---------------------------------------------------------------- logging
function log(line) {
  const stamped = `[${new Date().toISOString()}] ${line}`;
  console.log(stamped);
  backendLog.push(line);
  if (backendLog.length > 200) backendLog.shift();
  if (logStream) logStream.write(stamped + '\n');
}

// ---------------------------------------------------------------- backend
/**
 * Ask the OS for an unused port rather than hardcoding 8000, which may well be
 * taken by something else on the user's machine — including a copy of this
 * same service started from a terminal.
 *
 * There is a small race here: the port is released before the backend binds
 * it. Nothing else on a desktop machine is realistically racing for a random
 * high port, and the alternative (passing an inherited socket into Python) is
 * far more machinery than the risk warrants.
 */
function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

/**
 * Packaged: the frozen bundle sits in resources/backend.
 * Development: prefer the frozen bundle if it has been built, but fall back to
 * running server.py out of the venv so the shell can be iterated on without
 * re-running PyInstaller every time.
 */
function backendCommand() {
  if (app.isPackaged) {
    return { cmd: path.join(process.resourcesPath, 'backend', 'horizon-backend.exe'), args: [] };
  }
  const frozen = path.join(REPO, 'build', 'backend', 'horizon-backend', 'horizon-backend.exe');
  if (fs.existsSync(frozen)) return { cmd: frozen, args: [] };

  const py = path.join(REPO, '.venv', 'Scripts', 'python.exe');
  return { cmd: py, args: [path.join(REPO, 'server.py')] };
}

/**
 * Copy a database across, WAL sidecars included.
 *
 * The -wal and -shm files travel with the main file deliberately: the database
 * runs in WAL mode, so committed transactions can still be sitting in the -wal
 * file, and copying portfolio.db alone can silently lose them. The source is
 * left untouched, so this is reversible if anything looks wrong.
 */
function copyDatabaseFiles(source, target) {
  // Clear sidecars belonging to whatever is being replaced FIRST. A -wal file
  // left over from the previous database gets applied to the new one the next
  // time SQLite opens it, which is an efficient way to corrupt both.
  for (const suffix of ['-wal', '-shm']) {
    if (fs.existsSync(target + suffix)) fs.unlinkSync(target + suffix);
  }
  for (const suffix of ['', '-wal', '-shm']) {
    const from = source + suffix;
    if (fs.existsSync(from)) fs.copyFileSync(from, target + suffix);
  }
  log(`copied database ${source} -> ${target} (source left in place)`);
}

/**
 * Stop the backend and wait for the process to actually be gone.
 *
 * stopBackend() only sends the kill; on Windows the file handle survives for a
 * moment afterwards, and copying over a database the dying process still holds
 * open fails with EBUSY. Anything that replaces the database file has to wait
 * here first.
 */
function stopBackendAndWait(timeoutMs = 10000) {
  const child = backend;
  if (!child) return Promise.resolve();
  const exited = new Promise(resolve => child.once('exit', resolve));
  stopBackend();
  return Promise.race([exited, new Promise(r => setTimeout(r, timeoutMs))])
    .then(() => new Promise(r => setTimeout(r, 500)));
}

/**
 * First launch has no database, and starting a fresh one is NOT a harmless
 * default here. The entire point of this application is an unbroken NAV series,
 * so quietly seeding a new index while the user's real history sits in a file
 * somewhere else produces a second, discontinuous series that looks perfectly
 * legitimate until they notice the record restarts.
 *
 * Running from source, the project's own copy is sitting right next to the
 * shell and is taken automatically. Once packaged there is no such thing — the
 * install directory bears no relationship to wherever the user kept their
 * data — so the only honest option is to ask. An earlier version of this
 * function looked for the source copy in both cases, which silently did nothing
 * when packaged.
 */
async function ensureDatabase(userData) {
  const target = path.join(userData, 'portfolio.db');
  if (fs.existsSync(target)) return true;

  if (!app.isPackaged) {
    const devCopy = path.join(REPO, 'portfolio.db');
    if (fs.existsSync(devCopy)) {
      copyDatabaseFiles(devCopy, target);
      return true;
    }
  }

  log('no database found; asking whether to import one');
  // Three buttons, with cancel pointing at Quit on purpose. Dismissing a dialog
  // with Escape or the X returns cancelId, so if that mapped to "start fresh"
  // then closing the window without reading it would quietly seed a second,
  // disconnected NAV series — the exact outcome this prompt exists to prevent.
  // Seeding a new series now requires a deliberate click.
  const { response } = await dialog.showMessageBox({
    type: 'question',
    buttons: ['导入已有数据 / Import…', '全新开始 / Start fresh', '退出 / Quit'],
    defaultId: 0,
    cancelId: 2,
    title: 'Horizon Holdings',
    message: '没有找到数据库 / No database found',
    detail:
      '之前用 python server.py 跑过的话,请导入那个 portfolio.db。\n' +
      '选择「全新开始」会重新播种一条净值序列,与原来的不连续。\n' +
      '不确定就先「退出」—— 什么都不会被改动。\n\n' +
      'If you have been running this from source, import that portfolio.db. ' +
      'Starting fresh seeds a new NAV series that will not connect to your ' +
      'existing one. If unsure, quit — nothing is changed either way.',
  });

  if (response === 2) {
    log('no database chosen; quitting without creating one');
    return false;
  }
  if (response === 1) {
    log('starting with a fresh database, by explicit choice');
    return true;
  }

  const picked = await dialog.showOpenDialog({
    title: 'Select portfolio.db',
    properties: ['openFile'],
    filters: [{ name: 'SQLite database', extensions: ['db'] }],
  });
  if (picked.canceled || !picked.filePaths.length) {
    // Backing out of the file picker is not a request to start a new series
    // either. Quit; relaunching brings the prompt straight back.
    log('import cancelled; quitting without creating a database');
    return false;
  }
  copyDatabaseFiles(picked.filePaths[0], target);
  return true;
}

/**
 * Import a database at any time, not just on a first run with nothing to lose.
 *
 * The first-run prompt answered "where is my data" only at the one moment the
 * app had no data. Anyone who answered "start fresh", or who moves a machine,
 * or who restores a backup, had no route back — the only way in was to quit,
 * delete a file by hand in an AppData folder, and relaunch.
 *
 * This replaces live data, so it: refuses anything that is not a SQLite file
 * BEFORE touching the original, backs up what is there, stops the backend so
 * the file is not held open, swaps, restarts, and reloads the window.
 */
async function importDatabaseNow(userData) {
  const picked = await dialog.showOpenDialog({
    title: '选择要导入的 portfolio.db / Select a portfolio.db to import',
    properties: ['openFile'],
    filters: [{ name: 'SQLite database', extensions: ['db'] }],
  });
  if (picked.canceled || !picked.filePaths.length) return false;
  const source = picked.filePaths[0];

  // Every SQLite file begins with this exact string. Checking it costs nothing
  // and prevents the worst outcome here: the original replaced by a file the
  // backend then cannot open, leaving the app unable to start at all.
  let header = '';
  try {
    const fd = fs.openSync(source, 'r');
    const buf = Buffer.alloc(16);
    fs.readSync(fd, buf, 0, 16, 0);
    fs.closeSync(fd);
    header = buf.toString('utf8');
  } catch (e) {
    header = '';
  }
  if (!header.startsWith('SQLite format 3')) {
    dialog.showErrorBox(
      '这不是一个 SQLite 数据库 / Not a SQLite database',
      `${source}\n\n文件头不匹配,已取消 —— 当前数据未被改动。\n`
      + 'The file header does not match. Cancelled; nothing was changed.');
    return false;
  }

  const target = path.join(userData, 'portfolio.db');
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const backup = path.join(userData, `portfolio-replaced-${stamp}.db`);

  const { response } = await dialog.showMessageBox({
    type: 'warning',
    buttons: ['导入并重启 / Import and restart', '取消 / Cancel'],
    defaultId: 1,
    cancelId: 1,
    title: '导入数据库 / Import database',
    message: '当前数据库将被替换 / The current database will be replaced',
    detail: `导入 / From:\n${source}\n\n`
          + `现有数据先备份到 / Current data is backed up first:\n${backup}\n\n`
          + '随后会重启后台服务并刷新窗口。\n'
          + 'The backend will then restart and the window will reload.',
  });
  if (response !== 0) {
    log('import cancelled at the confirmation step');
    return false;
  }

  try {
    isRestarting = true;
    await stopBackendAndWait();

    if (fs.existsSync(target)) copyDatabaseFiles(target, backup);
    copyDatabaseFiles(source, target);

    backendPort = await freePort();
    startBackend(backendPort, userData);
    await waitForBackend(backendPort);
    isRestarting = false;

    // Both windows are pointed at the old port, which is now dead.
    if (guideWindow && !guideWindow.isDestroyed()) guideWindow.close();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadURL(`http://127.0.0.1:${backendPort}/`);
    }
    notify('数据库已导入 / Database imported',
           `原数据已备份 / Previous data saved as:\n${path.basename(backup)}`);
    return true;
  } catch (err) {
    isRestarting = false;
    log(`import failed: ${err.message}`);
    dialog.showErrorBox(
      '导入失败 / Import failed',
      `${err.message}\n\n原数据备份在 / Your previous data is at:\n${backup}`);
    return false;
  }
}

function startBackend(port, userData) {
  const { cmd, args } = backendCommand();
  if (!fs.existsSync(cmd)) {
    throw new Error(
      `backend executable not found:\n${cmd}\n\n` +
      `In development, build it first:\n` +
      `  .venv/Scripts/python.exe -m PyInstaller backend.spec --noconfirm ` +
      `--distpath build/backend --workpath build/pyinstaller`
    );
  }

  log(`starting backend: ${cmd} ${args.join(' ')} (port ${port})`);
  backend = spawn(cmd, args, {
    cwd: path.dirname(cmd),
    windowsHide: true,   // maps to CREATE_NO_WINDOW; the backend is a console
                         // binary so that print() keeps working, and without
                         // this a console window would flash up on every launch
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PORT: String(port),
      PORTFOLIO_DB: path.join(userData, 'portfolio.db'),
      PORTFOLIO_ENV_FILE: path.join(userData, '.env'),
      PORTFOLIO_DATA_DIR: userData,
      // Without this the backend's log lines come back mojibake, because its
      // output contains em-dashes and Chinese text that cp1252 cannot encode.
      PYTHONIOENCODING: 'utf-8',
    },
  });

  backend.stdout.on('data', d => String(d).trimEnd().split('\n').forEach(l => log(`[backend] ${l}`)));
  backend.stderr.on('data', d => String(d).trimEnd().split('\n').forEach(l => log(`[backend] ${l}`)));

  backend.on('exit', (code, signal) => {
    log(`backend exited (code=${code} signal=${signal})`);
    backend = null;
    // A restart stops the backend on purpose; without this guard the import
    // flow would greet the user with a crash dialog mid-way through working.
    if (!isQuitting && !isRestarting) {
      dialog.showErrorBox(
        '后台服务已停止 / Backend stopped',
        `数据服务意外退出 (code ${code})。请重启应用。\n\n` +
        `The data service exited unexpectedly. Restart the app.\n\n` +
        backendLog.slice(-15).join('\n')
      );
    }
  });
}

/** Poll until the API actually answers. A fixed sleep would be either a guess
 *  that's too short on a cold first launch, or wasted time on every launch after. */
function waitForBackend(port, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const attempt = () => {
      if (!backend) return reject(new Error('backend process died during startup'));
      const req = http.get({ host: '127.0.0.1', port, path: '/api/status', timeout: 2000 }, res => {
        res.resume();
        if (res.statusCode === 200) resolve();
        else retry();
      });
      req.on('error', retry);
      req.on('timeout', () => { req.destroy(); retry(); });
    };
    const retry = () => {
      if (Date.now() > deadline) {
        reject(new Error(`backend did not answer on port ${port} within ${timeoutMs / 1000}s`));
      } else {
        setTimeout(attempt, 300);
      }
    };
    attempt();
  });
}

function stopBackend() {
  if (!backend || !backend.pid) return;
  const pid = backend.pid;
  log(`stopping backend pid ${pid}`);
  if (process.platform === 'win32') {
    // child.kill() signals only the direct child. /T takes the whole tree, which
    // matters because the frozen bundle's launcher and the Python process it
    // starts are two different PIDs.
    execFile('taskkill', ['/PID', String(pid), '/T', '/F'], () => {});
  } else {
    backend.kill('SIGTERM');
  }
  backend = null;
}

function notify(title, body) {
  log(`notify: ${title} — ${body.replace(/\n/g, ' / ')}`);
  if (Notification.isSupported()) {
    new Notification({ title, body, icon: fs.existsSync(ICON) ? ICON : undefined }).show();
  } else {
    dialog.showMessageBox({ type: 'info', title: 'Horizon Holdings', message: title, detail: body });
  }
}

/**
 * Describe what the action actually did, in the same vocabulary the menu item
 * used. A tray command that succeeds silently is indistinguishable from one
 * that fails silently — which is exactly how someone ends up believing prices
 * have been updating for a month when they have not.
 */
function describeResult(urlPath, d) {
  if (urlPath.startsWith('/api/refresh_fundamentals')) {
    if (d.skipped) {
      return `${d.quarter} 本季度已是最新,未重复请求。\n`
           + `Already current for ${d.quarter}; nothing re-fetched.`;
    }
    const failed = (d.failed || []).length;
    return `${d.quarter}:${d.fetched} 支已更新,${failed} 支失败。\n`
         + `${d.fetched} tickers updated, ${failed} failed.`;
  }
  const nav = typeof d.nav_per_share === 'number' ? d.nav_per_share.toFixed(2) : '—';
  const back = (d.backfilled_dates || []).length;
  return `${d.date} · 每份净值 ${nav} ${d.base_ccy} · ${d.n_priced}/78 已定价`
       + (back ? `\n另补齐 ${back} 个交易日 / ${back} earlier session(s) backfilled.` : '');
}

function runAction(urlPath, label) {
  if (!backendPort) return;
  log(`tray action -> POST ${urlPath}`);
  const req = http.request(
    { host: '127.0.0.1', port: backendPort, path: urlPath, method: 'POST', timeout: 600000 },
    res => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', c => { body += c; });
      res.on('end', () => {
        let detail;
        try {
          const d = JSON.parse(body);
          // A 409 here is the backend deliberately refusing to write a NAV
          // because a held position had no price. Its message names the
          // tickers, so it is far more useful than a status code.
          detail = res.statusCode === 200
            ? describeResult(urlPath, d)
            : (d.detail || `HTTP ${res.statusCode}`);
        } catch {
          detail = `HTTP ${res.statusCode}`;
        }
        notify(res.statusCode === 200 ? `${label} 已更新` : `${label} 未能更新`, detail);
      });
    });
  req.on('error', e => notify(`${label} 未能更新`, e.message));
  req.on('timeout', () => { req.destroy(); notify(`${label} 超时 / timed out`, urlPath); });
  req.end();
}

/**
 * The build guide, in its own window inside the app rather than handed off to a
 * browser — the point is that the application can explain its own construction
 * without going anywhere.
 */
function openGuide() {
  if (guideWindow && !guideWindow.isDestroyed()) {
    guideWindow.show();
    guideWindow.focus();
    return;
  }
  guideWindow = new BrowserWindow({
    width: 1180,
    height: 940,
    minWidth: 720,
    minHeight: 600,
    backgroundColor: '#0F141A',
    title: 'How this app was built',
    icon: fs.existsSync(ICON) ? ICON : undefined,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  guideWindow.setMenuBarVisibility(false);
  guideWindow.loadURL(`http://127.0.0.1:${backendPort}/guide`);
  guideWindow.on('closed', () => { guideWindow = null; });
}

// ---------------------------------------------------------------- ui
function createWindow(show) {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 980,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    // Matches --bg in index.html. Without it the window paints white for a beat
    // before the dark page loads, which reads as a flash on every launch.
    backgroundColor: '#0B0F14',
    icon: fs.existsSync(ICON) ? ICON : undefined,
    title: 'Horizon Holdings',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      // This started with no preload at all, on the reasoning that the page is
      // an ordinary web page talking to a local HTTP API, so any bridge into
      // Node would be attack surface bought for nothing. That held until the
      // page needed to offer "Import database", which requires a native file
      // dialog and a backend restart — things HTTP cannot reach.
      //
      // The tradeoff changed, so the decision did. The bridge exposes two named
      // functions and nothing else; see preload.js for why that stays safe.
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${backendPort}/`);
  mainWindow.once('ready-to-show', () => { if (show) mainWindow.show(); });
  mainWindow.setMenuBarVisibility(false);

  // Anything that isn't the local backend opens in the real browser instead of
  // navigating this window away from the app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // The page's own guide link opens in the app's guide window; anything
    // genuinely external is handed to the real browser.
    if (url === `http://127.0.0.1:${backendPort}/guide`) openGuide();
    else shell.openExternal(url);
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (!url.startsWith(`http://127.0.0.1:${backendPort}`)) {
      e.preventDefault();
      shell.openExternal(url);
    }
  });

  // Closing hides to the tray so the scheduler survives; only an explicit Quit
  // actually exits. This is the whole reason the tray exists.
  mainWindow.on('close', e => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
}

function showWindow() {
  if (!mainWindow) return createWindow(true);
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

function buildTray(userData) {
  const image = fs.existsSync(ICON)
    ? nativeImage.createFromPath(ICON).resize({ width: 16, height: 16 })
    : nativeImage.createEmpty();

  tray = new Tray(image);
  tray.setToolTip(`Horizon Holdings ${app.getVersion()}`);

  const refreshMenu = () => {
    const openAtLogin = app.getLoginItemSettings().openAtLogin;
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: '打开窗口 / Show', click: showWindow },
      { type: 'separator' },
      // Each item names what it actually fetches. The old single "Fetch now"
      // said nothing about WHICH of the app's two independent pipelines it
      // ran — daily prices and NAV, or the quarterly fundamentals — and they
      // run on completely different schedules for different reasons.
      // NB: '&&' renders one literal ampersand; a single '&' is a Windows
      // menu mnemonic and would silently underline the next letter instead.
      {
        label: '更新行情与净值 / Update prices && NAV',
        toolTip: '抓取收盘价与汇率,重算净值(每日)',
        click: () => runAction('/api/refresh', '行情与净值 / Prices & NAV'),
      },
      {
        label: '更新 P/E、股息率、Beta / Update fundamentals',
        toolTip: '每季度一次;同一季度内重复点击会被跳过',
        click: () => runAction('/api/refresh_fundamentals', '基本面 / Fundamentals'),
      },
      { type: 'separator' },
      { label: '导入数据库… / Import database…', click: () => importDatabaseNow(userData) },
      { label: '这个应用是怎么做出来的 / How this app was built', click: openGuide },
      { label: '打开数据文件夹 / Open data folder', click: () => shell.openPath(userData) },
      { label: `版本 / Version ${app.getVersion()}`, enabled: false },
      { type: 'separator' },
      {
        label: '开机自启 / Start at login',
        type: 'checkbox',
        checked: openAtLogin,
        click: menuItem => {
          app.setLoginItemSettings({
            openAtLogin: menuItem.checked,
            args: ['--hidden'],   // start into the tray, not into a window
          });
          refreshMenu();
        },
      },
      { type: 'separator' },
      { label: '退出 / Quit', click: () => { isQuitting = true; app.quit(); } },
    ]));
  };

  refreshMenu();
  tray.on('double-click', showWindow);
}

// ---------------------------------------------------------------- lifecycle
// Must happen before anything else: a second copy would start a second backend
// and a second scheduler against the same database.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', showWindow);

  app.whenReady().then(async () => {
    const userData = app.getPath('userData');
    fs.mkdirSync(userData, { recursive: true });
    logStream = fs.createWriteStream(path.join(userData, 'desktop.log'), { flags: 'a' });
    log(`--- launch (packaged=${app.isPackaged}) userData=${userData}`);

    try {
      if (!await ensureDatabase(userData)) {
        isQuitting = true;
        app.quit();
        return;
      }
      backendPort = await freePort();
      startBackend(backendPort, userData);
      await waitForBackend(backendPort);
      log(`backend ready on port ${backendPort}`);
    } catch (err) {
      log(`startup failed: ${err.message}`);
      dialog.showErrorBox(
        '启动失败 / Startup failed',
        `${err.message}\n\n最近日志 / Recent log:\n${backendLog.slice(-15).join('\n')}\n\n` +
        `完整日志 / Full log:\n${path.join(userData, 'desktop.log')}`
      );
      isQuitting = true;
      stopBackend();
      app.quit();
      return;
    }

    // --hidden is passed by the launch-at-login entry so a boot goes straight
    // to the tray instead of throwing a window in the user's face.
    // The two channels preload.js exposes, and the only ones that exist. Both
    // are registered after userData is known, because the import needs it.
    ipcMain.handle('db:import', () => importDatabaseNow(userData));
    ipcMain.handle('app:version', () => {
      // The page requests this on load, so seeing it in the log is proof the
      // preload bridge actually loaded. If preload.js goes missing from the
      // build, this line stops appearing and the Import button silently never
      // renders — worth being able to check without opening devtools.
      log('renderer reached the preload bridge');
      return app.getVersion();
    });

    const startHidden = process.argv.includes('--hidden');
    buildTray(userData);
    createWindow(!startHidden);
  });

  // Deliberately NOT quitting here. Closing the window is "put it away", and
  // the daily 18:00 fetch only happens if this process stays alive.
  app.on('window-all-closed', () => {});

  app.on('before-quit', () => { isQuitting = true; });
  app.on('will-quit', stopBackend);
  process.on('exit', stopBackend);
}
