# -*- coding: utf-8 -*-
"""Vicky Talk reminder background service.

ReminderService polls Memory for due reminders every 30 seconds on a daemon
thread and fires the UI-supplied on_due(reminder_dict) callback for each,
then marks it done. stdlib only.
"""

import threading
import time


class ReminderService:
    """Background poller for due reminders.

    memory  — a memory.Memory instance
    on_due  — callable(reminder_dict) -> None (UI supplies the notifier)
    """

    def __init__(self, memory, on_due):
        self._memory = memory
        self._on_due = on_due
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the daemon polling thread. Idempotent."""
        if self._thread and self._thread.is_alive():
            return

        def _loop():
            while not self._stop_event.wait(30):
                try:
                    due = self._memory.due_reminders(time.time())
                except Exception:
                    continue
                for rem in due:
                    try:
                        self._on_due(rem)
                    except Exception:
                        pass
                    try:
                        self._memory.mark_reminder_done(rem["id"])
                    except Exception:
                        pass

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
