# -*- coding: utf-8 -*-
"""Vicky Talk tool layer — the hands of the assistant.

TOOLS_SCHEMA describes every capability the brain may route to.
ToolDispatcher executes them; every destructive or system-level action goes
through confirm_fn (supplied by the UI, typically a QMessageBox wrapper)
before anything happens.

Nothing in this module touches the OS at import time. Windows-only APIs are
guarded by `sys.platform == "win32"` *inside* the methods that need them.
dispatch() never raises — it always returns {"ok": bool, "result": str}.
"""

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

TOOLS_SCHEMA = [
    {
        "name": "file_list",
        "description": "List files and folders in a directory.",
        "args": {"path": "directory path (default: home)"},
    },
    {
        "name": "file_read",
        "description": "Read a text file (truncated).",
        "args": {"path": "file path", "max_chars": "max characters (default 4000)"},
    },
    {
        "name": "file_copy",
        "description": "Copy a file to a new location.",
        "args": {"src": "source path", "dst": "destination path"},
    },
    {
        "name": "file_move",
        "description": "Move (rename) a file to a new location.",
        "args": {"src": "source path", "dst": "destination path"},
    },
    {
        "name": "file_delete",
        "description": "Delete a file (asks for confirmation; to recycle bin if possible).",
        "args": {"path": "file path"},
    },
    {
        "name": "app_launch",
        "description": "Open an application or file with its default program (Windows only).",
        "args": {"target": "program, file or folder to open"},
    },
    {
        "name": "app_close",
        "description": "Close a running program by its image name, e.g. notepad.exe (asks for confirmation).",
        "args": {"name": "process image name, e.g. notepad.exe"},
    },
    {
        "name": "sys_shutdown",
        "description": "Shut down the PC after 30 seconds (asks for confirmation).",
        "args": {},
    },
    {
        "name": "sys_restart",
        "description": "Restart the PC after 30 seconds (asks for confirmation).",
        "args": {},
    },
    {
        "name": "sys_sleep",
        "description": "Put the PC to sleep (asks for confirmation).",
        "args": {},
    },
    {
        "name": "sys_lock",
        "description": "Lock the workstation immediately.",
        "args": {},
    },
    {
        "name": "web_search",
        "description": "Search the web and return titles + URLs.",
        "args": {"query": "search text", "n": "number of results (default 5)"},
    },
    {
        "name": "remember",
        "description": "Remember a fact about the user.",
        "args": {"key": "fact name", "value": "fact value"},
    },
    {
        "name": "recall",
        "description": "Recall a previously remembered fact.",
        "args": {"key": "fact name"},
    },
    {
        "name": "add_objective",
        "description": "Add an objective/goal.",
        "args": {"title": "objective text", "tag": "WORK or PERSONAL (default WORK)"},
    },
    {
        "name": "add_reminder",
        "description": "Set a reminder in N minutes.",
        "args": {"text": "reminder text", "minutes_from_now": "default 60"},
    },
]

# Paths we refuse to delete under, even with confirmation.
_PROTECTED_PREFIXES_WIN = ("c:\\windows", "c:\\program files",
                           "c:\\program files (x86)")


def _resolve(path):
    """Expand ~ / env vars and return an absolute resolved Path."""
    return Path(os.path.expandvars(os.path.expanduser(str(path))).strip()).resolve()


def _is_protected(path):
    """True if path is a drive root or inside a protected system folder."""
    p = _resolve(path)
    # Drive roots (C:\, D:\ ...)
    if p.parent == p:
        return True
    if sys.platform == "win32":
        s = str(p).lower()
        return s.startswith(_PROTECTED_PREFIXES_WIN)
    return False


class ToolDispatcher:
    """Execute tools by name. confirm_fn(title, text) -> bool."""

    def __init__(self, confirm_fn):
        self.confirm = confirm_fn

    # --------------------------------------------------------------- router
    def dispatch(self, name, **kwargs):
        """Run a tool. Never raises; returns {"ok": bool, "result": str}."""
        handler = {
            "file_list": self._file_list,
            "file_read": self._file_read,
            "file_copy": self._file_copy,
            "file_move": self._file_move,
            "file_delete": self._file_delete,
            "app_launch": self._app_launch,
            "app_close": self._app_close,
            "sys_shutdown": self._sys_shutdown,
            "sys_restart": self._sys_restart,
            "sys_sleep": self._sys_sleep,
            "sys_lock": self._sys_lock,
            "web_search": self._web_search,
            "remember": self._remember,
            "recall": self._recall,
            "add_objective": self._add_objective,
            "add_reminder": self._add_reminder,
        }.get(name)
        if handler is None:
            return {"ok": False, "result": "Unknown tool: %s" % name}
        try:
            return handler(**kwargs)
        except TypeError as exc:
            return {"ok": False,
                    "result": "Bad arguments for %s: %s" % (name, exc)}
        except Exception as exc:
            return {"ok": False, "result": "%s failed: %s" % (name, exc)}

    # ---------------------------------------------------------------- files
    def _file_list(self, path="~"):
        try:
            p = _resolve(path)
        except Exception as exc:
            return {"ok": False, "result": "Invalid path: %s" % exc}
        if not p.is_dir():
            return {"ok": False, "result": "Not a directory: %s" % p}
        try:
            entries = []
            for child in sorted(p.iterdir(),
                                key=lambda c: (not c.is_dir(), c.name.lower())):
                entries.append(
                    "[DIR]  %s" % child.name if child.is_dir() else child.name
                )
            return {"ok": True, "result": "\n".join(entries) or "(empty)"}
        except Exception as exc:
            return {"ok": False, "result": "Cannot list %s: %s" % (p, exc)}

    def _file_read(self, path, max_chars=4000):
        try:
            p = _resolve(path)
        except Exception as exc:
            return {"ok": False, "result": "Invalid path: %s" % exc}
        if not p.is_file():
            return {"ok": False, "result": "Not a file: %s" % p}
        try:
            n = int(max_chars)
        except (TypeError, ValueError):
            n = 4000
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return {"ok": False, "result": "Cannot read %s: %s" % (p, exc)}
        if len(text) > n:
            text = text[:n] + "\n…(truncated, %d chars total)" % len(text)
        return {"ok": True, "result": text}

    def _file_copy(self, src, dst):
        try:
            s, d = _resolve(src), _resolve(dst)
            if d.is_dir():
                d = d / s.name
            shutil.copy2(s, d)
            return {"ok": True, "result": "Copied to %s" % d}
        except Exception as exc:
            return {"ok": False, "result": "Copy failed: %s" % exc}

    def _file_move(self, src, dst):
        try:
            s, d = _resolve(src), _resolve(dst)
            if d.is_dir():
                d = d / s.name
            shutil.move(str(s), str(d))
            return {"ok": True, "result": "Moved to %s" % d}
        except Exception as exc:
            return {"ok": False, "result": "Move failed: %s" % exc}

    def _file_delete(self, path):
        try:
            p = _resolve(path)
        except Exception as exc:
            return {"ok": False, "result": "Invalid path: %s" % exc}
        if _is_protected(p):
            return {"ok": False,
                    "result": "Refused: %s is a protected system path." % p}
        if not p.exists():
            return {"ok": False, "result": "Not found: %s" % p}
        if not self.confirm("Delete file",
                            "Delete this for real?\n%s" % p):
            return {"ok": False, "result": "Deletion cancelled by user."}
        # Recycle bin first when possible.
        try:
            import send2trash  # noqa: F401  (optional, lazy)
            from send2trash import send2trash
            send2trash(str(p))
            return {"ok": True, "result": "Moved to recycle bin: %s" % p}
        except Exception:
            pass
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"ok": True, "result": "Deleted permanently: %s" % p}
        except Exception as exc:
            return {"ok": False, "result": "Delete failed: %s" % exc}

    # ----------------------------------------------------------------- apps
    def _app_launch(self, target):
        if sys.platform != "win32":
            return {"ok": False,
                    "result": "App launch is Windows-only."}
        try:
            os.startfile(os.path.expandvars(os.path.expanduser(target)))  # noqa
            return {"ok": True, "result": "Launched: %s" % target}
        except Exception as exc:
            return {"ok": False, "result": "Launch failed: %s" % exc}

    def _app_close(self, name):
        if sys.platform != "win32":
            return {"ok": False,
                    "result": "App close is Windows-only."}
        if not self.confirm("Close program",
                            "Force-close %s? Unsaved work will be lost."
                            % name):
            return {"ok": False, "result": "Close cancelled by user."}
        try:
            subprocess.run(["taskkill", "/IM", str(name), "/F"],
                           capture_output=True, timeout=15)
            return {"ok": True, "result": "Closed: %s" % name}
        except Exception as exc:
            return {"ok": False, "result": "Close failed: %s" % exc}

    # ---------------------------------------------------------------- system
    def _sys_shutdown(self):
        if sys.platform != "win32":
            return {"ok": False,
                    "result": "Shutdown control is Windows-only."}
        if not self.confirm("Shut down",
                            "Shut down the PC in 30 seconds?"):
            return {"ok": False, "result": "Shutdown cancelled by user."}
        try:
            subprocess.run(["shutdown", "/s", "/t", "30"],
                           capture_output=True, timeout=15)
            return {"ok": True, "result": "Shutting down in 30 seconds."}
        except Exception as exc:
            return {"ok": False, "result": "Shutdown failed: %s" % exc}

    def _sys_restart(self):
        if sys.platform != "win32":
            return {"ok": False,
                    "result": "Restart control is Windows-only."}
        if not self.confirm("Restart",
                            "Restart the PC in 30 seconds?"):
            return {"ok": False, "result": "Restart cancelled by user."}
        try:
            subprocess.run(["shutdown", "/r", "/t", "30"],
                           capture_output=True, timeout=15)
            return {"ok": True, "result": "Restarting in 30 seconds."}
        except Exception as exc:
            return {"ok": False, "result": "Restart failed: %s" % exc}

    def _sys_sleep(self):
        if sys.platform != "win32":
            return {"ok": False,
                    "result": "Sleep control is Windows-only."}
        if not self.confirm("Sleep", "Put the PC to sleep now?"):
            return {"ok": False, "result": "Sleep cancelled by user."}
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState",
                            "0,1,0"], capture_output=True, timeout=15)
            return {"ok": True, "result": "Sleeping."}
        except Exception as exc:
            return {"ok": False, "result": "Sleep failed: %s" % exc}

    def _sys_lock(self):
        if sys.platform != "win32":
            return {"ok": False,
                    "result": "Lock is Windows-only."}
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"],
                           capture_output=True, timeout=15)
            return {"ok": True, "result": "Workstation locked."}
        except Exception as exc:
            return {"ok": False, "result": "Lock failed: %s" % exc}

    # ------------------------------------------------------------------- web
    def _web_search(self, query, n=5):
        try:
            count = max(1, min(20, int(n)))
        except (TypeError, ValueError):
            count = 5
        try:
            url = ("https://html.duckduckgo.com/html/?q="
                   + urllib.parse.quote(str(query)))
            req = urllib.request.Request(
                url,
                headers={"User-Agent":
                         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0 Safari/537.36"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            results = re.findall(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL)
            if not results:
                return {"ok": False,
                        "result": "No results found for: %s" % query}
            lines = []
            for i, (link, title) in enumerate(results[:count], 1):
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                lines.append("%d. %s\n   %s" % (i, clean_title, link))
            return {"ok": True, "result": "\n".join(lines)}
        except Exception as exc:
            return {"ok": False, "result": "Web search failed: %s" % exc}

    # ------------------------------------------------------------ memory-ish
    def _memory(self):
        # Local import to avoid a cycle at module load.
        from memory import Memory
        return Memory()

    def _remember(self, key, value):
        try:
            self._memory().add_fact(key, value)
            return {"ok": True, "result": "Remembered: %s" % key}
        except Exception as exc:
            return {"ok": False, "result": "Remember failed: %s" % exc}

    def _recall(self, key):
        try:
            val = self._memory().get_fact(key)
            if val is None:
                return {"ok": False,
                        "result": "I don't remember anything about '%s'." % key}
            return {"ok": True, "result": "%s = %s" % (key, val)}
        except Exception as exc:
            return {"ok": False, "result": "Recall failed: %s" % exc}

    def _add_objective(self, title, tag="WORK"):
        try:
            oid = self._memory().add_objective(title, tag=tag)
            return {"ok": True,
                    "result": "Objective #%d added (%s): %s" % (oid, tag, title)}
        except Exception as exc:
            return {"ok": False, "result": "Add objective failed: %s" % exc}

    def _add_reminder(self, text, minutes_from_now=60):
        try:
            mins = float(minutes_from_now)
        except (TypeError, ValueError):
            mins = 60
        try:
            rid = self._memory().add_reminder(
                text, time.time() + mins * 60)
            return {"ok": True,
                    "result": "Reminder #%d set for %.0f minutes from now: %s"
                              % (rid, mins, text)}
        except Exception as exc:
            return {"ok": False, "result": "Add reminder failed: %s" % exc}
