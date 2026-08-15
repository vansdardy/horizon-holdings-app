# -*- coding: utf-8 -*-
"""
Central configuration.

Settings are resolved in this order (first match wins):

  1. A real environment variable  (e.g. PowerShell  $env:PORT="8001")
  2. A `.env` file next to this module
  3. The built-in default

The `.env` file exists because environment variables set in a terminal only
live as long as that terminal, and a virtual environment does not carry them
either. For a service meant to run every day, the settings need to live in a
file that survives reboots.

`.env` is plain text, one KEY=VALUE per line, `#` starts a comment:

    FETCH_HOUR=18
    PORT=8000

Nothing here is required — with no `.env` at all every default applies.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Once PyInstaller freezes this app, `__file__` resolves inside the bundle's
# read-only _internal directory, and the whole install directory is replaced on
# update. Anything the user owns — their database, their .env — has to live
# outside it or it is read-only today and deleted tomorrow. Running from source
# is unaffected: every path below collapses back to HERE.
FROZEN = getattr(sys, "frozen", False)
EXE_DIR = os.path.dirname(os.path.abspath(sys.executable)) if FROZEN else HERE


def _default_data_dir():
    """Writable directory for the files this app owns, per user."""
    if not FROZEN:
        return HERE
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "HorizonHoldings")


# The desktop shell passes these explicitly; the defaults only matter when the
# frozen backend is launched on its own.
DATA_DIR = os.environ.get("PORTFOLIO_DATA_DIR") or _default_data_dir()
ENV_FILE = os.environ.get("PORTFOLIO_ENV_FILE", os.path.join(EXE_DIR, ".env"))

_loaded_from = None


def _load_env_file(path=ENV_FILE):
    """Read KEY=VALUE lines into os.environ WITHOUT clobbering real env vars."""
    global _loaded_from
    if not os.path.isfile(path):
        return {}
    found = {}
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if not key:
                continue
            found[key] = val
            # A real environment variable always wins, so a one-off override
            # like `PORT=9000 python3 server.py` still works.
            os.environ.setdefault(key, val)
    if found:
        _loaded_from = path
    return found


_FILE_VALUES = _load_env_file()


def _int(name, default, lo=None, hi=None):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        v = int(raw)
    except ValueError:
        raise SystemExit(
            f"[config] {name}={raw!r} is not a whole number.\n"
            f"          Fix it in {ENV_FILE} (or unset the environment variable).")
    if lo is not None and not (lo <= v <= (hi if hi is not None else v)):
        raise SystemExit(
            f"[config] {name}={v} is out of range; expected {lo}–{hi}.\n"
            f"          Fix it in {ENV_FILE}.")
    return v


def _bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


PORT = _int("PORT", 8000, 1, 65535)
FETCH_HOUR = _int("FETCH_HOUR", 18, 0, 23)
FETCH_LOOKBACK = os.environ.get("FETCH_LOOKBACK") or "10d"
MARKETDATA_MOCK = _bool("MARKETDATA_MOCK", False)
DB_PATH = os.environ.get("PORTFOLIO_DB") or os.path.join(DATA_DIR, "portfolio.db")

# Reporting / denomination currency for the model index.
SUPPORTED_CCY = ("CHF", "USD", "EUR", "GBP", "CAD", "JPY", "DKK")
BASE_CCY = (os.environ.get("BASE_CCY") or "CHF").strip().upper()
if BASE_CCY not in SUPPORTED_CCY:
    raise SystemExit(
        f"[config] BASE_CCY={BASE_CCY!r} is not one of {', '.join(SUPPORTED_CCY)}.\n"
        f"          Fix it in {ENV_FILE}.")


def effective():
    """What the service is actually running with, and where each value came from."""
    def origin(key):
        if key in _FILE_VALUES and os.environ.get(key) == _FILE_VALUES.get(key):
            return f".env file"
        return "environment variable" if os.environ.get(key) else "default"

    return {
        "PORT": {"value": PORT, "source": origin("PORT")},
        "FETCH_HOUR": {"value": FETCH_HOUR, "source": origin("FETCH_HOUR")},
        "FETCH_LOOKBACK": {"value": FETCH_LOOKBACK, "source": origin("FETCH_LOOKBACK")},
        "MARKETDATA_MOCK": {"value": MARKETDATA_MOCK, "source": origin("MARKETDATA_MOCK")},
        "PORTFOLIO_DB": {"value": DB_PATH, "source": origin("PORTFOLIO_DB")},
        "BASE_CCY": {"value": BASE_CCY, "source": origin("BASE_CCY")},
        "env_file": ENV_FILE,
        "env_file_found": os.path.isfile(ENV_FILE),
    }


def print_summary():
    eff = effective()
    print(f"[config] .env: {ENV_FILE}"
          f"{'' if eff['env_file_found'] else '  (not present — using defaults)'}")
    for k in ("PORT", "FETCH_HOUR", "FETCH_LOOKBACK", "MARKETDATA_MOCK",
              "BASE_CCY", "PORTFOLIO_DB"):
        print(f"[config]   {k} = {eff[k]['value']}   ({eff[k]['source']})")
