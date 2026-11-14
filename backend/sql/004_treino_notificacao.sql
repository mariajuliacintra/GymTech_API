-- Coluna que controla se o lembrete por e-mail de treino próximo já foi enviado ao aluno.
-- Rode UMA vez no banco gymtech existente:
ALTER TABLE treino
    ADD COLUMN notificado TINYINT(1) NOT NULL DEFAULT 0;
