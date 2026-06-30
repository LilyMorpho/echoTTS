import re
import random

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
        if interaction.guild.id in self.forbidden_word_games:
            await interaction.response.send_message("❌ 이미 이 서버에서 금칙어 게임이 진행 중입니다!", ephemeral=True)
            return

        end_time = time.time() + (duration * 60)
        self.forbidden_word_games[interaction.guild.id] = {
            "word": word,
            "end_time": end_time,
            "losers": {},
            "channel_id": interaction.channel.id
        }

        embed = discord.Embed(
            title="🚫 금칙어 게임 시작!",
            description=f"지금부터 **{duration}분** 동안 지정된 단어를 말하면 안 됩니다!\n누가 가장 많이 실패할까요?",
            color=discord.Color.red()
        )
        embed.set_footer(text="금칙어를 말하면 봇이 이모지로 해당 메시지에 반응합니다!")

        await interaction.response.send_message(embed=embed)
        # 게임 종료 타이머 백그라운드로 실행
        self.bot.loop.create_task(self.end_game_timer(interaction.guild.id, duration * 60))

    async def end_game_timer(self, guild_id: int, duration: int):
        await asyncio.sleep(duration) # 지정된 시간만큼 대기

        # 시간이 다 지나면 게임 결과 발표
        if guild_id in self.forbidden_word_games:
            game_data = self.forbidden_word_games.pop(guild_id)
            channel = self.bot.get_channel(game_data["channel_id"])
            guild = self.bot.get_guild(guild_id)

            if channel:
                losers = game_data["losers"]
                if not losers:
                    result_text = "🎉 아무도 금칙어를 말하지 않았습니다! 모두의 훌륭한 눈치 게임 승리!"
                else:
                    losers_ranking = sorted(losers.items(), key=lambda user: user[1], reverse=True)
                    result_text = "💥 **[금칙어 게임 결과]** 💥\n\n"
                    for user_id, count in losers_ranking:
                        member = guild.get_member(user_id)
                        if not member:
                            try:
                                member = guild.fetch_member(user_id)
                            except discord.NotFound:
                                member = None
                        name = member.display_name if member else "알 수 없는 사용자"
                        result_text += f"**{name}**: {count}회\n"

                    max_count = losers_ranking[0][1]
                    worst_users = [user_id for user_id, count in losers_ranking if count == max_count]
                    mentions = ", ".join(f"<@{user_id}>" for user_id in worst_users)
                    result_text += f"\n **이번 게임의 패배자** {mentions} 님!\n"

                embed = discord.Embed(title="🚫 금칙어 게임 종료!", description=f"금칙어 게임이 종료되었습니다!(금칙어 :**{game_data['word']}**)\n\n{result_text}", color=discord.Color.gold())
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
                    await message.add_reaction("❌")
                except discord.Forbidden:
                    pass

    @app_commands.command(name="주사위", description="m면체 주사위를 n개 굴립니다. (예: 2d6)")
    @app_commands.describe(
        expression="주사위 형식 (예: '2d6'을 입력받으면 6면체 주사위 2개를 굴립니다.",
        explode_threshold="[선택] 이 수치 이상이 나오면 주사위를 다시 굴려 더합니다."
    )
    async def roll_dice(self, interaction: discord.Interaction, expression: str, explode_threshold: int = None):
        expression = expression.lower().strip()
        match = re.match(r"^(\d+)d(\d+)$", expression)

        if not match:
            await interaction.response.send_message("❌ 올바른 형식이 아닙니다! `숫자d숫자` 형식으로 입력해 주세요. (예: 2d6, 1d100)", ephemeral=True)
            return

        n = int(match.group(1))
        m = int(match.group(2))

        if n < 1 or n > 100:
            await interaction.response.send_message("❌ 주사위 개수는 1개에서 100개 사이로 입력해 주세요.", ephemeral=True)
            return

        if m < 2 or m > 1000:
            await interaction.response.send_message("❌ 주사위 면수는 2에서 1000 사이로 입력해 주세요.", ephemeral=True)
            return

        if explode_threshold is not None:
            if explode_threshold < 2 or explode_threshold > m:
                await interaction.response.send_message(f"❌ 추가 굴림 수치는 1보다 크고 {m}(주사위 최댓값) 이하여야 합니다.", ephemeral=True)
                return

        total = 0
        results_str_list = []

        for _ in range(n):
            roll = random.randint(1, m)
            total += roll

            if explode_threshold is not None and roll >= explode_threshold:
                chain = [str(roll)]
                current_roll = roll
                explosion_count = 0

                while current_roll >= explode_threshold:
                    current_roll = random.randint(1, m)
                    chain.append(str(current_roll))
                    total += current_roll
                    explosion_count += 1

                results_str_list.append("(" + " + ".join(chain) + ")")
            else:
                results_str_list.append(str(roll))

        results_str = ", ".join(results_str_list)

        if len(results_str) > 1000:
            results_str = results_str[:995] + " ... (너무 길어서 생략됨)"

        title_suffix = f" 💥(크리티컬: {explode_threshold} 이상)" if explode_threshold else ""

        embed = discord.Embed(
            title=f"🎲 {expression} 주사위 굴림 결과{title_suffix}",
            description=f"**총합: {total}**\n\n```\n[ {results_str} ]\n```",
            color=discord.Color.green() if not explode_threshold else discord.Color.orange()
        )
        embed.set_footer(text=f"{interaction.user.display_name} 님이 굴렸습니다.")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Minigame(bot))