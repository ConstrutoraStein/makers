import sqlite3
import os

DB_PATH = 'reserva_salas.db'

def update_database():
    """Adiciona a tabela de participantes ao banco de dados existente."""
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados '{DB_PATH}' não encontrado.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar se a tabela participantes já existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='participantes'")
    if cursor.fetchone():
        print("A tabela 'participantes' já existe.")
    else:
        print("Criando tabela 'participantes'...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reserva_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                nome TEXT,
                status TEXT CHECK(status IN ('pendente', 'confirmado', 'recusado')) DEFAULT 'pendente',
                notificado BOOLEAN DEFAULT 0,
                FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("Tabela 'participantes' criada com sucesso!")
    
    conn.close()
    print("Atualização do banco de dados concluída.")

if __name__ == "__main__":
    update_database() 