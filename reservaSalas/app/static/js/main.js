/**
 * Sistema de Reserva de Salas
 * Arquivo JavaScript principal
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Toggle para o menu lateral em dispositivos móveis
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            document.body.classList.toggle('sidebar-toggled');
            document.querySelector('.sidebar').classList.toggle('toggled');
        });
    }

    // Verificação de senha forte no formulário de cadastro
    const passwordField = document.getElementById('password');
    const passwordConfirmField = document.getElementById('password_confirm');
    const passwordFeedback = document.getElementById('password-feedback');
    
    if (passwordField && passwordFeedback) {
        passwordField.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            let feedback = '';
            
            // Verificar tamanho
            if (password.length >= 8) {
                strength += 1;
            } else {
                feedback += 'Sua senha deve ter pelo menos 8 caracteres. ';
            }
            
            // Verificar letras maiúsculas e minúsculas
            if (password.match(/[a-z]/) && password.match(/[A-Z]/)) {
                strength += 1;
            } else {
                feedback += 'Use letras maiúsculas e minúsculas. ';
            }
            
            // Verificar números
            if (password.match(/\d/)) {
                strength += 1;
            } else {
                feedback += 'Inclua pelo menos um número. ';
            }
            
            // Verificar caracteres especiais
            if (password.match(/[^a-zA-Z\d]/)) {
                strength += 1;
            } else {
                feedback += 'Inclua pelo menos um caractere especial. ';
            }
            
            // Atualizar o feedback
            if (strength < 2) {
                passwordFeedback.className = 'text-danger';
                passwordFeedback.textContent = feedback || 'Senha muito fraca';
            } else if (strength < 4) {
                passwordFeedback.className = 'text-warning';
                passwordFeedback.textContent = 'Senha média';
            } else {
                passwordFeedback.className = 'text-success';
                passwordFeedback.textContent = 'Senha forte';
            }
        });
    }
    
    // Verificar se as senhas coincidem
    if (passwordField && passwordConfirmField) {
        passwordConfirmField.addEventListener('input', function() {
            if (this.value !== passwordField.value) {
                this.setCustomValidity('As senhas não coincidem');
            } else {
                this.setCustomValidity('');
            }
        });
    }

    // Inicialização de tooltips do Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Função para obter dados das reservas para o calendário
    async function fetchReservas() {
        try {
            const response = await fetch('/api/reservas');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Erro ao buscar reservas:', error);
            return [];
        }
    }
    
    // Inicialização do calendário com dados dinâmicos
    const calendarEl = document.getElementById('calendar');
    if (calendarEl) {
        fetchReservas().then(eventos => {
            const calendar = new FullCalendar.Calendar(calendarEl, {
                locale: 'pt-br',
                initialView: 'dayGridMonth',
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                },
                buttonText: {
                    today: 'Hoje',
                    month: 'Mês',
                    week: 'Semana',
                    day: 'Dia'
                },
                events: eventos,
                eventClick: function(info) {
                    mostrarDetalhesReserva(info.event);
                }
            });
            calendar.render();
        });
    }
    
    // Função para exibir detalhes da reserva
    function mostrarDetalhesReserva(evento) {
        // Implementação de um modal para exibir detalhes
        const modal = new bootstrap.Modal(document.getElementById('modalDetalhesReserva'));
        
        // Preencher o modal com as informações do evento
        document.getElementById('detalhe-titulo').textContent = evento.title;
        document.getElementById('detalhe-sala').textContent = evento.extendedProps.sala || evento.title;
        document.getElementById('detalhe-data').textContent = formatarData(evento.start);
        document.getElementById('detalhe-horario').textContent = `${formatarHora(evento.start)} - ${formatarHora(evento.end)}`;
        document.getElementById('detalhe-descricao').textContent = evento.extendedProps.descricao || 'Sem descrição';
        
        // Exibir o modal
        modal.show();
    }
    
    // Funções auxiliares para formatação de data e hora
    function formatarData(data) {
        return data.toLocaleDateString('pt-BR');
    }
    
    function formatarHora(data) {
        return data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }
});

// Funções para tratamento de erros
function handleFetchError(error, message = 'Erro ao comunicar com o servidor') {
    console.error(error);
    alert(message);
}

// Funções para manipulação de reservas
async function cancelarReserva(reservaId) {
    if (!confirm('Tem certeza que deseja cancelar esta reserva?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/reservas/${reservaId}/cancelar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Reserva cancelada com sucesso!');
            window.location.reload();
        } else {
            alert(`Erro ao cancelar reserva: ${result.message}`);
        }
    } catch (error) {
        handleFetchError(error, 'Erro ao cancelar a reserva');
    }
}

// Integração com Google Calendar
async function sincronizarGoogleCalendar() {
    try {
        const response = await fetch('/api/sincronizar-google-calendar', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Sincronização com Google Calendar realizada com sucesso!');
        } else {
            window.location.href = result.auth_url;
        }
    } catch (error) {
        handleFetchError(error, 'Erro ao sincronizar com o Google Calendar');
    }
} 