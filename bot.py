import discord
from discord.ext import commands

import os

from dotenv import load_dotenv
load_dotenv()

import db


class TTSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # DB 모듈 초기화
        await db.setup_db()
        # cogs 안의 tts_core 로직과 목소리 설정 UI 불러오기
        await self.load_extension("cogs.tts_core")
        await self.load_extension("cogs.tts_settings")
        # 슬래시 커맨드 디스코드 서버와 동기화
        await self.tree.sync()

bot = TTSBot()

@bot.event
async def on_ready():
    print(f'로그인 및 슬래시 커맨드 준비 완료: {bot.user.name}')

# 봇 토큰 입력
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(DISCORD_TOKEN)