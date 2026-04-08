import re

import httpx
from bs4 import BeautifulSoup

replace_dict = {
    "ㄳ": "감사",
    "ㄱㅅ": "감사",
    "ㄱㄱ": "고고",
    "ㄴㄴ": "노노",
    "ㄷㄷ": "덜덜",
    "ㅂㅂ": "바바",
    "ㅇㅇ": "응응",
    "ㅊㅊ": "축축",
    "ㅌㅌ": "튀튀",
    "ㅋ": "크",
    "ㅎ": "흐",
    "ㄱㄷ": "기달",
    "ㄱㅊ": "괜찮",
    "ㄹㅇ": "레알",
    "ㅁㅊ": "미친",
    "ㅂㄷ": "부들",
    "ㅂㅇ": "바이",
    "ㅂ2": "바이",
    "ㅅㄱ": "수고",
    "ㅅㅂ": "시발",
    "ㅈㅅ": "죄송",
    "ㅗ": "엿",
    "ghoti": "fish" # 이스터에그
}
MAX_LENGTH = 100

async def get_link_title(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                if soup.title and soup.title.string:
                    title = soup.title.string.strip()
                    return title
    except Exception:
        pass

    return ""

async def replace_text(text):
    # 스포일러 태그 안의 텍스트 무시
    text = re.sub(r'\|\|.*?\|\|', '', text)
    # 디스코드 커스텀 이모지 처리(연속된 이모티콘 묶어서 처리)
    text = re.sub(r'(?:<a?:\w+:\d+>\s*)+', ' 이모티콘 ', text)
    # 링크 감지
    urls = re.findall(r'https?://\S+', text)
    if urls:
        for url in urls:
            title = await get_link_title(url)
            text = text.replace(url, f"링크 {title}")
    # 반복문자 줄이기
    text = re.sub(r'([ㅋㅎㅜㅠ])\1{4,}', r'\1\1\1\1\1', text)
    # 줄임말 풀어서 읽기
    for short, full in replace_dict.items():
        text = text.replace(short, full)

    text = text.strip()

    if text == "이모티콘":
        text = "이모티콘을 보냈어요."

    if len(text) > MAX_LENGTH:
        text = "너무 긴 글은 읽을 수 없어요."

    return text