"""
Nova Browser Agent — Full Click Control
Uses Playwright to control browser fully.
"""
import time, json, threading

_pw       = None
_browser  = None
_page     = None
_context  = None
_lock     = threading.Lock()
_started  = False


def get_page():
    global _pw, _browser, _page, _context, _started
    with _lock:
        if _started and _page and not _page.is_closed():
            return _page
        from playwright.sync_api import sync_playwright
        _pw      = sync_playwright().start()
        _browser = _pw.chromium.launch(
            headless=False,
            slow_mo=50,
            args=['--start-maximized']
        )
        _context = _browser.new_context(no_viewport=True)
        _page    = _context.new_page()
        _started = True
        return _page


def safe_wait(page, ms=1500):
    try: page.wait_for_load_state('domcontentloaded', timeout=ms)
    except: pass


# ─── YOUTUBE ──────────────────────────────────────────────────────────────────
def youtube_search_and_play(query):
    try:
        page = get_page()
        page.goto('https://www.youtube.com', timeout=15000)
        safe_wait(page)
        time.sleep(1)

        # Type in search
        search_box = page.locator('input#search').first
        search_box.click()
        search_box.fill(query)
        page.keyboard.press('Enter')
        safe_wait(page, 3000)
        time.sleep(2)

        # Click first video
        first = page.locator('ytd-video-renderer a#video-title').first
        if first.count() > 0:
            title = first.get_attribute('title') or query
            first.click()
            return f"Playing {title} on YouTube!"
        return "Opened YouTube search results!"
    except Exception as e:
        return f"YouTube error: {str(e)[:80]}"


def youtube_search_only(query):
    try:
        page = get_page()
        page.goto(f'https://www.youtube.com/results?search_query={query.replace(" ","+")}')
        safe_wait(page, 3000)
        return f"Searched YouTube for {query}!"
    except Exception as e:
        return f"YouTube search error: {str(e)[:60]}"


# ─── GOOGLE ───────────────────────────────────────────────────────────────────
def google_search(query):
    try:
        page = get_page()
        page.goto(f'https://www.google.com/search?q={query.replace(" ","+")}')
        safe_wait(page)
        time.sleep(1)

        # Try to get featured snippet
        snippets = page.locator('div.VwiC3b').all()
        for s in snippets[:2]:
            t = s.inner_text().strip()
            if t and len(t) > 20:
                return f"Google says: {t[:200]}"
        return f"Searched Google for {query}!"
    except Exception as e:
        return f"Google error: {str(e)[:60]}"


# ─── FILE EXPLORER CLICK ──────────────────────────────────────────────────────
def click_in_explorer(folder_name):
    """Click a folder in Windows File Explorer using pyautogui."""
    try:
        import pyautogui, subprocess, time
        subprocess.Popen('explorer', shell=True)
        time.sleep(1.5)
        # Double click the folder by finding it on screen
        location = pyautogui.locateOnScreen(f'{folder_name}.png', confidence=0.7)
        if location:
            pyautogui.doubleClick(location)
            return f"Opened {folder_name} folder!"
        # Fallback — just open the folder directly
        import os
        known = {
            'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
            'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
            'desktop':   os.path.join(os.path.expanduser('~'), 'Desktop'),
            'pictures':  os.path.join(os.path.expanduser('~'), 'Pictures'),
            'music':     os.path.join(os.path.expanduser('~'), 'Music'),
            'videos':    os.path.join(os.path.expanduser('~'), 'Videos'),
        }
        path = known.get(folder_name.lower())
        if path:
            subprocess.Popen(f'explorer "{path}"', shell=True)
            return f"Opened your {folder_name} folder!"
        return f"Opened File Explorer!"
    except Exception as e:
        import os, subprocess
        known = {
            'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
            'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
            'desktop':   os.path.join(os.path.expanduser('~'), 'Desktop'),
            'pictures':  os.path.join(os.path.expanduser('~'), 'Pictures'),
            'music':     os.path.join(os.path.expanduser('~'), 'Music'),
            'videos':    os.path.join(os.path.expanduser('~'), 'Videos'),
        }
        path = known.get(folder_name.lower())
        if path:
            subprocess.Popen(f'explorer "{path}"', shell=True)
            return f"Opened your {folder_name} folder!"
        return f"Opened File Explorer!"


# ─── GENERIC BROWSER ACTIONS ──────────────────────────────────────────────────
def open_url(url):
    try:
        if not url.startswith('http'): url = 'https://' + url
        page = get_page()
        page.goto(url, timeout=15000)
        safe_wait(page, 3000)
        # Give Nova instant page summary
        title = page.title()
        # Get visible text snapshot
        try:
            body = page.locator('body').inner_text()
            snippet = ' '.join(body.split()[:40])
        except:
            snippet = ''
        summary = f"Opened {title}."
        if snippet:
            summary += f" I can see: {snippet[:100]}"
        return summary
    except Exception as e:
        return f"Could not open that page."

def read_current_page():
    """Get a quick summary of what's visible on current page."""
    try:
        page = get_page()
        title = page.title()
        url   = page.url

        # Get all visible text
        body = page.locator('body').inner_text()
        words = ' '.join(body.split()[:60])

        return f"Page: {title}. Content: {words}"
    except:
        return "Can't read current page."
    
def scroll_page(direction='down'):
    try:
        page = get_page()
        page.keyboard.press('PageDown' if direction == 'down' else 'PageUp')
        return f"Scrolled {direction}!"
    except: return "Couldn't scroll."


def click_on_text(text):
    try:
        page = get_page()
        page.get_by_text(text, exact=False).first.click()
        return f"Clicked '{text}'!"
    except: return f"Couldn't find '{text}' to click."


def go_back():
    try: get_page().go_back(); return "Went back!"
    except: return "Couldn't go back."


def go_forward():
    try: get_page().go_forward(); return "Went forward!"
    except: return "Couldn't go forward."


def close_tab():
    try: get_page().close(); return "Closed the tab!"
    except: return "Couldn't close."


# ─── TASK PARSER ─────────────────────────────────────────────────────────────
def parse_browser_task(user_text, groq_api_key):
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        system = """You are a browser automation parser for Nova AI agent.
Parse the user command into ONE browser action JSON.

Available actions:
{"action": "youtube_play", "query": "song or video"}
{"action": "youtube_search", "query": "search term"}
{"action": "google_search", "query": "search query"}
{"action": "open_url", "url": "full or partial url"}
{"action": "scroll_down"}
{"action": "scroll_up"}
{"action": "click_text", "text": "text to click"}
{"action": "go_back"}
{"action": "go_forward"}
{"action": "open_folder", "folder": "downloads"}

Examples:
"open youtube and play shape of you" → {"action": "youtube_play", "query": "shape of you ed sheeran"}
"search youtube for lofi music" → {"action": "youtube_search", "query": "lofi music"}
"open downloads folder" → {"action": "open_folder", "folder": "downloads"}
"scroll down" → {"action": "scroll_down"}
"search google for weather hyderabad" → {"action": "google_search", "query": "weather hyderabad"}
"open instagram" → {"action": "open_url", "url": "instagram.com"}

Return ONLY the JSON. No explanation."""

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


def execute_browser_task(user_text, groq_api_key):
    parsed = parse_browser_task(user_text, groq_api_key)
    if not parsed: return None
    action = parsed.get('action','')

    if action == 'youtube_play':
        return youtube_search_and_play(parsed.get('query',''))
    elif action == 'youtube_search':
        return youtube_search_only(parsed.get('query',''))
    elif action == 'google_search':
        return google_search(parsed.get('query',''))
    elif action == 'open_url':
        return open_url(parsed.get('url',''))
    elif action == 'scroll_down':
        return scroll_page('down')
    elif action == 'scroll_up':
        return scroll_page('up')
    elif action == 'click_text':
        return click_on_text(parsed.get('text',''))
    elif action == 'go_back':
        return go_back()
    elif action == 'go_forward':
        return go_forward()
    elif action == 'open_folder':
        return click_in_explorer(parsed.get('folder','downloads'))
    return None