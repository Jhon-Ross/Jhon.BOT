import discord
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class CleanupClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        print("🔄 Conectado! Iniciando limpeza de comandos globais...")
        try:
            # Limpa a árvore interna
            self.tree.clear_commands(guild=None)
            # Sincroniza com a API (envia lista vazia)
            await self.tree.sync(guild=None)
            print("✅ Sucesso: Todos os comandos globais foram removidos.")
            print("⚠️ Nota: Pode levar até 1 hora para o Discord atualizar em todos os dispositivos, mas geralmente é rápido.")
        except Exception as e:
            print(f"❌ Erro ao limpar comandos: {e}")
        finally:
            await self.close()

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Erro: Token não encontrado no .env")
    else:
        print("🚀 Iniciando script de limpeza...")
        client = CleanupClient()
        client.run(TOKEN)
