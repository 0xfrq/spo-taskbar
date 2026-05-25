# Lyrics Taskbar (Windows Version)

A lightweight Windows tool that shows time-synced lyrics for the song currently playing in **Spotify** or any other media player that uses Windows Media Controls. It displays the lyrics directly as an overlay on your Windows Taskbar.

This repository contains two versions:
1. **Python Version (Recommended, easy to run)**
2. **C++ Native Version (For zero-dependency deployment)**

## Python Version (main.py)

### Requirements
- Windows 10/11
- Python 3.11+ 

### Installation & Run
1. Install Python (make sure to check "Add Python to PATH" during installation).
2. Open a terminal in this directory and install the dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
3. Run the application:
   ```cmd
   run.bat
   ```
*(Or simply run `python main.py`)*. This version includes a system tray icon (labeled "LM") to easily quit the app.

---

## C++ Native Version (main.cpp)

This is a pure C++ implementation. However, because it hooks directly into modern Windows SDK APIs (`C++/WinRT`), **it fundamentally requires Microsoft Visual Studio** to compile. MinGW/GCC cannot compile WinRT headers natively.

If you don't have Visual Studio installed, don't worry! I have provided a way to build a completely standalone `.exe` using Python instead:

### Building a Standalone Executable (No VS Required)
You can use the included `build_standalone.bat` script to package the Python version into a single, zero-dependency `.exe` file using `PyInstaller`.
1. Make sure Python is installed.
2. Run `build_standalone.bat`.
3. It will generate a standalone `LyricsTaskbar.exe` in the `dist/` folder which you can use forever without needing Python or Visual Studio installed!
### Compiling C++ (If you install Visual Studio)
1. Open a **Developer Command Prompt for VS**.
2. Run `cl.exe /EHsc /std:c++17 /W4 main.cpp /link /SUBSYSTEM:WINDOWS /OUT:LyricsTaskbar.exe`
3. This will output a native `LyricsTaskbar.exe`.

---

## How It Works

- Uses the Windows `GlobalSystemMediaTransportControlsSessionManager` to natively get the current track, artist, and playback position.
- Fetches time-synced LRC files from [lrclib.net](https://lrclib.net).
- Creates a transparent, borderless overlay right on top of your Windows Taskbar that updates seamlessly.
