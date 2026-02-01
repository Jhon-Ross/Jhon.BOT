import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import database
import os

# Definição das cartas e valores
SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

class Deck:
    def __init__(self, num_decks=4):
        self.num_decks = num_decks
        self.cards = []
        self.fill_deck()

    def fill_deck(self):
        self.cards = [(rank, suit) for suit in SUITS for rank in RANKS] * self.num_decks
        random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            return None
        return self.cards.pop()

    def remaining(self):
        return len(self.cards)

def calculate_score(hand):
    score = 0
    aces = 0
    for rank, _ in hand:
        score += VALUES[rank]
        if rank == 'A':
            aces += 1
    
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def is_blackjack(hand):
    return len(hand) == 2 and calculate_score(hand) == 21

def format_hand(hand, hide_second=False):
    if hide_second:
        return f"`{hand[0][0]}{hand[0][1]}` `??`"
    return " ".join([f"`{r}{s}`" for r, s in hand])

class IntervalView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=10) # 10 segundos de intervalo
        self.game = game
        self.message = None

    @discord.ui.button(label="Sair da Mesa", style=discord.ButtonStyle.danger, emoji="🚪")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.game.players:
            self.game.players.remove(interaction.user)
            await interaction.response.send_message(f"👋 {interaction.user.mention} saiu da mesa!", ephemeral=False)
            if not self.game.players:
                self.stop()
                if self.message:
                    try:
                        await self.message.edit(view=None)
                    except:
                        pass
                await self.game.channel.send("🚫 Mesa encerrada pois todos os jogadores saíram.")
        else:
             await interaction.response.send_message("Você não está nessa mesa.", ephemeral=True)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None) # Remove o botão
            except:
                pass
        
        if self.game.players:
            await self.game.start_new_round()
        else:
            await self.game.channel.send("🚫 Mesa fechada por falta de jogadores.")

class NextTurnView(discord.ui.View):
    def __init__(self, game, player):
        super().__init__(timeout=60)
        self.game = game
        self.player = player
        self.responded = False
        self.message = None

    @discord.ui.button(label="Próximo Jogador", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def next_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("Aguarde o jogador da vez confirmar.", ephemeral=True)
            return
        
        self.responded = True
        await interaction.response.defer()
        try:
            await self.message.edit(view=None)
        except:
            pass
        self.stop()
        await self.game.advance_turn()

    async def on_timeout(self):
        if not self.responded:
            if self.message:
                try:
                    await self.message.edit(view=None)
                except:
                    pass
            await self.game.channel.send(f"⏩ {self.player.mention} demorou muito. Avançando...")
            await self.game.advance_turn()

class BettingModal(discord.ui.Modal, title="Faça sua Aposta"):
    def __init__(self, game, view):
        super().__init__()
        self.game = game
        self.view = view
        self.amount = discord.ui.TextInput(
            label="Quantidade de Fichas",
            placeholder=f"Mínimo: {game.min_bet}",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message("❌ Digite um número válido.", ephemeral=True)
            return

        if bet < self.game.min_bet:
            await interaction.response.send_message(f"❌ Aposta mínima é {self.game.min_bet}.", ephemeral=True)
            return

        database.ensure_user(interaction.user.id)
        user_data = database.get_user(interaction.user.id)
        if user_data[2] < bet:
             await interaction.response.send_message(f"❌ Você não tem fichas suficientes! Saldo: {user_data[2]}", ephemeral=True)
             return

        self.game.bets[interaction.user.id] = bet
        await interaction.response.send_message(f"✅ Aposta de **{bet}** confirmada!", ephemeral=True)

        # Se todos apostaram, encerra a fase de apostas
        if len(self.game.bets) >= len(self.game.players):
            self.view.stop()

class BettingView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=10)
        self.game = game
    
    @discord.ui.button(label="Apostar", style=discord.ButtonStyle.green, emoji="💰")
    async def place_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.game.players:
             await interaction.response.send_message("Você não está na mesa.", ephemeral=True)
             return
        
        if interaction.user.id in self.game.bets:
            await interaction.response.send_message(f"Você já apostou {self.game.bets[interaction.user.id]}!", ephemeral=True)
            return

        await interaction.response.send_modal(BettingModal(self.game, self))

class BlackjackGame:
    def __init__(self, bot, channel, required_players, min_bet=10):
        self.bot = bot
        self.channel = channel
        self.required_players = required_players
        self.min_bet = min_bet
        self.players = [] # List of member objects
        self.bets = {} # Map player_id -> bet_amount
        self.hands = {}
        self.deck = Deck(num_decks=4) # 4 Baralhos (Shoe)
        self.active = True
        self.current_player_index = 0

    async def ensure_deck(self):
        # Se restarem menos de 20 cartas (aprox 1 rodada cheia), reembaralhar
        if self.deck.remaining() < 20:
            await self.channel.send("🔂 **O baralho (Shoe) está no fim! Embaralhando as cartas novamente...**")
            await asyncio.sleep(2)
            self.deck.fill_deck()
            await self.channel.send("✅ **Baralho renovado!**")

    async def ask_bets(self):
        view = BettingView(self)
        embed = discord.Embed(
            title="💰 Hora das Apostas!",
            description=f"Todos os jogadores devem definir suas apostas.\nMínimo: **{self.min_bet}** fichas.\nTempo: 10 segundos.",
            color=discord.Color.gold()
        )
        msg = await self.channel.send(embed=embed, view=view)
        
        # Wait for betting view timeout (handled by view timeout) or manually wait
        await view.wait()
        
        # Auto-bet logic for those who didn't bet
        bets_summary = "Apostas Confirmadas:\n"
        active_players = []
        
        for player in self.players:
            bet = self.bets.get(player.id)
            if not bet:
                # Try auto-bet min
                database.ensure_user(player.id)
                user_data = database.get_user(player.id)
                if user_data[2] >= self.min_bet:
                    self.bets[player.id] = self.min_bet
                    bet = self.min_bet
                    bets_summary += f"🔹 {player.mention}: {bet} (Automático)\n"
                else:
                    bets_summary += f"❌ {player.mention}: Removido (Sem aposta/fichas)\n"
                    continue
            else:
                bets_summary += f"🔸 {player.mention}: {bet}\n"
            
            active_players.append(player)
            
        self.players = active_players
        await self.channel.send(embed=discord.Embed(description=bets_summary, color=discord.Color.blue()))
        
        if not self.players:
            await self.channel.send("💸 Ninguém apostou. Mesa encerrada.")
            return False
            
        return True

    async def start(self):
        # Verificar saldos e descontar apostas antes de começar a rodada
        active_players = []
        for player in self.players:
            bet = self.bets.get(player.id, self.min_bet)
            
            # Re-verify balance just in case
            database.ensure_user(player.id)
            user_data = database.get_user(player.id)
            chips = user_data[2]
            
            if chips >= bet:
                database.update_chips(player.id, -bet)
                active_players.append(player)
            else:
                await self.channel.send(f"🚫 {player.mention} não tem fichas suficientes para a aposta de {bet} e foi removido.")
        
        self.players = active_players
        if not self.players:
            await self.channel.send("💸 Sem jogadores com fichas suficientes. Mesa encerrada.")
            return

        # Verificar baralho antes de começar
        await self.ensure_deck()

        # Deal initial cards
        self.dealer_hand = [self.deck.draw(), self.deck.draw()]
        self.hands = {} # Resetar mãos
        for player in self.players:
            self.hands[player.id] = [self.deck.draw(), self.deck.draw()]
        
        self.current_player_index = 0 # Reiniciar índice
        await self.next_turn()

    async def start_new_round(self):
        await self.channel.send("🔄 **Iniciando nova rodada...**")
        await asyncio.sleep(1)
        # Limpar apostas da rodada anterior para pedir novas
        self.bets = {}
        if await self.ask_bets():
            await self.start()

    async def advance_turn(self):
        self.current_player_index += 1
        await self.next_turn()

    async def next_turn(self):
        # Se os jogadores saírem no meio da rodada, precisamos verificar
        if not self.players:
             await self.channel.send("🚫 Todos saíram. Mesa fechada.")
             return

        if self.current_player_index >= len(self.players):
            await self.dealer_turn()
            return

        current_player = self.players[self.current_player_index]
        hand = self.hands.get(current_player.id)
        
        # Se por algum motivo o jogador não tiver mão (bug de saída), pular
        if not hand:
             await self.advance_turn()
             return

        score = calculate_score(hand)

        # Check for instant Blackjack
        if score == 21:
            embed = discord.Embed(title="🃏 Blackjack!", description=f"🎉 {current_player.mention} conseguiu 21 logo de cara!", color=discord.Color.gold())
            view = NextTurnView(self, current_player)
            msg = await self.channel.send(content=current_player.mention, embed=embed, view=view)
            view.message = msg
            return

        view = GameView(self, current_player)
        embed = discord.Embed(title="🃏 Blackjack - Sua Vez!", color=discord.Color.gold())
        embed.description = f"Vez de {current_player.mention}\n\n**Sua Mão:** {format_hand(hand)} (Total: **{score}**)\n**Dealer:** {format_hand(self.dealer_hand, hide_second=True)}"
        
        self.message = await self.channel.send(content=current_player.mention, embed=embed, view=view)

    async def hit(self, interaction):
        try:
            player = interaction.user
            hand = self.hands[player.id]
            card = self.deck.draw()
            
            if not card:
                 await interaction.response.send_message("❌ O baralho acabou inesperadamente! Reembaralhando...", ephemeral=True)
                 self.deck.fill_deck()
                 card = self.deck.draw()

            hand.append(card)
            score = calculate_score(hand)

            if score > 21:
                view = NextTurnView(self, player)
                await interaction.response.edit_message(content=f"💥 **Estourou!** {player.mention} tirou `{card[0]}{card[1]}` e foi para **{score}**.", view=view, embed=None)
                view.message = interaction.message
            elif score == 21:
                view = NextTurnView(self, player)
                await interaction.response.edit_message(content=f"🎉 **21!** {player.mention} atingiu o máximo! Aguardando o resultado final...", view=view, embed=None)
                view.message = interaction.message
            else:
                # Update message AND reset view timeout by creating a new one
                view = GameView(self, player)
                embed = discord.Embed(title="🃏 Blackjack - Sua Vez!", color=discord.Color.gold())
                embed.description = f"Vez de {player.mention}\n\n**Sua Mão:** {format_hand(hand)} (Total: **{score}**)\n**Dealer:** {format_hand(self.dealer_hand, hide_second=True)}"
                await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Erro no hit: {e}")
            await interaction.followup.send(f"Ocorreu um erro: {e}", ephemeral=True)

    async def stand(self, interaction):
        try:
            player = interaction.user
            score = calculate_score(self.hands[player.id])
            view = NextTurnView(self, player)
            await interaction.response.edit_message(content=f"🛑 {player.mention} parou com **{score}**.", view=view, embed=None)
            view.message = interaction.message
        except Exception as e:
            print(f"Erro no stand: {e}")

    async def dealer_turn(self):
        embed = discord.Embed(title="🃏 Turno do Dealer", color=discord.Color.red())
        message = await self.channel.send(embed=embed)
        
        dealer_score = calculate_score(self.dealer_hand)
        embed.description = f"**Mão do Dealer:** {format_hand(self.dealer_hand)} (Total: **{dealer_score}**)"
        await message.edit(embed=embed)
        await asyncio.sleep(1)

        while dealer_score < 17:
            card = self.deck.draw()
            if not card:
                 await self.channel.send("🔂 **O baralho acabou durante a vez do Dealer! Reembaralhando...**")
                 self.deck.fill_deck()
                 card = self.deck.draw()

            self.dealer_hand.append(card)
            dealer_score = calculate_score(self.dealer_hand)
            embed.description += f"\nDealer puxou `{card[0]}{card[1]}`... Total: **{dealer_score}**"
            await message.edit(embed=embed)
            await asyncio.sleep(1)

        # Final Results
        results = "**RESULTADO FINAL DA RODADA:**\n\n"
        results += f"🤵 **Dealer:** {dealer_score} "
        if dealer_score > 21:
            results += "(ESTOUROU 💥)\n"
        else:
            results += "\n"
        
        results += "-----------------------------------\n"

        for player in self.players:
            p_hand = self.hands[player.id]
            p_score = calculate_score(p_hand)
            p_bj = is_blackjack(p_hand)
            d_bj = is_blackjack(self.dealer_hand)
            bet = self.bets.get(player.id, 0)

            status = ""
            payout = 0

            if p_score > 21:
                status = "💥 ESTOUROU (Derrota)"
                payout = 0
            elif d_bj and not p_bj:
                status = "❌ PERDEU (Dealer Blackjack)"
                payout = 0
            elif p_bj and not d_bj:
                status = "🏆 VENCEU (Blackjack!)"
                payout = int(bet * 2.5) # 2.5x
            elif dealer_score > 21:
                status = "🏆 VENCEU!"
                payout = bet * 2
            elif p_score > dealer_score:
                status = "🏆 VENCEU!"
                payout = bet * 2
            elif p_score == dealer_score:
                status = "🤝 EMPATE"
                payout = bet
            else:
                status = "❌ PERDEU"
                payout = 0
            
            if payout > 0:
                database.update_chips(player.id, payout)
                status += f" (+{payout} 🎰)"
            else:
                status += f" (-{bet} 🎰)"

            results += f"👤 {player.mention}: **{p_score}** - {status}\n"

        final_embed = discord.Embed(title="🃏 Fim de Rodada", description=results, color=discord.Color.green())
        await self.channel.send(embed=final_embed)
        
        # Iniciar intervalo
        await self.start_interval()

    async def start_interval(self):
        view = IntervalView(self)
        embed = discord.Embed(
            title="⏳ Intervalo - Próxima Rodada em 10s", 
            description="Quem quiser sair da mesa, clique no botão abaixo agora!",
            color=discord.Color.blue()
        )
        msg = await self.channel.send(embed=embed, view=view)
        view.message = msg # Guardar referência para editar depois

class GameView(discord.ui.View):
    def __init__(self, game, current_player):
        super().__init__(timeout=60)
        self.game = game
        self.current_player = current_player

    @discord.ui.button(label="Pedir Carta (Hit)", style=discord.ButtonStyle.success, emoji="🃏")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("Não é sua vez!", ephemeral=True)
            return
        await self.game.hit(interaction)

    @discord.ui.button(label="Parar (Stand)", style=discord.ButtonStyle.danger, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("Não é sua vez!", ephemeral=True)
            return
        await self.game.stand(interaction)

class JoinView(discord.ui.View):
    def __init__(self, game, max_players):
        super().__init__(timeout=10)
        self.game = game
        self.max_players = max_players

    @discord.ui.button(label="Sentar à Mesa", style=discord.ButtonStyle.primary, emoji="🪑")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.game.players:
            await interaction.response.send_message("Você já está na mesa!", ephemeral=True)
            return
        
        # Verificar se tem fichas
        database.ensure_user(interaction.user.id)
        user_data = database.get_user(interaction.user.id)
        if user_data[2] < self.game.min_bet:
             await interaction.response.send_message(f"❌ Você não tem fichas suficientes! Precisa de {self.game.min_bet} 🎰.", ephemeral=True)
             return

        self.game.players.append(interaction.user)
        await interaction.response.send_message(f"{interaction.user.mention} sentou à mesa!", ephemeral=False)
        
        if len(self.game.players) >= self.max_players:
            self.stop()

class Blackjack21(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackjack", description="Inicia uma partida de Blackjack (21).")
    async def blackjack(self, interaction: discord.Interaction):
        blackjack_channel_id = os.getenv("BLACKJACK_CHANNEL_ID")
        if blackjack_channel_id and str(interaction.channel.id) != str(blackjack_channel_id):
             await interaction.response.send_message(f"❌ Este comando só pode ser usado no canal <#{blackjack_channel_id}>.", ephemeral=True)
             return

        max_jogadores = 7
        aposta_minima = 10
        
        game = BlackjackGame(self.bot, interaction.channel, max_jogadores, min_bet=aposta_minima)
        view = JoinView(game, max_jogadores)

        embed = discord.Embed(
            title="🃏 Mesa de Blackjack Aberta!",
            description=f"Clique no botão abaixo para sentar à mesa.\nLimite: **{max_jogadores}** jogadores.\nAposta Mínima: **{aposta_minima} 🎰**\n⏳ **A partida começará em 10 segundos!**",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        
        await view.wait()
        
        if len(game.players) == 0:
            await interaction.followup.send("⏰ Ninguém apareceu para jogar. Mesa fechada.")
        else:
             await interaction.followup.send("⏰ Tempo de espera acabou! Iniciando fase de apostas...")
             if await game.ask_bets():
                 await game.start()

async def setup(bot):
    await bot.add_cog(Blackjack21(bot))
