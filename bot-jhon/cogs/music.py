import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os

# Configurações do YT-DLP e FFMPEG
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        }
    }
}

# Usa cookies do navegador, se o arquivo existir (ajuda em erros de "Sign in to confirm")
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cookies_path = os.path.join(base_path, "cookies.txt")
if os.path.exists(cookies_path):
    ytdl_format_options["cookiefile"] = cookies_path

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

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
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queues = {} # Guild ID -> List of URLs
        self.current_song = {} # Guild ID -> Title

    def get_queue(self, guild_id):
        if guild_id not in self.music_queues:
            self.music_queues[guild_id] = []
        return self.music_queues[guild_id]

    async def play_next_song(self, guild_id, channel):
        queue = self.get_queue(guild_id)
        if len(queue) > 0:
            next_url = queue.pop(0)
            
            guild = self.bot.get_guild(guild_id)
            if not guild or not guild.voice_client:
                return

            try:
                # Nota: from_url precisa do loop
                player = await YTDLSource.from_url(next_url, loop=self.bot.loop, stream=True)
                self.current_song[guild_id] = player.title
                
                # Callback recursivo
                def after_playing(error):
                    if error:
                        print(f"Erro no player: {error}")
                    coro = self.play_next_song(guild_id, channel)
                    fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                    try:
                        fut.result()
                    except:
                        pass

                guild.voice_client.play(player, after=after_playing)
                await channel.send(f"🎵 Tocando agora: **{player.title}**")
            
            except Exception as e:
                await channel.send(f"Erro ao tocar música: {e}")
                # Tenta a próxima se der erro
                await self.play_next_song(guild_id, channel)
        else:
            if guild_id in self.current_song:
                del self.current_song[guild_id]

    @app_commands.command(name="musica", description="Toca uma música do YouTube.")
    @app_commands.describe(link="Link ou nome da música")
    async def musica(self, interaction: discord.Interaction, link: str):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz.", ephemeral=True)
            return

        # Garante que não foi respondido antes de deferir
        if not interaction.response.is_done():
            await interaction.response.defer() # YouTube pode demorar

        voice_channel = interaction.user.voice.channel
        
        try:
            if not interaction.guild.voice_client:
                vc = await voice_channel.connect(timeout=60.0, reconnect=True)
            else:
                vc = interaction.guild.voice_client

            if vc.is_playing() or vc.is_paused():
                queue = self.get_queue(interaction.guild_id)
                queue.append(link)
                await interaction.followup.send(f"📝 Música adicionada à fila! (Posição: {len(queue)})")
            else:
                player = await YTDLSource.from_url(link, loop=self.bot.loop, stream=True)
                self.current_song[interaction.guild_id] = player.title
                
                def after_playing(error):
                    if error: print(f"Erro: {error}")
                    coro = self.play_next_song(interaction.guild_id, interaction.channel)
                    asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

                vc.play(player, after=after_playing)
                await interaction.followup.send(f"🎵 Tocando agora: **{player.title}**")

        except Exception as e:
            await interaction.followup.send(f"Erro ao tentar tocar música: {e}")

    @app_commands.command(name="pular", description="Pula a música atual.")
    async def pular(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop() # Dispara o after -> play_next_song
            await interaction.response.send_message("⏭️ Música pulada!")
        else:
            await interaction.response.send_message("❌ Não há música tocando.", ephemeral=True)

    @app_commands.command(name="fila", description="Mostra a fila de músicas.")
    async def fila(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if len(queue) == 0:
            await interaction.response.send_message("📭 A fila está vazia.")
        else:
            lista = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queue[:10])])
            if len(queue) > 10:
                lista += f"\n... e mais {len(queue)-10} músicas."
            
            embed = discord.Embed(
                title="🎶 Fila de Reprodução",
                description=lista,
                color=discord.Color.purple()
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tocando", description="Mostra a música atual.")
    async def tocando(self, interaction: discord.Interaction):
        title = self.current_song.get(interaction.guild_id)
        if title:
            await interaction.response.send_message(f"🎵 **Tocando agora:** {title}")
        else:
            await interaction.response.send_message("❌ Nenhuma música tocando no momento.")

    @app_commands.command(name="pausar", description="Pausa a música.")
    async def pausar(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Música pausada.")
        else:
            await interaction.response.send_message("❌ Não estou tocando nada.", ephemeral=True)

    @app_commands.command(name="continuar", description="Retoma a música.")
    async def continuar(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Música retomada.")
        else:
            await interaction.response.send_message("❌ A música não está pausada.", ephemeral=True)

    @app_commands.command(name="parar", description="Para a música e desconecta.")
    async def parar(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            # Limpa a fila e a música atual
            if interaction.guild_id in self.music_queues:
                self.music_queues[interaction.guild_id] = []
            if interaction.guild_id in self.current_song:
                del self.current_song[interaction.guild_id]
            
            await vc.disconnect()
            await interaction.response.send_message("🛑 Música parada e desconectado.")
        else:
            await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Musica(bot))
