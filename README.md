# Nzila Plus — Backend API

> Projecto de Fim de Curso (PAP) — Curso de Informática  
> **Tema:** Aplicativo para Gestão e Optimização do Transporte de Cargas Urbanas com Monitoramento em Tempo Real

---

## Descrição

O **Nzila Plus** é uma plataforma de transporte de cargas urbanas desenvolvida em Angola. Funciona como um "Uber para frete" — o cliente publica uma carga que precisa de ser transportada e os motoristas disponíveis podem aceitar a entrega.

O sistema inclui monitoramento em tempo real via WebSockets, notificações push, cálculo automático de preço com base na distância real (integração com Mapbox no frontend), filtro de cargas por proximidade geográfica usando a fórmula de Haversine, e carteira digital para os motoristas.

---

## Tecnologias

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.12 | Linguagem principal |
| Django | 6.0 | Framework web |
| Django REST Framework | 3.x | API REST |
| MySQL | 8.0 | Base de dados |
| Django Channels | 4.x | WebSockets em tempo real |
| Redis | 7.x | Canal de mensagens para WebSockets |
| Expo Push Notifications | — | Notificações push |
| drf-spectacular | — | Documentação Swagger automática |
| Whitenoise | — | Ficheiros estáticos |

---

## Instalação e Configuração

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU_USUARIO/nzila-plus-backend.git
cd nzila-plus-backend
```

### 2. Criar e activar ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Cria um ficheiro `.env` na raiz do projecto:
```env
DJANGO_SECRET_KEY=django-insecure-chave-secreta-aqui
DJANGO_DEBUG=True

DB_NAME=nzila_plus
DB_USER=root
DB_PASSWORD=a_tua_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 5. Criar a base de dados MySQL
```sql
CREATE DATABASE nzila_plus CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. Correr as migrações
```bash
python manage.py migrate
```

### 7. Criar superutilizador (Django Admin)
```bash
python manage.py createsuperuser
```

### 8. Iniciar o servidor
```bash
python manage.py runserver
```

---

## Testes Automatizados

O projecto tem **23 testes automatizados** cobrindo todos os fluxos principais:

```bash
python manage.py test api --verbosity=2
```

Resultado esperado:
```
Ran 23 tests in ~80s — OK
```

Os testes cobrem: autenticação, ciclo completo da carga, filtro por raio geográfico, cálculo de preço, perfis, carteira digital e casos de erro.

---

## Documentação Swagger

Com o servidor a correr, acede a:
```
http://localhost:8000/api/schema/swagger-ui/
```

---

## Endpoints da API

Base URL: `http://localhost:8000/api/`

Todos os endpoints (excepto `/register/` e `/login/`) requerem autenticação via token:
```
Authorization: Token <token>
```

---

### Autenticação

#### POST /register/
Registo de novo utilizador (cliente ou motorista).

**Body:**
```json
{
  "username": "andre123",
  "password": "pass1234",
  "email": "andre@email.com",
  "tipo_usuario": "cliente",
  "bi": "BI000123",
  "telefone": "900111222",
  "morada": "Luanda, Maianga"
}
```

**Resposta (201):**
```json
{
  "message": "Usuário criado com sucesso!",
  "username": "andre123",
  "email": "andre@email.com"
}
```

---

#### POST /login/
Login — devolve token de autenticação e tipo de utilizador.

**Resposta (200):**
```json
{
  "token": "abc123...",
  "user_id": 1,
  "username": "andre123",
  "user_type": "cliente"
}
```

---

#### POST /logout/
Apaga o token do servidor — resolve problema de token persistente quando a app reinicia.

---

### Cargas

#### POST /cargas/
Cliente cria uma nova carga. O preço é calculado automaticamente.

**Fórmula do preço:**
```
Preço = 2000 Kz (base)
      + (peso_kg × 100 Kz × taxa_categoria)
      + (distancia_km × 50 Kz)

Taxa por categoria:
  construcao → 1.5×
  mobilia    → 1.2×
  eletro     → 1.0×
  outros     → 1.0×
```

---

#### GET /cargas/disponiveis/
Motorista lista cargas disponíveis com filtro por proximidade geográfica.

**Query params opcionais:**
```
lat=-8.8400&lon=13.2350&raio=15
```

As cargas são ordenadas da mais próxima para a mais distante usando a **fórmula geodésica de Haversine** — sem dependência de APIs externas.

---

#### POST /cargas/{id}/aceitar/
Motorista aceita uma carga. Validações aplicadas:
- Documentos (BI, carta, livrete) verificados pelo admin
- Sem outra viagem EM_TRANSITO activa
- Carga PENDENTE sem motorista atribuído

Devolve a cor do veículo para a animação no frontend.

---

#### POST /cargas/{id}/recusar/
Motorista recusa — carga não volta a aparecer na sua lista.

---

#### POST /cargas/{id}/cancelar/
Cliente cancela a carga. Só possível se PENDENTE.

---

#### POST /cargas/{id}/finalizar-entrega/
Motorista marca como entregue. Valor do frete creditado automaticamente na carteira.

---

#### POST /cargas/{id}/avaliar/
Cliente avalia o motorista (1-5 estrelas). Só uma vez por entrega.

**Body:** `{ "avaliacao": 5 }`

---

### Ciclo de vida da carga
```
PENDENTE → EM_TRANSITO → ENTREGUE
    ↓
CANCELADO (só pelo cliente, apenas quando PENDENTE)
```

---

### Perfis

#### GET /perfil/cliente/
Dados do cliente com estatísticas de cargas.

#### PATCH /perfil/cliente/editar/
Edita: `first_name`, `last_name`, `email`, `password`, `telefone`, `endereco`, `bi`, `foto_perfil`

#### GET /perfil/motorista/
Dados do motorista com saldo, avaliação média e veículo.

#### PATCH /perfil/motorista/editar/
Edita dados pessoais, documentos (frente/verso), e dados do veículo incluindo cor.

> Ao mudar a password, o token actual é invalidado e um `novo_token` é devolvido.  
> Ao enviar nova foto de documento, o campo de verificação volta a `False`.

#### GET /perfil/motorista/carteira/
Saldo actual e histórico de entregas pagas.

---

### Notificações

#### POST /notificacoes/registar-token/
Regista o token Expo do dispositivo.

**Body:** `{ "push_token": "ExponentPushToken[xxxxxx]" }`

**Eventos:** cliente notificado quando carga é aceite e quando é entregue.

---

## WebSockets

Canal: `ws://localhost:8000/ws/cargas/`

Emite actualizações de status em tempo real sempre que uma carga muda de estado.

---

## Django Admin

Acede em `http://localhost:8000/admin/` para verificar documentos dos motoristas e gerir o sistema.

---

## Estrutura do Projecto

```
nzila-plus-backend/
├── core/                   # Configurações do projecto
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── api/                    # App principal
│   ├── models.py           # Modelos de dados
│   ├── views.py            # Lógica da API
│   ├── serializers.py      # Serialização
│   ├── urls.py             # Endpoints
│   ├── admin.py            # Painel admin
│   ├── consumers.py        # WebSockets
│   ├── tests.py            # 23 testes automatizados
│   └── migrations/
├── manage.py
├── requirements.txt
└── README.md
```

---

*Desenvolvido por André Kumbo Kuwonza — PAP 2025/2026*