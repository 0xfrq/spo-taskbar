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
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus
import pystray
from PIL import Image, ImageDraw

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
                self.lrc_lines = [(0, "♪ (Network error)")]
        except Exception as e:
            print("Error fetching lyrics:", e)
            self.lrc_lines = [(0, "♪ (Network error)")]
            
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

    image = Image.new('RGB', (64, 64), color = (30, 215, 96)) 
    d = ImageDraw.Draw(image)
    d.text((16, 24), "LM", fill=(255, 255, 255))
    
    menu = pystray.Menu(pystray.MenuItem('Quit', on_quit))
    icon = pystray.Icon("LyricsTaskbar", image, "Lyrics Taskbar", menu)
    icon.run()

async def media_poll_loop():
    try:
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    except Exception as e:
        print("Could not get media manager:", e)
        return

    last_track = None
    last_artist = None

    while not state.quit_flag:
        try:
            session = manager.get_current_session()
            if session:
                info = await session.try_get_media_properties_async()
                title = info.title
                artist = info.artist
                
                timeline = session.get_timeline_properties()
                playback = session.get_playback_info()
                position_sec = timeline.position.total_seconds()
                
                if playback and playback.playback_status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    elapsed = now - timeline.last_updated_time
                    position_sec += elapsed.total_seconds()
                
                duration_sec = timeline.end_time.total_seconds()
                
                if title != last_track or artist != last_artist:
                    last_track = title
                    last_artist = artist
                    threading.Thread(target=fetcher.fetch_lyrics, args=(title, artist, duration_sec), daemon=True).start()
                
                text = fetcher.get_current_line(position_sec)
                if not text:
                    text = f"♪ {title} - {artist}"
                state.lyric_text = text
            else:
                state.lyric_text = "♪ No media playing"
                last_track = None
                last_artist = None
        except Exception as e:
            pass
        await asyncio.sleep(0.1)

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
    tray_thread = threading.Thread(target=create_tray_icon, daemon=True)
    tray_thread.start()
    
    async_thread = threading.Thread(target=run_async_loop, daemon=True)
    async_thread.start()
    
    main_gui()
