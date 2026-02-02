import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
import os
import asyncio
from database import (
    add_warning, get_warnings_count, log_mod_action, 
    get_staff_daily_actions, clear_warnings
)

# Configurações via .env
CANAL_LOG_ID = int(os.getenv("CANAL_LOG_ID") or 0)
STAFF_DAILY_LIMIT = 10 # Limite de ações por staff por dia

class Moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_control = {} # {user_id: [last_messages]}
        self.join_times = [] # [timestamp] para anti-raid
        self.emoji_regex = re.compile(r'<a?:.+?:\d+>|[\u263a-\U0001f645]') # Regex simples para emojis

    async def send_mod_log(self, embed):
        """Envia um log para o canal de logs configurado."""
        if CANAL_LOG_ID == 0:
            return
        channel = self.bot.get_channel(CANAL_LOG_ID)
        if channel:
            await channel.send(embed=embed)

    # --- COMANDOS DE AVISO ---

    @app_commands.command(name="aviso", description="Aplica um aviso educativo a um membro.")
    @app_commands.describe(membro="O membro que receberá o aviso", motivo="O motivo do aviso")
    async def aviso(self, interaction: discord.Interaction, membro: discord.Member, motivo: str):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ Você não tem permissão para dar avisos.", ephemeral=True)
            return

        if membro.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Você não pode avisar alguém com cargo igual ou superior ao seu.", ephemeral=True)
            return

        # Verificar limite diário do staff
        daily_actions = get_staff_daily_actions(interaction.user.id)
        if daily_actions >= STAFF_DAILY_LIMIT:
            await interaction.response.send_message(f"⚠️ Você atingiu seu limite diário de {STAFF_DAILY_LIMIT} ações administrativas.", ephemeral=True)
            return

        warn_count = add_warning(membro.id, interaction.user.id, motivo)
        log_mod_action('warn', interaction.user.id, membro.id, motivo)

        # Embed de Log
        embed_log = discord.Embed(title="⚠️ Novo Aviso Aplicado", color=discord.Color.gold())
        embed_log.add_field(name="Membro", value=f"{membro.mention} ({membro.id})", inline=False)
        embed_log.add_field(name="Staff", value=f"{interaction.user.mention}", inline=False)
        embed_log.add_field(name="Motivo", value=motivo, inline=False)
        embed_log.add_field(name="Total de Avisos", value=f"{warn_count}", inline=False)
        embed_log.set_footer(text=f"Horário: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await self.send_mod_log(embed_log)

        # Punições Progressivas
        punicao_msg = ""
        if warn_count == 3:
            try:
                await membro.timeout(datetime.timedelta(minutes=10), reason="3º Aviso atingido")
                punicao_msg = "\n\n**Punição:** Timeout de 10 minutos aplicado automaticamente."
            except:
                punicao_msg = "\n\n**Aviso:** Não consegui aplicar o timeout automático."
        elif warn_count >= 5:
            punicao_msg = "\n\n**Atenção Staff:** Este membro atingiu 5 avisos. Considerem uma punição mais severa."

        # Mensagem Educativa por DM
        try:
            embed_dm = discord.Embed(
                title="🛡️ Aviso do Servidor",
                description=(
                    f"Olá {membro.name}! Notei que algo aconteceu e você recebeu um aviso.\n\n"
                    f"**Motivo:** {motivo}\n"
                    f"**Total de avisos agora:** {warn_count}\n\n"
                    "Por favor, evite esse comportamento para mantermos o servidor amigável para todos! 😊"
                    f"{punicao_msg}"
                ),
                color=discord.Color.orange()
            )
            await membro.send(embed=embed_dm)
            dm_status = "Notificado por DM."
        except:
            dm_status = "Não consegui enviar DM (privado fechado)."

        await interaction.response.send_message(f"✅ Aviso aplicado a {membro.mention}. Total: {warn_count}. {dm_status}")

    @app_commands.command(name="avisos_limpar", description="Limpa todos os avisos de um membro.")
    async def avisos_limpar(self, interaction: discord.Interaction, membro: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem limpar avisos.", ephemeral=True)
            return

        clear_warnings(membro.id)
        log_mod_action('clear_warns', interaction.user.id, membro.id, "Limpeza manual de avisos")
        
        await interaction.response.send_message(f"✅ Todos os avisos de {membro.mention} foram removidos.")

    # --- SISTEMA ANTI-SPAM E ANTI-CAPS ---

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if message.author.guild_permissions.manage_messages:
            return

        # 1. Anti-Spam (Mensagens repetidas)
        user_id = message.author.id
        now = datetime.datetime.now()
        
        if user_id not in self.spam_control:
            self.spam_control[user_id] = []
        
        self.spam_control[user_id].append({"content": message.content, "time": now})
        
        # Limpa histórico antigo (mais de 10 segundos)
        self.spam_control[user_id] = [m for m in self.spam_control[user_id] if (now - m["time"]).total_seconds() < 10]

        recent = self.spam_control[user_id]
        if len(recent) >= 3 and all(m["content"] == message.content for m in recent[-3:]):
            await message.delete()
            try:
                await message.author.send("🤫 Opa, evite mandar a mesma mensagem várias vezes seguidas! Vamos manter o chat limpo.")
            except: pass
            return

        # 2. Anti-Caps (Excessivo)
        if len(message.content) > 10:
            uppercase_count = sum(1 for c in message.content if c.isupper())
            if uppercase_count / len(message.content) > 0.7:
                await message.delete()
                try:
                    await message.author.send("📢 Notei que você usou muito CAPS LOCK. Tente falar um pouco mais baixo, por favor! 😊")
                except: pass
                return

        # 3. Anti-Emoji (Excesso)
        emojis = self.emoji_regex.findall(message.content)
        if len(emojis) > 10:
            await message.delete()
            try:
                await message.author.send("✨ Muitos emojis em uma só mensagem podem poluir o chat. Tente usar um pouco menos! 😉")
            except: pass
            return

        # 4. Anti-Links (Canais não permitidos)
        links = self.link_regex.findall(message.content)
        if links:
            # Canais onde links são permitidos (nomes ou IDs)
            allowed_keywords = ["links", "divulgação", "midia", "vídeos", "verificar"]
            is_allowed_channel = any(kw in message.channel.name.lower() for kw in allowed_keywords)
            
            if not is_allowed_channel:
                await message.delete()
                try:
                    await message.author.send(
                        f"🔗 Notei que você postou um link em {message.channel.mention}.\n"
                        "Para manter a organização, links só são permitidos em canais de **divulgação** ou **links**! 😊"
                    )
                except: pass
                return

    # --- ANTI-RAID E ANTI-FAKE ---

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # 1. Anti-Fake (Contas muito novas)
        min_age_days = 7
        account_age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
        
        if account_age < min_age_days:
            # Notifica Staff sobre conta suspeita
            embed_log = discord.Embed(title="🛡️ Alerta de Conta Nova", color=discord.Color.red())
            embed_log.add_field(name="Membro", value=f"{member.mention} ({member.id})", inline=False)
            embed_log.add_field(name="Idade da Conta", value=f"{account_age} dias", inline=False)
            embed_log.description = "Esta conta é muito nova e pode ser um perfil fake/alt."
            await self.send_mod_log(embed_log)

        # 2. Anti-Raid (Entrada em massa)
        now = datetime.datetime.now()
        self.join_times.append(now)
        # Mantém apenas os últimos 60 segundos
        self.join_times = [t for t in self.join_times if (now - t).total_seconds() < 60]

        if len(self.join_times) > 10: # Mais de 10 entradas por minuto
            embed_raid = discord.Embed(title="🚨 POSSÍVEL RAID DETECTADO", color=discord.Color.dark_red())
            embed_raid.description = f"Houve {len(self.join_times)} entradas nos últimos 60 segundos. Fiquem atentos!"
            await self.send_mod_log(embed_raid)

async def setup(bot):
    await bot.add_cog(Moderacao(bot))
