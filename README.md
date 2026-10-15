# Vicky Talk

Vicky Talk is a **free** Jarvis-style AI assistant for Windows 10/11. It runs a
hybrid brain: a free local model (Ollama, on-device, zero cost, works offline)
by default, with an optional smarter mode using your own API key
(OpenAI / Anthropic / any OpenAI-compatible endpoint). The app has a voice
command center, an agent view, notes/objectives, and brain settings — all in a
dark + gold premium theme.

## Requirements

- Windows 10/11 (64-bit)
- Python 3.11+
- [Ollama](https://ollama.com) installed and running (for the free local brain)

## Quick start

1. Install Ollama from https://ollama.com and start it.
2. Pull a local model: `ollama pull llama-8b-q4`
   — if that tag is unavailable (e.g. renamed upstream), pull another one such
   as `ollama pull llama3.1:8b` and select it in Vicky Talk's **Brain** settings.
3. In the `app/` folder, double-click `build_exe.bat` (one-command build).
4. Launch `dist\VickyTalk\VickyTalk.exe`.

The free local brain works out of the box after step 2 — no API key needed.

## Rename

The app name lives in one place: `APP_NAME` in `app_name.py`. Edit that single
line and rebuild to rename the app everywhere (window title, dialogs, etc.).

## Project structure

- `app_name.py` — `APP_NAME` constant (rename the app here)
- `main.py` — main window: top bar + 4 views + brain/tool/reminder wiring
- `theme.py` — dark + gold theme definition and application
- `brain.py` — hybrid LLM layer (free local Ollama / user API key)
- `tools.py` — PC tool dispatcher (open apps, files, notifications, …)
- `memory.py` — local SQLite memory (stays on the PC)
- `tts.py` — text-to-speech voice (pyttsx3)
- `reminders.py` — background reminder service
- `stt.py` — voice input (offline faster-whisper, needs `pip install faster-whisper sounddevice`)
- `ui/orb.py` — voice orb widget
- `ui/command_center.py` — command center view (chat + controls)
- `ui/agent_view.py` — agent activity view
- `ui/notes_view.py` — notes / objectives view
- `ui/brain_view.py` — brain settings view (local / API mode)
- `ui/setup_wizard.py` — first-run wizard (Ollama install + model download)

## Notes

- **API key is NOT persisted — re-enter it each launch, by design.** The key is
  never written to disk; it lives only in memory for the session.
- **Voice input is real (offline).** Click the mic button and speak (6s) —
  transcribed locally with faster-whisper `tiny.en` (~75MB, downloaded once
  to `~/.vickytalk/models/`). Requires `pip install faster-whisper sounddevice`;
  without them the mic button stays disabled and typing is the input.
- **Local mode sends nothing off-PC.** All personal data stays in the local
  SQLite database; API mode sends only your chat messages to the provider you
  configured.
- The Windows EXE must be built on a Windows PC (PyInstaller cannot produce a
  Windows EXE from Linux).
