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
    # Chirp3 모델일 경우 음높이는 '지원 안함'으로 표시
    if "Chirp3" in voice:
        embed.add_field(name="🎼 음높이 (Pitch)", value=f"`지원되지 않음`", inline=True)
    else:
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
        self.is_chirp3 = "Chirp3" in current_voice
        # Chirp3 모델일 경우 음높이 입력 칸을 삭제
        if self.is_chirp3:
            self.remove_item(self.pitch_input)
        else:
            self.pitch_input.default = str(current_pitch)
        self.rate_input.default = str(current_rate)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력받은 내용을 숫자(float)로 바꾸고, 허용 범위 내에 들어오게 처리.
            new_pitch = 0.0 if self.is_chirp3 else max(-20.0, min(20.0, float(self.pitch_input.value)))
            new_rate = max(0.25, min(4.0, float(self.rate_input.value)))
            # DB에 변경된 값 저장
            await db.save_user_setting(interaction.user.id, self.current_voice, new_pitch, new_rate)
            # 화면을 변경된 설정 값으로 새로고침
            embed = show_settings_embed(interaction.user, self.current_voice, new_pitch, new_rate)
            view = VoiceSettingsView(self.current_voice, new_pitch, new_rate)
            await interaction.response.edit_message(embed=embed, view=view)
        except ValueError: # 숫자가 아닌 형식으로 입력되었을 때 에러 처리
            await interaction.response.send_message("❌ 숫자를 정확히 입력해 주세요!", ephemeral=True)

class ModelSelect(ui.Select):
    def __init__(self, current_model: str, is_selected: bool):
        options = [
            discord.SelectOption(label="WaveNet (표준)", value="wavenet", emoji="🌐",
                                 default=(is_selected and current_model=="wavenet")),
            discord.SelectOption(label="Chirp3 HD (차세대 생성형)", value="chirp3", emoji="✨",
                                 default=(is_selected and current_model=="chirp3"))
        ]
        super().__init__(placeholder="사용할 모델 종류를 선택하세요.", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        new_model = self.values[0]
        self.view.current_model = new_model

        self.view.model_selected = True

        if new_model == "wavenet" and "Chirp3" in self.view.voice:
            self.view.voice = "ko-KR-Wavenet-A"
        elif new_model == "chirp3" and "Wavenet" in self.view.voice:
            self.view.voice = "ko-KR-Chirp3-HD-Achernar" if self.view.current_gender == "female" else "ko-KR-Chirp3-HD-Achird"

        await self.view.update_and_respond(interaction)

class GenderSelect(ui.Select):
    def __init__(self, current_gender: str):
        options = [
            discord.SelectOption(label="👩 여성 목소리 보기", value="female", emoji="👩", default=(current_gender == "female")),
            discord.SelectOption(label="👨 남성 목소리 보기", value="male", emoji="👨", default=(current_gender == "male"))
        ]
        super().__init__(placeholder="목소리의 성별을 선택하세요", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.current_gender = self.values[0]
        # 성별이 바뀌면 해당 성별의 첫번째 목소리로 자동 변경
        if self.view.current_gender == "female": self.view.voice = "ko-KR-Chirp3-HD-Achernar"
        else: self.view.voice = "ko-KR-Chirp3-HD-Achird"

        await self.view.update_and_respond(interaction)

class VoiceSelect(ui.Select):
    def __init__(self, current_model: str, current_gender: str, current_voice: str):
        row_num = 1 if current_model == "wavenet" else 2 # 줄 번호 계산 추가
        if current_model == "wavenet":
            options = [
                discord.SelectOption(label="👩 또렷한 여성 (WaveNet-A)", value="ko-KR-Wavenet-A", emoji="👩",
                                     default=(current_voice=="ko-KR-Wavenet-A")),
                discord.SelectOption(label="👩 친근한 여성 (WaveNet-B)", value="ko-KR-Wavenet-B", emoji="👧",
                                     default=(current_voice=="ko-KR-Wavenet-B")),
                discord.SelectOption(label="👨 중후한 남성 (WaveNet-C)", value="ko-KR-Wavenet-C", emoji="👨",
                                     default=(current_voice=="ko-KR-Wavenet-C")),
                discord.SelectOption(label="👨 명쾌한 남성 (WaveNet-D)", value="ko-KR-Wavenet-D", emoji="👦",
                                     default=(current_voice=="ko-KR-Wavenet-D")),
            ]
        elif current_model == "chirp3" and current_gender == "female": # Chirp3-HD 모델의 경우 여성을 선택시 여성 리스트만 노출
            female_voices = ["Achernar", "Aoede", "Autonoe", "Callirrhoe", "Despina", "Erinome", "Gacrux", "Kore",
                             "Laomedeia", "Leda", "Pulcherrima", "Sulafat", "Vindemiatrix", "Zephyr"]
            options = [discord.SelectOption(label=f"👩 {name}", value=f"ko-KR-Chirp3-HD-{name}", emoji="✨",
                                            default=(current_voice == f"ko-KR-Chirp3-HD-{name}")) for name in female_voices]
        else: # Chirp3-HD 모델의 경우 남성을 선택 시 남성 리스트 노출
            male_voices = ["Achird", "Algenib", "Algieba", "Alnilam", "Charon", "Enceladus", "Fenrir", "Iapetus",
                           "Orus", "Puck", "Rasalgethi", "Sadachbia", "Sadaltager", "Schedar", "Umbriel", "Zubenelgenubi"]
            options = [discord.SelectOption(label=f"👨 {name}", value=f"ko-KR-Chirp3-HD-{name}", emoji="🌠",
                                            default=(current_voice == f"ko-KR-Chirp3-HD-{name}")) for name in male_voices]

        super().__init__(placeholder="변경할 목소리를 선택하세요", min_values=1, max_values=1, options=options, row=row_num)

    async def callback(self, interaction: discord.Interaction): # 드롭다운 메뉴에서 특정 목소리를 선택했을 때 실행
        self.view.voice = self.values[0]
        await self.view.update_and_respond(interaction)

class VoiceSettingsView(ui.View): # 드롭다운 메뉴와 버튼을 하나의 덩어리로 묶어주는 역할
    def __init__(self, voice: str, pitch: float, rate: float):
        super().__init__(timeout=None) # 시간 제한 없이 버튼을 누를 수 있도록
        self.voice = voice
        self.pitch = pitch
        self.rate = rate
        self.model_selected = False
        # DB에서 가져온 목소리 이름으로 현재 모델 판별
        self.current_model = "chirp3" if "Chirp3" in voice else "wavenet"
        # DB에서 가져온 목소리 이름으로 현재 목소리 성별 판별
        female_voices = ["Achernar", "Aoede", "Autonoe", "Callirrhoe", "Despina", "Erinome", "Gacrux", "Kore",
                         "Laomedeia", "Leda", "Pulcherrima", "Sulafat", "Vindemiatrix", "Zephyr"]
        if self.current_model == "chirp3":
            is_female = any(name in voice for name in female_voices)
            self.current_gender = "female" if is_female else "male"
        else:
            self.current_gender = "female"

        self.update_components()

    async def update_and_respond(self, interaction: discord.Interaction): # DB 저장 및 화면 새로고침을 담당하는 함수
        await db.save_user_setting(interaction.user.id, self.voice, self.pitch, self.rate)
        self.update_components()
        embed = show_settings_embed(interaction.user, self.voice, self.pitch, self.rate)
        await interaction.response.edit_message(embed=embed, view=self)

    def update_components(self):
        # 기존 아이템들을 전부 지우고 상태에 맞춰 다시 생성
        self.clear_items()

        # 모델 선택
        self.add_item(ModelSelect(self.current_model, self.model_selected))
        # 모델 고르기 이전이라면 메뉴를 숨김
        if not self.model_selected:
            return
        # 조건부 UI 렌더링
        if self.current_model == "wavenet":
            self.add_item(VoiceSelect(self.current_model, self.current_gender, self.voice))
            button_row = 2
        else:
            self.add_item(GenderSelect(self.current_gender))
            self.add_item(VoiceSelect(self.current_model, self.current_gender, self.voice))
            button_row = 3
        # 세부 설정 버튼
        detail_btn = ui.Button(label="세부 설정 (피치/속도) 변경", style=discord.ButtonStyle.secondary, emoji="⚙️",
                               row=button_row, custom_id="detail")
        detail_btn.callback = self.edit_details_callback
        self.add_item(detail_btn)

    async def edit_details_callback(self, interaction: discord.Interaction):
        # 세부 설정 동작 로직
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
        view = VoiceSettingsView(voice, pitch, rate)
        embed = show_settings_embed(interaction.user, voice, pitch, rate)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TTSSettings(bot))