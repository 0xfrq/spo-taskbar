import sys
import threading
import asyncio
import time
import datetime
import urllib.request
import urllib.parse
import json
import re
import tkinter as tk
import ctypes
from ctypes import wintypes
# Attempt to import winsdk for media control. If unavailable (e.g., on non‑Windows or missing package), provide lightweight stubs so the rest of the app continues to run.
try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus,
    )
except Exception:  # pragma: no cover – environment without winsdk
    class _DummySession:
        """A minimal session object that mimics the attributes we query.
        It never reports a playing track, keeping the UI in a safe idle state.
        """
        def __init__(self):
            pass
        def get_playback_info(self):
            return None
        def get_timeline_properties(self):
            class _Timeline:
                position = type('Pos', (), {'total_seconds': lambda: 0})()
                end_time = type('End', (), {'total_seconds': lambda: 0})()
                last_updated_time = None
            return _Timeline()
        async def try_get_media_properties_async(self):
            class _Info:
                title = ""
                artist = ""
            return _Info()
    class GlobalSystemMediaTransportControlsSessionManager:
        @staticmethod
        async def request_async():
            # Return a dummy manager with no sessions.
            class _DummyManager:
                def get_current_session(self):
                    return None
                def get_sessions(self):
                    return []
            return _DummyManager()
    class GlobalSystemMediaTransportControlsSessionPlaybackStatus:
        PLAYING = 1


import pystray
from PIL import Image, ImageDraw
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_WORKFLOW = os.getenv("GITHUB_WORKFLOW")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")

def trigger_github_workflow(title, artist):
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        print("GitHub env vars not set, skipping workflow trigger.")
        return
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
        payload = json.dumps({
    "ref": GITHUB_BRANCH
}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"GitHub workflow triggered: {resp.status} for '{title}' by {artist}")
    except urllib.error.HTTPError as e:
        print(f"GitHub workflow trigger failed: {e.code} - {e.read().decode()}")
    except Exception as e:
        print(f"GitHub workflow trigger error: {e}")

# List of supported music application IDs (substring match)
SUPPORTED_MUSIC_APPS = [
    "Spotify",        # Spotify (Desktop & Windows Store)
    "AppleMusic",     # Apple Music
]

def is_music_app(source_id: str) -> bool:
    """Checks if the given source ID matches any supported music app."""
    if not source_id:
        return False
    return any(app.lower() in source_id.lower() for app in SUPPORTED_MUSIC_APPS)

async def find_active_music_session(manager):
    """
    Finds the most relevant music session.
    Priority:
    1. Any music app session that is currently PLAYING
    2. Any music app session found (fallback)
    3. Any session with title/artist that looks like music
    """
    try:
        sessions = manager.get_sessions()

        # 1. Look for a PLAYING music app session
        for s in sessions:
            source_id = getattr(s, "source_app_user_model_id", "") or getattr(s, "source_app_id", "")
            if is_music_app(source_id):
                playback = s.get_playback_info()
                if playback and playback.playback_status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                    return s

        # 2. Fallback: any music app session (even if paused)
        for s in sessions:
            source_id = getattr(s, "source_app_user_model_id", "") or getattr(s, "source_app_id", "")
            if is_music_app(source_id):
                return s
        # 3. Last resort: any session with valid title/artist while playing
        for s in sessions:
            playback = s.get_playback_info()
            if playback and playback.playback_status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                try:
                    info = await s.try_get_media_properties_async()
                    title = getattr(info, "title", "")
                    artist = getattr(info, "artist", "")
                    if title and artist:
                        return s
                except Exception:
                    pass
    except Exception as e:
        # Silently ignore session errors
        pass
    return None

class LyricsFetcher:
    def __init__(self):
        self.current_track = None
        self.current_artist = None
        self.lrc_lines = []
        self.loading = False
    
    def fetch_lyrics(self, track, artist, duration_sec=None):
        self.loading = True
        self.current_track = track
        self.current_artist = artist
        self.lrc_lines = []
        
        try:
            params = {'track_name': track, 'artist_name': artist}
            if duration_sec:
                params['duration'] = int(duration_sec)
            
            qs = urllib.parse.urlencode(params)
            url = f"https://lrclib.net/api/get?{qs}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'LyricsTaskbar/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data and 'syncedLyrics' in data and data['syncedLyrics']:
                        self.lrc_lines = self.parse_lrc(data['syncedLyrics'])
                    elif data and 'plainLyrics' in data and data['plainLyrics']:
                        self.lrc_lines = [(0, "♪ (Plain lyrics only)")]
                    else:
                        self.lrc_lines = [(0, "♪ (No lyrics found)")]
                else:
                    self.lrc_lines = [(0, "♪ (No lyrics found)")]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.lrc_lines = [(0, "♪ (No lyrics found)")]
            else:
                self.lrc_lines = []
        except Exception as e:
            print("Error fetching lyrics:", e)
            self.lrc_lines = []
            
        self.loading = False

    def parse_lrc(self, lrc_text):
        lines = []
        for line in lrc_text.split('\n'):
            match = re.match(r'\[(\d+):(\d+\.\d+|\d+)\](.*)', line)
            if match:
                m = int(match.group(1))
                s = float(match.group(2))
                text = match.group(3).strip()
                if text: 
                    time_sec = m * 60 + s
                    lines.append((time_sec, text))
        return lines

    def get_current_line(self, current_time_sec, offset_sec=0.0):
        current_time_sec += offset_sec
        if self.loading:
            return "Loading lyrics..."
        if not self.lrc_lines:
            return ""
        
        current_line = ""
        for time_sec, text in self.lrc_lines:
            if current_time_sec >= time_sec:
                current_line = text
            else:
                break
        return current_line

class AppState:
    def __init__(self):
        self.lyric_text = "Waiting for media..."
        self.quit_flag = False

state = AppState()
fetcher = LyricsFetcher()

def create_tray_icon():
    def on_quit(icon, item):
        state.quit_flag = True
        icon.stop()

    image = Image.new('RGB', (64, 64), color=(30, 215, 96)) 
    d = ImageDraw.Draw(image)
    d.text((16, 24), "LM", fill=(255, 255, 255))
    
    menu = pystray.Menu(pystray.MenuItem('Quit', on_quit))
    icon = pystray.Icon("LyricsTaskbar", image, "Lyrics Taskbar", menu)
    icon.run()

async def media_poll_loop():
    try:
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        print("Media manager initialized successfully")
    except Exception as e:
        print("Could not get media manager:", e)
        return

    last_track = None
    last_artist = None

    while not state.quit_flag:
        try:
            session = await find_active_music_session(manager)
            if session:
                info = await session.try_get_media_properties_async()
                title = getattr(info, "title", "")
                artist = getattr(info, "artist", "")

                timeline = session.get_timeline_properties()
                playback = session.get_playback_info()
                position_sec = timeline.position.total_seconds()

                if playback and playback.playback_status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    elapsed = now - timeline.last_updated_time
                    position_sec += elapsed.total_seconds()

                duration_sec = timeline.end_time.total_seconds()

                if (title != last_track or artist != last_artist) and title and artist:
                    last_track = title
                    last_artist = artist
                    threading.Thread(target=fetcher.fetch_lyrics, args=(title, artist, duration_sec), daemon=True).start()

                    if supabase_client:
                        def publish_to_supabase(t, a):
                            try:
                                supabase_client.table("now_playing").insert({
                                    "song_name": t,
                                    "artist_name": a
                                }).execute()
                                print(f"Published to Supabase: {t} by {a}")
                            except Exception as e:
                                print(f"Error publishing to Supabase: {e}")
                        threading.Thread(target=publish_to_supabase, args=(title, artist), daemon=True).start()

                    threading.Thread(target=trigger_github_workflow, args=(title, artist), daemon=True).start()

                text = fetcher.get_current_line(position_sec)
                if not text:
                    text = f"♪ {title} - {artist}" if title else "♪ No media playing"
                state.lyric_text = text
            else:
                state.lyric_text = "♪ No media playing"
                last_track = None
                last_artist = None
        except Exception as e:
            print(f"Error in poll loop: {e}")
        await asyncio.sleep(0.5)

def run_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(media_poll_loop())

def main_gui():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "black")
    root.config(bg="black")
    
    label = tk.Label(root, text="♪ Starting...", font=("Segoe UI", 11, "bold"), fg="white", bg="black")
    label.pack(padx=10, pady=2)
    
    user32 = ctypes.windll.user32
    
    def update_ui():
        if state.quit_flag:
            root.destroy()
            return
            
        label.config(text=state.lyric_text)
        
        hTaskbar = user32.FindWindowW("Shell_TrayWnd", None)
        if hTaskbar:
            rect = wintypes.RECT()
            user32.GetWindowRect(hTaskbar, ctypes.byref(rect))
            
            root.update_idletasks()
            w = root.winfo_reqwidth()
            h = root.winfo_reqheight()
            
            hTrayNotify = user32.FindWindowExW(hTaskbar, None, "TrayNotifyWnd", None)
            if hTrayNotify:
                tray_rect = wintypes.RECT()
                user32.GetWindowRect(hTrayNotify, ctypes.byref(tray_rect))
                x = tray_rect.left - w - 20
            else:
                x = rect.right - w - 350 
                
            y = rect.top + (rect.bottom - rect.top - h) // 2
            
            root.geometry(f"{w}x{h}+{x}+{y}")
            root.lift()
            
        root.after(50, update_ui)
        
    update_ui()
    root.mainloop()

if __name__ == "__main__":
    # Prevent multiple instances using a named system mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Local\\LyricsTaskbarMutex")
    if not _mutex or ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS = 183
        sys.exit(0)

    tray_thread = threading.Thread(target=create_tray_icon, daemon=True)
    tray_thread.start()
    
    async_thread = threading.Thread(target=run_async_loop, daemon=True)
    async_thread.start()
    
    main_gui()
