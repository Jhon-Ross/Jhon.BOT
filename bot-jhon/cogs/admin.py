import discord
from discord import app_commands
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="limpar", description="Apaga mensagens do canal.")
    @app_commands.describe(quantidade="Número de mensagens para apagar (1-100)")
    async def limpar(self, interaction: discord.Interaction, quantidade: int = 10):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            return

        if not (1 <= quantidade <= 100):
            await interaction.response.send_message("❌ Número de mensagens deve estar entre 1 e 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True) # Defer porque purge pode demorar um pouco
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"✅ {len(deleted)} mensagens foram excluídas.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
