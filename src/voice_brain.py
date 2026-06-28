"""
Nova Voice Brain — Fixed Version
Fixes:
- No PowerShell for conversational replies
- Playwright runs in dedicated thread (no sync API error)
- Clear text works properly
- Screen context properly injected
- Smart routing prevents nonsense replies
"""

import os, sys, json, queue, time, threading
import sounddevice as sd
import numpy as np
import vosk
import subprocess
import tempfile

# ─── CONFIG ───────────────────────────────────────────────────────────────────
VOSK_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'vosk-model')
WAKE_WORDS      = ['hello nova', 'hello', 'nova', 'hey nova']
STOP_WORDS      = ['stop', 'quiet', 'shut up', 'enough', 'cancel']
BYE_WORDS       = ['bye bye', 'bye', 'goodbye', 'go to sleep', 'sleep']
SAMPLE_RATE     = 16000
DEVICE_INDEX    = 1
SPEECH_RATE     = 1
AWAKE_TIMEOUT   = 300
GROQ_API_KEY    = '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'

# Words that are clearly conversational — never run tools on these
CONVERSATIONAL = [
    'thank you', 'thanks', 'okay', 'ok', 'cool', 'nice', 'great',
    'awesome', 'perfect', 'got it', 'sure', 'yes', 'no', 'maybe',
    'hello', 'hi', 'hey', 'good morning', 'good night', 'bye',
    'what do you think', 'how are you', 'who are you', 'what are you',
    'tell me', 'explain', 'what is', 'who is', 'why is', 'how is',
    'what do you see', 'what can you see', 'describe the screen',
    'what am i doing', 'what is on my screen',
]

# ─── IPC ──────────────────────────────────────────────────────────────────────
def send(event, data=''):
    print(json.dumps({'event': event, 'data': data}), flush=True)

# ─── SPEAKING FLAGS ───────────────────────────────────────────────────────────
is_speaking   = threading.Event()
stop_speaking = threading.Event()

# ─── TTS ──────────────────────────────────────────────────────────────────────
def speak(text, interruptible=True):
    # Never speak raw PowerShell output or error messages
    if text.startswith('Done! ') and any(c in text for c in ['\\', '---', 'MainWindow', 'Directory:']):
        send('log', 'Suppressed raw system output')
        send('state', 'idle')
        return

    send('state', 'speaking')
    is_speaking.set()
    stop_speaking.clear()
    try:
        clean = text.replace("'","").replace('"','').replace('\n',' ').strip()
        if len(clean) > 300: clean = clean[:300]
        ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female)
$s.Rate = {SPEECH_RATE}
$s.Volume = 100
$s.Speak('{clean}')
$s.Dispose()
"""
        proc = [None]
        def run_tts():
            proc[0] = subprocess.Popen(['powershell','-Command',ps],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc[0].wait()
        t = threading.Thread(target=run_tts, daemon=True)
        t.start()
        if interruptible: _listen_for_stop(proc, t)
        else: t.join(timeout=25)
        time.sleep(0.1)
    except Exception as e:
        send('log', f'TTS error: {e}')
    finally:
        is_speaking.clear()
        stop_speaking.clear()
        send('state', 'idle')


def _listen_for_stop(proc, tts_thread):
    try:
        m   = vosk.Model(VOSK_MODEL_PATH)
        rec = vosk.KaldiRecognizer(m, SAMPLE_RATE)
        aq  = queue.Queue()
        def cb(indata, frames, t, status): aq.put(bytes(indata))
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4096,
                               dtype='int16', channels=1,
                               device=DEVICE_INDEX, callback=cb):
            while tts_thread.is_alive():
                try: data = aq.get(timeout=0.1)
                except queue.Empty: continue
                if rec.AcceptWaveform(data):
                    heard = json.loads(rec.Result()).get('text','').lower()
                    if any(s in heard for s in STOP_WORDS):
                        send('log', f'Stop word: "{heard}"')
                        if proc[0] and proc[0].poll() is None: proc[0].kill()
                        stop_speaking.set()
                        break
    except Exception as e:
        tts_thread.join(timeout=25)


# ─── RECORD AUDIO ─────────────────────────────────────────────────────────────
def record_audio(seconds=6):
    send('state', 'listening')
    send('log', 'Recording...')
    aq     = queue.Queue()
    frames = []
    silence       = 0
    spoken        = False
    peak_amplitude = 0
    SILENCE_THRESHOLD = 500   # raised from 300 — filters more background noise
    SPEECH_THRESHOLD  = 800   # must reach this to count as real speech
    SILENCE_LIMIT     = int(SAMPLE_RATE / 1024 * 1.8)

    def cb(indata, frame_count, time_info, status):
        aq.put(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype='int16', blocksize=1024,
                        device=DEVICE_INDEX, callback=cb):
        max_frames = int(SAMPLE_RATE / 1024 * seconds)
        count = 0
        while count < max_frames:
            data = aq.get(); frames.append(data); count += 1
            amplitude = np.abs(data).mean()
            if amplitude > peak_amplitude:
                peak_amplitude = amplitude
            if amplitude > SILENCE_THRESHOLD:
                spoken = True; silence = 0
            elif spoken:
                silence += 1
                if silence >= SILENCE_LIMIT: break

    # If peak amplitude never reached speech threshold — it was just noise
    if peak_amplitude < SPEECH_THRESHOLD:
        send('log', f'No real speech detected (peak={int(peak_amplitude)}), skipping')
        return None

    if not frames: return None
    return np.concatenate(frames, axis=0)

def audio_to_wav_bytes(audio):
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE); wf.writeframes(audio.tobytes())
    buf.seek(0); return buf.read()


# ─── WHISPER STT ──────────────────────────────────────────────────────────────
def transcribe_audio(audio):
    if audio is None or len(audio) < SAMPLE_RATE * 0.3: return ''
    try:
        from groq import Groq
        client    = Groq(api_key=GROQ_API_KEY)
        wav_bytes = audio_to_wav_bytes(audio)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(wav_bytes); tmp_path = tmp.name
        try:
            with open(tmp_path, 'rb') as f:
                result = client.audio.transcriptions.create(
                    model='whisper-large-v3-turbo',
                    file=('audio.wav', f, 'audio/wav'),
                    language='en',
                    prompt='Nova AI assistant command'
                )
            text = result.text.strip()

            # ── Filter out noise transcriptions ──
            words = text.split()

            # Too short — likely noise
            if len(words) < 2:
                send('log', f'Ignored short transcription: "{text}"')
                return ''

            # Looks like a single name or random word with no context
            noise_patterns = [
                'thank you', 'thanks', 'hmm', 'um', 'uh',
                'mm', 'ah', 'oh', 'okay', 'ok'
            ]
            if len(words) == 2 and text.lower().strip('.') in noise_patterns:
                send('log', f'Ignored noise: "{text}"')
                return ''

            send('log', f'Whisper: "{text}"')
            return text
        finally:
            try: os.unlink(tmp_path)
            except: pass
    except Exception as e:
        send('log', f'Whisper error: {e}')
        return ''


def record_command(seconds=6):
    audio = record_audio(seconds)
    if audio is None: return ''
    return transcribe_audio(audio)


# ─── PLAYWRIGHT THREAD ────────────────────────────────────────────────────────
# Playwright sync API must run in its own thread — never call from voice thread
_browser_queue  = queue.Queue()
_browser_result = {}
_browser_lock   = threading.Lock()

def _browser_worker():
    """Dedicated thread for all Playwright operations."""
    while True:
        try:
            task_id, func, args, kwargs = _browser_queue.get(timeout=1)
            try:
                result = func(*args, **kwargs)
                with _browser_lock:
                    _browser_result[task_id] = ('ok', result)
            except Exception as e:
                with _browser_lock:
                    _browser_result[task_id] = ('err', str(e)[:100])
        except queue.Empty:
            continue

_browser_thread = threading.Thread(target=_browser_worker, daemon=True)
_browser_thread.start()

def run_in_browser_thread(func, *args, timeout=20, **kwargs):
    """Submit a Playwright task and wait for result."""
    import uuid
    task_id = str(uuid.uuid4())
    _browser_queue.put((task_id, func, args, kwargs))
    deadline = time.time() + timeout
    while time.time() < deadline:
        with _browser_lock:
            if task_id in _browser_result:
                status, val = _browser_result.pop(task_id)
                if status == 'ok': return val
                else: return f"Browser error: {val}"
        time.sleep(0.1)
    return "Browser timed out."


# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────
conversation_history = []

def is_conversational(text):
    """Check if text is purely conversational — no tools needed."""
    t = text.lower().strip().rstrip('.')
    # Exact match
    if t in CONVERSATIONAL: return True
    # Starts with conversational phrase
    conv_starts = ['thank', 'what do you', 'what can you', 'who are',
                   'how are', 'tell me about', 'explain', 'what is ',
                   'who is ', 'why ', 'how does', 'describe the screen',
                   'what am i', 'what is on']
    if any(t.startswith(c) for c in conv_starts): return True
    return False


def handle_command(user_text):
    send('state', 'thinking')
    if not GROQ_API_KEY or GROQ_API_KEY == 'PASTE-YOUR-GROQ-KEY-HERE':
        return "Please add your Groq API key."

    text_lower = user_text.lower().strip().rstrip('.')

    # ── Purely conversational — go straight to AI ──
    if is_conversational(text_lower):
        return ask_ai(user_text)

    try:
        # ── Clear text ──
        if any(p in text_lower for p in ['clear text', 'clear the text',
               'remove text', 'delete text', 'erase text', 'clear search',
               'remove search', 'clear input', 'clear field']):
            import pyautogui
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('delete')
            return "Cleared the text!"

        # ── Screen description ──
        if any(p in text_lower for p in ['what do you see', 'what can you see',
               'describe the screen', 'what is on screen', 'what am i doing',
               'what is on my screen', 'tell me what you see']):
            return describe_screen()

        # ── Chrome/browser commands — use real Chrome via CDP ──
        chrome_triggers = [
            'tab', 'tabs', 'chrome', 'browser', 'click on', 'scroll',
            'go back', 'go forward', 'search youtube', 'search google',
            'type in', 'navigate to', 'open new tab', 'close tab',
            'youtube', 'google', 'play ', 'search for', 'in the browser',
            'in chrome', 'in google', 'in youtube', 'open tab'
        ]
        is_chrome_cmd = any(t in text_lower for t in chrome_triggers)

        if is_chrome_cmd:
            try:
                from chrome_agent import execute_chrome_command, is_chrome_running
                result = execute_chrome_command(user_text, GROQ_API_KEY)
                if result and 'error' not in result.lower() \
                           and "couldn't find" not in result.lower():
                    send('log', f'Chrome agent: {result}')
                    return result
            except Exception as e:
                send('log', f'Chrome agent error: {e}')

        # ── Open/launch → task executor ──
        open_triggers = ['open ', 'launch ', 'start ', 'run ']
        is_open = any(text_lower.startswith(t) for t in open_triggers)

        if not is_open:
            # ── Other interactions → UI agent ──
            interact_triggers = [
                'press', 'select', 'tap', 'write', 'enter text',
                'insert text', 'type', 'inside', 'on the page'
            ]
            is_interact = any(t in text_lower for t in interact_triggers)
            if is_interact:
                try:
                    from ui_agent import execute_ui_command
                    result = execute_ui_command(user_text, GROQ_API_KEY)
                    if result and 'not open' not in result \
                               and "couldn't find" not in result.lower() \
                               and 'error' not in result.lower():
                        send('log', f'UI agent: {result}')
                        return result
                except Exception as e:
                    send('log', f'UI agent error: {e}')

        # ── Task executor (open apps, folders, screenshots) ──
        from task_executor import route_command_with_browser, execute_tool
        parsed = route_command_with_browser(user_text, GROQ_API_KEY)
        tool   = parsed.get('tool', 'answer')
        args   = parsed.get('args', {})
        send('log', f'Tool: {tool} args: {args}')

        if tool not in ('browser', 'answer'):
            result = execute_tool(tool, args)
            if result: return result

        # ── Normal AI answer ──
        return ask_ai(user_text)

    except Exception as e:
        send('log', f'Router error: {e}')
        return ask_ai(user_text)


def describe_screen():
    """Describe what's currently on screen."""
    try:
        from screen_watcher import get_context_string
        ctx = get_context_string()
        if not ctx or ctx == 'No screen context available.':
            return "I can see your screen but couldn't read much text right now."
        return ask_ai(f"Based on this screen context, describe what the user is doing in 1-2 sentences: {ctx}")
    except:
        return "I'm having trouble reading the screen right now."


def ask_ai(user_text):
    """Conversational AI with screen context."""
    try:
        from groq import Groq
        try:
            from screen_watcher import get_context_string
            ctx = get_context_string()
        except: ctx = ''

        client = Groq(api_key=GROQ_API_KEY)
        system = f"""You are Nova, a friendly AI desktop companion shaped like a tiny turtle.
You sit near the user cursor and help with anything.
{'Current screen: ' + ctx[:300] if ctx else ''}
Keep replies SHORT — 1 to 2 sentences max. Warm, playful, helpful.
Never use bullet points or markdown.
Never output system data, file paths, or raw command output.
Speak naturally like a friendly assistant."""

        conversation_history.append({'role': 'user', 'content': user_text})
        r = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            max_tokens=150,
            messages=[{'role': 'system', 'content': system},
                      *conversation_history[-12:]]
        )
        reply = r.choices[0].message.content.strip()
        conversation_history.append({'role': 'assistant', 'content': reply})
        return reply
    except Exception as e:
        send('log', f'AI error: {e}')
        return "I had trouble thinking, try again?"


# ─── WAKE MODEL ───────────────────────────────────────────────────────────────
def load_wake_model():
    if not os.path.exists(VOSK_MODEL_PATH):
        send('error', f'Vosk model not found: {VOSK_MODEL_PATH}')
        sys.exit(1)
    send('log', 'Loading wake word model...')
    m = vosk.Model(VOSK_MODEL_PATH)
    send('log', 'Wake word model ready!')
    return m


# ─── CONVERSATION MANAGER ─────────────────────────────────────────────────────
class ConversationManager:
    def __init__(self):
        self.awake=False; self.last_active=0
        self.timer=None; self.lock=threading.Lock()

    def wake_up(self):
        with self.lock: self.awake=True; self.last_active=time.time()
        self._schedule_check()

    def touch(self):
        with self.lock: self.last_active=time.time()

    def is_awake(self):
        with self.lock: return self.awake

    def sleep(self):
        with self.lock: self.awake=False
        if self.timer: self.timer.cancel()
        send('state','idle')

    def _schedule_check(self):
        if self.timer: self.timer.cancel()
        self.timer=threading.Timer(10, self._check_timeout)
        self.timer.daemon=True; self.timer.start()

    def _check_timeout(self):
        with self.lock:
            if not self.awake: return
            elapsed=time.time()-self.last_active
        if elapsed >= AWAKE_TIMEOUT: self.sleep()
        else: self._schedule_check()

conv = ConversationManager()

def flush_queue(q):
    while not q.empty():
        try: q.get_nowait()
        except: break


# ─── MAIN LOOP ────────────────────────────────────────────────────────────────
def listen_for_wake_word(wake_model):
    send('log', 'Nova ready. Say "Hello Nova"!')
    send('state', 'idle')
    rec = vosk.KaldiRecognizer(wake_model, SAMPLE_RATE)
    aq  = queue.Queue()

    def cb(indata, frames, t, status):
        if not is_speaking.is_set(): aq.put(bytes(indata))

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4096,
                           dtype='int16', channels=1,
                           device=DEVICE_INDEX, callback=cb):
        send('ready', 'Nova is ready!')

        while True:
            if is_speaking.is_set(): time.sleep(0.05); continue
            try: data = aq.get(timeout=0.5)
            except queue.Empty: continue

            if conv.is_awake():
                if rec.AcceptWaveform(data):
                    partial = json.loads(rec.Result()).get('text','').strip()
                    # Only proceed if Vosk detected something meaningful
                    if not partial or len(partial) < 2:
                        continue

                    flush_queue(aq)
                    send('log', 'Speech detected, transcribing...')
                    audio = record_audio(seconds=7)

                    # No real speech — stay silent, stay awake
                    if audio is None:
                        rec = vosk.KaldiRecognizer(wake_model, SAMPLE_RATE)
                        continue

                    text = transcribe_audio(audio)

                    # Empty or filtered — stay silent
                    if not text or len(text.split()) < 2:
                        rec = vosk.KaldiRecognizer(wake_model, SAMPLE_RATE)
                        continue

                    text_lower = text.lower().strip()
                    send('log', f'Command: "{text}"')

                    if any(b in text_lower for b in BYE_WORDS):
                        conv.touch()
                        speak("Goodbye! Say Hello Nova when you need me.",
                              interruptible=False)
                        conv.sleep()
                        flush_queue(aq)
                        rec = vosk.KaldiRecognizer(wake_model, SAMPLE_RATE)
                        continue

                    if any(w == text_lower for w in WAKE_WORDS):
                        conv.touch(); continue

                    conv.touch()
                    reply = handle_command(text)
                    send('log', f'Reply: "{reply}"')
                    send('state', 'happy')
                    time.sleep(0.1)
                    speak(reply)
                    flush_queue(aq)
                    rec = vosk.KaldiRecognizer(wake_model, SAMPLE_RATE)

            else:
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get('text','').lower()
                    if any(wake in text for wake in WAKE_WORDS):
                        send('log', f'Wake word: "{text}"')
                        send('wake', 'detected')
                        conv.wake_up()
                        speak("Hey! I'm here. What do you need?", interruptible=False)
                        audio   = record_audio(seconds=8)
                        command = transcribe_audio(audio)
                        send('log', f'First command: "{command}"')
                        if command and len(command) > 1:
                            if any(b in command.lower() for b in BYE_WORDS):
                                speak("Okay, going to sleep!", interruptible=False)
                                conv.sleep()
                            else:
                                conv.touch()
                                reply = handle_command(command)
                                send('log', f'Reply: "{reply}"')
                                send('state', 'happy')
                                time.sleep(0.1)
                                speak(reply)
                        else:
                            speak("I'm here! Talk to me.", interruptible=False)
                        flush_queue(aq)
                        rec = vosk.KaldiRecognizer(wake_model, SAMPLE_RATE)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    global GROQ_API_KEY
    if len(sys.argv) > 1 and sys.argv[1]: GROQ_API_KEY = sys.argv[1]

    try:
        from screen_watcher import start_screen_watcher
        start_screen_watcher()
        send('log', 'Screen watcher started!')
    except Exception as e:
        send('log', f'Screen watcher: {e}')

    wake_model = load_wake_model()
    listen_for_wake_word(wake_model)

if __name__ == '__main__':
    main()
