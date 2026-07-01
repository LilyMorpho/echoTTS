import discord
from discord.ext import commands

import os
import asyncio
import signal

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
        await self.load_extension("cogs.minigame")
        # 슬래시 커맨드 디스코드 서버와 동기화
        await self.tree.sync()

        try:
            self.loop.add_signal_handler(signal.SIGTERM, lambda: self.loop.create_task(self.stop_bot()))
        except NotImplementedError:
            pass

    async def stop_bot(self):
        print("봇 재시작/종료 중...\n 안전 종료 시퀀스 시작!")

        minigame_cog = self.get_cog("Minigame")
        if minigame_cog:
            try:
                await minigame_cog.force_end_all_games()
                print("진행 중인 미니게임 결과 발표 완료")
            except Exception as e:
                print(f"미니게임 조기 종료 중 에러 발생: {e}")

        for vc in self.voice_clients:
            voice_channel = vc.channel
            try:
                await voice_channel.send(f"👋 **{self.user.name}**이(가) 업데이트를 위해 잠시 채팅방을 떠날거예요. 금방 돌아올게요!")
                await vc.disconnect(force=True)
                print(f"✅ [{voice_channel.guild.name}] 음성 채널 및 내부 채팅방 퇴장 완료")
            except discord.Forbidden:
                print(f"⚠️ 해당 채널에 메시지를 보낼 권한이 없습니다.")
            except Exception as e:
                print(f"⚠️ 메시지 전송 중 에러: {e}")

        print("에코봇을 완전히 종료합니다.")
        await self.close()

bot = TTSBot()

@bot.event
async def on_ready():
    print(f'로그인 및 슬래시 커맨드 준비 완료: {bot.user.name}')

# 봇 토큰 입력
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

async def main():
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"봇 실행 중 오류: {e}")