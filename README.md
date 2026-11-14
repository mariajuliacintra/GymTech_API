# 🏋️‍♂️ GYMtech - Sistema Integrado de Gestão Fitness

![Status](https://img.shields.io/badge/Status-Finalizado-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql)

O **GYMtech** é uma plataforma Backend RESTful completa e centralizada, desenvolvida para revolucionar a gestão de academias e a interação entre **gestores**, **profissionais da saúde/fitness** e **alunos**. 

O ecossistema resolve a fragmentação do mercado fitness ao unificar, em uma única API de alta performance, a prescrição de treinos, o agendamento inteligente de aulas e avaliações físicas, além de notificações automatizadas.

---

## 🎯 Principais Funcionalidades e Diferenciais

O sistema foi arquitetado com separação estrita de escopos (RBAC via JWT) e regras de negócio robustas para garantir integridade e fluidez:

### 🏢 Para a Academia (Gestão)
* **Controle Centralizado:** Gestão de alunos e profissionais vinculados à unidade.
* **Catálogo de Exercícios:** Criação de uma biblioteca unificada de exercícios para padronização.
* **Administração de Aulas:** Criação de turmas e aulas com limites estritos de capacidade.
* **Visão Macro:** Monitoramento e reagendamento de avaliações físicas e reservas.

### 🧑‍⚕️ Para o Profissional (Personal / Avaliador)
* **Prescrição de Treinos:** Montagem de treinos individualizados com definição de séries, repetições, carga sugerida e tempos de descanso.
* **Avaliação Física:** Agendamento e preenchimento detalhado de anamnese e métricas corporais (peso, altura, % de gordura, medidas).
* **Gestão de Turmas:** Visualização em tempo real da lista de alunos confirmados em suas aulas.

### 🏃 Para o Aluno
* **Reserva de Aulas:** Agendamento rápido em aulas coletivas.
* **Agendamento de Avaliações:** Marcação de horários diretamente com os profissionais, com validação automática de conflitos.
* **Lembretes Diários:** Recebimento automático de e-mails detalhados contendo o treino do dia.

### ⚙️ Engenharia e Diferenciais Técnicos
* **Controle de Concorrência (Locking):** Proteção contra *overbooking* em aulas usando travas transacionais no banco de dados (`SELECT ... FOR UPDATE`), garantindo que a capacidade máxima nunca seja ultrapassada.
* **Agendamento de Tarefas (Cron Jobs):** Integração com `APScheduler` para rodar verificações diárias automáticas em segundo plano e disparar e-mails.
* **Mensageria Rica:** Disparo de e-mails em HTML (via `Jinja2` e SMTP) para validação de contas, redefinição de senhas e lembretes de treinos.
* **Exclusão em Cascata (Soft & Hard Delete):** Regras inteligentes que cancelam reservas e agendamentos futuros automaticamente caso um usuário seja inativado.

---

## 🛠️ Stack Tecnológica

* **Linguagem:** Python 3.10+
* **Framework Web:** FastAPI
* **Banco de Dados:** MySQL 8.0+
* **ORM e Query Builder:** SQLAlchemy
* **Validação e Serialização:** Pydantic V2
* **Agendamento de Tarefas (Background):** APScheduler
* **Templates HTML (E-mails):** Jinja2
* **Segurança:** PyJWT (Tokens JWT), Passlib (Bcrypt) para hashing de senhas.
* **Servidor ASGI:** Uvicorn

---

## 🚀 Como Rodar o Projeto Localmente

Siga o passo a passo abaixo para configurar e executar a API em seu ambiente de desenvolvimento.

### 📋 Pré-requisitos
* **Python 3.10+**
* **MySQL 8.0+** rodando localmente ou em container (Docker).
* **Git** para clonar o repositório.

### 1. Clonar e Preparar o Ambiente
```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd GYMtech/backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual (Windows)
.\venv\Scripts\activate
# Ativar ambiente virtual (Linux/macOS)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar o Banco de Dados
1. Acesse seu servidor MySQL.
2. Execute o script SQL principal para criar o banco de dados e as tabelas:
   * Localizado em: `sql/gymtech.sql`
   * Caso esteja atualizando de uma versão anterior, verifique também os scripts na pasta `sql/`.

### 3. Variáveis de Ambiente
Crie um arquivo `.env` na raiz da pasta `backend` fazendo uma cópia do arquivo de exemplo:
```bash
cp .env.example .env
```
Edite o arquivo `.env` preenchendo as chaves necessárias:
* `DATABASE_URL`: String de conexão do MySQL (ex: `mysql+pymysql://user:pass@localhost:3306/gymtech`).
* `SECRET_KEY`: Chave aleatória para assinatura dos tokens JWT.
* **Configurações SMTP:** (Obrigatório para o envio de e-mails e códigos de verificação).
* **Configurações de Notificação:** Ajuste horários do Cron Job (`NOTIFICACAO_TREINO_HORA`, etc).

### 4. Executar a Aplicação
Inicie o servidor Uvicorn com recarregamento automático:
```bash
uvicorn app.main:app --reload
```
A API estará online! 🚀

---

## 📚 Documentação da API (Swagger)

O FastAPI gera a documentação interativa automaticamente. Com o servidor rodando, acesse no seu navegador:

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Pelo Swagger UI é possível testar todos os endpoints, realizar login, injetar o token JWT globalmente e simular o fluxo completo da aplicação.