import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from flask import url_for, session, redirect, request

# Escopos necessários para o Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarAPI:
    def __init__(self, app=None):
        self.app = app
        self.client_secrets_file = 'client_secret.json'  # Arquivo de credenciais da API Google
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
    
    def get_credentials(self):
        """Obtém as credenciais do Google da sessão do usuário."""
        if 'credentials' not in session:
            return None
            
        return Credentials.from_authorized_user_info(session['credentials'], SCOPES)
    
    def build_service(self):
        """Constrói o serviço da API Google Calendar."""
        credentials = self.get_credentials()
        if not credentials or not credentials.valid:
            return None
            
        return build('calendar', 'v3', credentials=credentials)
    
    def create_auth_flow(self, redirect_uri):
        """Cria um fluxo de autenticação OAuth."""
        return Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    
    def get_auth_url(self, redirect_uri):
        """Gera a URL para o fluxo de autenticação OAuth."""
        flow = self.create_auth_flow(redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        session['oauth_state'] = state
        return auth_url
    
    def finalize_auth(self, redirect_uri, code):
        """Finaliza o fluxo de autenticação OAuth."""
        flow = self.create_auth_flow(redirect_uri)
        flow.fetch_token(code=code)
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        return credentials
    
    def create_event(self, sala, data, hora_inicio, hora_fim, descricao, usuario=None):
        """Cria um evento no Google Calendar."""
        service = self.build_service()
        if not service:
            return None
            
        # Formatar data e hora conforme RFC 3339
        data_inicio = f"{data}T{hora_inicio}:00"
        data_fim = f"{data}T{hora_fim}:00"
        
        # Criação do evento
        evento = {
            'summary': f"Reserva de Sala: {sala}",
            'location': sala,
            'description': descricao,
            'start': {
                'dateTime': data_inicio,
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': data_fim,
                'timeZone': 'America/Sao_Paulo',
            },
            'attendees': [],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        # Adicionar o usuário como participante, se fornecido
        if usuario and 'email' in usuario:
            evento['attendees'].append({'email': usuario['email']})
            
        # Criar o evento no calendário primário do usuário
        evento = service.events().insert(calendarId='primary', body=evento).execute()
        return evento.get('id')
    
    def delete_event(self, event_id):
        """Remove um evento do Google Calendar."""
        service = self.build_service()
        if not service:
            return False
            
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    
    def update_event(self, event_id, sala, data, hora_inicio, hora_fim, descricao):
        """Atualiza um evento existente no Google Calendar."""
        service = self.build_service()
        if not service:
            return False
            
        # Formatar data e hora conforme RFC 3339
        data_inicio = f"{data}T{hora_inicio}:00"
        data_fim = f"{data}T{hora_fim}:00"
        
        # Obter o evento atual
        evento = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Atualizar o evento
        evento['summary'] = f"Reserva de Sala: {sala}"
        evento['location'] = sala
        evento['description'] = descricao
        evento['start']['dateTime'] = data_inicio
        evento['end']['dateTime'] = data_fim
        
        # Enviar a atualização
        updated_event = service.events().update(
            calendarId='primary', 
            eventId=event_id, 
            body=evento
        ).execute()
        
        return updated_event.get('id') 