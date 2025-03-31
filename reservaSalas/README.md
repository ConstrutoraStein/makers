# Sistema de Reserva de Salas com Integração Google Calendar

Um sistema web moderno para gerenciamento e reserva de salas de reuniões com integração ao Google Calendar, desenvolvido com Flask, MySQL e Bootstrap.

![Screenshot do Sistema](app/static/img/screenshot.png)

## Funcionalidades

- ✅ Login e autenticação de usuários
- ✅ Dashboard intuitivo com visão geral das reservas
- ✅ Reserva de salas com verificação de disponibilidade
- ✅ Visualização de calendário interativo
- ✅ Gerenciamento de reservas (criar, editar, cancelar)
- ✅ Integração com Google Calendar
- ✅ Interface responsiva e moderna
- ✅ Banco de dados MySQL

## Requisitos

- Python 3.7+
- MySQL Server
- Pip (gerenciador de pacotes Python)
- Credenciais da API Google Calendar

## Instalação

1. Clone o repositório:
```
git clone https://github.com/seu_usuario/reserva-salas.git
cd reserva-salas
```

2. Crie e ative um ambiente virtual:
```
python -m venv venv
# No Windows
venv\Scripts\activate
# No Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:
```
pip install -r requirements.txt
```

4. Configure o banco de dados:
   - Crie um banco de dados MySQL
   - Importe o script SQL do arquivo `app/database/setup.sql`
   - Atualize as configurações de conexão em `app.py`

5. Configure a integração com o Google Calendar:
   - Obtenha as credenciais da API Google Calendar
   - Salve o arquivo `client_secret.json` na raiz do projeto

6. Execute a aplicação:
```
python app.py
```

7. Acesse a aplicação em seu navegador:
```
http://localhost:5000
```

## Usuários Padrão

- **Administrador**: 
  - Usuário: admin
  - Senha: admin123

- **Usuário Comum**:
  - Usuário: user
  - Senha: user123

## Estrutura do Projeto

```
reserva-salas/
├── app/
│   ├── controllers/           # Controladores da aplicação
│   ├── database/              # Scripts e configurações do banco de dados
│   ├── static/                # Arquivos estáticos (CSS, JS, imagens)
│   │   ├── css/              
│   │   ├── js/               
│   │   └── img/              
│   └── templates/             # Templates HTML
├── app.py                     # Arquivo principal da aplicação
├── requirements.txt           # Dependências do projeto
└── README.md                  # Documentação
```

## Integração com Google Calendar

Para ativar a integração com o Google Calendar:

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/)
2. Ative a API Google Calendar
3. Configure as credenciais OAuth
4. Baixe o arquivo JSON de credenciais e salve como `client_secret.json` na raiz do projeto

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes. 