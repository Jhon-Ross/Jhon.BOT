import discord
from discord import app_commands
from discord.ext import commands
import qrcode
from io import BytesIO
import requests
import re
import random
import os
from dotenv import load_dotenv

load_dotenv()

VISITANTE_ID = int(os.getenv("VISITANTE_ID") or 0)
COMUNIDADE_ID = int(os.getenv("COMUNIDADE_ID") or 0)
PALAVRA_CHANNEL_ID = int(os.getenv("PALAVRA_CHANNEL_ID") or 0)
BIBLE_ID = os.getenv("BIBLE_ID")
API_KEY = os.getenv("API_KEY")

class PersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Iniciar verificação", style=discord.ButtonStyle.green, emoji="✅", custom_id="verificacao_botao")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        guild = member.guild
        visitante_role = discord.utils.get(guild.roles, id=VISITANTE_ID)
        comunidade_role = discord.utils.get(guild.roles, id=COMUNIDADE_ID)

        if visitante_role in member.roles:
            await member.remove_roles(visitante_role)
            await member.add_roles(comunidade_role)
            await interaction.response.send_message(
                f"Parabéns {member.mention}! Você agora é um membro verificado e recebeu o cargo **Comunidade**! 🎉",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{member.mention}, você já é um membro verificado! Esse botão não serve para você. 😉",
                ephemeral=True
            )

class Utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pix", description="Gera QR Code e link Pix para doação ao canal.")
    async def pix(self, interaction: discord.Interaction):
        pix_code = "00020126710014BR.GOV.BCB.PIX0111094014879010234Muito obrigado por ajudar o canal.5204000053039865802BR5922Jhon Ross Abdo de Lara6009SAO PAULO62140510BN6RYqd88P63043AFF"
        qr = qrcode.make(pix_code)
        byte_io = BytesIO()
        qr.save(byte_io, "PNG")
        byte_io.seek(0)
        pix_link = f"https://nubank.com.br/cobrar/1ala9x/6745f61b-7998-41ed-9239-a0b6517b195d"

        embed = discord.Embed(
            title="Pix QR Code",
            description=f"Aqui está o QR code do Pix. Escaneie para fazer uma doação ao canal!\n\n[Clique aqui para pagar via Pix Copia e Cola]({pix_link})",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Pix - Pagamento instantâneo")
        await interaction.response.send_message(embed=embed, file=discord.File(byte_io, filename="qrcode.png"))

    @app_commands.command(name="palavra", description="Receba uma palavra do Senhor para o seu dia!")
    async def palavra(self, interaction: discord.Interaction):
        if PALAVRA_CHANNEL_ID and interaction.channel.id != PALAVRA_CHANNEL_ID:
            await interaction.response.send_message(f"❌ Este comando só pode ser usado no canal <#{PALAVRA_CHANNEL_ID}>.", ephemeral=True)
            return

        await interaction.response.defer() # A API pode demorar
        verse = self.get_random_verse()
        if len(verse) > 2000:
            await interaction.followup.send("❌ O versículo excede o limite de 2000 caracteres.")
        else:
            await interaction.followup.send(verse)

    @app_commands.command(name="apresentacao", description="Envia embed com a apresentação do desenvolvedor.")
    async def apresentacao(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌟 Jhon Ross | Desenvolvedor em Ascensão 🚀",
            description=(
                "💻 **Linguagens:**\n"
                "🐍 Python\n"
                "⚡ JavaScript\n"
                "🌙 Lua\n\n"
                "🌐 **Desenvolvimento Web:**\n"
                "🎨 HTML & CSS\n\n"
                "🛠️ Apaixonado por transformar ideias em **linhas de código** que fazem a diferença!\n"
                "🎯 Focado em **crescimento contínuo** e criando experiências únicas na web.\n\n"
                "💡 Sempre pronto para **aprender, colaborar e inovar**!\n"
                "📬 Me chama pra trocar uma ideia ou discutir aquele projeto incrível! ✌️"
            ),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="verificar", description="Envia o painel de verificação.")
    async def verificar(self, interaction: discord.Interaction):
        if VERIFICAR_ID and interaction.channel.id != VERIFICAR_ID:
            await interaction.response.send_message(f"❌ Este comando só pode ser usado no canal <#{VERIFICAR_ID}>.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem enviar o painel de verificação.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🚀 Bem-vindo ao nosso servidor!",
            description=(
                "Para nossa segurança 🔒, mostre que você não é um robô assim como eu 🤭! "
                "Clique no botão abaixo para se verificar.✅"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Esperamos que se divirta muito por aqui. 😊")
        
        # Tenta usar imagem local 'verificar.gif', se não existir usa a padrão
        file = None
        if os.path.exists("verificar.gif"):
            file = discord.File("verificar.gif", filename="verificar.gif")
            embed.set_image(url="attachment://verificar.gif")
        else:
            embed.set_image(url="https://media.discordapp.net/attachments/1310617769326153738/1310617942207238224/discord.png?ex=67488293&is=67473113&hm=40ca91c5481bf1dd211c57cdef551335a3b60a15085269cb04bc5376d2e23ee1&=&format=webp&quality=lossless")

        if file:
            await interaction.channel.send(embed=embed, view=PersistentView(), file=file)
        else:
            await interaction.channel.send(embed=embed, view=PersistentView())
        
        await interaction.response.send_message("Painel enviado!", ephemeral=True)

    @app_commands.command(name="regras", description="Exibe as regras de moderação e convivência do servidor.")
    async def regras(self, interaction: discord.Interaction):
        file_path = "REGRAS_MODERACAO.md"
        
        if not os.path.exists(file_path):
            await interaction.response.send_message("❌ O arquivo de regras não foi encontrado.", ephemeral=True)
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove o título principal do MD para usar no título do Embed
        lines = content.split("\n")
        title = "🛡️ Regras de Convivência"
        clean_content = content
        
        if lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
            clean_content = "\n".join(lines[1:]).strip()

        embed = discord.Embed(
            title=title,
            description=clean_content,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_footer(text="Leia com atenção para uma boa convivência! 😊")
        
        # Tenta usar a imagem de verificação como thumbnail para dar um estilo
        if os.path.exists("verificar.gif"):
            file = discord.File("verificar.gif", filename="verificar.gif")
            embed.set_thumbnail(url="attachment://verificar.gif")
            await interaction.response.send_message(embed=embed, file=file)
        else:
            await interaction.response.send_message(embed=embed)

    def get_random_verse(self):
        try:
            headers = {"api-key": API_KEY}
            books_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/books"
            response = requests.get(books_url, headers=headers)
            response.raise_for_status()
            books = response.json().get("data", [])
            if not books: return "❌ Nenhum livro encontrado."

            random_book = random.choice(books)
            chapters_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/books/{random_book['id']}/chapters"
            chapters_response = requests.get(chapters_url, headers=headers)
            chapters_response.raise_for_status()
            chapters = chapters_response.json().get("data", [])
            if not chapters: return f"❌ O livro '{random_book['name']}' não contém capítulos."

            random_chapter = random.choice(chapters)
            verses_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/chapters/{random_chapter['id']}/verses"
            verses_response = requests.get(verses_url, headers=headers)
            verses_response.raise_for_status()
            verses = verses_response.json().get("data", [])
            if len(verses) < 2: return f"❌ O capítulo '{random_chapter['reference']}' não contém versículos suficientes."

            sorted_verses = sorted(verses, key=lambda x: int(x["reference"].split(":")[-1].split("-")[0]))
            start_index = random.randint(0, len(sorted_verses) - 2)
            selected_verses = sorted_verses[start_index:start_index + 2]

            formatted_verses = []
            references = []
            for verse in selected_verses:
                verse_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/verses/{verse['id']}"
                verse_response = requests.get(verse_url, headers=headers)
                verse_response.raise_for_status()
                verse_data = verse_response.json().get("data", {})
                content = re.sub(r"<.*?>", "", verse_data.get("content", "Texto não disponível")).strip()
                content = re.sub(r"^\d+\s*", "", content)
                formatted_verses.append(content)
                references.append(verse_data.get("reference", "Referência desconhecida"))

            chapter_reference = f"{random_chapter['reference']}:{references[0].split(':')[-1]}-{references[1].split(':')[-1]}"
            return f"**{chapter_reference.upper()}**\n" + "\n".join(formatted_verses)

        except Exception as e:
            return f"❌ Erro ao buscar versículo: {e}"

async def setup(bot):
    bot.add_view(PersistentView()) # Adiciona a view persistente
    await bot.add_cog(Utilitarios(bot))
