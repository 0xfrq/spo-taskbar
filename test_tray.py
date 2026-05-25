import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
hTaskbar = user32.FindWindowW("Shell_TrayWnd", None)
if hTaskbar:
    hTrayNotify = user32.FindWindowExW(hTaskbar, None, "TrayNotifyWnd", None)
    if hTrayNotify:
        rect = wintypes.RECT()
        user32.GetWindowRect(hTrayNotify, ctypes.byref(rect))
        print("TrayNotifyWnd left:", rect.left)
        
        taskbar_rect = wintypes.RECT()
        user32.GetWindowRect(hTaskbar, ctypes.byref(taskbar_rect))
        print("Taskbar right:", taskbar_rect.right)
