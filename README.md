# 🏋️‍♂️ GYMtech - Sistema Integrado para Academias, Profissionais e Alunos

> 🚧 **Status do Projeto:** Em Desenvolvimento (Em Fase de Construção)

O **GYMtech** é uma plataforma centralizada criada para conectar e facilitar a gestão e interação entre **academias**, **profissionais da saúde/fitness** e **alunos**. O ecossistema visa solucionar o ecossistema fragmentado do fitness, unificando objetivos, criação de treinos, agendamento de aulas, biblioteca de exercícios e modos de execução em uma única aplicação.

## 🎯 Objetivo do Projeto

O objetivo principal do GYMtech é fornecer uma solução de ponta a ponta que atenda às necessidades de todos os atores do ambiente fitness:

1. **Para as Academias:**

   * Gerenciamento simplificado de unidades, turmas, aulas e dados de frequência.

   * Controle centralizado de alunos e profissionais vinculados.

2. **Para os Profissionais (Personal Trainers, Instrutores, Nutricionistas):**

   * Ferramentas ágeis para montagem e prescrição de treinos individualizados.

   * Acompanhamento do progresso, histórico dos alunos e rotinas de exercícios.

3. **Para os Alunos:**

   * Acesso rápido aos treinos prescritos, guia com modos de execução de exercícios e acompanhamento de seus objetivos pessoais.

   * Interatividade e integração direta com a academia e seus instrutores.

## 🛠️ Tecnologias Utilizadas (Backend)

* **Linguagem:** Python 3.10+

* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/)

* **Servidor ASGI:** Uvicorn

* **Validação de Dados:** Pydantic / Email-Validator

* **Segurança e Criptografia:** Bcrypt / PyJWT / Passlib

* **Gerenciamento de Ambientes:** Python Dotenv

## 🚀 Como Rodar o Projeto Localmente

Siga o passo a passo abaixo para configurar e executar a API em seu ambiente de desenvolvimento.

### 📋 Pré-requisitos

* **Python 3.10+** instalado no sistema.

* **Git** para clonar o repositório.

### Step 1: Clonar o Repositório

```
git clone <URL_DO_SEU_REPOSITORIO>
cd GYMtech/backend

```

### Step 2: Criar e Ativar o Ambiente Virtual (`venv`)

* **No Linux / macOS:**

  ```
  python3 -m venv venv
  source venv/bin/activate
  
  ```

* **No Windows (PowerShell):**

  ```
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  
  ```

### Step 3: Instalar as Dependências

Com o ambiente virtual ativado, execute:

```
pip install -r requirements.txt

```

### Step 4: Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz da pasta `backend` com base no arquivo de exemplo (`.env.example`):

```
cp .env.example .env

```

*Edite o arquivo `.env` ajustando a chave secreta JWT e parâmetros de banco de dados conforme necessário.*

### Step 5: Executar o Servidor de Desenvolvimento

Para iniciar o servidor FastAPI com recarregamento automático (*hot-reload*):

```
uvicorn app.main:app --reload

```

A API estará disponível no seu navegador ou cliente HTTP em: **`http://127.0.0.1:8000`**

## 📌 Próximos Passos no Desenvolvimento

* \[ \] Modelagem final dos módulos de Treinos e Exercícios.

* \[ \] Implementação do módulo de presenças e aulas coletivas.

* \[ \] Implementação dos módulos de avaliação

* \[ \] Desenvolvimento dos endpoints para monitoramento de execução de treino do aluno.

* \[ \] Implantação da API e do Banco de dados.