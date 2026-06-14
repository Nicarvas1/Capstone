import io
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("small")
    return _whisper_model


def transcribir(audio_bytes: bytes) -> str:
    """Transcribe WAV bytes to Spanish text using Whisper (no ffmpeg needed)."""
    model = _get_model()
    buf = io.BytesIO(audio_bytes)
    audio_data, sample_rate = sf.read(buf)

    # Mono
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)

    # Resample to 16 000 Hz
    if sample_rate != 16000:
        g = gcd(int(sample_rate), 16000)
        audio_data = resample_poly(audio_data, 16000 // g, int(sample_rate) // g)

    audio_data = audio_data.astype(np.float32)
    result = model.transcribe(audio_data, language="es", fp16=False)
    return result["text"].strip()
