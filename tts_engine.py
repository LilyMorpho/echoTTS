
from google.cloud import texttospeech

def generate_tts_file(text, user_id, setting):
    client = texttospeech.TextToSpeechClient()

    request = texttospeech.SynthesizeSpeechRequest({
        "input": {"text": str(text)},
        "voice": {"language_code": "ko-KR", "name": str(setting["voice"])},
        "audio_config": {
            "audio_encoding": texttospeech.AudioEncoding.MP3,
            "pitch": float(setting["pitch"]),
            "speaking_rate": float(setting["rate"])
        }
    })

    response = client.synthesize_speech(request=request)
    filename = f"tts_temp_{user_id}.mp3"

    with open(filename, "wb") as out:
        out.write(response.audio_content)

    return filename