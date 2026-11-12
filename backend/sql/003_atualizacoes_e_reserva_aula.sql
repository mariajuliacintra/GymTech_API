-- Migração incremental para quem já tem o banco gymtech criado anteriormente.
-- 1. Academia: adiciona endereco e telefone
ALTER TABLE academia
    ADD COLUMN endereco VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN telefone CHAR(14)     NOT NULL DEFAULT '';

-- 2. Aluno: remove modalidade_treino
ALTER TABLE aluno
    DROP COLUMN modalidade_treino;

-- 3. Aula: adiciona tipo_aula
ALTER TABLE aula
    ADD COLUMN tipo_aula VARCHAR(100) NOT NULL DEFAULT 'Geral';

-- 4. Reserva de aula (sem UNIQUE fixa para permitir nova reserva após cancelamento)
CREATE TABLE IF NOT EXISTS reserva_aula (
    id_reserva_aula  INT      NOT NULL AUTO_INCREMENT,
    fk_id_aula       INT      NOT NULL,
    fk_id_aluno      INT      NOT NULL,
    data_agendamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status           ENUM('Confirmado','Cancelado') NOT NULL DEFAULT 'Confirmado',

    CONSTRAINT pk_reserva_aula PRIMARY KEY (id_reserva_aula),
    CONSTRAINT fk_reserva_aula_aula
        FOREIGN KEY (fk_id_aula) REFERENCES aula (id_aula),
    CONSTRAINT fk_reserva_aula_aluno
        FOREIGN KEY (fk_id_aluno) REFERENCES aluno (id_usuario)
) ENGINE=InnoDB;
