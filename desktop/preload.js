'use strict';
/**
 * The one bridge between the page and Electron.
 *
 * This file did not exist until the app needed a button the page could not
 * provide on its own. Everything else the interface does is an HTTP call to the
 * local backend, which needs no privileges at all — but importing a database
 * requires a native file picker and a backend restart, and neither is something
 * a web page can do.
 *
 * The rules that keep this safe:
 *
 *   - `contextIsolation` is on, so this runs in its own world. The page cannot
 *     reach `require`, Node, or anything not listed below.
 *   - Only named functions are exposed, never `ipcRenderer` itself. Handing the
 *     page a general-purpose message channel would let it invoke every handler
 *     the main process has, which is the usual way this pattern goes wrong.
 *   - The privileged action on the other side asks the user to confirm. Even if
 *     the page were compromised, the worst it achieves is a dialog nobody
 *     agreed to.
 *
 * `window.desktop` existing is also how the page knows it is running in the
 * desktop app at all — in an ordinary browser it is undefined, and the button
 * that depends on it stays hidden.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktop', {
  /** Resolves true if a database was imported, false if the user backed out. */
  importDatabase: () => ipcRenderer.invoke('db:import'),

  /** The app version, so a user can report what they are running. */
  version: () => ipcRenderer.invoke('app:version'),
});
