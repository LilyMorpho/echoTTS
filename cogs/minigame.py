import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time

class Minigame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 서버별로 잔행 중인 금칙어 게임 상태를 저장
        self.forbidden_word_games = {}

    @app_commands.command(name="금칙어_게임", description="특정 단어를 말하면 안 되는 금칙어 게임을 시작합니다.")
    @app_commands.describe(word="금지할 단어", duration="게임 진행 시간 (분)")
    async def start_forbidden_word_game(self, interaction: discord.Interaction, word: str, duration: int = 5):
        if interaction.guild.id not in self.forbidden_word_games:
            await interaction.response.send_message("❌ 이미 이 서버에서 금칙어 게임이 진행 중입니다!", ephemeral=True)
            return

        end_time = time.time() + (duration * 60)
        self.forbidden_word_games[interaction.guild.id] = {
            "word": word,
            "end_time": end_time,
            "losers": {}
            "channel_id": interaction.channel.id
        }

        embed = discord.Embed(
            title="🚫 금칙어 게임 시작!",
            description=f"지금부터 **{duration}분** 동안 아래 지정된 단어를 말하면 안 됩니다!\n누가 가장 많이 실패할까요?",
            color=discord.Color.red()
        )
        embed.add_field(name="금칙어(클릭해서 확인)", value=f"||{word}||", inline=False)
        embed.set_footer(text="금칙어를 말하면 봇이 이모지로 해당 메시지에 반응합니다!")

        await interaction.response.send_message(embed=embed)
        # 게임 종료 타이머 백그라운드로 실행
        self.bot.loop.create_task(self.end_game_timer(interatcion.guild.id, duration * 60))

    async def end_game_timer(self, guild_id: int, duration: int):
        await asyncio.sleep(duration) # 지정된 시간만큼 대기

        # 시간이 다 지나면 게임 결과 발표
        if guild_id in self.forbidden_word_games:
            game_data = self.forbidden_word_games.pop(guild_id)
            channel = self.bot.get_channel(game_data["channel_id"])

            if channel:
                losers = game_data["losers"]
                if not losers:
                    result_text = "🎉 아무도 금칙어를 말하지 않았습니다! 모두의 훌륭한 승리입니다!"
                else:
                    losers_ranking = sorted(losers.items(), key=lambda user: user[1], reverse=True)
                    result_text = "💥 **[금칙어 게임 결과]** 💥\n\n"
                    for user_id, count in losers_ranking:
                        result_text += f"<@{user_id}: {count}>회\n"

                    worst_user = losers_ranking[0][0]
                    result_text += f"\n **이번 게임의 패배자** <@{worst_user}> 님!\n"

                embed = discord.Embed(title="🚫 금칙어 게임 종료!", description=f"금칙어 게임이 종료되었습니다!(금칙어 :**{game_data['word']**}\n\n{result_text}", color=discord.Color.gold())
                await channel.send(embed=embed)
    @app_commands.command(name="금칙어_게임_중단", description="진행중인 금칙어 게임을 강제로 중단합니다.")
    async def stop_forbidden_word_game(self, interaction: discord.Interaction):
        if interaction.guild.id not in self.forbidden_word_games:
            await interaction.response.send_message("❌ 현재 진행 중인 금칙어 게임이 없습니다.", ephemeral=True)
            return

        game_data = self.forbidden_word_games.pop(interaction.guild.id)
        await interaction.response.send_message(f"🛑 금칙어 게임이 강제로 종료되었습니다. (금칙어: **{game_data['word']}**)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        guild_id = message.guild.id
        if guild_id in self.forbidden_word_games:
            game_data = self.forbidden_word_games[guild_id]
            word = game_data["word"]

            if word in message.content:
                user_id = message.author.id
                game_data["losers"][user_id] = game_data["losers"].get(user_id, 0) + 1

                try:
                    await message.add_reaction()
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(Minigame(bot))