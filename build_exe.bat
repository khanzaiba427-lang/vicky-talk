@echo off
setlocal
cd /d "%~dp0"

echo [1/5] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python not found in PATH.
  echo Install Python 3.11+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

echo [2/5] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  pause
  exit /b 1
)

echo [3/5] Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: dependency install failed.
  pause
  exit /b 1
)

echo [4/5] Installing PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
  echo ERROR: PyInstaller install failed.
  pause
  exit /b 1
)

echo [5/5] Building EXE...
pyinstaller app.spec --noconfirm
if errorlevel 1 (
  echo ERROR: PyInstaller build failed.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  Build finished. Launch the app at:
echo    dist\VickyTalk\VickyTalk.exe
echo ============================================================
pause
