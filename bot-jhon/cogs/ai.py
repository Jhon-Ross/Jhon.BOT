import discord
import ollama
from discord.ext import commands

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cliente assíncrono do Ollama
        self.client = ollama.AsyncClient()
        # Modelo padrão (pode ser alterado para 'mistral', 'phi3', etc.)
        self.model = "llama3" 
        self.system_prompt = self.load_personality()

    def load_personality(self):
        try:
            with open("personalidade.md", "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Erro ao carregar personalidade.md: {e}")
            return "Você é um assistente útil do Discord. Seja breve e direto."

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora mensagens do próprio bot
        if message.author == self.bot.user:
            return

        # Verifica se o bot foi mencionado ou se é uma resposta a uma mensagem dele
        is_mentioned = self.bot.user.mentioned_in(message)
        is_reply = (message.reference and message.reference.resolved and 
                    message.reference.resolved.author == self.bot.user)

        if is_mentioned or is_reply:
            async with message.channel.typing():
                try:
                    # Limpa a menção da mensagem para enviar apenas o texto
                    content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
                    if not content:
                        content = "Olá!"  # Resposta padrão se apenas marcarem sem texto

                    # Constrói as mensagens para o chat context
                    messages = [
                        {'role': 'system', 'content': self.system_prompt},
                        {'role': 'user', 'content': content}
                    ]

                    # Gera a resposta usando Ollama
                    response = await self.client.chat(model=self.model, messages=messages)
                    reply_text = response['message']['content']
                    
                    # Envia a resposta (Discord tem limite de 2000 caracteres)
                    if len(reply_text) > 2000:
                        reply_text = reply_text[:1997] + "..."
                        
                    await message.reply(reply_text)

                except Exception as e:
                    err_msg = str(e).lower()
                    if "connection refused" in err_msg or "target machine actively refused" in err_msg:
                        await message.reply("⚠️ Não consegui conectar ao Ollama! Verifique se ele está rodando no seu PC (`ollama serve`).")
                    elif "not found" in err_msg and "model" in err_msg:
                        await message.reply(f"⚠️ O modelo `{self.model}` não foi encontrado. Execute no terminal: `ollama pull {self.model}`")
                    else:
                        print(f"Erro no Ollama: {e}")
                        await message.reply("Tive um problema ao processar sua resposta. 🤯")

async def setup(bot):
    await bot.add_cog(AI(bot))
