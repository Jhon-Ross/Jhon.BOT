import sqlite3
import os

DB_NAME = "economy.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabela de usuários
    # user_id: ID do Discord
    # pulerins: Moeda principal (dinheiro)
    # chips: Fichas para o cassino
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    pulerins INTEGER DEFAULT 0,
                    chips INTEGER DEFAULT 0
                )''')
    
    # Tabela de Avisos (Warnings)
    c.execute('''CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    staff_id INTEGER,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')

    # Tabela de Logs de Moderação
    c.execute('''CREATE TABLE IF NOT EXISTS mod_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT, -- 'warn', 'ban', 'kick', 'timeout'
                    staff_id INTEGER,
                    target_id INTEGER,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')

    # Tabela de Tickets
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
                    channel_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    ticket_type TEXT,
                    status TEXT DEFAULT 'open',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME
                )''')

    # Tabela de Mensagens dos Tickets
    c.execute('''CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    author_id INTEGER,
                    author_name TEXT,
                    content TEXT,
                    attachment_url TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(channel_id) REFERENCES tickets(channel_id)
                )''')
                
    conn.commit()
    conn.close()

def get_top_users(limit=10, order_by="pulerins"):
    """Retorna os top usuários ordenados por pulerins ou chips."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if order_by not in ["pulerins", "chips"]:
        order_by = "pulerins"
        
    query = f"SELECT user_id, pulerins, chips FROM users ORDER BY {order_by} DESC LIMIT ?"
    c.execute(query, (limit,))
    users = c.fetchall()
    conn.close()
    return users

def get_user(user_id):
    """Retorna os dados do usuário (user_id, pulerins, chips) ou None se não existir."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, initial_pulerins=1000):
    """Cria um novo usuário com o saldo inicial."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, pulerins, chips) VALUES (?, ?, ?)", (user_id, initial_pulerins, 0))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Usuário já existe
    conn.close()

def ensure_user(user_id):
    """Garante que o usuário existe no banco. Se não, cria."""
    if get_user(user_id) is None:
        create_user(user_id)

def update_pulerins(user_id, amount):
    """Adiciona (valor positivo) ou remove (valor negativo) Pulerins."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET pulerins = pulerins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_chips(user_id, amount):
    """Adiciona (valor positivo) ou remove (valor negativo) Fichas."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET chips = chips + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE MODERAÇÃO ---

def add_warning(user_id, staff_id, reason):
    """Adiciona um aviso ao usuário e retorna o total de avisos ativos."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO warnings (user_id, staff_id, reason) VALUES (?, ?, ?)", (user_id, staff_id, reason))
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.commit()
    conn.close()
    return count

def get_warnings_count(user_id):
    """Retorna o total de avisos de um usuário."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def log_mod_action(action_type, staff_id, target_id, reason):
    """Registra uma ação administrativa no log."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO mod_logs (action_type, staff_id, target_id, reason) VALUES (?, ?, ?, ?)", 
              (action_type, staff_id, target_id, reason))
    conn.commit()
    conn.close()

def get_staff_daily_actions(staff_id):
    """Retorna o número de ações realizadas por um staff hoje."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM mod_logs WHERE staff_id = ? AND date(timestamp) = date('now')", (staff_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def clear_warnings(user_id):
    """Remove todos os avisos de um usuário."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE TICKETS ---

def create_ticket(channel_id, user_id, ticket_type):
    """Registra um novo ticket no banco de dados."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO tickets (channel_id, user_id, ticket_type) VALUES (?, ?, ?)", 
              (channel_id, user_id, ticket_type))
    conn.commit()
    conn.close()

def close_ticket(channel_id):
    """Marca o ticket como fechado e define a data de fechamento."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

def is_ticket_open(channel_id):
    """Verifica se o canal é um ticket aberto."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM tickets WHERE channel_id = ? AND status = 'open'", (channel_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_ticket_message(channel_id, author_id, author_name, content, attachment_url=None):
    """Registra uma mensagem enviada dentro de um ticket."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO ticket_messages (channel_id, author_id, author_name, content, attachment_url) 
                 VALUES (?, ?, ?, ?, ?)''', (channel_id, author_id, author_name, content, attachment_url))
    conn.commit()
    conn.close()

def get_ticket_messages(channel_id):
    """Retorna todas as mensagens de um ticket ordenadas por data."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT author_name, content, timestamp, attachment_url FROM ticket_messages WHERE channel_id = ? ORDER BY id ASC", (channel_id,))
    messages = c.fetchall()
    conn.close()
    return messages

def get_user_tickets(user_id):
    """Retorna o histórico de tickets de um usuário."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT channel_id, ticket_type, status, created_at, closed_at FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    tickets = c.fetchall()
    conn.close()
    return tickets
