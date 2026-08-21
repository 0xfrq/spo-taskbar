@echo off
echo Running single-instance validation checks...
python test_single_instance.py
if %errorlevel% neq 0 (
    echo.
    echo Single-instance configuration tests failed. Aborting build.
    exit /b %errorlevel%
)

echo Building Standalone Executable (Version 2) without Visual Studio...

python -m pip install pyinstaller
python -m pip install -r requirements.txt
python -m PyInstaller --noconsole --onefile --name LyricsTaskbarV2 mainv2.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed. Make sure Python is installed.
    exit /b %errorlevel%
)

echo Build succeeded! Run dist\LyricsTaskbarV2.exe
