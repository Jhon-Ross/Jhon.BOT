import discord
from discord import app_commands
from discord.ext import commands
import logging

# Configurações de IDs
CATEGORY_LOJA_ID = 1098657328569524415
CATEGORY_SUPORTE_ID = 1096139038886473828 # Categoria onde os tickets serão abertos
CHANNEL_ANUNCIOS_ID = 1467914590825484487
CHANNEL_PRODUTOS_ID = 1467914700582031462
CHANNEL_DUVIDAS_ID = 1467914831699902628

class ProductView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # View persistente

    @discord.ui.button(label="Comprar Agora", style=discord.ButtonStyle.green, emoji="🛒", custom_id="loja_btn_comprar")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Lógica de criação de Ticket de Compra
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_SUPORTE_ID)
        
        if not category:
            await interaction.response.send_message("❌ Erro: Categoria de Suporte não configurada.", ephemeral=True)
            return

        # Verifica se já tem ticket aberto (opcional, mas recomendado para evitar spam)
        channel_name = f"carrinho-{interaction.user.name.lower().replace(' ', '-')}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name, category=category)
        
        if existing_channel:
            await interaction.response.send_message(f"⚠️ Você já tem um carrinho aberto em {existing_channel.mention}!", ephemeral=True)
            return

        # Permissões do Ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Carrinho de compras de {interaction.user.name} (ID: {interaction.user.id})"
            )
            
            # Tenta pegar informações do produto do embed original
            product_name = "Produto da Loja"
            if interaction.message.embeds:
                product_name = interaction.message.embeds[0].title or product_name

            embed_ticket = discord.Embed(
                title=f"🛒 Carrinho: {product_name}",
                description=f"Olá {interaction.user.mention}, um membro da nossa equipe vai te atender em breve!",
                color=discord.Color.green()
            )
            
            await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed_ticket)
            await interaction.response.send_message(f"✅ Seu carrinho foi aberto em {ticket_channel.mention}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao criar ticket: {e}", ephemeral=True)
            logging.error(f"Erro ao criar ticket de loja: {e}")

    @discord.ui.button(label="Tenho Dúvidas", style=discord.ButtonStyle.secondary, emoji="❓", custom_id="loja_btn_duvidas")
    async def doubt_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_duvidas = interaction.guild.get_channel(CHANNEL_DUVIDAS_ID)
        msg = "👋 Tem dúvidas sobre este produto?"
        if channel_duvidas:
            msg += f"\nPor favor, vá até o canal {channel_duvidas.mention} e abra um ticket de suporte ou pergunte lá!"
        else:
            msg += "\nEntre em contato com a administração."
            
        await interaction.response.send_message(msg, ephemeral=True)

class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Registra a View persistente para que os botões funcionem após reinício
        self.bot.add_view(ProductView())
        logging.info("Store View registrada com sucesso.")

    def is_in_store_category(self, interaction: discord.Interaction) -> bool:
        """Verifica se o comando foi usado dentro da categoria LOJA."""
        if interaction.channel and interaction.channel.category_id == CATEGORY_LOJA_ID:
            return True
        return False

    @app_commands.command(name="anuncio-loja", description="Cria um anúncio personalizado para a loja.")
    @app_commands.describe(
        titulo="Título do anúncio",
        descricao="Descrição do anúncio",
        imagem="URL da imagem (opcional)",
        cor="Cor do embed em Hex (ex: #FF0000) (opcional)",
        rodape="Texto do rodapé (opcional)"
    )
    async def anuncio_loja(
        self, 
        interaction: discord.Interaction, 
        titulo: str = None, 
        descricao: str = None, 
        imagem: str = None, 
        cor: str = None, 
        rodape: str = None
    ):
        # Verificação de Categoria
        if not self.is_in_store_category(interaction):
            await interaction.response.send_message("❌ Este comando só pode ser usado na categoria **LOJA**.", ephemeral=True)
            return

        # Busca o canal de anúncios
        channel = self.bot.get_channel(CHANNEL_ANUNCIOS_ID)
        if not channel:
            await interaction.response.send_message("❌ Canal de Anúncios não encontrado! Verifique a configuração.", ephemeral=True)
            return

        # Tratamento de cor
        color = discord.Color.blue() # Padrão
        if cor:
            try:
                # Remove # se tiver e converte
                cor_clean = cor.replace("#", "")
                color = discord.Color(int(cor_clean, 16))
            except ValueError:
                await interaction.response.send_message("❌ Cor inválida! Use formato Hex (ex: #FF0000).", ephemeral=True)
                return

        embed = discord.Embed(color=color)
        
        if titulo:
            embed.title = titulo
        if descricao:
            # Substitui \n por quebras de linha reais
            embed.description = descricao.replace("\\n", "\n")
        if imagem:
            embed.set_image(url=imagem)
        if rodape:
            embed.set_footer(text=rodape)
        
        # Se o usuário não colocou nada
        if not titulo and not descricao and not imagem:
            await interaction.response.send_message("❌ Você precisa fornecer pelo menos um Título, Descrição ou Imagem.", ephemeral=True)
            return

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Anúncio postado com sucesso em {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao enviar anúncio: {e}", ephemeral=True)
            logging.error(f"Erro ao enviar anúncio de loja: {e}")

    def format_price(self, price: str) -> str:
        """Formata o preço para incluir R$ se for apenas números."""
        if not price:
            return price
        # Remove espaços
        clean_price = price.strip()
        # Se só tiver números e/ou vírgula/ponto, adiciona R$
        # Verifica se começa com número
        if clean_price[0].isdigit():
             return f"R$ {clean_price}"
        return clean_price

    @app_commands.command(name="produto", description="Posta um novo produto na loja.")
    @app_commands.describe(
        nome="Nome do produto",
        preco="Preço do produto",
        descricao="Descrição detalhada",
        imagem="URL da imagem do produto",
        estoque="Quantidade em estoque ou 'Ilimitado'",
        link="Link para compra ou mais info",
        cor="Cor da lateral do anúncio (Hex)"
    )
    async def produto(
        self, 
        interaction: discord.Interaction, 
        nome: str = None, 
        preco: str = None, 
        descricao: str = None, 
        imagem: str = None, 
        estoque: str = None, 
        link: str = None,
        cor: str = None
    ):
        # Verificação de Categoria
        if not self.is_in_store_category(interaction):
            await interaction.response.send_message("❌ Este comando só pode ser usado na categoria **LOJA**.", ephemeral=True)
            return

        channel = self.bot.get_channel(CHANNEL_PRODUTOS_ID)
        if not channel:
            await interaction.response.send_message("❌ Canal de Produtos não encontrado!", ephemeral=True)
            return

        # Cor padrão verde para produtos (venda)
        color = discord.Color.green()
        if cor:
            try:
                cor_clean = cor.replace("#", "")
                color = discord.Color(int(cor_clean, 16))
            except:
                pass

        embed = discord.Embed(color=color)
        
        if nome:
            embed.title = nome
        
        if descricao:
            embed.description = descricao.replace("\\n", "\n")
            
        if preco:
            formatted_price = self.format_price(preco)
            embed.add_field(name="💰 Preço", value=f"**{formatted_price}**", inline=True)
            
        if estoque:
            embed.add_field(name="📦 Estoque", value=f"`{estoque}`", inline=True)
            
        if link:
            embed.add_field(name="🔗 Link / Compra", value=f"[Clique Aqui]({link})", inline=False)
            
        if imagem:
            embed.set_image(url=imagem)

        # Rodapé padrão da loja
        embed.set_footer(text="🛒 Loja Oficial • Dúvidas? Vá ao canal de suporte!")

        if not nome and not imagem and not descricao:
             await interaction.response.send_message("❌ O produto precisa ter pelo menos Nome, Descrição ou Imagem.", ephemeral=True)
             return

        try:
            msg = await channel.send(embed=embed, view=ProductView())
            await interaction.response.send_message(f"✅ Produto postado! (ID da mensagem: `{msg.id}`)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao postar produto: {e}", ephemeral=True)

    @app_commands.command(name="editar-produto", description="Edita um produto já postado (Use o ID da mensagem).")
    @app_commands.describe(
        mensagem_id="ID da mensagem do produto (copie do chat)",
        novo_preco="Novo preço (opcional)",
        novo_estoque="Novo estoque (opcional)",
        nova_descricao="Nova descrição (opcional)"
    )
    async def editar_produto(
        self, 
        interaction: discord.Interaction, 
        mensagem_id: str, 
        novo_preco: str = None, 
        novo_estoque: str = None,
        nova_descricao: str = None
    ):
        if not self.is_in_store_category(interaction):
            await interaction.response.send_message("❌ Este comando só pode ser usado na categoria **LOJA**.", ephemeral=True)
            return

        channel = self.bot.get_channel(CHANNEL_PRODUTOS_ID)
        
        try:
            msg = await channel.fetch_message(int(mensagem_id))
        except:
            await interaction.response.send_message("❌ Mensagem não encontrada no canal de produtos.", ephemeral=True)
            return

        if not msg.embeds:
            await interaction.response.send_message("❌ Essa mensagem não contém um produto válido.", ephemeral=True)
            return

        embed = msg.embeds[0]

        # Atualiza campos existentes ou adiciona novos
        if nova_descricao:
            embed.description = nova_descricao.replace("\\n", "\n")

        # Para campos (fields), precisamos reconstruir a lista pois fields são imutáveis diretamente por índice as vezes em libs antigas, 
        # mas no discord.py moderno podemos limpar e refazer ou editar.
        # A estratégia mais segura é recriar os fields mantendo o que não mudou.
        
        # Vamos fazer um mapa dos fields atuais
        fields_data = {field.name: field.value for field in embed.fields}
        
        if novo_preco:
            formatted_price = self.format_price(novo_preco)
            fields_data["💰 Preço"] = f"**{formatted_price}**"
            
        if novo_estoque:
            fields_data["📦 Estoque"] = f"`{novo_estoque}`"

        # Limpa e readiciona na ordem preferencial
        embed.clear_fields()
        
        # Ordem de exibição
        order = ["💰 Preço", "📦 Estoque", "🔗 Link / Compra"]
        
        for name in order:
            if name in fields_data:
                # Link costuma ser inline=False
                inline = False if "Link" in name else True
                embed.add_field(name=name, value=fields_data[name], inline=inline)
        
        # Adiciona quaisquer outros campos que não estavam na ordem padrão (caso tenha adicionado extras manualmente)
        for name, value in fields_data.items():
            if name not in order:
                 embed.add_field(name=name, value=value, inline=True)

        await msg.edit(embed=embed)
        await interaction.response.send_message("✅ Produto atualizado com sucesso!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Store(bot))
