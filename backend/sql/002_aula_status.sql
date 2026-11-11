-- Coluna que permite CANCELAR uma aula sem apagá-la.
-- Rode UMA vez no banco que já tem a tabela aula.
ALTER TABLE aula
    ADD COLUMN status ENUM('Ativa', 'Cancelada') NOT NULL DEFAULT 'Ativa';

-- Para quem for criar a tabela do zero, o script completo ficou assim:
--
-- CREATE TABLE aula (
--     id_aula            INT          NOT NULL AUTO_INCREMENT,
--     fk_id_academia     INT          NOT NULL,
--     fk_id_profissional INT          NOT NULL,
--     nome_aula          VARCHAR(100) NOT NULL,
--     data_horario       DATETIME     NOT NULL,
--     capacidade_maxima  INT          NOT NULL,
--     status             ENUM('Ativa', 'Cancelada') NOT NULL DEFAULT 'Ativa',
--
--     CONSTRAINT pk_aula PRIMARY KEY (id_aula),
--     CONSTRAINT fk_aula_academia
--         FOREIGN KEY (fk_id_academia) REFERENCES academia (id_academia),
--     CONSTRAINT fk_aula_profissional
--         FOREIGN KEY (fk_id_profissional) REFERENCES profissional (id_usuario),
--     CONSTRAINT ck_aula_capacidade CHECK (capacidade_maxima > 0)
-- ) ENGINE=InnoDB;
