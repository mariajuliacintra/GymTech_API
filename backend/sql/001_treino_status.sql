-- Coluna que permite CANCELAR um treino sem apagá-lo.
-- Rode UMA vez no banco que já tem a tabela treino.
ALTER TABLE treino
    ADD COLUMN status ENUM('Ativo', 'Cancelado') NOT NULL DEFAULT 'Ativo';

-- Para quem for criar a tabela do zero, o script completo ficou assim:
--
-- CREATE TABLE treino (
--     id_treino          INT          NOT NULL AUTO_INCREMENT,
--     fk_id_aluno        INT          NOT NULL,
--     fk_id_profissional INT          NOT NULL,
--     titulo_treino      VARCHAR(100) NOT NULL,
--     data_criacao       DATE         NOT NULL DEFAULT (CURRENT_DATE),
--     data_programada    DATE         NULL,
--     status             ENUM('Ativo', 'Cancelado') NOT NULL DEFAULT 'Ativo',
--
--     CONSTRAINT pk_treino PRIMARY KEY (id_treino),
--     CONSTRAINT fk_treino_aluno
--         FOREIGN KEY (fk_id_aluno) REFERENCES aluno (id_usuario),
--     CONSTRAINT fk_treino_profissional
--         FOREIGN KEY (fk_id_profissional) REFERENCES profissional (id_usuario),
--     CONSTRAINT ck_treino_datas
--         CHECK (data_programada IS NULL OR data_programada >= data_criacao)
-- ) ENGINE=InnoDB;
