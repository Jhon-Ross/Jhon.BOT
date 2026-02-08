import discord
from discord.ext import commands, tasks
from discord import app_commands
import mercadopago
import os
from dotenv import load_dotenv
import database
import uuid
import asyncio

load_dotenv()

# --- CLASSE DA VIEW PERSISTENTE ---
class BuyView(discord.ui.View):
    def __init__(self, payments_cog):
        # timeout=None faz o botão não expirar nunca
        super().__init__(timeout=None)
        self.payments_cog = payments_cog

    # custom_id fixo é o segredo para o botão funcionar após reinício
    @discord.ui.button(label="Comprar P1000 - R$ 10,00", style=discord.ButtonStyle.success, emoji="🛒", custom_id="persistent_buy_p1000")
    async def buy_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Chama a função de gerar pagamento do Cog
        await self.payments_cog.gerar_pagamento(interaction)

class Payments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Inicializa SDK do Mercado Pago
        self.sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))
        
        # Dicionário para armazenar pedidos pendentes
        self.pending_orders = {}
        
        # Inicia o loop de verificação
        self.check_payments_loop.start()

    async def cog_load(self):
        # Registra a View Persistente quando o Cog carregar
        self.bot.add_view(BuyView(self))

    def cog_unload(self):
        self.check_payments_loop.cancel()

    # --- COMANDO PARA POSTAR O ANÚNCIO ---
    @app_commands.command(name="painel_vendas", description="Posta o painel de vendas permanente com botão.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_vendas(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Responde só pro admin que deu certo

        embed = discord.Embed(
            title="Acabou os Pulerins?",
            description=(
                "Atenção <@&1097523878839980163>, não se preocupe, temos a solução!\n"
                "Por apenas **R$ 10,00** você pode adquirir até **P1000**.\n\n"
                "💎 **Entrega 100% Automática**\n"
                "💳 **Pix, Cartão ou Boleto**\n"
                "🔒 **Seguro via Mercado Pago**\n\n"
                "Clique no botão abaixo para gerar seu link de pagamento exclusivo! 👇"
            ),
            color=0xFFD700 # Dourado
        )
        
        # Configura imagem local de forma relativa
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_path, "imgs", "pulerins.png")
        
        file = discord.File(file_path, filename="pulerins.png")
        embed.set_image(url="attachment://pulerins.png")
        
        embed.set_footer(text="Comunidade Jhon Ross • Sistema Automático")

        # Envia no canal onde o comando foi usado
        await interaction.channel.send(embed=embed, file=file, view=BuyView(self))
        await interaction.followup.send("✅ Painel de vendas postado com sucesso!", ephemeral=True)

    # --- COMANDO ANTIGO (Mantido como atalho) ---
    @app_commands.command(name="pulerins", description="Gera um link de compra rápido.")
    async def comprar_pulerins(self, interaction: discord.Interaction):
        # Apenas chama a função centralizada
        await self.gerar_pagamento(interaction)

    # --- LÓGICA CENTRAL DE PAGAMENTO ---
    async def gerar_pagamento(self, interaction: discord.Interaction):
        # Se já foi deferida (pelo botão) ou não
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        try:
            order_id = str(uuid.uuid4())

            # Preferência de Pagamento
            preference_data = {
                "items": [
                    {
                        "id": "pulerins_1000",
                        "title": "1000 Pulerins - Servidor do Jhon",
                        "quantity": 1,
                        "currency_id": "BRL",
                        "unit_price": 10.00
                    }
                ],
                "back_urls": {
                    "success": "https://www.google.com",
                    "failure": "https://www.google.com",
                    "pending": "https://www.google.com"
                },
                "auto_return": "approved",
                "external_reference": order_id,
                "statement_descriptor": "JHON STORE"
            }

            preference_response = self.sdk.preference().create(preference_data)
            preference = preference_response["response"]
            checkout_url = preference["init_point"]

            # Salva pedido
            self.pending_orders[order_id] = {
                "user_id": interaction.user.id,
                "created_at": discord.utils.utcnow(),
                "interaction": interaction
            }

            # Embed de Pagamento (Individual)
            embed = discord.Embed(
                title="💎 Finalizar Compra",
                description="Clique no link abaixo para pagar no Mercado Pago.",
                color=0x00AEEF
            )
            embed.add_field(name="💰 Valor", value="R$ 10,00", inline=True)
            embed.set_footer(text=f"ID: {order_id}")

            view = discord.ui.View()
            button = discord.ui.Button(label="Pagar no Mercado Pago", style=discord.ButtonStyle.link, url=checkout_url)
            view.add_item(button)

            # Envia APENAS para quem clicou (ephemeral)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"Erro ao gerar link: {e}")
            await interaction.followup.send("❌ Erro ao gerar link. Tente novamente.", ephemeral=True)

    @tasks.loop(seconds=15)
    async def check_payments_loop(self):
        if not self.pending_orders:
            return

        orders_to_remove = []

        for order_id, data in self.pending_orders.items():
            try:
                filters = {"external_reference": order_id}
                search_result = self.sdk.payment().search(filters)
                
                if search_result["status"] == 200 and search_result["response"]["results"]:
                    payment = search_result["response"]["results"][-1]
                    status = payment["status"]
                    status_detail = payment.get("status_detail", "N/A")
                    
                    if status == "approved":
                        print(f"💰 Pagamento APROVADO para {order_id}: Detalhe={status_detail}")
                        await self.deliver_product(data["user_id"], 1000, order_id)
                        orders_to_remove.append(order_id)
                    
                    elif status == "rejected" or status == "cancelled":
                        print(f"❌ Pagamento rejeitado/cancelado para {order_id}")
                        orders_to_remove.append(order_id)
                else:
                    pass

            except Exception as e:
                print(f"Erro ao verificar pedido {order_id}: {e}")

        for oid in orders_to_remove:
            if oid in self.pending_orders:
                del self.pending_orders[oid]

    async def deliver_product(self, user_id, amount, order_id):
        try:
            database.ensure_user(user_id)
            database.update_pulerins(user_id, amount)

            print(f"✅ Entrega realizada: {amount} Pulerins para {user_id} (Ref: {order_id})")

            user = self.bot.get_user(user_id)
            if user:
                try:
                    await user.send(f"✅ **Pagamento Aprovado!** Você recebeu **{amount} Pulerins** na sua conta. Obrigado por comprar! 🛒")
                except:
                    pass

            if order_id in self.pending_orders:
                interaction = self.pending_orders[order_id].get("interaction")
                if interaction:
                    try:
                        new_embed = discord.Embed(
                            title="✅ Compra Concluída!",
                            description=f"Pagamento confirmado! **{amount} Pulerins** creditados.",
                            color=discord.Color.green()
                        )
                        await interaction.edit_original_response(embed=new_embed, view=None)
                    except Exception as ex:
                        print(f"Não foi possível editar a mensagem original: {ex}")

        except Exception as e:
            print(f"❌ Erro crítico ao entregar produto: {e}")

async def setup(bot):
    await bot.add_cog(Payments(bot))
