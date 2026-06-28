"""
Nova Task Executor — Phase 4
Handles all actions Nova can perform on the computer.
"""

import os
import subprocess
import webbrowser
import pyautogui
import pyperclip
import time
import json
import threading

# Safety — stop pyautogui if mouse hits corner
pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.3

# ─── APP NAME MAP ─────────────────────────────────────────────────────────────
# Common app names users might say → actual executable
APP_MAP = {
    'chrome':       'chrome',
    'google chrome':'chrome',
    'browser':      'chrome',
    'firefox':      'firefox',
    'edge':         'msedge',
    'notepad':      'notepad',
    'calculator':   'calc',
    'calendar':     'outlookcal:',
    'excel':        'excel',
    'word':         'winword',
    'powerpoint':   'powerpnt',
    'vs code':      'code',
    'vscode':       'code',
    'visual studio code': 'code',
    'file explorer':'explorer',
    'explorer':     'explorer',
    'task manager': 'taskmgr',
    'settings':     'ms-settings:',
    'paint':        'mspaint',
    'spotify':      'spotify',
    'discord':      'discord',
    'slack':        'slack',
    'zoom':         'zoom',
    'teams':        'teams',
    'terminal':     'cmd',
    'command prompt':'cmd',
    'powershell':   'powershell',
    'chrome':             None,  # handled by open_app smart logic below
    'google chrome':      None,
    'browser':            None,
}


# ─── TOOLS ────────────────────────────────────────────────────────────────────
def open_chrome_url(url):
    """Open URL in regular Chrome, not Beta or Edge."""
    import os, subprocess, webbrowser

    # Try regular Chrome paths in order
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.join(os.getenv('LOCALAPPDATA',''),
                     r'Google\Chrome\Application\chrome.exe'),
        os.path.join(os.getenv('PROGRAMFILES',''),
                     r'Google\Chrome\Application\chrome.exe'),
    ]

    for path in chrome_paths:
        if os.path.exists(path):
            subprocess.Popen([path, url])
            return True

    # Fallback to default browser
    webbrowser.open(url)
    return True

def open_app(app_name):
    """Open an application or website by name."""
    import os, webbrowser, subprocess

    name_lower = app_name.lower().strip()

    # ── Websites — open directly in browser ──
    websites = {
        'youtube': 'https://youtube.com',
        'google':  'https://google.com',
        'instagram': 'https://instagram.com',
        'facebook': 'https://facebook.com',
        'twitter': 'https://twitter.com',
        'reddit':  'https://reddit.com',
        'netflix': 'https://netflix.com',
        'gmail':   'https://mail.google.com',
        'whatsapp': 'https://web.whatsapp.com',
        'github':  'https://github.com',
        'maps':    'https://maps.google.com',
        'spotify': 'https://open.spotify.com',
    }
    if name_lower in websites:
        open_chrome_url(websites[name_lower])
        return f"Opened {app_name}!"

    # ── Chrome — find the real Chrome, not Beta ──
    if name_lower in ['chrome', 'google chrome', 'browser']:
        return open_chrome_url('https://www.google.com')

    # ── Known Windows apps ──
    win_apps = {
        'notepad':        'notepad',
        'calculator':     'calc',
        'file explorer':  'explorer',
        'file manager':   'explorer',
        'explorer':       'explorer',
        'paint':          'mspaint',
        'task manager':   'taskmgr',
        'settings':       'ms-settings:',
        'vs code':        'code',
        'vscode':         'code',
        'visual studio code': 'code',
        'cmd':            'cmd',
        'terminal':       'cmd',
        'powershell':     'powershell',
        'word':           'winword',
        'excel':          'excel',
        'powerpoint':     'powerpnt',
        'discord':        'discord',
        'slack':          'slack',
        'zoom':           'zoom',
    }
    if name_lower in win_apps:
        target = win_apps[name_lower]
        try:
            if target.endswith(':'): os.startfile(target)
            else: subprocess.Popen(target, shell=True)
            return f"Opened {app_name}!"
        except:
            pass

    # ── Looks like a website ──
    if any(ext in name_lower for ext in ['.com','.org','.net','.io','.co','.in','.tv','.ai']):
        open_chrome_url('https://' + name_lower)
        return f"Opened {app_name}!"

    # ── Try as executable ──
    try:
        subprocess.Popen(name_lower, shell=True)
        return f"Opened {app_name}!"
    except: pass

    # ── Last resort — Google it ──
    open_chrome_url(f'https://www.google.com/search?q={name_lower.replace(" ","+")}')
    return f"I searched Google for {app_name}!"


def web_search(query):
    """Search Google and open in default browser."""
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"I searched Google for {query}!"
    except Exception as e:
        return f"Couldn't open the browser. Error: {str(e)[:40]}"


def open_url(url):
    """Open a specific URL."""
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        webbrowser.open(url)
        return f"Opened {url} in your browser!"
    except Exception as e:
        return f"Couldn't open that URL."


def write_file(filename, content):
    """Write content to a file on the Desktop."""
    try:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        filepath = os.path.join(desktop, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"I created {filename} on your Desktop!"
    except Exception as e:
        return f"Couldn't write the file. Error: {str(e)[:40]}"


def read_file(filepath):
    """Read and return contents of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(1000)  # limit to 1000 chars
        return f"Here's what's in the file: {content}"
    except Exception as e:
        return f"Couldn't read that file."


def open_folder(path=None):
    """Open folder — reuses existing File Explorer window."""
    import os, subprocess

    known = {
        'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
        'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
        'desktop':   os.path.join(os.path.expanduser('~'), 'Desktop'),
        'pictures':  os.path.join(os.path.expanduser('~'), 'Pictures'),
        'music':     os.path.join(os.path.expanduser('~'), 'Music'),
        'videos':    os.path.join(os.path.expanduser('~'), 'Videos'),
        'home':      os.path.expanduser('~'),
    }

    resolved = known.get(str(path).lower().strip(), path) if path else os.path.expanduser('~')

    if not resolved or not os.path.exists(str(resolved)):
        return f"Couldn't find that folder."

    # Always use Shell.Application — opens in existing Explorer
    ps = f"$s = New-Object -ComObject Shell.Application; $s.Open('{resolved}')"
    subprocess.run(['powershell','-Command',ps], capture_output=True, timeout=5)
    return f"Opened {path or 'home'} folder!"


def take_screenshot(filename=None):
    """Take a screenshot and save to Desktop."""
    try:
        desktop  = os.path.join(os.path.expanduser('~'), 'Desktop')
        filename = filename or f"screenshot_{int(time.time())}.png"
        filepath = os.path.join(desktop, filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return f"Screenshot saved to your Desktop as {filename}!"
    except Exception as e:
        return f"Couldn't take a screenshot."


def type_text(text):
    """Type text at current cursor position."""
    try:
        time.sleep(1)  # give user time to click where they want
        pyautogui.typewrite(text, interval=0.05)
        return f"I typed that for you!"
    except Exception as e:
        return f"Couldn't type that text."


def copy_to_clipboard(text):
    """Copy text to clipboard."""
    try:
        pyperclip.copy(text)
        return f"Copied to your clipboard!"
    except Exception as e:
        return f"Couldn't copy to clipboard."


def set_volume(level):
    """Set system volume (0-100)."""
    try:
        level = max(0, min(100, int(level)))
        # Use PowerShell to set volume
        ps = f"""
$vol = {level} / 100
$obj = New-Object -ComObject WScript.Shell
Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{ int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev); }}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint); }}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{ }}
"@
$enumerator = New-Object MMDeviceEnumeratorComObject
$id = [System.Guid]::new("5CDF2C82-841E-4546-9722-0CF74078229A")
[IMMDeviceEnumerator]$enum = $enumerator
[IMMDevice]$dev = $null
$enum.GetDefaultAudioEndpoint(0, 1, [ref]$dev) | Out-Null
[IAudioEndpointVolume]$aev = $null
$dev.Activate([ref]$id, 23, 0, [ref]$aev) | Out-Null
$aev.SetMasterVolumeLevelScalar($vol, [System.Guid]::Empty) | Out-Null
"""
        subprocess.run(['powershell', '-Command', ps], capture_output=True, timeout=5)
        return f"Volume set to {level} percent!"
    except Exception as e:
        # Fallback using key presses
        return f"Couldn't set volume precisely, try saying increase or decrease volume."


def press_key(key_combo):
    """Press a keyboard shortcut."""
    try:
        keys = [k.strip() for k in key_combo.lower().split('+')]
        pyautogui.hotkey(*keys)
        return f"Pressed {key_combo}!"
    except Exception as e:
        return f"Couldn't press those keys."


def get_clipboard():
    """Get current clipboard content."""
    try:
        text = pyperclip.paste()
        if text:
            return f"Your clipboard has: {text[:100]}"
        return "Your clipboard is empty."
    except:
        return "Couldn't read clipboard."


# ─── TOOL ROUTER ─────────────────────────────────────────────────────────────
# Ask AI to decide which tool to use and with what arguments

def route_command(user_text, groq_api_key):
    """
    Ask the AI to parse the user command into a tool call.
    Returns (tool_name, args_dict, speak_result)
    """
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        system = """You are a command parser for an AI desktop agent called Nova.
The user gives a voice command. You must decide if it is a TASK or a QUESTION.

If it is a TASK, respond with ONLY a JSON object like:
{"tool": "tool_name", "args": {"arg1": "value1"}}

Available tools and their args:
- open_app: {"app": "app name"}
- web_search: {"query": "search query"}
- open_url: {"url": "website url"}
- write_file: {"filename": "file.txt", "content": "file content"}
- take_screenshot: {}
- type_text: {"text": "text to type"}
- copy_to_clipboard: {"text": "text to copy"}
- set_volume: {"level": 50}
- press_key: {"key_combo": "ctrl+c"}
- get_clipboard: {}
- open_folder: {"path": "optional path"}

If it is a QUESTION (not a task), respond with:
{"tool": "answer", "args": {}}

Examples:
"open chrome" → {"tool": "open_app", "args": {"app": "chrome"}}
"search for weather in hyderabad" → {"tool": "web_search", "args": {"query": "weather in hyderabad"}}
"take a screenshot" → {"tool": "take_screenshot", "args": {}}
"set volume to 50" → {"tool": "set_volume", "args": {"level": 50}}
"what is python" → {"tool": "answer", "args": {}}
"open youtube" → {"tool": "open_url", "args": {"url": "youtube.com"}}
"write a note that says buy milk" → {"tool": "write_file", "args": {"filename": "note.txt", "content": "buy milk"}}
"open amazon" → {"tool": "open_app", "args": {"app": "amazon"}}
"open zomato" → {"tool": "open_app", "args": {"app": "zomato"}}
"open flipkart" → {"tool": "open_app", "args": {"app": "flipkart"}}
"open hotstar" → {"tool": "open_app", "args": {"app": "hotstar.com"}}
"go to linkedin" → {"tool": "open_app", "args": {"app": "linkedin.com"}}
"open my email" → {"tool": "open_app", "args": {"app": "gmail"}}
"open maps" → {"tool": "open_url", "args": {"url": "maps.google.com"}}

Respond with ONLY the JSON. No explanation."""

        r = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            max_tokens=100,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': user_text}
            ]
        )

        raw = r.choices[0].message.content.strip()
        # Strip markdown if present
        raw = raw.replace('```json','').replace('```','').strip()
        parsed = json.loads(raw)
        return parsed

    except Exception as e:
        return {'tool': 'answer', 'args': {}}


def execute_tool(tool_name, args):
    """Execute the parsed tool and return result string."""
    try:
        if tool_name == 'open_app':
            return open_app(args.get('app', ''))
        elif tool_name == 'web_search':
            return web_search(args.get('query', ''))
        elif tool_name == 'open_url':
            return open_url(args.get('url', ''))
        elif tool_name == 'write_file':
            return write_file(args.get('filename','note.txt'), args.get('content',''))
        elif tool_name == 'take_screenshot':
            return take_screenshot()
        elif tool_name == 'type_text':
            return type_text(args.get('text',''))
        elif tool_name == 'copy_to_clipboard':
            return copy_to_clipboard(args.get('text',''))
        elif tool_name == 'set_volume':
            return set_volume(args.get('level', 50))
        elif tool_name == 'press_key':
            return press_key(args.get('key_combo',''))
        elif tool_name == 'get_clipboard':
            return get_clipboard()
        elif tool_name == 'open_folder':
            return open_folder(args.get('path'))
        else:
            return None  # not a task, fall through to normal AI answer
    except Exception as e:
        return f"I tried but ran into an error: {str(e)[:60]}"


# ─── BROWSER TASK KEYWORDS ────────────────────────────────────────────────────
# If command contains these, hand off to browser_agent
BROWSER_KEYWORDS = [
    'youtube', 'play', 'search on', 'google search',
    'scroll', 'go back', 'go forward', 'click on',
    'open instagram', 'open twitter', 'open facebook',
    'open reddit', 'open netflix', 'open spotify web',
    'find on google', 'look up on', 'browse'
]

def is_browser_task(text):
    text_lower = text.lower()
    return any(k in text_lower for k in BROWSER_KEYWORDS)


def route_command_with_browser(user_text, groq_api_key):
    """
    Extended router that also handles browser tasks.
    Call this instead of route_command in voice_brain.
    """
    # Check browser keywords first
    if is_browser_task(user_text):
        return {'tool': 'browser', 'args': {'text': user_text}}

    # Fall through to normal tool router
    return route_command(user_text, groq_api_key)
