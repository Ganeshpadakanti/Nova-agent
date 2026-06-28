import subprocess

text = "Hello I am Nova your AI assistant"

ps_script = """
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = 1
$s.Volume = 100
$s.Speak('""" + text + """')
"""

subprocess.run(['powershell', '-Command', ps_script], timeout=30)
print("Done")