import io
from google.cloud import texttospeech

tts_client = texttospeech.TextToSpeechClient()

def generate_tts_voice(text, setting):
    is_chirp3 = "Chirp3" in str(setting["voice"])
    safe_pitch = 0.0 if is_chirp3 else float(setting["pitch"])

    request = texttospeech.SynthesizeSpeechRequest({
        "input": {"text": str(text)},
        "voice": {"language_code": "ko-KR", "name": str(setting["voice"])},
        "audio_config": {
            "audio_encoding": texttospeech.AudioEncoding.MP3,
            "pitch": safe_pitch,
            "speaking_rate": float(setting["rate"])
        }
    })

    response = tts_client.synthesize_speech(request=request)

    return io.BytesIO(response.audio_content)