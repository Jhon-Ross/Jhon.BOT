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
