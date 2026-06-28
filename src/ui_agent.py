"""
Nova UI Agent — Full System Control
Web: Playwright DOM
Desktop: PyAutoGUI + OCR + PowerShell
"""

import time, json, subprocess, threading
import pyautogui, pyperclip
pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.2


# ════════════════════════════════════════════════════════════
# WEB INTERACTION
# ════════════════════════════════════════════════════════════

def get_browser_page():
    try:
        from browser_agent import get_page
        return get_page()
    except: return None


def web_click_text(text):
    try:
        page = get_browser_page()
        if not page: return "Browser is not open."
        for strategy in [
            lambda: page.get_by_text(text, exact=False).first.click(timeout=4000),
            lambda: page.get_by_role('button', name=text).first.click(timeout=3000),
            lambda: page.get_by_role('link', name=text).first.click(timeout=3000),
            lambda: page.get_by_label(text).first.click(timeout=3000),
        ]:
            try: strategy(); return f"Clicked '{text}'!"
            except: continue
        return f"Couldn't find '{text}' on the page."
    except Exception as e:
        return f"Click error: {str(e)[:60]}"


def web_search_in_page(search_text):
    try:
        page = get_browser_page()
        if not page: return "Browser is not open."
        selectors = [
            'input[type="search"]',
            'input[placeholder*="search" i]',
            'input[aria-label*="search" i]',
            'input[name="q"]',
            'input[name="search"]',
            'input[id*="search" i]',
            'textarea[aria-label*="search" i]',
            '#searchboxinput',
            'input#search',
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click(); el.fill(search_text)
                    page.keyboard.press('Enter')
                    return f"Searched for '{search_text}'!"
            except: continue
        # fallback
        page.locator('input:visible').first.click()
        page.keyboard.type(search_text)
        page.keyboard.press('Enter')
        return f"Typed and searched for '{search_text}'!"
    except Exception as e:
        return f"Search error: {str(e)[:60]}"


def web_type_in_field(field_hint, text_to_type):
    try:
        page = get_browser_page()
        if not page: return "Browser is not open."
        for strategy in [
            lambda: page.get_by_placeholder(field_hint, exact=False).first,
            lambda: page.get_by_label(field_hint, exact=False).first,
        ]:
            try:
                el = strategy()
                el.click(); el.fill(text_to_type)
                return f"Typed '{text_to_type}'!"
            except: continue
        # Try matching any input
        inputs = page.locator('input:visible, textarea:visible').all()
        for inp in inputs:
            attrs = ' '.join([
                inp.get_attribute('placeholder') or '',
                inp.get_attribute('aria-label') or '',
                inp.get_attribute('name') or '',
            ]).lower()
            if field_hint.lower() in attrs:
                inp.click(); inp.fill(text_to_type)
                return f"Typed '{text_to_type}'!"
        # Last resort
        page.locator('input:visible').first.click()
        page.locator('input:visible').first.fill(text_to_type)
        return f"Typed '{text_to_type}' in the first field!"
    except Exception as e:
        return f"Type error: {str(e)[:60]}"


def web_navigate_to(url_or_query):
    try:
        page = get_browser_page()
        if not page: return "Browser is not open."
        url = url_or_query if url_or_query.startswith('http') \
              else f'https://www.google.com/search?q={url_or_query.replace(" ","+")}'
        page.goto(url, timeout=15000)
        return f"Navigated to {url_or_query}!"
    except Exception as e:
        return f"Navigation error: {str(e)[:60]}"


def web_get_page_info():
    try:
        page = get_browser_page()
        if not page: return "Browser not open."
        title = page.title()
        url   = page.url
        try:
            body    = page.locator('body').inner_text()
            snippet = ' '.join(body.split()[:40])
        except: snippet = ''
        return f"You are on: {title}. {snippet[:100]}"
    except: return "Couldn't get page info."


def google_maps_search(location):
    try:
        page = get_browser_page()
        if not page or 'maps.google' not in page.url:
            from browser_agent import open_url
            open_url('maps.google.com')
            time.sleep(2)
            page = get_browser_page()
        search = page.locator('#searchboxinput, input[aria-label*="Search"]').first
        search.click(); search.fill(location)
        page.keyboard.press('Enter')
        time.sleep(2)
        return f"Searched Maps for '{location}'!"
    except Exception as e:
        return f"Maps error: {str(e)[:60]}"


def youtube_search_in_page(query):
    try:
        page = get_browser_page()
        if not page or 'youtube' not in page.url:
            from browser_agent import open_url
            open_url('youtube.com')
            time.sleep(2)
            page = get_browser_page()
        search = page.locator('input#search').first
        search.click(); search.fill(query)
        page.keyboard.press('Enter')
        time.sleep(2)
        return f"Searched YouTube for '{query}'!"
    except Exception as e:
        return f"YouTube search error: {str(e)[:60]}"


def youtube_click_video(index=0):
    try:
        page = get_browser_page()
        videos = page.locator('ytd-video-renderer a#video-title').all()
        if index < len(videos):
            title = videos[index].get_attribute('title') or f'video {index+1}'
            videos[index].click()
            return f"Playing: {title}!"
        return "No videos found."
    except Exception as e:
        return f"Click error: {str(e)[:60]}"


# ════════════════════════════════════════════════════════════
# DESKTOP INTERACTION
# ════════════════════════════════════════════════════════════

def find_text_on_screen(text):
    try:
        import mss
        from PIL import Image
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = \
            r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])
            img  = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        for i, word in enumerate(data['text']):
            if text.lower() in word.lower() and int(data['conf'][i]) > 40:
                x = data['left'][i] + data['width'][i]  // 2
                y = data['top'][i]  + data['height'][i] // 2
                return x, y
        return None
    except: return None


def desktop_click_text(text):
    coords = find_text_on_screen(text)
    if coords:
        pyautogui.click(coords[0], coords[1])
        return f"Clicked '{text}'!"
    return f"Couldn't find '{text}' on screen."


def desktop_open_folder(folder_name):
    """Open folder in existing File Explorer window or launch new one."""
    import os
    known = {
        'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
        'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
        'desktop':   os.path.join(os.path.expanduser('~'), 'Desktop'),
        'pictures':  os.path.join(os.path.expanduser('~'), 'Pictures'),
        'music':     os.path.join(os.path.expanduser('~'), 'Music'),
        'videos':    os.path.join(os.path.expanduser('~'), 'Videos'),
        'home':      os.path.expanduser('~'),
    }
    path = known.get(folder_name.lower().strip(),
                     folder_name if os.path.exists(folder_name) else None)
    if not path:
        return f"Couldn't find the {folder_name} folder."

    # Use Shell.Application — opens in existing Explorer, new tab
    ps = f"$s = New-Object -ComObject Shell.Application; $s.Open('{path}')"
    subprocess.run(['powershell','-Command',ps], capture_output=True, timeout=5)
    return f"Opened {folder_name} folder!"


def desktop_search_in_explorer(search_text):
    try:
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.5)
        pyautogui.typewrite(search_text, interval=0.05)
        pyautogui.press('enter')
        return f"Searched for '{search_text}' in File Explorer!"
    except Exception as e:
        return f"Search error: {str(e)[:60]}"


def press_shortcut(shortcut):
    try:
        keys = [k.strip() for k in shortcut.lower().split('+')]
        pyautogui.hotkey(*keys)
        return f"Pressed {shortcut}!"
    except Exception as e:
        return f"Shortcut error: {str(e)[:40]}"


def type_anywhere(text):
    try:
        time.sleep(0.5)
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        return f"Typed for you!"
    except Exception as e:
        return f"Type error: {str(e)[:40]}"


def get_active_window():
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        return win.title if win else 'Unknown'
    except: return 'Unknown'


# ════════════════════════════════════════════════════════════
# FULL SYSTEM CONTROL (PowerShell fallback)
# ════════════════════════════════════════════════════════════

def full_system_command(command_text, groq_api_key):
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        r = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            max_tokens=150,
            messages=[{
                'role': 'system',
                'content': '''Generate a safe Windows PowerShell one-liner for the user request.
Return ONLY the PowerShell command, nothing else.
Only use safe UI/read commands. Never delete files or format drives.'''
            }, {
                'role': 'user', 'content': command_text
            }]
        )
        ps_cmd = r.choices[0].message.content.strip()
        ps_cmd = ps_cmd.replace('```powershell','').replace('```','').strip()
        result = subprocess.run(['powershell','-Command',ps_cmd],
                                capture_output=True, text=True, timeout=10)
        output = result.stdout.strip()
        return f"Done! {output[:100]}" if output else "Done!"
    except Exception as e:
        return f"Couldn't do that: {str(e)[:60]}"


# ════════════════════════════════════════════════════════════
# SMART UI COMMAND PARSER
# ════════════════════════════════════════════════════════════

def parse_ui_command(user_text, groq_api_key):
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        active = get_active_window()
        system = f"""You are a UI automation parser for Nova AI agent.
Active window: {active}

Parse into ONE action JSON:
{{"action": "web_click", "text": "element text"}}
{{"action": "web_type", "field": "field hint", "text": "text"}}
{{"action": "web_search", "text": "query"}}
{{"action": "web_navigate", "url": "url"}}
{{"action": "maps_search", "location": "place"}}
{{"action": "youtube_search", "query": "query"}}
{{"action": "youtube_play_nth", "index": 0}}
{{"action": "desktop_click", "text": "screen text"}}
{{"action": "desktop_search", "text": "query"}}
{{"action": "open_folder", "folder": "name"}}
{{"action": "press_shortcut", "shortcut": "ctrl+c"}}
{{"action": "type_anywhere", "text": "text"}}
{{"action": "web_info"}}

Examples:
"click on restaurants" → {{"action": "web_click", "text": "Restaurants"}}
"search for pizza near me in maps" → {{"action": "maps_search", "location": "pizza near me"}}
"search youtube for lofi" → {{"action": "youtube_search", "query": "lofi"}}
"play the first video" → {{"action": "youtube_play_nth", "index": 0}}
"open downloads folder" → {{"action": "open_folder", "folder": "downloads"}}
"click downloads in sidebar" → {{"action": "desktop_click", "text": "Downloads"}}
"search for report in file explorer" → {{"action": "desktop_search", "text": "report"}}
"press ctrl c" → {{"action": "press_shortcut", "shortcut": "ctrl+c"}}
"type hello world" → {{"action": "type_anywhere", "text": "hello world"}}
"what page am i on" → {{"action": "web_info"}}

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
    except: return None


def execute_ui_command(user_text, groq_api_key):
    parsed = parse_ui_command(user_text, groq_api_key)
    if not parsed: return None
    action = parsed.get('action','')

    if   action == 'web_click':        return web_click_text(parsed.get('text',''))
    elif action == 'web_type':         return web_type_in_field(parsed.get('field',''), parsed.get('text',''))
    elif action == 'web_search':       return web_search_in_page(parsed.get('text',''))
    elif action == 'web_navigate':     return web_navigate_to(parsed.get('url',''))
    elif action == 'maps_search':      return google_maps_search(parsed.get('location',''))
    elif action == 'youtube_search':   return youtube_search_in_page(parsed.get('query',''))
    elif action == 'youtube_play_nth': return youtube_click_video(parsed.get('index',0))
    elif action == 'desktop_click':    return desktop_click_text(parsed.get('text',''))
    elif action == 'desktop_search':   return desktop_search_in_explorer(parsed.get('text',''))
    elif action == 'open_folder':      return desktop_open_folder(parsed.get('folder',''))
    elif action == 'press_shortcut':   return press_shortcut(parsed.get('shortcut',''))
    elif action == 'type_anywhere':    return type_anywhere(parsed.get('text',''))
    elif action == 'web_info':         return web_get_page_info()
    return None