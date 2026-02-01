import discord
from discord import app_commands
from discord.ext import commands
import database

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        database.init_db()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Novo membro ganha 1k Pulerins
        database.create_user(member.id, initial_pulerins=1000)
    
    @app_commands.command(name="saldo", description="Verifica sua carteira de Pulerins e Fichas.")
    @app_commands.describe(usuario="Usuário para ver o saldo (opcional)")
    async def saldo(self, interaction: discord.Interaction, usuario: discord.User = None):
        target = usuario or interaction.user
        database.ensure_user(target.id)
        user_data = database.get_user(target.id)
        
        # user_data: (id, pulerins, chips)
        pulerins = user_data[1]
        chips = user_data[2]
        
        embed = discord.Embed(title=f"💰 Carteira de {target.display_name}", color=discord.Color.gold())
        embed.add_field(name="🪙 Pulerins", value=f"**{pulerins}**", inline=True)
        embed.add_field(name="🎰 Fichas", value=f"**{chips}**", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        if target.id == interaction.user.id:
            embed.set_footer(text="Use /loja para comprar mais fichas!")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loja", description="Acesse a loja para comprar ou vender fichas.")
    @app_commands.describe(acao="O que você deseja fazer?", quantidade="Quantidade de fichas")
    @app_commands.choices(acao=[
        app_commands.Choice(name="Comprar Fichas (1 Pulerin = 1 Ficha)", value="comprar"),
        app_commands.Choice(name="Vender Fichas (1 Ficha = 1 Pulerin)", value="vender")
    ])
    async def loja(self, interaction: discord.Interaction, acao: str, quantidade: int):
        if quantidade <= 0:
            await interaction.response.send_message("❌ A quantidade deve ser maior que zero.", ephemeral=True)
            return

        database.ensure_user(interaction.user.id)
        user_data = database.get_user(interaction.user.id)
        pulerins = user_data[1]
        chips = user_data[2]

        if acao == "comprar":
            custo = quantidade # 1:1
            if pulerins < custo:
                await interaction.response.send_message(f"❌ Você não tem Pulerins suficientes! (Tem: {pulerins}, Precisa: {custo})", ephemeral=True)
                return
            
            database.update_pulerins(interaction.user.id, -custo)
            database.update_chips(interaction.user.id, quantidade)
            await interaction.response.send_message(f"✅ **Compra realizada!**\nGastou: {custo} 🪙\nRecebeu: {quantidade} 🎰")

        elif acao == "vender":
            if chips < quantidade:
                await interaction.response.send_message(f"❌ Você não tem Fichas suficientes! (Tem: {chips}, Quer vender: {quantidade})", ephemeral=True)
                return
            
            database.update_chips(interaction.user.id, -quantidade)
            database.update_pulerins(interaction.user.id, quantidade) # 1:1
            await interaction.response.send_message(f"✅ **Venda realizada!**\nVendeu: {quantidade} 🎰\nRecebeu: {quantidade} 🪙")

    @app_commands.command(name="pagar", description="Transfere Pulerins para outro jogador.")
    @app_commands.describe(usuario="Quem vai receber", valor="Quantidade de Pulerins")
    async def pagar(self, interaction: discord.Interaction, usuario: discord.User, valor: int):
        if valor <= 0:
            await interaction.response.send_message("❌ O valor deve ser positivo.", ephemeral=True)
            return
        
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("❌ Você não pode pagar a si mesmo.", ephemeral=True)
            return

        database.ensure_user(interaction.user.id)
        user_data = database.get_user(interaction.user.id)
        pulerins = user_data[1]

        if pulerins < valor:
            await interaction.response.send_message(f"❌ Saldo insuficiente. Você tem {pulerins} Pulerins.", ephemeral=True)
            return

        database.ensure_user(usuario.id)
        
        database.update_pulerins(interaction.user.id, -valor)
        database.update_pulerins(usuario.id, valor)
        
        await interaction.response.send_message(f"💸 **Transferência realizada!**\n{interaction.user.mention} enviou **{valor} Pulerins** para {usuario.mention}.")

    @app_commands.command(name="rank", description="Veja o ranking dos membros mais ricos.")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Maior fortuna em Pulerins 🪙", value="pulerins"),
        app_commands.Choice(name="Maior quantidade de Fichas 🎰", value="chips")
    ])
    async def rank(self, interaction: discord.Interaction, tipo: str = "pulerins"):
        top_users = database.get_top_users(limit=10, order_by=tipo)
        
        if not top_users:
            await interaction.response.send_message("📉 Ainda não há dados suficientes para o ranking.", ephemeral=True)
            return

        title = "🏆 Ranking de Pulerins" if tipo == "pulerins" else "🎰 Ranking de Fichas"
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        description = ""
        for index, user_data in enumerate(top_users, start=1):
            user_id, pulerins, chips = user_data
            
            # Tenta pegar o membro do servidor
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"Usuário Desconhecido ({user_id})"
            
            if index == 1:
                medal = "🥇"
            elif index == 2:
                medal = "🥈"
            elif index == 3:
                medal = "🥉"
            else:
                medal = f"**{index}º**"
            
            val = pulerins if tipo == "pulerins" else chips
            currency = "🪙" if tipo == "pulerins" else "🎰"
            
            description += f"{medal} **{name}** — {val} {currency}\n"

        embed.description = description
        embed.set_footer(text="Use /loja para transformar Pulerins em Fichas!")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))
