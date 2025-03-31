import sqlite3
import os

DB_PATH = 'reserva_salas.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_and_create_salas():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se tabela salas existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salas'")
    if not cursor.fetchone():
        print("Tabela 'salas' não encontrada. Criando...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS salas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                capacidade INTEGER NOT NULL,
                localizacao TEXT,
                recursos TEXT,
                status TEXT CHECK(status IN ('disponivel', 'manutencao')) DEFAULT 'disponivel'
            )
        ''')
    
    # Verificar se já existem salas
    cursor.execute("SELECT COUNT(*) FROM salas")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Nenhuma sala encontrada. Criando salas de exemplo...")
        # Inserir salas de exemplo
        salas = [
            ('Sala de Reuniões 1', 8, 'Térreo', 'Projetor, Quadro Branco, Videoconferência'),
            ('Sala de Conferência', 20, '2º Andar', 'Projetor, Sistema de Som, Videoconferência'),
            ('Sala Executiva', 4, '3º Andar', 'Videoconferência, TV, Café'),
            ('Auditório', 50, 'Térreo', 'Projetor, Sistema de Som, Microfones')
        ]
        
        cursor.executemany('''
            INSERT INTO salas (nome, capacidade, localizacao, recursos)
            VALUES (?, ?, ?, ?)
        ''', salas)
        
        conn.commit()
        print(f"Criadas {len(salas)} salas.")
    else:
        print(f"Encontradas {count} salas no banco de dados.")
        cursor.execute("SELECT * FROM salas")
        salas = cursor.fetchall()
        for sala in salas:
            print(f"ID: {sala['id']}, Nome: {sala['nome']}, Capacidade: {sala['capacidade']}")
    
    conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados '{DB_PATH}' não encontrado.")
    else:
        print(f"Verificando banco de dados '{DB_PATH}'...")
        check_and_create_salas() 