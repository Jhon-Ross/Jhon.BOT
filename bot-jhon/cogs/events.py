import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração
CANAL_LOG_ID = int(os.getenv("CANAL_LOG_ID") or 0)
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID") or 0)
RULES_CHANNEL_ID = int(os.getenv("RULES_CHANNEL_ID") or 0)
VERIFICAR_ID = int(os.getenv("VERIFICAR_ID") or 0)
VISITANTE_ID = int(os.getenv("VISITANTE_ID") or 0)
BOAS_VINDAS_ID = int(os.getenv("BOAS_VINDAS_ID") or 0)
GUILD_ID = int(os.getenv("GUILD_ID") or 0)

class Eventos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.basicConfig(level=logging.INFO)

    def get_emoji_for_number(self, number):
        emojis = {
            0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"
        }
        return "".join([emojis[int(digit)] for digit in str(number)])

    async def update_channel_member_count(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild: return
        
        channel = guild.get_channel(BOAS_VINDAS_ID)
        if not channel: return

        member_count = guild.member_count
        new_topic = f"Já contabilizamos {self.get_emoji_for_number(member_count)} membros nesse servidor muito louco."

        try:
            await channel.edit(topic=new_topic)
            logging.info(f"Contagem de membros atualizada para {member_count}")
        except Exception as e:
            logging.error(f"Erro ao tentar atualizar o 'topic' do canal: {e}")

    async def send_log_message(self, content=None, embed=None):
        channel = self.bot.get_channel(CANAL_LOG_ID)
        if not channel:
            logging.error(f"Canal de log com ID {CANAL_LOG_ID} não encontrado.")
            return
        try:
            if content and embed:
                await channel.send(content, embed=embed)
            elif embed:
                await channel.send(embed=embed)
            elif content:
                await channel.send(content)
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem de log: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✔️ Bot {self.bot.user.name} está online e pronto! (Sistema Modular)")
        # Log de inicialização
        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, id=CANAL_LOG_ID)
            if channel:
                await channel.send("🚀 O bot foi iniciado com sucesso! (Sistema Modular)")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            if not hasattr(channel, 'send'):
                logging.error(f"Erro de Configuração: O canal de boas-vindas (ID: {WELCOME_CHANNEL_ID}) não é um canal de texto.")
                return

            rules_channel = self.bot.get_channel(RULES_CHANNEL_ID)
            verificar_channel = self.bot.get_channel(VERIFICAR_ID)

            embed = discord.Embed(
                title="👋 Bem-vindo(a)!",
                description=(
                    f"Seja bem-vindo ao meu servidor {member.mention}, espero que você se divirta muito por aqui!\n\n"
                    f"Por favor, leia as regras em {rules_channel.mention if rules_channel else '#regras'},\n"
                    f"Utilize o nosso sistema de verificação em {verificar_channel.mention if verificar_channel else '#verificar'}."
                ),
                color=discord.Color.green()
            )
            embed.set_image(url="https://media.discordapp.net/attachments/1310617769326153738/1310617942441852928/blitz-crank-league-of-legends.gif")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="ID do Usuário", value=str(member.id), inline=True)
            await channel.send(embed=embed)
        
        visitante_role = discord.utils.get(member.guild.roles, id=VISITANTE_ID)
        if visitante_role:
            try:
                await member.add_roles(visitante_role)
            except Exception as e:
                logging.error(f"Erro ao adicionar cargo: {e}")

        await self.update_channel_member_count()
        await self.send_log_message(content=f"✅ {member.mention} entrou no servidor. ID: {member.id}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.update_channel_member_count()
        await self.send_log_message(content=f"🚪 {member.mention} saiu do servidor. ID: {member.id}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            await self.send_log_message(content=f"🔊 {member.mention} entrou no canal de voz `{after.channel.name}`.")
        elif before.channel is not None and after.channel is None:
            await self.send_log_message(content=f"🔇 {member.mention} saiu do canal de voz `{before.channel.name}`.")
        elif before.channel != after.channel:
            await self.send_log_message(content=f"🔁 {member.mention} mudou do canal de voz `{before.channel.name}` para `{after.channel.name}`.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        gained_roles = [role for role in after_roles - before_roles if not role.is_default()]
        lost_roles = [role for role in before_roles - after_roles if not role.is_default()]

        messages = []
        if gained_roles:
            role_names = ", ".join([role.name for role in gained_roles])
            messages.append(f"➕ Cargos adicionados: {role_names}")
        if lost_roles:
            role_names = ", ".join([role.name for role in lost_roles])
            messages.append(f"➖ Cargos removidos: {role_names}")

        if messages:
            await self.send_log_message(content=f"🛡️ Atualização de cargos para {after.mention}:\n" + "\n".join(messages))

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot: return
        content = message.content if message.content else "[sem conteúdo de texto]"
        await self.send_log_message(content=f"🗑️ Mensagem apagada em {message.channel.mention} por {message.author.mention} (ID: {message.id}):\n{content}")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot: return
        if before.content == after.content: return
        before_content = before.content if before.content else "[vazio]"
        after_content = after.content if after.content else "[vazio]"
        await self.send_log_message(content=f"✏️ Mensagem editada em {before.channel.mention} por {before.author.mention} (ID: {before.id}):\nAntes: {before_content}\nDepois: {after_content}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot: return
        await self.send_log_message(content=f"➕ Reação adicionada por {user.mention} em {reaction.message.channel.mention}: {reaction.emoji}")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot: return
        await self.send_log_message(content=f"➖ Reação removida por {user.mention} em {reaction.message.channel.mention}: {reaction.emoji}")

async def setup(bot):
    await bot.add_cog(Eventos(bot))
