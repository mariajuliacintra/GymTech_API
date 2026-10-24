# Verificação por e-mail (guia para o front)

A pessoa prova quem é com um **código de 6 dígitos** enviado ao e-mail da conta.
Em todas as rotas abaixo o código vai assim:

```json
"verificacao": { "codigo": "123456" }
```

## Esqueci a senha (academia, aluno ou profissional)
1. `POST /auth/{perfil}/esqueci-senha`  com `{"email": "..."}`
   (`perfil` = `academia`, `aluno` ou `profissional`).
   A resposta é **sempre a mesma**, exista a conta ou não.
2. `POST /auth/{perfil}/redefinir-senha` com
   `{"email": "...", "nova_senha": "...", "verificacao": {"codigo": "123456"}}`

## Alterar os próprios dados (aluno ou profissional logado)
1. `POST /usuarios/me/codigo-email` (sem corpo) — envia o código ao e-mail cadastrado.
2. `PATCH /alunos/me` ou `PATCH /profissionais/me` com os campos a mudar + `verificacao`.

Só os campos enviados mudam. Editáveis: `nome`, `email`, `telefone` (`null` remove),
`data_nascimento` · aluno: `modalidade_treino`, `objetivo` ·
profissional: `especialidade`, `registro_profissional`.
Qualquer outro campo (cpf, senha, status...) dá 422. A academia não altera dados de usuários.

## Regras do código
- vale 10 minutos e só pode ser usado uma vez;
- só o último código pedido vale;
- 60 segundos entre um pedido e outro (resposta 429 com `Retry-After`);
- 5 erros invalidam o código e bloqueiam novos pedidos por 15 minutos;
- erro de regra (ex.: e-mail já em uso) **não** gasta o código: a pessoa corrige e reenvia.

## Configurar o e-mail (Gmail)
1. Na conta do projeto, ligue a **Verificação em duas etapas**
   (myaccount.google.com/security). Sem isso a "senha de app" não aparece.
2. Crie uma **senha de app** em myaccount.google.com/apppasswords (16 letras, sem espaços).
3. Preencha no `.env` (modelo no `.env.example`): `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`,
   `SMTP_USER`, `SMTP_PASSWORD` (a senha de app) e `SMTP_FROM`.

Limite do Gmail: cerca de 500 destinatários por dia em conta pessoal.
No desenvolvimento, deixe `SMTP_HOST` vazio com `DEBUG=true`: o e-mail (com o código)
aparece no terminal, sem enviar nada.

Para trocar de provedor no futuro (Resend, Brevo, Amazon SES...), basta mudar essas
variáveis do `.env`: o código não muda. Eles exigem um domínio próprio verificado.
