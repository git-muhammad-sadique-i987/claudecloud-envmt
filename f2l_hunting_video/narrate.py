"""Voiceover: one cached WAV clip per spoken line.

Engines, in order of preference:
  ElevenLabs  set ELEVENLABS_KEY_FILE to a text file holding your API key (or ELEVENLABS_API_KEY to the key);
              ELEVENLABS_VOICE picks the voice id (default George), ELEVENLABS_MODEL the model (default eleven_v4)
  Edge        set EDGE_VOICE to a Microsoft Edge neural voice, e.g. en-US-AndrewMultilingualNeural
              (needs the edge-tts package and an internet connection; no account or key)
  Kokoro     set KOKORO_MODEL and KOKORO_VOICES to kokoro-v1.0(.int8).onnx and voices-v1.0.bin
              (KOKORO_VOICE picks the voice, default af_heart)
  Piper       set PIPER_VOICE to a Piper .onnx voice model
  SAPI        the built-in Windows voice (fallback)
NARRATION_SPEED overrides the speaking speed (1.0 = the voice's normal pace).
"""
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import wave

import numpy as np

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "narration_cache")
RATE = 24000
SPEED = {"elevenlabs": 0.95, "edge": 0.95, "kokoro": 0.9}  # a touch slower than each voice's default
ELEVEN_SETTINGS = dict(stability=0.45, similarity_boost=0.75, style=0.15, use_speaker_boost=True)
_voice = None


def speakable(text):
    """Turn cube notation into words the TTS reads naturally: R' -> 'R prime', U2 -> 'U two'.

    '!' becomes '.', so the voice stays calm instead of sounding excited, and '^' (a timing mark) is dropped.
    """
    def tok(m):
        base, mod = m.group(1), m.group(2)
        return base + {"'": " prime", "2": " two", "": ""}[mod]
    t = text.replace("**", "").replace("^", "").replace("!", ".")
    t = t.replace("→", ", then").replace("·", ",").replace("F2L", "F two L")
    t = re.sub(r"(?<![A-Za-z])([RUFLDB])(2|'|)(?![A-Za-z0-9])", tok, t)
    return t


def _eleven_key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"].strip()
    with open(os.environ["ELEVENLABS_KEY_FILE"], encoding="utf-8") as f:
        return f.read().strip()


def engine():
    if os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVENLABS_KEY_FILE"):
        voice = os.environ.get("ELEVENLABS_VOICE", "JBFqnCBsd6RMkjVDRZzb")
        model = os.environ.get("ELEVENLABS_MODEL", "eleven_v4")
        return "elevenlabs", f"{voice}/{model}/{json.dumps(ELEVEN_SETTINGS, sort_keys=True)}"
    if os.environ.get("EDGE_VOICE"):
        return "edge", os.environ["EDGE_VOICE"]
    if os.environ.get("KOKORO_MODEL"):
        return "kokoro", os.environ.get("KOKORO_VOICE", "af_heart")
    if os.environ.get("PIPER_VOICE"):
        return "piper", os.environ["PIPER_VOICE"]
    return "sapi", ""


def _write(a, sr, path):
    """Trim the silence around a line and save it as 16-bit mono WAV."""
    loud = np.flatnonzero(np.abs(a) > 0.01)
    if len(loud):
        a = a[max(0, loud[0] - int(0.03 * sr)):loud[-1] + int(0.08 * sr)]
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def _elevenlabs(text, path, voice, speed, prev, nxt):
    voice_id, model, _ = voice.split("/", 2)
    body = dict(text=text, model_id=model, voice_settings=dict(ELEVEN_SETTINGS, speed=speed))
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_{RATE}"
    for attempt in range(5):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"xi-api-key": _eleven_key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                pcm = r.read()
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"ElevenLabs HTTP {e.code}: {detail}") from None
    _write(np.frombuffer(pcm, "<i2").astype(np.float32) / 32768, RATE, path)


def _edge(text, path, voice, speed):
    import asyncio
    import edge_tts

    async def fetch():
        audio = b""
        async for chunk in edge_tts.Communicate(text, voice, rate=f"{round((speed - 1) * 100):+d}%").stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio
    for attempt in range(5):
        try:
            mp3 = asyncio.run(fetch())
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", "-", "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-"],
                         input=mp3, capture_output=True, check=True).stdout
    _write(np.frombuffer(pcm, "<i2").astype(np.float32) / 32768, RATE, path)


def _kokoro(text, path, voice, speed):
    global _voice
    from kokoro_onnx import Kokoro
    if _voice is None:
        _voice = Kokoro(os.environ["KOKORO_MODEL"], os.environ["KOKORO_VOICES"])
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, sr = _voice.create(text, voice=voice, speed=speed, lang=lang)
    _write(np.asarray(samples, np.float32), sr, path)


def _piper(text, path):
    global _voice
    from piper import PiperVoice
    if _voice is None:
        _voice = PiperVoice.load(os.environ["PIPER_VOICE"])
    with wave.open(path, "wb") as wf:
        _voice.synthesize_wav(text, wf)


def _sapi(text, path):
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.Rate = 0; $f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, "
          "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono); "
          "$s.SetOutputToWaveFile($env:TTS_OUT, $f); $s.Speak($env:TTS_TEXT); $s.Dispose()")
    env = dict(os.environ, TTS_OUT=path, TTS_TEXT=text)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, check=True)


def _path(text, speed=None):
    eng, voice = engine()
    speed = speed or float(os.environ.get("NARRATION_SPEED", 0)) or SPEED.get(eng, 1.0)
    key = hashlib.sha1(f"{eng}|{voice}|{speed}|{speakable(text)}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{key}.wav"), eng, voice, speed


def clip(text, speed=None, prev=None, nxt=None):
    """Path and duration (seconds) of the narration clip for `text`, generating it if needed.

    prev/nxt are the neighbouring lines; ElevenLabs uses them so the delivery flows from line to line.
    """
    os.makedirs(CACHE, exist_ok=True)
    path, eng, voice, speed = _path(text, speed)
    if not os.path.exists(path):
        tmp = path + ".tmp.wav"
        spoken = speakable(text)
        if eng == "elevenlabs":
            _elevenlabs(spoken, tmp, voice, speed, prev and speakable(prev), nxt and speakable(nxt))
        elif eng == "edge":
            _edge(spoken, tmp, voice, speed)
        elif eng == "kokoro":
            _kokoro(spoken, tmp, voice, speed)
        elif eng == "piper":
            _piper(spoken, tmp)
        else:
            _sapi(spoken, tmp)
        os.replace(tmp, path)
    with wave.open(path) as wf:
        return path, wf.getnframes() / wf.getframerate()


def prepare(lines):
    """Voice every line that isn't cached yet, in script order, each with its neighbours as context."""
    todo = [k for k, t in enumerate(lines) if not os.path.exists(_path(t)[0])]
    if todo:
        chars = sum(len(speakable(lines[k])) for k in todo)
        print(f"voicing {len(todo)} of {len(lines)} lines ({chars} characters) with {engine()[0]}", flush=True)
    for n, k in enumerate(todo, 1):
        clip(lines[k], prev=lines[k - 1] if k else None, nxt=lines[k + 1] if k + 1 < len(lines) else None)
        if n % 10 == 0:
            print(f"  {n}/{len(todo)}", flush=True)


def read_mono(path):
    with wave.open(path) as wf:
        sr, ch, n = wf.getframerate(), wf.getnchannels(), wf.getnframes()
        a = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if sr != RATE:
        a = np.interp(np.arange(0, len(a), sr / RATE), np.arange(len(a)), a)
    return a


def mix(cues, total_seconds, out):
    """Place each (start_seconds, wav_path, ...) cue on one track and write a 16-bit mono WAV."""
    track = np.zeros(int(total_seconds * RATE) + RATE, np.float32)
    for start, path, *_ in cues:
        a = read_mono(path)
        i = int(start * RATE)
        n = min(len(a), len(track) - i)
        track[i:i + n] += a[:n]
    peak = max(1e-6, float(np.abs(track).max()))
    track *= min(1.0, 0.89 / peak)
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes((track * 32767).astype(np.int16).tobytes())


def srt(cues, out):
    """Closed captions (SubRip) from (start, wav_path, text, duration) cues."""
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(out, "w", encoding="utf-8") as f:
        for k, (start, _, text, dur) in enumerate(cues, 1):
            f.write(f"{k}\n{ts(start)} --> {ts(start + dur)}\n{text.replace('**', '')}\n\n")
