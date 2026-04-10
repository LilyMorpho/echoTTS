import io
from google.cloud import texttospeech

tts_client = texttospeech.TextToSpeechClient()

def generate_tts_voice(text, setting):
    request = texttospeech.SynthesizeSpeechRequest({
        "input": {"text": str(text)},
        "voice": {"language_code": "ko-KR", "name": str(setting["voice"])},
        "audio_config": {
            "audio_encoding": texttospeech.AudioEncoding.MP3,
            "pitch": float(setting["pitch"]),
            "speaking_rate": float(setting["rate"])
        }
    })

    response = tts_client.synthesize_speech(request=request)

    return io.BytesIO(response.audio_content)