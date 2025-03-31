# Configuração do Google OAuth para Sistema de Reserva de Salas

Este documento explica como configurar as credenciais do Google OAuth para o sistema de reserva de salas.

## Pré-requisitos

1. Uma conta Google
2. Acesso ao [Google Cloud Console](https://console.cloud.google.com/)

## Passo a Passo

### 1. Criar um Projeto no Google Cloud

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Clique em "Selecionar Projeto" no topo da página
3. Clique em "Novo Projeto"
4. Dê um nome para o projeto (ex: "Sistema de Reservas")
5. Clique em "Criar"

### 2. Configurar a Tela de Consentimento OAuth

1. No menu lateral, navegue até "APIs e Serviços" > "Tela de consentimento OAuth"
2. Selecione "Externo" (disponível para qualquer usuário com conta Google)
3. Clique em "Criar"
4. Preencha as informações necessárias:
   - Nome do aplicativo: "Sistema de Reserva de Salas"
   - Email de suporte do usuário: seu email
   - Domínio autorizado: o domínio onde seu aplicativo será hospedado (para testes locais pode ficar em branco)
   - Informações de contato do desenvolvedor: seu email
5. Clique em "Salvar e Continuar"
6. Na seção "Escopos", adicione os seguintes escopos:
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/calendar`
   - `openid`
7. Clique em "Salvar e Continuar"
8. Adicione seu email como usuário de teste
9. Clique em "Salvar e Continuar"
10. Revise as informações e clique em "Voltar ao painel"

### 3. Criar Credenciais OAuth

1. No menu lateral, navegue até "APIs e Serviços" > "Credenciais"
2. Clique em "Criar Credenciais" > "ID do cliente OAuth"
3. Selecione "Aplicativo da Web" como tipo de aplicativo
4. Dê um nome para o cliente (ex: "Sistema de Reserva de Salas - Web")
5. Em "URIs de redirecionamento autorizados", adicione:
   - Para desenvolvimento local: `http://localhost:5000/login/google/callback`
   - Para produção: `https://seu-dominio.com/login/google/callback`
6. Clique em "Criar"

Você receberá um "ID do cliente" e uma "Chave secreta do cliente". Guarde essas informações com segurança.

### 4. Ativar a API do Google Calendar

1. No menu lateral, navegue até "APIs e Serviços" > "Biblioteca"
2. Procure por "Google Calendar API"
3. Clique na API do Google Calendar
4. Clique em "Ativar"

### 5. Configurar o Arquivo .env

Adicione as credenciais obtidas ao arquivo `.env`:

```
GOOGLE_CLIENT_ID=seu_client_id
GOOGLE_CLIENT_SECRET=seu_client_secret
```

Agora seu Sistema de Reserva de Salas está configurado para usar a autenticação do Google e a API do Google Calendar!

## Testando a Integração

1. Execute a aplicação
2. Acesse a página de login
3. Clique no botão "Entrar com Google"
4. Escolha sua conta Google
5. Permita o acesso ao aplicativo

Se a configuração estiver correta, você será autenticado e redirecionado para o dashboard do sistema, e suas reservas serão automaticamente sincronizadas com seu Google Calendar. 