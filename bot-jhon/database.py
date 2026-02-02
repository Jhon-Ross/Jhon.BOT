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
