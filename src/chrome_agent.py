"""
Nova Chrome Agent — Controls your REAL Chrome browser
Uses Chrome DevTools Protocol (CDP) to:
- See all open tabs
- Switch between tabs
- Click elements
- Type in fields
- Read page content
- Navigate
"""

import json
import time
import subprocess
import os
import requests

CDP_URL = 'http://localhost:9222'


# ─── CONNECTION HELPERS ───────────────────────────────────────────────────────

def is_chrome_running():
    """Check if Chrome is running with debug port."""
    try:
        r = requests.get(f'{CDP_URL}/json', timeout=2)
        return r.status_code == 200
    except:
        return False


def launch_chrome_with_debug():
    """Launch Chrome with remote debugging if not already running."""
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.join(os.getenv('LOCALAPPDATA',''),
                     r'Google\Chrome\Application\chrome.exe'),
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            subprocess.Popen([
                path,
                '--remote-debugging-port=9222',
                '--no-first-run',
                '--no-default-browser-check'
            ])
            time.sleep(2)
            return True
    return False


def get_tabs():
    """Get list of all open Chrome tabs."""
    try:
        r = requests.get(f'{CDP_URL}/json', timeout=3)
        tabs = r.json()
        # Filter only real page tabs (not extensions)
        return [t for t in tabs if t.get('type') == 'page']
    except:
        return []


def get_tab_by_index(index):
    """Get tab by position (0=first, 1=second etc)."""
    tabs = get_tabs()
    if 0 <= index < len(tabs):
        return tabs[index]
    return None


def get_tab_by_title(title_hint):
    """Find tab whose title contains the hint."""
    tabs = get_tabs()
    title_lower = title_hint.lower()
    for tab in tabs:
        if title_lower in tab.get('title','').lower():
            return tab
        if title_lower in tab.get('url','').lower():
            return tab
    return None


def get_active_tab():
    """Get the currently focused tab (first in list is usually active)."""
    tabs = get_tabs()
    return tabs[0] if tabs else None


def send_cdp(tab, method, params=None):
    """Send a CDP command to a specific tab via WebSocket."""
    try:
        import websocket
        ws_url = tab.get('webSocketDebuggerUrl','')
        if not ws_url: return None

        ws = websocket.create_connection(ws_url, timeout=10)
        msg = json.dumps({'id': 1, 'method': method, 'params': params or {}})
        ws.send(msg)
        result = json.loads(ws.recv())
        ws.close()
        return result.get('result')
    except Exception as e:
        return None


# ─── TAB OPERATIONS ───────────────────────────────────────────────────────────

def focus_tab(tab):
    """Bring a tab to front."""
    try:
        tab_id = tab.get('id','')
        requests.get(f'{CDP_URL}/json/activate/{tab_id}', timeout=3)
        time.sleep(0.5)
        return True
    except:
        return False


def switch_to_tab_by_index(index):
    """Switch to tab by number (say 'second tab' = index 1)."""
    tab = get_tab_by_index(index)
    if tab:
        focus_tab(tab)
        title = tab.get('title', f'tab {index+1}')
        return f"Switched to tab {index+1}: {title[:40]}!"
    tabs = get_tabs()
    return f"Only {len(tabs)} tabs are open."


def switch_to_tab_by_name(name):
    """Switch to tab by title or URL keyword."""
    tab = get_tab_by_title(name)
    if tab:
        focus_tab(tab)
        title = tab.get('title', name)
        return f"Switched to {title[:40]}!"
    return f"Couldn't find a tab matching '{name}'."


def list_tabs():
    """List all open tabs."""
    tabs = get_tabs()
    if not tabs: return "No tabs open in Chrome."
    names = [f"{i+1}. {t.get('title','Untitled')[:30]}" for i,t in enumerate(tabs)]
    return f"You have {len(tabs)} tabs open: " + ", ".join(names)


def open_new_tab(url='chrome://newtab'):
    """Open a new tab, optionally with a URL."""
    try:
        if not url.startswith('http') and not url.startswith('chrome'):
            url = 'https://' + url
        subprocess.Popen([
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            f'--remote-debugging-port=9222', url
        ])
        time.sleep(1)
        return f"Opened new tab!"
    except:
        # Fallback via keyboard shortcut
        import pyautogui
        pyautogui.hotkey('ctrl', 't')
        time.sleep(0.5)
        if url and url != 'chrome://newtab':
            import pyperclip
            pyperclip.copy(url)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press('enter')
        return f"Opened new tab!"


def close_current_tab():
    """Close the current tab."""
    import pyautogui
    pyautogui.hotkey('ctrl', 'w')
    return "Closed the tab!"


def navigate_current_tab(url):
    """Navigate current tab to a URL."""
    try:
        import pyautogui, pyperclip
        if not url.startswith('http'): url = 'https://' + url
        pyautogui.hotkey('ctrl', 'l')  # focus address bar
        time.sleep(0.3)
        pyperclip.copy(url)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)
        return f"Navigated to {url}!"
    except Exception as e:
        return f"Navigation error: {str(e)[:40]}"


# ─── PAGE INTERACTION VIA PYAUTOGUI + OCR ─────────────────────────────────────

def click_on_screen_text(text):
    """Find text on screen using OCR and click it."""
    try:
        import mss
        from PIL import Image
        import pytesseract
        import pyautogui

        pytesseract.pytesseract.tesseract_cmd = \
            r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])
            img  = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        text_lower = text.lower()
        best_x, best_y, best_conf = None, None, 0

        for i, word in enumerate(data['text']):
            if text_lower in word.lower():
                conf = int(data['conf'][i])
                if conf > best_conf:
                    best_conf = conf
                    best_x = data['left'][i] + data['width'][i]  // 2
                    best_y = data['top'][i]  + data['height'][i] // 2

        if best_x and best_conf > 30:
            pyautogui.click(best_x, best_y)
            return f"Clicked '{text}'!"

        # Try partial word match
        words = text_lower.split()
        for word in words:
            for i, w in enumerate(data['text']):
                if word in w.lower() and int(data['conf'][i]) > 40:
                    x = data['left'][i] + data['width'][i]  // 2
                    y = data['top'][i]  + data['height'][i] // 2
                    pyautogui.click(x, y)
                    return f"Clicked on '{w}'!"

        return f"Couldn't find '{text}' on screen."
    except Exception as e:
        return f"Click error: {str(e)[:60]}"


def type_in_chrome(text):
    """Type text in whatever is focused in Chrome."""
    try:
        import pyautogui, pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        return f"Typed '{text[:40]}'!"
    except Exception as e:
        return f"Type error: {str(e)[:40]}"


def search_in_current_page(query):
    """Use Ctrl+F to search in current page."""
    try:
        import pyautogui, pyperclip
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.3)
        pyperclip.copy(query)
        pyautogui.hotkey('ctrl', 'v')
        return f"Searching for '{query}' on page!"
    except Exception as e:
        return f"Search error: {str(e)[:40]}"


def scroll_page(direction='down', amount=3):
    """Scroll current page."""
    try:
        import pyautogui
        for _ in range(amount):
            if direction == 'down': pyautogui.press('pagedown')
            else: pyautogui.press('pageup')
            time.sleep(0.1)
        return f"Scrolled {direction}!"
    except Exception as e:
        return f"Scroll error: {str(e)[:40]}"


def go_back():
    import pyautogui
    pyautogui.hotkey('alt', 'left')
    return "Went back!"


def go_forward():
    import pyautogui
    pyautogui.hotkey('alt', 'right')
    return "Went forward!"


def reload_page():
    import pyautogui
    pyautogui.key('f5')
    return "Reloaded the page!"


def search_youtube(query):
    """Focus Chrome, go to YouTube and search."""
    try:
        import pyautogui, pyperclip

        # Go to YouTube search URL directly
        search_url = f'https://www.youtube.com/results?search_query={query.replace(" ","+")}'
        navigate_current_tab(search_url)
        time.sleep(2)
        return f"Searched YouTube for '{query}'!"
    except Exception as e:
        return f"YouTube search error: {str(e)[:60]}"


def search_google(query):
    """Search Google in current tab."""
    try:
        url = f'https://www.google.com/search?q={query.replace(" ","+")}'
        navigate_current_tab(url)
        time.sleep(1)
        return f"Searched Google for '{query}'!"
    except Exception as e:
        return f"Google search error: {str(e)[:60]}"


def get_current_page_info():
    """Get title and URL of current tab."""
    tabs = get_tabs()
    if not tabs: return "Chrome is not open."
    tab = tabs[0]
    title = tab.get('title','Unknown')
    url   = tab.get('url','')[:60]
    total = len(tabs)
    return f"You have {total} tabs open. Current page: {title[:40]} at {url}"


# ─── SMART COMMAND PARSER ────────────────────────────────────────────────────

def parse_chrome_command(user_text, groq_api_key):
    """Ask AI to parse a Chrome control command."""
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        tabs     = get_tabs()
        tab_list = ', '.join([f"{i+1}.{t.get('title','?')[:20]}"
                              for i,t in enumerate(tabs)]) if tabs else 'none'

        system = f"""You are a Chrome browser controller for Nova AI.
Current open tabs: {tab_list}

Parse user command into ONE action JSON:
{{"action": "switch_tab_index", "index": 0}}
{{"action": "switch_tab_name", "name": "youtube"}}
{{"action": "list_tabs"}}
{{"action": "new_tab", "url": "optional url"}}
{{"action": "close_tab"}}
{{"action": "navigate", "url": "url or website"}}
{{"action": "click_text", "text": "text on screen"}}
{{"action": "type_text", "text": "text to type"}}
{{"action": "search_youtube", "query": "search query"}}
{{"action": "search_google", "query": "search query"}}
{{"action": "scroll_down"}}
{{"action": "scroll_up"}}
{{"action": "go_back"}}
{{"action": "go_forward"}}
{{"action": "page_info"}}
{{"action": "search_page", "query": "text to find on page"}}

Examples:
"click on the second tab" → {{"action": "switch_tab_index", "index": 1}}
"go to the third tab" → {{"action": "switch_tab_index", "index": 2}}
"click on YouTube tab" → {{"action": "switch_tab_name", "name": "youtube"}}
"how many tabs are open" → {{"action": "list_tabs"}}
"open a new tab" → {{"action": "new_tab", "url": ""}}
"open instagram in new tab" → {{"action": "new_tab", "url": "instagram.com"}}
"search youtube for lofi music" → {{"action": "search_youtube", "query": "lofi music"}}
"search google for weather" → {{"action": "search_google", "query": "weather hyderabad"}}
"click on Hotels" → {{"action": "click_text", "text": "Hotels"}}
"type hello world" → {{"action": "type_text", "text": "hello world"}}
"scroll down" → {{"action": "scroll_down"}}
"go back" → {{"action": "go_back"}}
"what tabs are open" → {{"action": "list_tabs"}}
"what page am i on" → {{"action": "page_info"}}

Return ONLY the JSON."""

        r = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            max_tokens=80,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': user_text}
            ]
        )
        raw = r.choices[0].message.content.strip()
        raw = raw.replace('```json','').replace('```','').strip()
        return json.loads(raw)
    except Exception as e:
        return None


def execute_chrome_command(user_text, groq_api_key):
    """Parse and execute a Chrome command. Returns result or None."""

    # Make sure Chrome is running
    if not is_chrome_running():
        launched = launch_chrome_with_debug()
        if not launched:
            return "Chrome is not open. Please open Chrome first."
        time.sleep(2)

    parsed = parse_chrome_command(user_text, groq_api_key)
    if not parsed: return None

    action = parsed.get('action','')

    if   action == 'switch_tab_index': return switch_to_tab_by_index(parsed.get('index',0))
    elif action == 'switch_tab_name':  return switch_to_tab_by_name(parsed.get('name',''))
    elif action == 'list_tabs':        return list_tabs()
    elif action == 'new_tab':          return open_new_tab(parsed.get('url',''))
    elif action == 'close_tab':        return close_current_tab()
    elif action == 'navigate':         return navigate_current_tab(parsed.get('url',''))
    elif action == 'click_text':       return click_on_screen_text(parsed.get('text',''))
    elif action == 'type_text':        return type_in_chrome(parsed.get('text',''))
    elif action == 'search_youtube':   return search_youtube(parsed.get('query',''))
    elif action == 'search_google':    return search_google(parsed.get('query',''))
    elif action == 'scroll_down':      return scroll_page('down')
    elif action == 'scroll_up':        return scroll_page('up')
    elif action == 'go_back':          return go_back()
    elif action == 'go_forward':       return go_forward()
    elif action == 'page_info':        return get_current_page_info()
    elif action == 'search_page':      return search_in_current_page(parsed.get('query',''))
    return None