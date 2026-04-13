import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import os
import uuid

import db
from tts_engine import generate_tts_voice
from text_filter import replace_text

class TTSCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_tts_channels = {}
        self.tts_queues = {}
        self.is_processing = {}

    async def prepare_tts(self, text, user_id):
        # 메시지 처리
        processed_content = await replace_text(text)
        # DB 모듈에서 설정 가져오기
        setting = await db.get_user_settings(user_id)
        # TTS 엔진 모듈에서 메모리 버퍼를 받아오기
        voice_buffer = await asyncio.to_thread(generate_tts_voice, processed_content, setting)
        return voice_buffer

    async def process_and_play(self, guild):
        # 이미 다른 채팅을 읽고 처리하는 중이라면 돌아감.
        if self.is_processing.get(guild.id, False): return

        vc = guild.voice_client
        # 봇이 음성 채널에 없으면 스킵
        if not vc or not vc.is_connected():
            self.is_processing[guild.id] = False
            return

        if guild.id in self.tts_queues and len(self.tts_queues[guild.id]) > 0:
            # 이 채팅을 다 읽기 전까지 다른 채팅 대기
            self.is_processing[guild.id] = True

            # 백그라운드에서 돌아가는 작업을 순서대로 꺼냄
            gen_task = self.tts_queues[guild.id].pop(0)

            try:
                voice_buffer = await gen_task
                # 임시 파일 저장(uuid를 사용, 겹칠 확률이 없는 고유 파일 생성)
                unique_id = uuid.uuid4()
                file_path = f"tts_temp_{guild.id}_{unique_id}.mp3"

                with open(file_path, "wb") as f:
                    f.write(voice_buffer.read())

                def after_play(error):
                    self.is_processing[guild.id] = False
                    # 재생이 끝난 후, 해당 임시 파일만 깔끔하게 삭제
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    # 백그라운드 스레드에서 메인 루프로 안전하게 다음 큐 지시
                    asyncio.run_coroutine_threadsafe(self.process_and_play(guild), self.bot.loop)

                vc.play(discord.FFmpegPCMAudio(file_path), after=after_play)

            except Exception as e:
                print(f"TTS 에러: {e}")
                self.is_processing[guild.id] = False
                # 에러가 나더라도 다른 채팅을 읽을 수 있도록 조치
                asyncio.run_coroutine_threadsafe(self.process_and_play(guild), self.bot.loop)
        else:
            self.is_processing[guild.id] = False

    # =============== 디스코드 명령어 ===============

    @app_commands.command(name="에코_입장", description="이 채팅방에 올라오는 모든 글을 음성 채널에서 읽어줍니다.")
    async def start_tts(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("먼저 음성 채널에 들어가서 명령어를 써주세요!", ephemeral=True)
            return

        vc = interaction.guild.voice_client
        voice_channel = interaction.user.voice.channel

        # 음성 채널 접속
        if not vc:
            await voice_channel.connect(self_deaf=True)
        else:
            await vc.move_to(voice_channel)

        # 현재 슬래시 커맨드를 친 '텍스트 채널'을 주시 대상으로 등록
        self.auto_tts_channels[interaction.guild.id] = interaction.channel_id
        self.tts_queues[interaction.guild.id] = []  # 대기열 초기화

        await interaction.response.send_message(f"✅ 지금부터 봇이 음성 채널에 접속하여 이 채널의 채팅을 순서대로 읽어줍니다!")

    @app_commands.command(name="에코_잘가", description="자동 읽기를 종료하고 봇을 내보냅니다.")
    async def stop_tts(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()

        # 주시 대상 및 대기열 삭제
        if interaction.guild.id in self.auto_tts_channels:
            del self.auto_tts_channels[interaction.guild.id]
        if interaction.guild.id in self.tts_queues:
            del self.tts_queues[interaction.guild.id]

        await interaction.response.send_message("🛑 자동 읽기를 종료하고 퇴장합니다.")

    # =============== 이벤트 감지 ===============

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 봇이 친 채팅은 무시
        if message.author.bot: return

        # 이 서버에 TTS 봇이 켜져 있는지 확인
        if message.guild.id in self.auto_tts_channels and message.channel.id == self.auto_tts_channels[message.guild.id]:
            # 사진(첨부파일) 확인
            attachment_text = ""
            if message.attachments:
                # 첨부파일 중 '이미지'가 몇 개인지 확인
                photo_count = sum(1 for a in message.attachments if a.content_type.startswith("image/"))
                if photo_count == 1:
                    attachment_text += "사진을 보냈어요. "
                elif photo_count > 1:
                    attachment_text += "여러 장의 사진을 보냈어요. "
            if message.stickers:
                attachment_text += "스티커를 보냈어요. "

            reply_prefix = ""
            if message.reference is not None:
                reply_prefix = "답장 : "

            raw_text = reply_prefix + attachment_text + message.clean_content

            # 내용이 없는 채팅 무시하기
            if not raw_text.strip(): return

            # 대기열에 채팅 추가
            if message.guild.id not in self.tts_queues:
                self.tts_queues[message.guild.id] = []

            # 텍스트를 직접 대기열에 넣지 않고, 파일을 생성하는 백그라운드 작업을 즉시 실행 후 작업을 대기열에 넣음.
            gen_task = asyncio.create_task(self.prepare_tts(raw_text.strip(), message.author.id))
            self.tts_queues[message.guild.id].append(gen_task)

            # tts 음성 처리 함수 호출 (이미 재생 중이면 알아서 무시하고 큐에만 담김)
            await self.process_and_play(message.guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

        # 현재 봇이 이 서버의 음성 채널에 연결되어 있는지 확인
        vc = member.guild.voice_client
        if not vc or not vc.is_connected(): return

        # 누군가 음성 채널을 '떠났거나', '다른 채널로 이동'했을 때
        if before.channel and before.channel == vc.channel:
            # 봇이 있는 채널에 남은 멤버 수를 세어봄
            # (멤버 수가 1명이고, 그 1명이 봇 자신일 경우)
            if len(vc.channel.members) == 1 and vc.channel.members[0].id == self.bot.user.id:
                # 1. 음성 채널에서 봇 퇴장
                await vc.disconnect()
                # 2. 주시 중이던 텍스트 채널 및 큐(Queue) 데이터 초기화
                if member.guild.id in self.auto_tts_channels:
                    del self.auto_tts_channels[member.guild.id]
                if member.guild.id in self.tts_queues:
                    del self.tts_queues[member.guild.id]

                print(f"🚪 [{member.guild.name}] 유저가 모두 떠나서 봇이 자동 퇴장했습니다.")

async def setup(bot):
    await bot.add_cog(TTSCore(bot))