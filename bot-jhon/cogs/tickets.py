import discord
from discord import app_commands
from discord.ext import commands

SUPORTE_CATEGORIA_ID = 1096139038886473828
TICKET_CANAL_ID = 1096139214938177647
TICKET_STAFF_IDS = {
    865436484117987338,
    880760237374713906,
    880761415739269140,
}


def _normalize_channel_name(name: str) -> str:
    name = (name or "").strip().lower()
    safe = []
    for ch in name:
        if ch.isalnum():
            safe.append(ch)
        elif ch in {" ", "_", "-"}:
            safe.append("-")
    value = "".join(safe).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:80] or "usuario"


def _member_has_any_id(member: discord.Member, ids: set[int]) -> bool:
    if member.id in ids:
        return True
    for role in getattr(member, "roles", []):
        if role.id in ids:
            return True
    return False


def _staff_overwrites(guild: discord.Guild) -> dict:
    overwrites: dict = {}
    for sid in TICKET_STAFF_IDS:
        role = guild.get_role(sid)
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            continue
        member = guild.get_member(sid)
        if member is not None:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    return overwrites


def _staff_mentions(guild: discord.Guild) -> str:
    mentions = []
    for sid in TICKET_STAFF_IDS:
        role = guild.get_role(sid)
        if role is not None:
            mentions.append(role.mention)
            continue
        member = guild.get_member(sid)
        if member is not None:
            mentions.append(member.mention)
    return " ".join(mentions)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _open_ticket(self, interaction: discord.Interaction, ticket_type: str):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Este botão só funciona dentro do servidor.", ephemeral=True)
            return

        guild = interaction.guild
        category = guild.get_channel(SUPORTE_CATEGORIA_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Categoria de suporte não encontrada.", ephemeral=True)
            return

        existing = discord.utils.get(category.text_channels, name=f"ticket-{ticket_type}-{interaction.user.id}")
        if existing:
            await interaction.response.send_message(f"⚠️ Você já tem um ticket aberto em {existing.mention}.", ephemeral=True)
            return

        for ch in category.text_channels:
            if ch.topic and f"UserID:{interaction.user.id}" in ch.topic and not ch.name.startswith("fechado-"):
                await interaction.response.send_message(f"⚠️ Você já tem um ticket aberto em {ch.mention}.", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        overwrites.update(_staff_overwrites(guild))

        user_slug = _normalize_channel_name(interaction.user.display_name)
        channel_name = f"ticket-{ticket_type}-{interaction.user.id}"
        topic = f"Ticket:{ticket_type} UserID:{interaction.user.id} User:{user_slug}"

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=topic,
            )
        except Exception:
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{ticket_type}-{interaction.user.id}"[:80],
                category=category,
                overwrites=overwrites,
                topic=topic,
            )

        embed = discord.Embed(
            title="🎫 Ticket aberto",
            description=f"Olá {interaction.user.mention}, um membro da nossa equipe vai te atender em breve!",
            color=discord.Color.green(),
        )

        ping_staff = _staff_mentions(guild)
        content = f"{interaction.user.mention}"
        if ping_staff:
            content = f"{content} {ping_staff}"

        await ticket_channel.send(content=content, embed=embed, view=TicketManageView())
        await interaction.response.send_message(f"✅ Ticket criado em {ticket_channel.mention}.", ephemeral=True)

    @discord.ui.button(label="Suporte", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket_open_suporte")
    async def open_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_ticket(interaction, "suporte")

    @discord.ui.button(label="Compras", style=discord.ButtonStyle.success, emoji="🛒", custom_id="ticket_open_compras")
    async def open_sales(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_ticket(interaction, "compras")

    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="ticket_open_denuncia")
    async def open_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_ticket(interaction, "denuncia")


class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _get_owner_id(self, channel: discord.abc.GuildChannel) -> int | None:
        topic = getattr(channel, "topic", None) or ""
        marker = "UserID:"
        if marker not in topic:
            return None
        try:
            value = topic.split(marker, 1)[1].strip().split()[0]
            return int(value)
        except Exception:
            return None

    def _is_staff(self, member: discord.Member) -> bool:
        return _member_has_any_id(member, TICKET_STAFF_IDS)

    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Este botão só funciona dentro do servidor.", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Canal inválido.", ephemeral=True)
            return

        owner_id = self._get_owner_id(channel)
        if owner_id is None:
            await interaction.response.send_message("❌ Não foi possível identificar o dono do ticket.", ephemeral=True)
            return

        if interaction.user.id != owner_id and not self._is_staff(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para fechar este ticket.", ephemeral=True)
            return

        if channel.name.startswith("fechado-"):
            await interaction.response.send_message("⚠️ Este ticket já está fechado.", ephemeral=True)
            return

        owner = interaction.guild.get_member(owner_id)
        if owner is not None:
            try:
                await channel.set_permissions(owner, read_messages=False, send_messages=False)
            except Exception:
                pass

        new_name = f"fechado-{channel.name}"[:80]
        try:
            await channel.edit(name=new_name)
        except Exception:
            pass

        await interaction.response.send_message("✅ Ticket fechado.", ephemeral=True)

    @discord.ui.button(label="Deletar", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="ticket_delete")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Este botão só funciona dentro do servidor.", ephemeral=True)
            return

        if not self._is_staff(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para deletar este ticket.", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Canal inválido.", ephemeral=True)
            return

        await interaction.response.send_message("🗑️ Deletando ticket...", ephemeral=True)
        await channel.delete()


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketManageView())

    def _can_use_ticket_command(self, member: discord.Member) -> bool:
        return _member_has_any_id(member, TICKET_STAFF_IDS)

    @app_commands.command(name="ticket", description="Publica o painel de tickets no canal configurado.")
    async def ticket(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Este comando só funciona dentro do servidor.", ephemeral=True)
            return

        if not self._can_use_ticket_command(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(TICKET_CANAL_ID)
        if channel is None or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Canal de ticket não encontrado.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 Central de Atendimento",
            description="Clique em um botão abaixo para abrir seu ticket.",
            color=discord.Color.blurple(),
        )
        await channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message(f"✅ Painel enviado em {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
