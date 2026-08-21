@echo off
echo Building Standalone Executable without Visual Studio...

python -m pip install pyinstaller
python -m PyInstaller --noconsole --onefile --name LyricsTaskbar main.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed. Make sure Python is installed.
    exit /b %errorlevel%
)

echo Build succeeded! Run dist\LyricsTaskbar.exe
