# Lyrics Taskbar

Lyrics Taskbar is a lightweight Windows utility that displays time-synced lyrics for the track currently playing in Spotify or another player supported by Windows Media Controls.

![Lyrics Taskbar architecture](spo-taskbar-architecture.svg)

## Features

- Reads the active media session through Windows Media Controls.
- Fetches synchronized .lrc lyrics from [LRCLIB](https://lrclib.net).
- Displays lyrics in a transparent taskbar overlay.
- Supports a system-tray menu for quickly exiting the app.
- Includes Python and native C++ implementations.

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer for the Python implementation

Install dependencies:

`powershell
python -m pip install -r requirements.txt
```
Run the recommended implementation:

`powershell
python main.py
```
mainv2.py is an alternative implementation for v2 behavior testing.

## Configuration

Optional integrations read settings from a local .env file. Start from the template:

`powershell
Copy-Item .env.example .env
```
Keep real credentials local and never commit .env or publish its contents.

## Building

Create a standalone Python executable with PyInstaller:

`powershell
./build_standalone.bat
```
Build output is written to dist/ and ignored by Git.

The native C++ implementation requires Visual Studio with C++/WinRT support:

`cmd
cl.exe /EHsc /std:c++17 /W4 main.cpp /link /SUBSYSTEM:WINDOWS /OUT:LyricsTaskbar.exe
```
## Tests

Run the maintained smoke tests with:

`powershell
python -m pytest
```
## Project layout

| Path | Purpose |
| --- | --- |
| main.py | Recommended Python implementation |
| mainv2.py | Alternative Python implementation |
| main.cpp | Native Windows implementation |
|
equirements.txt | Python dependencies |
| LyricsTaskbar*.spec | PyInstaller specifications |
| spo-taskbar-architecture.svg | Architecture diagram |

## License

No license has been declared yet. Add one before distributing the project publicly.
