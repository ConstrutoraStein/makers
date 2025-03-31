-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'user')) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Salas
CREATE TABLE IF NOT EXISTS salas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    capacidade INTEGER NOT NULL,
    localizacao TEXT,
    recursos TEXT,
    status TEXT CHECK(status IN ('disponivel', 'manutencao')) DEFAULT 'disponivel'
);

-- Tabela de Reservas
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sala_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fim TEXT NOT NULL,
    descricao TEXT,
    status TEXT CHECK(status IN ('confirmada', 'pendente', 'cancelada')) DEFAULT 'confirmada',
    google_event_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabela de Participantes das Reservas
CREATE TABLE IF NOT EXISTS participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id INTEGER NOT NULL,
    email TEXT NOT NULL,
    nome TEXT,
    status TEXT CHECK(status IN ('pendente', 'confirmado', 'recusado')) DEFAULT 'pendente',
    notificado BOOLEAN DEFAULT 0,
    FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE CASCADE
);

-- Inserir alguns usuários de exemplo
INSERT INTO users (nome, username, email, password, role) VALUES
('Administrador', 'admin', 'admin@example.com', 'admin123', 'admin'),
('Usuário Teste', 'user', 'user@example.com', 'user123', 'user');

-- Inserir algumas salas de exemplo
INSERT INTO salas (nome, capacidade, localizacao, recursos) VALUES
('Sala de Reuniões 1', 8, 'Térreo', 'Projetor, Quadro Branco, Videoconferência'),
('Sala de Conferência', 20, '2º Andar', 'Projetor, Sistema de Som, Videoconferência'),
('Sala Executiva', 4, '3º Andar', 'Videoconferência, TV, Café'),
('Auditório', 50, 'Térreo', 'Projetor, Sistema de Som, Microfones'); 