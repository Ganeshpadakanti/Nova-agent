"""
Nova Screen Watcher — Phase 3
Captures screen every few seconds, extracts text via OCR,
detects active window, and provides context to voice brain.
"""

import os
import time
import threading
import subprocess

# Tesseract path — update if yours is different
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# How often to capture screen (seconds)
CAPTURE_INTERVAL = 5

# Max characters of screen text to send to AI (keep it short)
MAX_CONTEXT_CHARS = 500

# Shared context — voice_brain reads this
screen_context = {
    'active_app':  'Unknown',
    'window_title': '',
    'screen_text':  '',
    'updated_at':   0,
    'lock':         threading.Lock()
}


def get_active_window_info():
    """Get the currently focused window title and app name on Windows."""
    try:
        ps = """
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@
$hwnd = [WinAPI]::GetForegroundWindow()
$title = New-Object System.Text.StringBuilder 256
[WinAPI]::GetWindowText($hwnd, $title, 256) | Out-Null
$pid = 0
[WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
Write-Output "$($title.ToString())|$($proc.Name)"
"""
        result = subprocess.run(
            ['powershell', '-Command', ps],
            capture_output=True, text=True, timeout=3
        )
        output = result.stdout.strip()
        if '|' in output:
            title, app = output.split('|', 1)
            return title.strip(), app.strip()
        return output, 'Unknown'
    except Exception as e:
        return '', 'Unknown'


def capture_screen_text():
    """Take a screenshot and extract text using OCR."""
    try:
        import mss
        import pytesseract
        from PIL import Image

        # Set tesseract path
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

        with mss.mss() as sct:
            # Capture primary monitor
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)

            # Convert to PIL image
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')

            # Resize to speed up OCR (half size)
            w, h = img.size
            img = img.resize((w // 2, h // 2), Image.LANCZOS)

            # Extract text — fast mode
            text = pytesseract.image_to_string(
                img,
                config='--psm 6 --oem 1'
            )

            # Clean up — remove blank lines, limit length
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            clean = ' | '.join(lines)
            return clean[:MAX_CONTEXT_CHARS]

    except Exception as e:
        return f'(OCR error: {str(e)[:60]})'


def update_context():
    """Capture screen and update shared context dict."""
    title, app = get_active_window_info()
    text       = capture_screen_text()

    with screen_context['lock']:
        screen_context['active_app']   = app
        screen_context['window_title'] = title
        screen_context['screen_text']  = text
        screen_context['updated_at']   = time.time()


def get_context_string():
    """Return a formatted context string for the AI prompt."""
    with screen_context['lock']:
        app   = screen_context['active_app']
        title = screen_context['window_title']
        text  = screen_context['screen_text']

    parts = []
    if app and app != 'Unknown':
        parts.append(f'Active app: {app}')
    if title:
        parts.append(f'Window title: {title}')
    if text:
        parts.append(f'Visible text on screen: {text}')

    return '\n'.join(parts) if parts else 'No screen context available.'


def start_screen_watcher():
    """Start background thread that captures screen every CAPTURE_INTERVAL seconds."""
    def loop():
        while True:
            try:
                update_context()
            except Exception as e:
                pass  # silently continue if capture fails
            time.sleep(CAPTURE_INTERVAL)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
