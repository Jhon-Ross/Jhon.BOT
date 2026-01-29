import os
import sys
import discord
import subprocess
import logging
import requests
import re
import random
import qrcode
import asyncio
import yt_dlp
from io import BytesIO
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

# ==========================
# SEÇÃO: CONFIGURAÇÃO GERAL
# ==========================
# Carregar variáveis de ambiente
load_dotenv()

def get_env_int(var_name):
    value = os.getenv(var_name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"[ERRO] A variavel de ambiente '{var_name}' deve ser um numero inteiro. Valor atual: '{value}'")
        return None

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BIBLE_ID = os.getenv("BIBLE_ID")
API_KEY = os.getenv("API_KEY")

# Variaveis obrigatorias (IDs)
COMUNIDADE_ID = get_env_int("COMUNIDADE_ID")
CANAL_LOG_ID = get_env_int("CANAL_LOG_ID")
VISITANTE_ID = get_env_int("VISITANTE_ID")
WELCOME_CHANNEL_ID = get_env_int("WELCOME_CHANNEL_ID")
RULES_CHANNEL_ID = get_env_int("RULES_CHANNEL_ID")
VERIFICAR_ID = get_env_int("VERIFICAR_ID")
GUILD_ID = get_env_int("GUILD_ID")
BOAS_VINDAS_ID = get_env_int("BOAS_VINDAS_ID")

# Verifica se variaveis criticas estao faltando
missing_vars = []
if not DISCORD_TOKEN: missing_vars.append("DISCORD_TOKEN")
if not COMUNIDADE_ID: missing_vars.append("COMUNIDADE_ID")
if not GUILD_ID: missing_vars.append("GUILD_ID")

if missing_vars:
    print("\n" + "="*50)
    print(" [ERRO DE CONFIGURACAO] ")
    print(" As seguintes variaveis estao faltando ou invalidas no arquivo .env:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\n Por favor, edite o arquivo .env na pasta 'bot-jhon' e adicione os valores.")
    print("="*50 + "\n")
    # Nao sai imediatamente para permitir que funcoes auxiliares rodem, mas o bot nao vai iniciar o run()

# Configuração do bot e intents necessários
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix=".", intents=intents)

# Atualiza pacotes a partir do arquivo requirements.txt (se existir)
def update_requirements():
    requirements_file = "requirements.txt"  # Exemplo de nome de arquivo
    if os.path.exists(requirements_file):
        # Lógica para atualizar os requisitos
        print("Arquivo requirements.txt encontrado!")
    else:
        print("Arquivo requirements.txt não encontrado!")


update_requirements()

# ==========================
# SEÇÃO: VERIFICAÇÃO DE MEMBROS
# ==========================
# View persistente com o botão de verificação de membros
class PersistentView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            Button(
                label="Iniciar verificação",
                style=discord.ButtonStyle.green,
                emoji="✅",
                custom_id="verificacao_botao"
            )
        )

# Evento chamado sempre que existe uma interação (ex.: clique em botão)
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data.get("custom_id") == "verificacao_botao":
        await handle_verification(interaction)

# ==========================
# SEÇÃO: MÚSICA / YOUTUBE
# ==========================
# Configurações do yt_dlp para baixar/streamar áudio do YouTube
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
ffmpeg_options = {
    'options': '-vn',
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


# Fonte de áudio que integra yt_dlp com o FFmpeg para tocar música
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:  # Playlist ou lista de vídeos
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@bot.command(name='musica')
# Comando .musica: toca áudio de um link do YouTube no canal de voz do autor
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando.")
        return

    voice_channel = ctx.author.voice.channel

    try:
        if not ctx.voice_client:
            vc = await voice_channel.connect(timeout=60.0, reconnect=True)
        else:
            vc = ctx.voice_client

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            vc.play(player, after=lambda e: print(
                f'Erro ao tocar: {e}') if e else None)
            await ctx.send(f"Tocando agora: **{player.title}**")
    except asyncio.TimeoutError:
        await ctx.send("Não foi possível conectar ao canal de voz. Verifique a conexão do bot ou tente novamente.")
    except discord.ClientException as e:
        await ctx.send(f"Ocorreu um erro ao tentar conectar: {e}")
    except Exception as e:
        await ctx.send("Erro inesperado ao tentar tocar música.")
        print(f"Erro: {e}")

# Lógica principal do botão de verificação: troca cargo de visitante para comunidade
async def handle_verification(interaction):
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

# Comando para iniciar o sistema de verificação


@bot.command()
# Comando .verificar: envia embed com o botão de verificação persistente
async def verificar(ctx):
    embed = discord.Embed(
        title="🚀 Bem-vindo ao nosso servidor!",
        description=(
            "Para nossa segurança 🔒, mostre que você não é um robô assim como eu 🤭! "
            "Clique no botão abaixo para se verificar.✅"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Esperamos que se divirta muito por aqui. 😊")
    embed.set_image(url="https://media.discordapp.net/attachments/1310617769326153738/1310617942207238224/discord.png?ex=67488293&is=67473113&hm=40ca91c5481bf1dd211c57cdef551335a3b60a15085269cb04bc5376d2e23ee1&=&format=webp&quality=lossless")

    await ctx.send(embed=embed, view=PersistentView())

# ==========================
# SEÇÃO: LOGGING E CONTAGEM DE MEMBROS
# ==========================
# Configuração do logging para exibir mensagens no console
logging.basicConfig(level=logging.INFO)


# Converte um número em uma sequência de emojis numéricos (0️⃣ a 9️⃣)
def get_emoji_for_number(number):
    emojis = {
        0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"
    }
    return "".join([emojis[int(digit)] for digit in str(number)])

# Atualiza o tópico do canal de boas-vindas com a contagem atual de membros
async def update_channel_member_count():
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(BOAS_VINDAS_ID)

    member_count = guild.member_count
    new_topic = f"Já contabilizamos {get_emoji_for_number(member_count)} membros nesse servidor muito louco."

    try:
        await channel.edit(topic=new_topic)
        logging.info(f"Contagem de membros atualizada para {member_count}")
    except Exception as e:
        logging.error(f"Erro ao tentar atualizar o 'topic' do canal: {e}")


# Envia mensagens de log para o canal de eventos configurado (CANAL_LOG_ID)
async def send_log_message(content=None, embed=None):
    channel = bot.get_channel(CANAL_LOG_ID)
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

# ==========================
# SEÇÃO: EVENTOS DE MEMBROS / LOGS
# ==========================
# Evento disparado quando um novo membro entra no servidor
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        rules_channel = bot.get_channel(RULES_CHANNEL_ID)
        verificar_channel = bot.get_channel(VERIFICAR_ID)

        embed = discord.Embed(
            title="👋 Bem-vindo(a)!",
            description=(
                f"Seja bem-vindo ao meu servidor {member.mention}, espero que você se divirta muito por aqui!\n\n"
                f"Por favor, leia as regras em {rules_channel.mention},\n"
                f"Utilize o nosso sistema de verificação em {verificar_channel.mention}."
            ),
            color=discord.Color.green()
        )
        embed.set_image(
            url="https://media.discordapp.net/attachments/1310617769326153738/1310617942441852928/blitz-crank-league-of-legends.gif")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID do Usuário",
                        value=str(member.id), inline=True)
        await channel.send(embed=embed)
        logging.info(f"Mensagem de boas-vindas enviada para {member.name}.")
    else:
        logging.error(
            f"Erro: Canal com ID {WELCOME_CHANNEL_ID} não encontrado.")

    visitante_role = discord.utils.get(member.guild.roles, id=VISITANTE_ID)
    if visitante_role:
        await member.add_roles(visitante_role)
        logging.info(
            f"Novo membro {member.name} recebeu o cargo {visitante_role.name}.")
    else:
        logging.error(
            f"Erro: O cargo com o ID '{VISITANTE_ID}' não foi encontrado no servidor.")

    await update_channel_member_count()
    logging.info(f"Membro {member.name} entrou no servidor.")
    await send_log_message(
        content=f"✅ {member.mention} entrou no servidor. ID: {member.id}"
    )

# Evento disparado quando um membro sai do servidor
@bot.event
async def on_member_remove(member):
    await update_channel_member_count()
    logging.info(f"Membro {member.name} saiu do servidor.")
    await send_log_message(
        content=f"🚪 {member.mention} saiu do servidor. ID: {member.id}"
    )

# Tratamento global de erros de comandos do bot
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError) and "Unknown message" in str(error.original):
        return
    logging.error(f"Erro no comando: {error}")
    raise error


# Evento de voz: entrada, saída e troca de canal de voz
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        await send_log_message(
            content=f"🔊 {member.mention} entrou no canal de voz `{after.channel.name}`."
        )
    elif before.channel is not None and after.channel is None:
        await send_log_message(
            content=f"🔇 {member.mention} saiu do canal de voz `{before.channel.name}`."
        )
    elif before.channel != after.channel:
        await send_log_message(
            content=f"🔁 {member.mention} mudou do canal de voz `{before.channel.name}` para `{after.channel.name}`."
        )


@bot.event
# Evento disparado quando há atualização em um membro (ex.: mudança de cargos)
async def on_member_update(before, after):
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
        await send_log_message(
            content=f"🛡️ Atualização de cargos para {after.mention}:\n" + "\n".join(messages)
        )


@bot.event
# Evento disparado quando uma mensagem é apagada em qualquer canal
async def on_message_delete(message):
    if message.author.bot:
        return
    content = message.content if message.content else "[sem conteúdo de texto]"
    await send_log_message(
        content=(
            f"🗑️ Mensagem apagada em {message.channel.mention} por {message.author.mention} "
            f"(ID: {message.id}):\n{content}"
        )
    )


@bot.event
# Evento disparado quando uma mensagem é editada
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if before.content == after.content:
        return
    before_content = before.content if before.content else "[vazio]"
    after_content = after.content if after.content else "[vazio]"
    await send_log_message(
        content=(
            f"✏️ Mensagem editada em {before.channel.mention} por {before.author.mention} "
            f"(ID: {before.id}):\n"
            f"Antes: {before_content}\nDepois: {after_content}"
        )
    )


@bot.event
# Evento disparado quando uma reação é adicionada a uma mensagem
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    message = reaction.message
    await send_log_message(
        content=(
            f"➕ Reação adicionada por {user.mention} em {message.channel.mention} "
            f"na mensagem ID {message.id}: {reaction.emoji}"
        )
    )


@bot.event
# Evento disparado quando uma reação é removida de uma mensagem
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    message = reaction.message
    await send_log_message(
        content=(
            f"➖ Reação removida por {user.mention} em {message.channel.mention} "
            f"na mensagem ID {message.id}: {reaction.emoji}"
        )
    )

# ==========================
# SEÇÃO: COMANDOS ESPECIAIS (PIX / BÍBLIA)
# ==========================
# Comando .pix: gera QR Code e link Pix para doação ao canal
@bot.command()
async def pix(ctx):
    # Código Pix estático reutilizável
    pix_code = "00020126710014BR.GOV.BCB.PIX0111094014879010234Muito obrigado por ajudar o canal.5204000053039865802BR5922Jhon Ross Abdo de Lara6009SAO PAULO62140510BN6RYqd88P63043AFF"

    # Gerar o QR code com o código fornecido
    qr = qrcode.make(pix_code)

    # Salvar o QR code em um arquivo de imagem na memória
    byte_io = BytesIO()
    qr.save(byte_io, "PNG")
    byte_io.seek(0)  # Voltar para o início do arquivo

    # Link para pagamento Pix (Pix Copia e Cola)
    pix_link = f"https://nubank.com.br/cobrar/1ala9x/6745f61b-7998-41ed-9239-a0b6517b195d"

    # Criar embed com a imagem do QR code
    embed = discord.Embed(
        title="Pix QR Code",
        description="Aqui está o QR code do Pix. Escaneie para fazer uma doação ao canal!\n\n"
                    f"[Clique aqui para pagar via Pix Copia e Cola]({pix_link})",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Pix - Pagamento instantâneo")

    # Enviar o embed com a imagem do QR code
    await ctx.send(embed=embed, file=discord.File(byte_io, filename="qrcode.png"))

# Busca um trecho bíblico aleatório usando a Scripture API (2 versículos seguidos)
def get_random_verse():
    try:
        headers = {"api-key": API_KEY}

        # Buscar livros da Bíblia
        books_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/books"
        response = requests.get(books_url, headers=headers)
        response.raise_for_status()
        books = response.json().get("data", [])
        if not books:
            return "❌ Nenhum livro encontrado."

        # Selecionar um livro aleatório
        random_book = random.choice(books)

        # Buscar capítulos do livro
        chapters_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/books/{random_book['id']}/chapters"
        chapters_response = requests.get(chapters_url, headers=headers)
        chapters_response.raise_for_status()
        chapters = chapters_response.json().get("data", [])
        if not chapters:
            return f"❌ O livro '{random_book['name']}' não contém capítulos."

        # Selecionar um capítulo aleatório
        random_chapter = random.choice(chapters)

        # Buscar versículos do capítulo
        verses_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/chapters/{random_chapter['id']}/verses"
        verses_response = requests.get(verses_url, headers=headers)
        verses_response.raise_for_status()
        verses = verses_response.json().get("data", [])
        if len(verses) < 2:
            return f"❌ O capítulo '{random_chapter['reference']}' não contém versículos suficientes para retornar dois."

        # Ordenar versículos por sequência e selecionar dois consecutivos
        # Fix: Tratar referências com intervalos (ex: '20-21') pegando apenas o primeiro número
        sorted_verses = sorted(verses, key=lambda x: int(
            x["reference"].split(":")[-1].split("-")[0]))
        start_index = random.randint(0, len(sorted_verses) - 2)
        selected_verses = sorted_verses[start_index:start_index + 2]

        formatted_verses = []
        references = []
        for verse in selected_verses:
            # Buscar o conteúdo de cada versículo
            verse_url = f"https://rest.api.bible/v1/bibles/{BIBLE_ID}/verses/{verse['id']}"
            verse_response = requests.get(verse_url, headers=headers)
            verse_response.raise_for_status()
            verse_data = verse_response.json().get("data", {})

            # Extrair informações do versículo
            content = re.sub(
                r"<.*?>", "", verse_data.get("content", "Texto não disponível")).strip()
            reference = verse_data.get("reference", "Referência desconhecida")

            # Remover o número inicial do versículo, se existir
            content = re.sub(r"^\d+\s*", "", content)

            formatted_verses.append(content)
            references.append(reference)

        # Combinar as informações no formato desejado
        chapter_reference = f"{random_chapter['reference']}:{references[0].split(':')[-1]}-{references[1].split(':')[-1]}"
        formatted_content = "\n".join(formatted_verses)

        return f"**{chapter_reference.upper()}**\n{formatted_content}"

    except requests.exceptions.RequestException as e:
        # Verificar se o erro é especificamente 503
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 503:
            return "❌ A API não está disponível no momento. Tente novamente mais tarde."
        return f"❌ Erro ao buscar versículo: {e}"


# ==========================
# SEÇÃO: COMANDOS GERAIS DO BOT
# ==========================
# Comando .comandos: lista todos os comandos disponíveis do bot
@bot.command()
async def comandos(ctx):
    comandos_message = """
🌟 **Esses são os comandos para você interagir comigo:**

1️⃣ **.ola**  
   👋 *O bot responde: "Olá!" para te cumprimentar com todo carinho.*

2️⃣ **.limpar [número]**  
   🧹 *Limpa até 10 mensagens no canal escolhido.* 

3️⃣ **.palavra**  
   📖 *Receba uma palavra do Senhor para o seu dia! Uma mensagem de fé e esperança para te inspirar.*

4️⃣ **.musica [link]**
   🎵 *Toca uma música do YouTube no canal de voz em que você está conectado.*

✨ *Por enquanto esses são os comandos disponíveis, mas fique ligado... em breve teremos mais utilidades!*

📌 *Use o comando "." antes de cada comando para interagir comigo!* 

Espero que aproveite, e qualquer dúvida, é só chamar um de nossos staff's disponiveis no momento. 😉
"""
    await ctx.send(comandos_message)

# Comando .ola: retorna uma saudação personalizada para o usuário
@bot.command()
async def ola(ctx):
    usuario = ctx.author
    await ctx.reply(f"👋 Olá, {usuario.display_name}!")


@bot.command()
# Comando .palavra: envia um versículo aleatório formatado
async def palavra(ctx):
    verse = get_random_verse()
    if len(verse) > 2000:
        await ctx.send("❌ O versículo excede o limite de 2000 caracteres.")
    else:
        await ctx.send(verse)

# Comando .apresentação: envia embed com sua apresentação como desenvolvedor
@bot.command(name="apresentação")
async def apresentacao(ctx):
    # Criando o embed
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
        color=discord.Color.blue(),  # Define uma cor para o embed
    )

    # Envia o embed no canal onde o comando foi usado
    await ctx.send(embed=embed)


@bot.command()
# Comando .limpar: apaga de 1 a 100 mensagens, se o usuário tiver permissão
async def limpar(ctx, num_messages: int = 10):
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.reply("❌ Você não tem permissão para usar este comando.")
        return

    if not (1 <= num_messages <= 100):
        await ctx.reply("❌ Número de mensagens deve estar entre 1 e 100.")
        return

    deleted = await ctx.channel.purge(limit=num_messages)
    await ctx.reply(f"✅ {len(deleted)} mensagens foram excluídas.")

# ==========================
# SEÇÃO: CICLO DE VIDA DO BOT
# ==========================
# Evento disparado quando o bot entra online e está pronto para uso
@bot.event
async def on_ready():
    print(f"✔️ Bot {bot.user.name} está online!")

    for guild in bot.guilds:
        # Substitua CANAL_LOG_ID pelo ID do canal onde a mensagem será enviada
        channel = discord.utils.get(guild.text_channels, id=CANAL_LOG_ID)
        if channel:
            await channel.send("🚀 O bot foi iniciado com sucesso!")
        else:
            print(f"❌ Canal de log não encontrado no servidor: {guild.name}")

# Ponto de entrada do script: valida variáveis e inicia o bot
if __name__ == "__main__":
    if missing_vars:
        print("❌ Bot nao iniciado devido a falta de variaveis de ambiente.")
        sys.exit(1)
    
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN não definido.")
    else:
        bot.run(DISCORD_TOKEN)
