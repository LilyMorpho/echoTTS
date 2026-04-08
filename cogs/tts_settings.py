import discord
from discord import app_commands
from discord.ext import commands
from discord import ui

import db

# =============== UI 화면 생성 ===============

def show_settings_embed(user: discord.User, voice: str, pitch: float, rate: float): # 현재 설정을 보여주는 임베드 생성
    embed = discord.Embed(
        title=f"{user.display_name}의 목소리 설정",
        description="현재 적용된 목소리 정보입니다. 아래 메뉴를 통해 수정할 수 있습니다.",
        color=discord.Color.blue()
    )
    embed.add_field(name="🗣️ 목소리 종류", value=f"`{voice}`", inline=False)
    embed.add_field(name="🎼 음높이 (Pitch)", value=f"`{pitch}`", inline=True)
    embed.add_field(name="⏩ 속도 (Rate)", value=f"`{rate}x`", inline=True)
    embed.set_thumbnail(url=user.display_avatar.url) # 우측 상단에 유저 프로필 사진 표시
    return embed

# =============== UI 컴포넌트 ===============

class DetailSettingsModal(ui.Modal, title="음높이 및 속도 조절"):
    pitch_input = ui.TextInput(label="음높이 (-20.0 ~ 20.0)", style=discord.TextStyle.short, placeholder="기본값: 0.0")
    rate_input = ui.TextInput(label="말하는 속도 (0.25 ~ 4.0)", style=discord.TextStyle.short, placeholder="기본값: 1.0")

    def __init__(self, current_voice: str, current_pitch: float, current_rate: float):
        super().__init__()
        # 현재 설정 값 저장(DB 저장 시 사용)
        self.current_voice = current_voice
        # 모달 창을 열었을 때 기존 설정값이 칸 안에 미리 적혀있도록 설정
        self.pitch_input.default = str(current_pitch)
        self.rate_input.default = str(current_rate)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력받은 내용을 숫자(float)로 바꾸고, 허용 범위 내에 들어오게 처리.
            new_pitch = max(-20.0, min(20.0, float(self.pitch_input.value)))
            new_rate = max(0.25, min(4.0, float(self.rate_input.value)))
            # DB에 변경된 값 저장
            await db.save_user_setting(interaction.user.id, self.current_voice, new_pitch, new_rate)
            # 화면을 변경된 설정 값으로 새로고침
            embed = show_settings_embed(interaction.user, self.current_voice, new_pitch, new_rate)
            view = VoiceSettingsView(self.current_voice, new_pitch, new_rate)
            await interaction.response.edit_message(embed=embed, view=view)
        except ValueError: # 숫자가 아닌 형식으로 입력되었을 때 에러 처리
            await interaction.response.send_message("❌ 숫자를 정확히 입력해 주세요!", ephemeral=True)

class VoiceSelect(ui.Select):
    def __init__(self, current_voice: str):
        options = [
            discord.SelectOption(label="👩 또렷한 여성 (WaveNet-A)", value="ko-KR-Wavenet-A", emoji="👩", default=(current_voice=="ko-KR-Wavenet-A")),
            discord.SelectOption(label="👩 친근한 여성 (WaveNet-B)", value="ko-KR-Wavenet-B", emoji="👧", default=(current_voice=="ko-KR-Wavenet-B")),
            discord.SelectOption(label="👨 중후한 남성 (WaveNet-C)", value="ko-KR-Wavenet-C", emoji="👨", default=(current_voice=="ko-KR-Wavenet-C")),
            discord.SelectOption(label="👨 명쾌한 남성 (WaveNet-D)", value="ko-KR-Wavenet-D", emoji="👦", default=(current_voice=="ko-KR-Wavenet-D")),
        ]
        super().__init__(placeholder="변경할 목소리를 선택하세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction): # 드롭다운 메뉴에서 특정 목소리를 선택했을 때 실행
        new_voice = self.values[0] # 유저가 선택한 목소리 값
        # 현재 음높이와 속도는 View 객체에서 불러오기(기존 값 유지)
        current_pitch = self.view.pitch
        current_rate = self.view.rate
        # DB에 변경된 목소리 저장
        await db.save_user_setting(interaction.user.id, new_voice, current_pitch, current_rate)
        # 화면을 변경된 목소리로 새로고침
        embed = show_settings_embed(interaction.user, new_voice, current_pitch, current_rate)
        view = VoiceSettingsView(new_voice, current_pitch, current_rate)
        await interaction.response.edit_message(embed=embed, view=view)

class VoiceSettingsView(ui.View): # 드롭다운 메뉴와 버튼을 하나의 덩어리로 묶어주는 역할
    def __init__(self, voice: str, pitch: float, rate: float):
        super().__init__(timeout=None) # 시간 제한 없이 버튼을 누를 수 있도록
        self.voice = voice
        self.pitch = pitch
        self.rate = rate
        # View 컨테이너 안에 드롭다운 메뉴 구성
        self.add_item(VoiceSelect(voice))

    # View 컨테이너 안에 버튼 구성
    @ui.button(label="세부 설정 (피치/속도) 변경", style=discord.ButtonStyle.secondary, emoji="⚙️", row=1)
    async def edit_details(self, interaction: discord.Interaction, button: ui.Button): # 버튼을 누르면 모달 창을 표시
        modal = DetailSettingsModal(self.voice, self.pitch, self.rate)
        await interaction.response.send_modal(modal)

# =============== Cog(디스코드 명령어 등록) ===============

class TTSSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="목소리_설정", description="나만의 TTS 목소리를 설정합니다.")
    async def set_voice(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        # DB에서 이 유저의 기존 설정 값 불러오기
        setting = await db.get_user_settings(user_id)
        # DB에 값이 있으면 그 값을 사용, 기존 값이 없으면 기본값으로 덮어 쓰기
        if setting:
            voice = setting.get("voice", setting.get("voice_name", setting.get("voice_type", "ko-KR-Wavenet-A")))
            pitch = float(setting.get("pitch", 0.0))
            rate = float(setting.get("rate", setting.get("speaking_rate", 1.0)))
        else:
            voice, pitch, rate = ("ko-KR-Wavenet-A", 0.0, 1.0)
        # 가져온 설정값으로 화면과 메뉴 표시
        embed = show_settings_embed(interaction.user, voice, pitch, rate)
        view = VoiceSettingsView(voice, pitch, rate)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TTSSettings(bot))