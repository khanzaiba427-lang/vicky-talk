# -*- mode: python ; coding: utf-8 -*-
"""Vicky Talk - PyInstaller one-dir build spec for Windows 10/11.

Run from the app/ folder with:  pyinstaller app.spec --noconfirm
Result:  dist/VickyTalk/VickyTalk.exe

NOTE: icon=None (no app icon yet). When you have an .ico file, add it with:
    icon="assets\\vickytalk.ico"
in the EXE(...) block below.
"""

# Import this so the frozen exe carries the same display name as the source.
# (SPECPATH is injected by PyInstaller when it executes this spec file;
# without it, the spec's own folder isn't on sys.path.)
import os
import sys

try:
    sys.path.insert(0, SPECPATH)
    from app_name import APP_NAME  # noqa: F401
except Exception:
    APP_NAME = "Vicky Talk"  # fallback: keep in sync with app_name.py


def _sounddevice_datas():
    """Bundle PortAudio (loaded at runtime via cffi — invisible to PyInstaller).

    Guarded: returns [] when sounddevice isn't installed, so the spec never
    breaks a build on machines without the optional voice-input deps.
    """
    try:
        import os
        import sounddevice
        data_dir = os.path.join(
            os.path.dirname(sounddevice.__file__), "_sounddevice_data")
        if os.path.isdir(data_dir):
            return [(data_dir, os.path.join("sounddevice", "_sounddevice_data"))]
    except Exception:
        pass
    return []


a = Analysis(
    ["main.py"],                      # entry point
    pathex=["."],                     # app/ is the project root for imports
    binaries=[],
    datas=_sounddevice_datas(),
    hiddenimports=[
        # ollama + requests are imported lazily inside brain.py — PyInstaller
        # cannot see them statically, so list them explicitly.
        "ollama",
        "requests",
        # pyttsx3 is imported lazily inside tts.py.
        "pyttsx3",
        # pyttsx3's Windows (SAPI5) backend needs pywin32's COM modules.
        "win32com",
        "win32com.client",
        "pythoncom",
        "pywintypes",
        # plyer is optional in tools.py; pin the Windows notification backend
        # so the frozen build does not drop it.
        "plyer.platforms.win.notification",
        # faster-whisper pulls ctranslate2 (native); both are imported at the
        # top of stt.py but listed here explicitly for frozen builds.
        "faster_whisper",
        "ctranslate2",
        # sounddevice is imported at the top of stt.py; listed explicitly
        # for frozen builds.
        "sounddevice",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VickyTalk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                    # windowed app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                        # <- put "assets\\vickytalk.ico" here when you have one
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VickyTalk",
)
