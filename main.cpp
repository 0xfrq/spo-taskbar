#include <windows.h>
#include <wininet.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Media.Control.h>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <regex>
#include <iostream>

#pragma comment(lib, "windowsapp")
#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

using namespace winrt;
using namespace Windows::Media::Control;

struct LyricLine {
    double timeSec;
    std::wstring text;
};

std::wstring g_currentLyric = L"♪ Waiting for media...";
std::vector<LyricLine> g_lrcLines;
std::wstring g_currentTrack = L"";
std::wstring g_currentArtist = L"";
std::mutex g_mutex;
bool g_loading = false;

std::wstring Utf8ToUtf16(const std::string& utf8) {
    if (utf8.empty()) return std::wstring();
    int size = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, nullptr, 0);
    std::wstring utf16(size, 0);
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, &utf16[0], size);
    return utf16;
}

std::string UrlEncode(const std::string& value) {
    std::string escaped;
    for (char c : value) {
        if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
            escaped += c;
        } else {
            char buf[4];
            snprintf(buf, sizeof(buf), "%%%02X", (unsigned char)c);
            escaped += buf;
        }
    }
    return escaped;
}

std::string FetchUrl(const std::string& url) {
    HINTERNET hInternet = InternetOpenA("LyricsTaskbar/1.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) return "";

    HINTERNET hUrl = InternetOpenUrlA(hInternet, url.c_str(), NULL, 0, INTERNET_FLAG_RELOAD, 0);
    if (!hUrl) {
        InternetCloseHandle(hInternet);
        return "";
    }

    std::string response;
    char buffer[4096];
    DWORD bytesRead = 0;
    while (InternetReadFile(hUrl, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        response.append(buffer, bytesRead);
    }

    InternetCloseHandle(hUrl);
    InternetCloseHandle(hInternet);
    return response;
}

std::string ExtractJsonField(const std::string& json, const std::string& field) {
    std::string key = "\"" + field + "\":";
    size_t pos = json.find(key);
    if (pos == std::string::npos) return "";
    pos += key.length();

    while (pos < json.length() && isspace(json[pos])) pos++;

    if (json[pos] == '\"') {
        pos++; 
        std::string val;
        while (pos < json.length()) {
            if (json[pos] == '\\' && pos + 1 < json.length()) {
                if (json[pos+1] == 'n') val += '\n';
                else if (json[pos+1] == 'r') val += '\r';
                else if (json[pos+1] == '\"') val += '\"';
                else if (json[pos+1] == '\\') val += '\\';
                pos += 2;
            } else if (json[pos] == '\"') {
                break;
            } else {
                val += json[pos];
                pos++;
            }
        }
        return val;
    }
    return "";
}

void FetchLyricsThread(std::string track, std::string artist, int durationSec) {
    std::lock_guard<std::mutex> lock(g_mutex);
    g_loading = true;
    g_lrcLines.clear();
    g_currentLyric = L"Loading lyrics...";

    std::string url = "https://lrclib.net/api/get?track_name=" + UrlEncode(track) + "&artist_name=" + UrlEncode(artist);
    if (durationSec > 0) {
        url += "&duration=" + std::to_string(durationSec);
    }

    std::string response = FetchUrl(url);
    
    std::string synced = ExtractJsonField(response, "syncedLyrics");
    if (!synced.empty()) {
        std::vector<LyricLine> lines;
        std::istringstream iss(synced);
        std::string line;
        std::regex re(R"(\[(\d+):(\d+\.\d+|\d+)\](.*))");
        while (std::getline(iss, line)) {
            std::smatch match;
            if (std::regex_match(line, match, re)) {
                int m = std::stoi(match[1]);
                double s = std::stod(match[2]);
                std::string text = match[3];
                text.erase(0, text.find_first_not_of(" \t\r\n"));
                text.erase(text.find_last_not_of(" \t\r\n") + 1);
                
                if (!text.empty()) {
                    lines.push_back({ m * 60.0 + s, Utf8ToUtf16(text) });
                }
            }
        }
        g_lrcLines = lines;
    } else {
        std::string plain = ExtractJsonField(response, "plainLyrics");
        if (!plain.empty()) {
            g_lrcLines.push_back({0.0, L"♪ (Plain lyrics only)"});
        } else {
            g_lrcLines.push_back({0.0, L"♪ (No lyrics found)"});
        }
    }
    g_loading = false;
}

LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    static HBRUSH hBrushBlack = CreateSolidBrush(RGB(0, 0, 0));
    
    switch (uMsg) {
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        
        RECT rect;
        GetClientRect(hwnd, &rect);
        FillRect(hdc, &rect, hBrushBlack);
        
        SetBkMode(hdc, TRANSPARENT);
        SetTextColor(hdc, RGB(255, 255, 255));
        
        HFONT hFont = CreateFontW(18, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_OUTLINE_PRECIS,
            CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, VARIABLE_PITCH, L"Segoe UI");
        HFONT hOldFont = (HFONT)SelectObject(hdc, hFont);
        
        std::lock_guard<std::mutex> lock(g_mutex);
        DrawTextW(hdc, g_currentLyric.c_str(), -1, &rect, DT_LEFT | DT_VCENTER | DT_SINGLELINE);
        
        SelectObject(hdc, hOldFont);
        DeleteObject(hFont);
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_TIMER: {
        try {
            auto manager = GlobalSystemMediaTransportControlsSessionManager::RequestAsync().get();
            auto session = manager.GetCurrentSession();
            if (session) {
                auto props = session.TryGetMediaPropertiesAsync().get();
                auto timeline = session.GetTimelineProperties();
                
                std::wstring title = props.Title().c_str();
                std::wstring artist = props.Artist().c_str();
                double posSec = (double)timeline.Position().count() / 10000000.0; 
                double durSec = (double)timeline.EndTime().count() / 10000000.0;
                
                if (title != g_currentTrack || artist != g_currentArtist) {
                    g_currentTrack = title;
                    g_currentArtist = artist;
                    
                    int utf8Size = WideCharToMultiByte(CP_UTF8, 0, title.c_str(), -1, nullptr, 0, nullptr, nullptr);
                    std::string u8Title(utf8Size, 0);
                    WideCharToMultiByte(CP_UTF8, 0, title.c_str(), -1, &u8Title[0], utf8Size, nullptr, nullptr);
                    
                    utf8Size = WideCharToMultiByte(CP_UTF8, 0, artist.c_str(), -1, nullptr, 0, nullptr, nullptr);
                    std::string u8Artist(utf8Size, 0);
                    WideCharToMultiByte(CP_UTF8, 0, artist.c_str(), -1, &u8Artist[0], utf8Size, nullptr, nullptr);
                    
                    std::thread(FetchLyricsThread, u8Title, u8Artist, (int)durSec).detach();
                }
                
                std::lock_guard<std::mutex> lock(g_mutex);
                if (!g_loading && !g_lrcLines.empty()) {
                    std::wstring currentLine = g_lrcLines[0].text;
                    for (const auto& line : g_lrcLines) {
                        if (posSec >= line.timeSec) currentLine = line.text;
                        else break;
                    }
                    g_currentLyric = currentLine;
                } else if (!g_loading) {
                    g_currentLyric = L"♪ " + title + L" - " + artist;
                }
            } else {
                std::lock_guard<std::mutex> lock(g_mutex);
                g_currentLyric = L"♪ No media playing";
                g_currentTrack = L"";
                g_currentArtist = L"";
            }
        } catch (...) {
        }
        
        HWND hTaskbar = FindWindowW(L"Shell_TrayWnd", NULL);
        if (hTaskbar) {
            RECT taskbarRect;
            GetWindowRect(hTaskbar, &taskbarRect);
            
            int w = 500;
            int h = 30;
            int x = taskbarRect.right - w - 400; 
            
            HWND hTrayNotify = FindWindowExW(hTaskbar, NULL, L"TrayNotifyWnd", NULL);
            if (hTrayNotify) {
                RECT trayRect;
                GetWindowRect(hTrayNotify, &trayRect);
                x = trayRect.left - w - 20; 
            }
            
            int y = taskbarRect.top + (taskbarRect.bottom - taskbarRect.top - h) / 2;
            
            SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_NOACTIVATE);
        }
        
        InvalidateRect(hwnd, NULL, TRUE);
        return 0;
    }
    case WM_NCHITTEST:
        return HTTRANSPARENT; 
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    winrt::init_apartment();

    const wchar_t CLASS_NAME[] = L"LyricsTaskbarClass";
    
    WNDCLASSW wc = {};
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    
    RegisterClassW(&wc);
    
    HWND hwnd = CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
        CLASS_NAME, L"LyricsTaskbar",
        WS_POPUP,
        0, 0, 500, 30,
        NULL, NULL, hInstance, NULL
    );
    
    if (hwnd == NULL) return 0;
    
    SetLayeredWindowAttributes(hwnd, RGB(0, 0, 0), 0, LWA_COLORKEY);
    
    ShowWindow(hwnd, SW_SHOW);
    SetTimer(hwnd, 1, 100, NULL);
    
    MSG msg = {};
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    
    return 0;
}
