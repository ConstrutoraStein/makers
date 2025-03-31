-- Criação do Banco de Dados
CREATE DATABASE IF NOT EXISTS reserva_salas;
USE reserva_salas;

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Salas
CREATE TABLE IF NOT EXISTS salas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    capacidade INT NOT NULL,
    localizacao VARCHAR(100),
    recursos TEXT,
    status ENUM('disponivel', 'manutencao') DEFAULT 'disponivel'
);

-- Tabela de Reservas
CREATE TABLE IF NOT EXISTS reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sala_id INT NOT NULL,
    user_id INT NOT NULL,
    data DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    descricao TEXT,
    status ENUM('confirmada', 'pendente', 'cancelada') DEFAULT 'confirmada',
    google_event_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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