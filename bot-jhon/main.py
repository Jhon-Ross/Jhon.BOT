import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

# Configuração de Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True
intents.voice_states = True

class JhonBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents, help_command=None)

    async def setup_hook(self):
        # Carregar Cogs (Extensões)
        initial_extensions = [
            'cogs.events',
            'cogs.utils',
            'cogs.admin',
            'cogs.music',
            'cogs.ai',
            'cogs.minigames.blackjack21'
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Extensão carregada: {ext}")
            except Exception as e:
                print(f"❌ Falha ao carregar extensão {ext}: {e}")

        # Sincronizar Slash Commands
        try:
            # Sincroniza comandos globais
            synced = await self.tree.sync()
            print(f"🔄 Slash Commands Globais sincronizados: {len(synced)} comandos.")

            # Limpa comandos antigos específicos do servidor (Guild) para evitar duplicatas
            if GUILD_ID:
                try:
                    guild_obj = discord.Object(id=int(GUILD_ID))
                    # Copia os comandos globais para o servidor para atualização imediata
                    self.tree.copy_global_to(guild=guild_obj)
                    await self.tree.sync(guild=guild_obj)
                    print(f"🧹 Comandos sincronizados com o servidor ({GUILD_ID}) para acesso imediato.")
                except Exception as e:
                    print(f"⚠️ Aviso: Não foi possível sincronizar comandos do servidor: {e}")

        except Exception as e:
            print(f"❌ Falha ao sincronizar comandos: {e}")

bot = JhonBot()

# Tratamento de erro global para Slash Commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Calma lá! Tente novamente em {error.retry_after:.2f}s.", ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
    else:
        command_name = interaction.command.name if interaction.command else "Desconhecido"
        print(f"Erro no comando /{command_name}: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Ocorreu um erro ao processar o comando.", ephemeral=True)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN não encontrado no arquivo .env")
    else:
        print("🚀 Iniciando Bot Jhon...")
        bot.run(DISCORD_TOKEN)
