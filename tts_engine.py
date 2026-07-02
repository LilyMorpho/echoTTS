import io
import time
from google.cloud import texttospeech
from google.api_core.exceptions import GoogleAPIError

tts_client = texttospeech.TextToSpeechClient()

def generate_tts_voice(text, setting):
    is_chirp3 = "Chirp3" in str(setting["voice"])
    safe_pitch = 0.0 if is_chirp3 else float(setting["pitch"])

    ssml_content = f"<speak>{str(text)}</speak>"

    request = texttospeech.SynthesizeSpeechRequest({
        "input": {"ssml": ssml_content},
        "voice": {"language_code": "ko-KR", "name": str(setting["voice"])},
        "audio_config": {
            "audio_encoding": texttospeech.AudioEncoding.MP3,
            "pitch": safe_pitch,
            "speaking_rate": float(setting["rate"])
        }
    })

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = tts_client.synthesize_speech(request=request)
            return io.BytesIO(response.audio_content)

        except GoogleAPIError as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 구글 TTS 서버 지연. 재시도 중... ({attempt + 1}/{max_retries})", flush=True)
                time.sleep(0.5)  # 1.5초 대기 후 다시 요청
            else:
                print(f"❌ 구글 TTS 서버 최종 응답 없음: {e}", flush=True)
                raise

    response = tts_client.synthesize_speech(request=request)

    return io.BytesIO(response.audio_content)