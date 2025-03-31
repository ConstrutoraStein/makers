from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import sqlite3
from datetime import datetime
from functools import wraps
from authlib.integrations.flask_client import OAuth
import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Configuração secreta
app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta')

# Configuração do SQLite - usando um caminho que funciona no Render
DB_PATH = os.path.join(os.getenv('DATABASE_DIR', os.getcwd()), 'reserva_salas.db')

# Configuração OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params={
        'hd': 'cstein.com.br',  # Restringe login apenas para o domínio corporativo
    },
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.send'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
)

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Inicialização do banco de dados
def init_db():
    conn = get_db_connection()
    with open('app/database/schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Banco de dados inicializado.")

# Decorator para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Rota para página inicial - Login
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        account = cursor.fetchone()
        conn.close()
        
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['email'] = account['email']
            return redirect(url_for('dashboard'))
        else:
            msg = 'Usuário ou senha incorretos!'
    
    return render_template('login.html', msg=msg)

# Rota para login com Google
@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

# Callback para autenticação Google
@app.route('/login/google/callback')
def google_auth():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    
    # Verificar se o email pertence ao domínio cstein.com.br
    if not user_info['email'].endswith('@cstein.com.br'):
        return render_template('login.html', msg='Apenas emails do domínio cstein.com.br são permitidos')
    
    # Verificar se o usuário já existe no banco
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (user_info['email'],))
    user = cursor.fetchone()
    
    if not user:
        # Criar novo usuário
        cursor.execute(
            'INSERT INTO users (nome, username, email, password, role) VALUES (?, ?, ?, ?, ?)',
            (user_info.get('name', ''), user_info['email'].split('@')[0], user_info['email'], 'google_oauth', 'user')
        )
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE email = ?', (user_info['email'],))
        user = cursor.fetchone()
    
    # Armazenar dados básicos de todos os usuários do domínio para autocompletar/sugestões
    cursor.execute('SELECT id, nome, email FROM users WHERE email LIKE ?', ('%@cstein.com.br',))
    domain_users = cursor.fetchall()
    domain_users_list = [{'id': u['id'], 'nome': u['nome'], 'email': u['email']} for u in domain_users]
    
    conn.close()
    
    # Definir sessão
    session['loggedin'] = True
    session['id'] = user['id']
    session['username'] = user['username']
    session['email'] = user['email']
    session['nome'] = user['nome']
    session['google_token'] = token
    session['domain_users'] = domain_users_list
    
    return redirect(url_for('dashboard'))

# Rota para logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('email', None)
    session.pop('google_token', None)
    return redirect(url_for('login'))

# Rota para o painel principal
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obter total de salas disponíveis (não ocupadas no momento atual)
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')
    
    # Todas as salas
    cursor.execute('SELECT COUNT(*) as total FROM salas')
    total_salas = cursor.fetchone()['total']
    
    # Salas ocupadas agora
    cursor.execute('''
        SELECT COUNT(DISTINCT r.sala_id) as ocupadas
        FROM reservas r
        WHERE r.data = ? 
        AND r.hora_inicio <= ? 
        AND r.hora_fim > ?
        AND r.status = 'confirmada'
    ''', (hoje, hora_atual, hora_atual))
    salas_ocupadas = cursor.fetchone()['ocupadas']
    
    # Salas disponíveis
    salas_disponiveis = total_salas - salas_ocupadas
    
    # Minhas reservas (total)
    cursor.execute('''
        SELECT COUNT(*) as total
        FROM reservas
        WHERE user_id = ?
    ''', (session['id'],))
    total_minhas_reservas = cursor.fetchone()['total']
    
    # Reservas para hoje
    cursor.execute('''
        SELECT COUNT(*) as total
        FROM reservas
        WHERE data = ? AND user_id = ?
    ''', (hoje, session['id']))
    reservas_hoje = cursor.fetchone()['total']
    
    # Próximas reservas (limitado a 5)
    cursor.execute('''
        SELECT r.*, s.nome as sala_nome
        FROM reservas r
        JOIN salas s ON r.sala_id = s.id
        WHERE r.data >= ? AND r.user_id = ?
        ORDER BY r.data, r.hora_inicio
        LIMIT 5
    ''', (hoje, session['id']))
    proximas_reservas_raw = cursor.fetchall()
    
    # Converter para lista de dicionários e formatar datas
    proximas_reservas = []
    for row in proximas_reservas_raw:
        reserva = dict(row)
        if reserva['data'] and len(reserva['data'].split('-')) == 3:
            ano, mes, dia = reserva['data'].split('-')
            reserva['data_formatada'] = f"{dia}/{mes}/{ano}"
        else:
            reserva['data_formatada'] = reserva['data']
        proximas_reservas.append(reserva)
    
    conn.close()
    
    return render_template('dashboard.html', 
                          salas_disponiveis=salas_disponiveis,
                          total_minhas_reservas=total_minhas_reservas,
                          reservas_hoje=reservas_hoje,
                          proximas_reservas=proximas_reservas)

# Rota para reservar salas
@app.route('/reservar-sala', methods=['GET', 'POST'])
@login_required
def reservar_sala():
    if request.method == 'POST':
        sala_id = request.form['sala_id']
        data = request.form['data']
        hora_inicio = request.form['hora_inicio']
        hora_fim = request.form['hora_fim']
        descricao = request.form['descricao']
        user_id = session['id']
        participantes_json = request.form.get('participantes_json', '[]')
        
        try:
            participantes = json.loads(participantes_json)
        except:
            participantes = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter informações da sala
        cursor.execute('SELECT nome FROM salas WHERE id = ?', (sala_id,))
        sala = cursor.fetchone()
        
        # Inserir reserva no banco
        cursor.execute(
            'INSERT INTO reservas (sala_id, user_id, data, hora_inicio, hora_fim, descricao, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (sala_id, user_id, data, hora_inicio, hora_fim, descricao, 'confirmada')
        )
        reserva_id = cursor.lastrowid
        conn.commit()
        
        # Obter informações do usuário para o convite
        cursor.execute('SELECT nome, email FROM users WHERE id = ?', (user_id,))
        organizador = cursor.fetchone()
        
        # Adicionar participantes ao banco de dados
        if participantes:
            participantes_values = [(reserva_id, p.get('email'), p.get('nome', ''), 'pendente', 0) for p in participantes]
            cursor.executemany(
                'INSERT INTO participantes (reserva_id, email, nome, status, notificado) VALUES (?, ?, ?, ?, ?)',
                participantes_values
            )
            conn.commit()
        
        # Integração com Google Calendar
        event_id = None
        if 'google_token' in session:
            event_id = criar_evento_google_calendar(
                sala['nome'], 
                data, 
                hora_inicio, 
                hora_fim, 
                descricao, 
                organizador, 
                participantes
            )
            
            if event_id:
                cursor.execute('UPDATE reservas SET google_event_id = ? WHERE id = ?', (event_id, reserva_id))
                conn.commit()
        
        # Enviar emails para os participantes
        for participante in participantes:
            # Tentar enviar via Gmail API primeiro (se autenticado)
            if 'google_token' in session:
                # Preparar o corpo do email HTML
                data_obj = datetime.strptime(data, '%Y-%m-%d')
                data_formatada = data_obj.strftime('%d/%m/%Y')
                
                corpo_email = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ color: #3366cc; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
                        .info {{ margin: 20px 0; background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                        .info-item {{ margin: 10px 0; }}
                        .instructions {{ background-color: #e8f4fb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                        .instruction-step {{ margin-bottom: 10px; }}
                        .footer {{ margin-top: 30px; font-size: 0.9em; color: #666; border-top: 1px solid #ddd; padding-top: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2 class="header">Convite para Reserva de Sala</h2>
                        
                        <p>Olá {participante.get('nome', 'Participante')},</p>
                        
                        <p>Você foi adicionado(a) como participante em uma reserva de sala.</p>
                        
                        <div class="info">
                            <div class="info-item"><strong>Sala:</strong> {sala['nome']}</div>
                            <div class="info-item"><strong>Data:</strong> {data_formatada}</div>
                            <div class="info-item"><strong>Horário:</strong> {hora_inicio} - {hora_fim}</div>
                            <div class="info-item"><strong>Organizador:</strong> {organizador['nome']} ({organizador['email']})</div>
                            <div class="info-item"><strong>Descrição:</strong> {descricao}</div>
                        </div>
                        
                        <div class="instructions">
                            <h3>Como visualizar e aceitar este convite:</h3>
                            <div class="instruction-step">1. O convite já foi adicionado ao seu Google Calendar</div>
                            <div class="instruction-step">2. Acesse seu Google Calendar em <a href="https://calendar.google.com">calendar.google.com</a></div>
                            <div class="instruction-step">3. Encontre o evento "{sala['nome']}" no dia {data_formatada}</div>
                            <div class="instruction-step">4. Clique no evento para ver os detalhes e responder (Sim, Não, Talvez)</div>
                        </div>
                        
                        <p>Se tiver alguma dúvida, entre em contato com o organizador da reunião.</p>
                        
                        <div class="footer">
                            <p>Este é um email automático do Sistema de Reserva de Salas. Não responda a este email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                enviado = enviar_email_via_gmail_api(
                    participante.get('email'),
                    f"Convite para Reunião: {sala['nome']}",
                    corpo_email,
                    organizador
                )
                
                # Se não conseguir via API, tenta pelo método tradicional
                if not enviado:
                    enviado = enviar_email_convite(
                        participante.get('nome', ''),
                        participante.get('email'),
                        organizador,
                        sala['nome'],
                        data,
                        hora_inicio,
                        hora_fim,
                        descricao
                    )
            else:
                # Método tradicional via SMTP
                enviado = enviar_email_convite(
                    participante.get('nome', ''),
                    participante.get('email'),
                    organizador,
                    sala['nome'],
                    data,
                    hora_inicio,
                    hora_fim,
                    descricao
                )
            
            # Marcar como notificado se o email foi enviado
            if enviado:
                cursor.execute(
                    'UPDATE participantes SET notificado = 1 WHERE reserva_id = ? AND email = ?',
                    (reserva_id, participante.get('email'))
                )
                conn.commit()
                app.logger.info(f"Participante {participante.get('email')} marcado como notificado")
        
        conn.close()
        
        return redirect(url_for('minhas_reservas'))
    
    # Buscar todas as salas disponíveis
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM salas')
    salas = cursor.fetchall()
    conn.close()
    
    return render_template('reservar_sala.html', salas=salas)

# Função para criar evento no Google Calendar
def criar_evento_google_calendar(sala_nome, data, hora_inicio, hora_fim, descricao, organizador=None, participantes=None):
    if 'google_token' not in session:
        return None
    
    token = session['google_token']
    
    # Formato ISO 8601 para datas
    data_inicio = f"{data}T{hora_inicio}:00"
    data_fim = f"{data}T{hora_fim}:00"
    
    # Preparar lista de participantes
    attendees = []
    if participantes:
        for participante in participantes:
            attendees.append({
                'email': participante.get('email'),
                'displayName': participante.get('nome', ''),
                'responseStatus': 'needsAction'
            })
    
    evento = {
        'summary': f'Reserva: {sala_nome}',
        'location': sala_nome,
        'description': descricao,
        'start': {
            'dateTime': data_inicio,
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': data_fim,
            'timeZone': 'America/Sao_Paulo',
        },
        'attendees': attendees,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    
    headers = {
        'Authorization': f"Bearer {token['access_token']}",
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
        headers=headers,
        json=evento
    )
    
    if response.status_code == 200:
        return response.json()['id']
    else:
        print(f"Erro ao criar evento: {response.text}")
        return None

# Rota para visualizar minhas reservas
@app.route('/minhas-reservas')
@login_required
def minhas_reservas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, s.nome as sala_nome
        FROM reservas r
        JOIN salas s ON r.sala_id = s.id
        WHERE r.user_id = ?
        ORDER BY r.data, r.hora_inicio
    ''', [session['id']])
    reservas_raw = cursor.fetchall()
    conn.close()
    
    # Converter objetos Row para dicionários (que são mutáveis)
    reservas = []
    for row in reservas_raw:
        reserva = dict(row)
        # Formatar datas para exibição brasileira
        if reserva['data'] and len(reserva['data'].split('-')) == 3:
            ano, mes, dia = reserva['data'].split('-')
            reserva['data'] = f"{dia}/{mes}/{ano}"
        reservas.append(reserva)
    
    return render_template('minhas_reservas.html', reservas=reservas)

# API para verificar disponibilidade
@app.route('/api/verificar-disponibilidade', methods=['POST'])
@login_required
def verificar_disponibilidade():
    data = request.json
    sala_id = data['sala_id']
    data_reserva = data['data']
    hora_inicio = data['hora_inicio']
    hora_fim = data['hora_fim']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM reservas 
        WHERE sala_id = ? AND data = ? AND 
        ((hora_inicio <= ? AND hora_fim > ?) OR 
         (hora_inicio < ? AND hora_fim >= ?) OR
         (hora_inicio >= ? AND hora_fim <= ?))
    ''', (sala_id, data_reserva, hora_inicio, hora_inicio, hora_fim, hora_fim, hora_inicio, hora_fim))
    
    conflito = cursor.fetchone()
    conn.close()
    
    if conflito:
        return jsonify({'disponivel': False, 'mensagem': 'Há um conflito com outra reserva'})
    
    return jsonify({'disponivel': True})

# API para obter o status atual das salas
@app.route('/api/status-salas', methods=['GET'])
@login_required
def status_salas():
    # Obter a data e hora atual
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar todas as salas
    cursor.execute('SELECT * FROM salas')
    salas_raw = cursor.fetchall()
    
    salas = []
    for sala_raw in salas_raw:
        sala = dict(sala_raw)
        
        # Verificar se a sala está ocupada agora
        cursor.execute('''
            SELECT r.*, u.username as usuario_nome
            FROM reservas r
            JOIN users u ON r.user_id = u.id
            WHERE r.sala_id = ? AND r.data = ? 
            AND r.hora_inicio <= ? AND r.hora_fim > ?
            AND r.status = 'confirmada'
        ''', (sala['id'], hoje, hora_atual, hora_atual))
        
        reserva_atual = cursor.fetchone()
        
        sala['ocupada'] = reserva_atual is not None
        
        if sala['ocupada']:
            reserva = dict(reserva_atual)
            sala['reserva_id'] = reserva['id']
            sala['usuario'] = reserva['usuario_nome']
            sala['hora_inicio'] = reserva['hora_inicio']
            sala['hora_fim'] = reserva['hora_fim']
            sala['descricao'] = reserva['descricao']
        
        salas.append(sala)
    
    conn.close()
    
    return jsonify({'salas': salas})

# Rota para excluir reserva
@app.route('/excluir-reserva/<int:reserva_id>', methods=['POST'])
def excluir_reserva(reserva_id):
    if 'id' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se a reserva existe e pertence ao usuário
    cursor.execute('''
        SELECT r.*, s.nome as sala_nome 
        FROM reservas r
        JOIN salas s ON r.sala_id = s.id
        WHERE r.id = ? AND r.user_id = ?
    ''', (reserva_id, session['id']))
    
    reserva = cursor.fetchone()
    
    if not reserva:
        conn.close()
        return jsonify({'success': False, 'error': 'Reserva não encontrada ou sem permissão'}), 404
    
    # Se houver ID do evento do Google Calendar, excluí-lo
    if reserva['google_event_id']:
        try:
            excluir_evento_google_calendar(reserva['google_event_id'])
        except Exception as e:
            app.logger.error(f"Erro ao excluir evento do Google Calendar: {e}")
            # Continuamos mesmo se houver erro com o Google Calendar
    
    # Excluir a reserva
    cursor.execute('DELETE FROM reservas WHERE id = ?', (reserva_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Reserva excluída com sucesso'})

# Rota para editar reserva - formulário
@app.route('/editar-reserva/<int:reserva_id>', methods=['GET'])
@login_required
def editar_reserva_form(reserva_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obter a reserva
    cursor.execute('''
        SELECT r.*, s.nome as sala_nome 
        FROM reservas r
        JOIN salas s ON r.sala_id = s.id
        WHERE r.id = ? AND r.user_id = ?
    ''', (reserva_id, session['id']))
    reserva = cursor.fetchone()
    
    if not reserva:
        conn.close()
        return redirect(url_for('minhas_reservas'))
    
    # Obter participantes da reserva
    cursor.execute('SELECT * FROM participantes WHERE reserva_id = ?', (reserva_id,))
    participantes_raw = cursor.fetchall()
    
    participantes = []
    for p in participantes_raw:
        participantes.append({
            'id': p['id'],
            'nome': p['nome'],
            'email': p['email'],
            'status': p['status']
        })
    
    # Obter todas as salas para o formulário
    cursor.execute('SELECT * FROM salas')
    salas = cursor.fetchall()
    conn.close()
    
    return render_template('editar_reserva.html', 
                           reserva=dict(reserva), 
                           salas=salas, 
                           participantes_json=json.dumps(participantes))

# Rota para processar edição de reserva
@app.route('/editar-reserva/<int:reserva_id>', methods=['POST'])
@login_required
def editar_reserva(reserva_id):
    sala_id = request.form['sala_id']
    data = request.form['data']
    hora_inicio = request.form['hora_inicio']
    hora_fim = request.form['hora_fim']
    descricao = request.form['descricao']
    participantes_json = request.form.get('participantes_json', '[]')
    
    try:
        participantes = json.loads(participantes_json)
    except:
        participantes = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se a reserva existe e pertence ao usuário
    cursor.execute('SELECT * FROM reservas WHERE id = ? AND user_id = ?', (reserva_id, session['id']))
    reserva = cursor.fetchone()
    
    if not reserva:
        conn.close()
        return redirect(url_for('minhas_reservas'))
    
    # Obter informações da sala
    cursor.execute('SELECT nome FROM salas WHERE id = ?', (sala_id,))
    sala = cursor.fetchone()
    
    # Obter informações do usuário para o convite
    cursor.execute('SELECT nome, email FROM users WHERE id = ?', (session['id'],))
    organizador = cursor.fetchone()
    
    # Atualizar a reserva
    cursor.execute('''
        UPDATE reservas 
        SET sala_id = ?, data = ?, hora_inicio = ?, hora_fim = ?, descricao = ?
        WHERE id = ?
    ''', (sala_id, data, hora_inicio, hora_fim, descricao, reserva_id))
    conn.commit()
    
    # Atualizar participantes - primeiro remover todos os existentes
    cursor.execute('DELETE FROM participantes WHERE reserva_id = ?', (reserva_id,))
    
    # Adicionar os novos participantes
    if participantes:
        participantes_values = [(reserva_id, p.get('email'), p.get('nome', ''), 'pendente', 0) for p in participantes]
        cursor.executemany(
            'INSERT INTO participantes (reserva_id, email, nome, status, notificado) VALUES (?, ?, ?, ?, ?)',
            participantes_values
        )
        conn.commit()
    
    # Atualizar o evento no Google Calendar
    if reserva['google_event_id'] and 'google_token' in session:
        atualizar_evento_google_calendar(
            reserva['google_event_id'], 
            sala['nome'], 
            data, 
            hora_inicio, 
            hora_fim, 
            descricao,
            organizador,
            participantes
        )
    
    # Enviar emails para os novos participantes
    for participante in participantes:
        # Tentar enviar via Gmail API primeiro (se autenticado)
        if 'google_token' in session:
            # Preparar o corpo do email HTML
            data_obj = datetime.strptime(data, '%Y-%m-%d')
            data_formatada = data_obj.strftime('%d/%m/%Y')
            
            corpo_email = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ color: #3366cc; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
                    .info {{ margin: 20px 0; background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                    .info-item {{ margin: 10px 0; }}
                    .instructions {{ background-color: #e8f4fb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .instruction-step {{ margin-bottom: 10px; }}
                    .footer {{ margin-top: 30px; font-size: 0.9em; color: #666; border-top: 1px solid #ddd; padding-top: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2 class="header">Atualização de Reserva de Sala</h2>
                    
                    <p>Olá {participante.get('nome', 'Participante')},</p>
                    
                    <p>Uma reserva foi atualizada e você está incluído como participante.</p>
                    
                    <div class="info">
                        <div class="info-item"><strong>Sala:</strong> {sala['nome']}</div>
                        <div class="info-item"><strong>Data:</strong> {data_formatada}</div>
                        <div class="info-item"><strong>Horário:</strong> {hora_inicio} - {hora_fim}</div>
                        <div class="info-item"><strong>Organizador:</strong> {organizador['nome']} ({organizador['email']})</div>
                        <div class="info-item"><strong>Descrição:</strong> {descricao}</div>
                    </div>
                    
                    <div class="instructions">
                        <h3>Como visualizar e aceitar este convite:</h3>
                        <div class="instruction-step">1. O convite foi atualizado no seu Google Calendar</div>
                        <div class="instruction-step">2. Acesse seu Google Calendar em <a href="https://calendar.google.com">calendar.google.com</a></div>
                        <div class="instruction-step">3. Encontre o evento "{sala['nome']}" no dia {data_formatada}</div>
                        <div class="instruction-step">4. Clique no evento para ver os detalhes e responder (Sim, Não, Talvez)</div>
                    </div>
                    
                    <p>Se tiver alguma dúvida, entre em contato com o organizador da reunião.</p>
                    
                    <div class="footer">
                        <p>Este é um email automático do Sistema de Reserva de Salas. Não responda a este email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            enviado = enviar_email_via_gmail_api(
                participante.get('email'),
                f"[ATUALIZAÇÃO] Convite para Reunião: {sala['nome']}",
                corpo_email,
                organizador
            )
            
            # Se não conseguir via API, tenta pelo método tradicional
            if not enviado:
                enviado = enviar_email_convite(
                    participante.get('nome', ''),
                    participante.get('email'),
                    organizador,
                    sala['nome'],
                    data,
                    hora_inicio,
                    hora_fim,
                    descricao,
                    is_update=True
                )
        else:
            # Método tradicional via SMTP
            enviado = enviar_email_convite(
                participante.get('nome', ''),
                participante.get('email'),
                organizador,
                sala['nome'],
                data,
                hora_inicio,
                hora_fim,
                descricao,
                is_update=True
            )
        
        # Marcar como notificado se o email foi enviado
        if enviado:
            cursor.execute(
                'UPDATE participantes SET notificado = 1 WHERE reserva_id = ? AND email = ?',
                (reserva_id, participante.get('email'))
            )
            conn.commit()
    
    conn.close()
    return redirect(url_for('minhas_reservas'))

# Função para excluir evento do Google Calendar
def excluir_evento_google_calendar(event_id):
    """Exclui um evento do Google Calendar."""
    if 'google_token' not in session:
        return False
        
    token = session['google_token']
    headers = {
        'Authorization': f"Bearer {token['access_token']}",
        'Content-Type': 'application/json'
    }
    
    response = requests.delete(
        f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}',
        headers=headers
    )
    
    if response.status_code in [200, 204]:
        return True
    else:
        app.logger.error(f"Erro ao excluir evento: {response.text}")
        return False

# Função para atualizar evento no Google Calendar
def atualizar_evento_google_calendar(event_id, sala_nome, data, hora_inicio, hora_fim, descricao, organizador=None, participantes=None):
    if 'google_token' not in session:
        return False
    
    token = session['google_token']
    
    # Formato ISO 8601 para datas
    data_inicio = f"{data}T{hora_inicio}:00"
    data_fim = f"{data}T{hora_fim}:00"
    
    # Preparar lista de participantes
    attendees = []
    if participantes:
        for participante in participantes:
            attendees.append({
                'email': participante.get('email'),
                'displayName': participante.get('nome', ''),
                'responseStatus': 'needsAction'
            })
    
    evento = {
        'summary': f'Reserva: {sala_nome}',
        'location': sala_nome,
        'description': descricao,
        'start': {
            'dateTime': data_inicio,
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': data_fim,
            'timeZone': 'America/Sao_Paulo',
        },
        'attendees': attendees,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    
    headers = {
        'Authorization': f"Bearer {token['access_token']}",
        'Content-Type': 'application/json'
    }
    
    response = requests.put(
        f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}',
        headers=headers,
        json=evento
    )
    
    if response.status_code == 200:
        return True
    else:
        print(f"Erro ao atualizar evento: {response.text}")
        return False

# Função para enviar e-mails de convite
def enviar_email_convite(nome_participante, email_participante, organizador, sala_nome, data, hora_inicio, hora_fim, descricao, is_update=False):
    """Envia um e-mail de convite ou atualização para o participante."""
    app.logger.info(f"Tentando enviar email para {email_participante}")
    
    try:
        # Obter credenciais do arquivo .env
        smtp_server = os.getenv('EMAIL_SMTP_SERVER')
        smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        # Verificar configurações de email
        app.logger.info(f"Configurações de email: SMTP={smtp_server}:{smtp_port}, USER={email_user}")
        
        # Se alguma configuração de e-mail estiver faltando, registrar erro e retornar
        if not all([smtp_server, smtp_port, email_user, email_password]):
            app.logger.error("Configurações de e-mail incompletas. Verifique o arquivo .env")
            return False
        
        # Formatar a data para exibição
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d')
            data_formatada = data_obj.strftime('%d/%m/%Y')
        except:
            data_formatada = data
        
        # Configurar o e-mail
        msg = MIMEMultipart()
        
        if is_update:
            msg['Subject'] = f'[ATUALIZAÇÃO] Convite para Reunião: {sala_nome}'
        else:
            msg['Subject'] = f'Convite para Reunião: {sala_nome}'
            
        msg['From'] = email_user
        msg['To'] = email_participante
        
        # Corpo do e-mail com instruções sobre como aceitar o convite
        corpo_email = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ color: #3366cc; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
                .info {{ margin: 20px 0; background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                .info-item {{ margin: 10px 0; }}
                .instructions {{ background-color: #e8f4fb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .instruction-step {{ margin-bottom: 10px; }}
                .footer {{ margin-top: 30px; font-size: 0.9em; color: #666; border-top: 1px solid #ddd; padding-top: 10px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="header">{"Atualização de Reserva de Sala" if is_update else "Convite para Reunião"}</h2>
                
                <p>Olá {nome_participante or "Participante"},</p>
                
                <p>{"Uma reserva foi atualizada e você continua como participante" if is_update else "Você foi adicionado(a) como participante em uma reserva de sala"}.</p>
                
                <div class="info">
                    <div class="info-item"><strong>Sala:</strong> {sala_nome}</div>
                    <div class="info-item"><strong>Data:</strong> {data_formatada}</div>
                    <div class="info-item"><strong>Horário:</strong> {hora_inicio} - {hora_fim}</div>
                    <div class="info-item"><strong>Organizador:</strong> {organizador['nome']} ({organizador['email']})</div>
                    <div class="info-item"><strong>Descrição:</strong> {descricao}</div>
                </div>
                
                <div class="instructions">
                    <h3>Como visualizar e aceitar este convite:</h3>
                    <div class="instruction-step">1. O convite já deve estar no seu Google Calendar</div>
                    <div class="instruction-step">2. Acesse seu Google Calendar em <a href="https://calendar.google.com">calendar.google.com</a></div>
                    <div class="instruction-step">3. Encontre o evento "{sala_nome}" no dia {data_formatada}</div>
                    <div class="instruction-step">4. Clique no evento para ver os detalhes e responder (Sim, Não, Talvez)</div>
                </div>
                
                <p>Se tiver alguma dúvida, entre em contato com o organizador da reunião.</p>
                
                <div class="footer">
                    <p>Este é um email automático do Sistema de Reserva de Salas. Não responda a este email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(corpo_email, 'html'))
        
        # Enviar o e-mail
        try:
            app.logger.info(f"Tentando conectar ao servidor SMTP {smtp_server}:{smtp_port}")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.set_debuglevel(1)  # Habilitar debugging para depuração
                app.logger.info("Iniciando TLS...")
                server.starttls()
                app.logger.info(f"Fazendo login com usuário {email_user}")
                server.login(email_user, email_password)
                app.logger.info(f"Enviando mensagem para {email_participante}")
                server.send_message(msg)
                app.logger.info(f"Email enviado com sucesso para {email_participante}")
            return True
        except Exception as e:
            app.logger.error(f"Erro ao enviar e-mail via SMTP: {e}")
            return False
    except Exception as e:
        app.logger.error(f"Erro ao preparar e-mail: {e}")
        return False

# Adicionar após a função enviar_email_convite
def enviar_email_via_gmail_api(destinatario, assunto, conteudo_html, organizador=None):
    """
    Envia um email usando a API do Gmail se o usuário estiver autenticado.
    Esta função é uma alternativa ao envio via SMTP.
    """
    app.logger.info(f"Tentando enviar email via Gmail API para {destinatario}")
    
    # Verificar se o usuário está autenticado no Google
    if 'google_token' not in session:
        app.logger.warning("Token do Google não disponível. Não é possível usar Gmail API.")
        return False
    
    try:
        token = session['google_token']
        
        # Verificar se o token tem a permissão necessária
        if 'https://www.googleapis.com/auth/gmail.send' not in token.get('scope', ''):
            app.logger.warning("Token não tem permissão para enviar emails. Tentando método SMTP.")
            return False
        
        headers = {
            'Authorization': f"Bearer {token['access_token']}",
            'Content-Type': 'application/json'
        }
        
        # Codificar o email em Base64
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import base64
        
        msg = MIMEMultipart()
        msg['to'] = destinatario
        msg['subject'] = assunto
        
        # Adicionar nome do organizador no From se disponível
        if organizador and 'nome' in organizador and 'email' in organizador:
            msg['from'] = f"{organizador['nome']} <{organizador['email']}>"
        else:
            msg['from'] = session.get('email', '')
        
        msg.attach(MIMEText(conteudo_html, 'html'))
        
        # O Gmail API espera a mensagem em base64url 
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        # Preparar a solicitação para a API do Gmail
        payload = {
            'raw': encoded_message
        }
        
        # Enviar a mensagem
        app.logger.info(f"Enviando email via Gmail API para {destinatario}")
        response = requests.post(
            'https://www.googleapis.com/gmail/v1/users/me/messages/send',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            app.logger.info(f"Email enviado com sucesso via Gmail API para {destinatario}")
            return True
        else:
            app.logger.error(f"Falha ao enviar via Gmail API: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        app.logger.error(f"Erro ao tentar enviar email via Gmail API: {e}")
        return False

# Função para criar o banco de dados se não existir
def create_db_if_not_exists():
    if not os.path.exists(DB_PATH):
        with app.app_context():
            init_db()

# API para buscar usuários do domínio para sugestões
@app.route('/api/usuarios-dominio', methods=['GET'])
@login_required
def usuarios_dominio():
    # Se temos uma lista em cache na sessão, usamos ela
    if 'domain_users' in session and session['domain_users']:
        return jsonify(session['domain_users'])
    
    # Caso contrário, buscamos do banco de dados
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, email FROM users WHERE email LIKE ?', ('%@cstein.com.br',))
    usuarios = cursor.fetchall()
    conn.close()
    
    # Converter para lista de dicionários
    usuarios_lista = []
    for usuario in usuarios:
        usuarios_lista.append({
            'id': usuario['id'],
            'nome': usuario['nome'] or usuario['email'].split('@')[0],
            'email': usuario['email']
        })
    
    # Atualizar cache na sessão
    session['domain_users'] = usuarios_lista
    
    return jsonify(usuarios_lista)

if __name__ == '__main__':
    create_db_if_not_exists()
    app.run(debug=True) 