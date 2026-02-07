import discord
from discord.ext import commands, tasks
from discord import app_commands
import mercadopago
import os
from dotenv import load_dotenv
import sqlite3
import uuid
import asyncio

load_dotenv()

class Payments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Inicializa SDK do Mercado Pago
        self.sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))
        
        # Dicionário para armazenar pedidos pendentes
        # Chave: external_reference (UUID), Valor: {user_id: int, channel_id: int, message_id: int}
        self.pending_orders = {}
        
        # Inicia o loop de verificação
        self.check_payments_loop.start()

    def cog_unload(self):
        self.check_payments_loop.cancel()

    @app_commands.command(name="pulerins", description="Compre 1000 Pulerins e pague como quiser (Pix, Cartão, Boleto)")
    async def comprar_pulerins(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Gera um ID único para essa transação
            order_id = str(uuid.uuid4())

            # Dados da preferência de pagamento (Checkout Pro)
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
                "payer": {
                    "email": f"user_{interaction.user.id}@discord.com", # Email fictício apenas para controle
                    "name": interaction.user.name,
                    "surname": interaction.user.discriminator
                },
                "back_urls": {
                    "success": "https://www.google.com", # Pode redirecionar para site do servidor se tiver
                    "failure": "https://www.google.com",
                    "pending": "https://www.google.com"
                },
                "auto_return": "approved",
                "external_reference": order_id, # Chave para rastrearmos o pagamento depois
                "statement_descriptor": "JHON STORE"
            }

            # Cria a preferência
            preference_response = self.sdk.preference().create(preference_data)
            preference = preference_response["response"]
            
            # Pega o link de pagamento (init_point é o link para produção)
            checkout_url = preference["init_point"]

            # Salva o pedido para monitoramento
            self.pending_orders[order_id] = {
                "user_id": interaction.user.id,
                "created_at": discord.utils.utcnow()
            }

            # Cria Embed Bonita
            embed = discord.Embed(
                title="💎 Comprar 1000 Pulerins",
                description=(
                    "Clique no botão abaixo para finalizar sua compra de forma segura pelo **Mercado Pago**.\n\n"
                    "✅ **Aceitamos:** Pix, Cartão de Crédito, Débito, Boleto.\n"
                    "🚀 **Entrega Automática:** Assim que o pagamento for aprovado, seus Pulerins cairão na conta!"
                ),
                color=0x00AEEF # Azul Cyan
            )
            embed.add_field(name="💰 Valor", value="R$ 10,00", inline=True)
            embed.add_field(name="📦 Produto", value="1000 Pulerins", inline=True)
            embed.set_footer(text=f"ID do Pedido: {order_id}")
            embed.set_image(url="https://media.discordapp.net/attachments/1335039046522900595/1337222852239458315/image.png?ex=67a6a7cb&is=67a5564b&hm=602b972e399589d81f21192e210519f074d28994e63e793930b8e7520e58849b&=&format=webp&quality=lossless&width=394&height=350")

            # Botão com Link
            view = discord.ui.View()
            button = discord.ui.Button(label="Pagar Agora", style=discord.ButtonStyle.link, url=checkout_url)
            view.add_item(button)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"Erro ao criar preferência: {e}")
            await interaction.followup.send("❌ Ocorreu um erro interno ao gerar o link. Tente novamente.", ephemeral=True)

    @tasks.loop(seconds=15)
    async def check_payments_loop(self):
        """Verifica se algum pedido pendente foi pago"""
        if not self.pending_orders:
            return

        orders_to_remove = []

        for order_id, data in self.pending_orders.items():
            try:
                # Busca pagamentos com essa external_reference
                filters = {"external_reference": order_id}
                search_result = self.sdk.payment().search(filters)
                
                if search_result["status"] == 200 and search_result["response"]["results"]:
                    # Pega o pagamento mais recente
                    payment = search_result["response"]["results"][-1] # Último da lista
                    status = payment["status"]

                    if status == "approved":
                        await self.deliver_product(data["user_id"], 1000, order_id)
                        orders_to_remove.append(order_id)
                    
                    elif status == "rejected" or status == "cancelled":
                        # Se foi rejeitado, removemos da lista para ele tentar de novo gerando outro link se quiser
                        orders_to_remove.append(order_id)

                # Limpeza de pedidos muito antigos (opcional, para não acumular lixo na memória)
                # (Lógica simples: se passar muito tempo, removemos. Por enquanto deixo infinito até reiniciar)

            except Exception as e:
                print(f"Erro ao verificar pedido {order_id}: {e}")

        # Remove pedidos processados
        for oid in orders_to_remove:
            if oid in self.pending_orders:
                del self.pending_orders[oid]

    async def deliver_product(self, user_id, amount, order_id):
        """Entrega os Pulerins e avisa o usuário"""
        try:
            # Atualiza no Banco de Dados
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            
            # Verifica se usuário existe, se não cria
            c.execute("SELECT * FROM economy WHERE user_id = ?", (user_id,))
            if not c.fetchone():
                c.execute("INSERT INTO economy (user_id, wallet, bank) VALUES (?, ?, ?)", (user_id, 0, 0))
            
            # Adiciona dinheiro
            c.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
            conn.close()

            print(f"✅ Entrega realizada: {amount} Pulerins para {user_id} (Ref: {order_id})")

            # Tenta avisar o usuário no DM (ou busca canal se preferir)
            user = self.bot.get_user(user_id)
            if user:
                try:
                    await user.send(f"✅ **Pagamento Aprovado!** Você recebeu **{amount} Pulerins** na sua conta. Obrigado por comprar! 🛒")
                except:
                    pass # DM fechada
            
        except Exception as e:
            print(f"❌ Erro crítico ao entregar produto: {e}")

async def setup(bot):
    await bot.add_cog(Payments(bot))
