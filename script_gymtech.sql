-- =====================================================================
-- GYMtech - Script de criação do banco de dados (MySQL 8.0.16+)
-- =====================================================================
DROP DATABASE IF EXISTS gymtech;
CREATE DATABASE gymtech CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE gymtech;

-- =====================================================================
-- 1. ACADEMIA
-- =====================================================================
CREATE TABLE academia (
    id_academia        INT          NOT NULL AUTO_INCREMENT,
    nome_academia      VARCHAR(100) NOT NULL,
    email_corporativo  VARCHAR(100) NOT NULL,
    senha_adm          VARCHAR(255) NOT NULL,
    cnpj               CHAR(14)     NOT NULL,

    CONSTRAINT pk_academia PRIMARY KEY (id_academia),
    CONSTRAINT uq_academia_email UNIQUE (email_corporativo),
    CONSTRAINT uq_academia_cnpj  UNIQUE (cnpj)
) ENGINE=InnoDB;

-- =====================================================================
-- 2. USUARIO (supertipo)
-- =====================================================================
CREATE TABLE usuario (
    id_usuario       INT          NOT NULL AUTO_INCREMENT,
    fk_id_academia   INT          NOT NULL,
    nome             VARCHAR(100) NOT NULL,
    cpf              CHAR(11)     NOT NULL,
    email            VARCHAR(100) NOT NULL,
    senha            VARCHAR(255) NOT NULL,
    telefone         CHAR(11)     NULL,
    data_nascimento  DATE         NOT NULL,
    data_cadastro    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status           ENUM('Ativo','Inativo')       NOT NULL DEFAULT 'Ativo',
    tipo_perfil      ENUM('Profissional','Aluno')  NOT NULL,

    CONSTRAINT pk_usuario PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuario_cpf   UNIQUE (cpf),
    CONSTRAINT uq_usuario_email UNIQUE (email),
    -- Chave alternativa que permite às tabelas filhas referenciar
    -- o par (id, tipo_perfil). É ela que garante a exclusividade.
    CONSTRAINT uq_usuario_id_tipo UNIQUE (id_usuario, tipo_perfil),
    CONSTRAINT fk_usuario_academia
        FOREIGN KEY (fk_id_academia) REFERENCES academia (id_academia)
) ENGINE=InnoDB;

-- =====================================================================
-- 3. ALUNO e PROFISSIONAL (subtipos disjuntos)
--    Cada filha repete tipo_perfil com valor fixo e referencia
--    (id_usuario, tipo_perfil) do pai. Como o usuário tem UM único
--    tipo_perfil, ele só consegue existir em UMA das filhas.
-- =====================================================================
CREATE TABLE aluno (
    id_usuario         INT          NOT NULL,
    tipo_perfil        ENUM('Profissional','Aluno') NOT NULL DEFAULT 'Aluno',
    modalidade_treino  VARCHAR(50)  NULL,
    objetivo           VARCHAR(150) NULL,

    CONSTRAINT pk_aluno PRIMARY KEY (id_usuario),
    CONSTRAINT ck_aluno_tipo CHECK (tipo_perfil = 'Aluno'),
    CONSTRAINT fk_aluno_usuario
        FOREIGN KEY (id_usuario, tipo_perfil)
        REFERENCES usuario (id_usuario, tipo_perfil)
) ENGINE=InnoDB;

CREATE TABLE profissional (
    id_usuario             INT          NOT NULL,
    tipo_perfil            ENUM('Profissional','Aluno') NOT NULL DEFAULT 'Profissional',
    especialidade          VARCHAR(100) NULL,
    registro_profissional  VARCHAR(50)  NOT NULL,

    CONSTRAINT pk_profissional PRIMARY KEY (id_usuario),
    CONSTRAINT uq_profissional_registro UNIQUE (registro_profissional),
    CONSTRAINT ck_profissional_tipo CHECK (tipo_perfil = 'Profissional'),
    CONSTRAINT fk_profissional_usuario
        FOREIGN KEY (id_usuario, tipo_perfil)
        REFERENCES usuario (id_usuario, tipo_perfil)
) ENGINE=InnoDB;

-- =====================================================================
-- 4. EXERCICIO
-- =====================================================================
CREATE TABLE exercicio (
    id_exercicio       INT          NOT NULL AUTO_INCREMENT,
    fk_id_academia     INT          NOT NULL,
    nome_exercicio     VARCHAR(100) NOT NULL,
    grupo_muscular     VARCHAR(50)  NOT NULL,
    descricao_execucao TEXT         NULL,

    CONSTRAINT pk_exercicio PRIMARY KEY (id_exercicio),
    CONSTRAINT fk_exercicio_academia
        FOREIGN KEY (fk_id_academia) REFERENCES academia (id_academia)
) ENGINE=InnoDB;

-- =====================================================================
-- 5. TREINO e ITEM_TREINO
--    fk_id_aluno aponta para ALUNO e fk_id_profissional para
--    PROFISSIONAL (e não para usuario), então o tipo de cada papel
--    fica garantido pela própria estrutura.
-- =====================================================================
CREATE TABLE treino (
    id_treino          INT          NOT NULL AUTO_INCREMENT,
    fk_id_aluno        INT          NOT NULL,
    fk_id_profissional INT          NOT NULL,
    titulo_treino      VARCHAR(100) NOT NULL,
    data_criacao       DATE         NOT NULL DEFAULT (CURRENT_DATE),
    data_programada    DATE         NULL,

    CONSTRAINT pk_treino PRIMARY KEY (id_treino),
    CONSTRAINT fk_treino_aluno
        FOREIGN KEY (fk_id_aluno) REFERENCES aluno (id_usuario),
    CONSTRAINT fk_treino_profissional
        FOREIGN KEY (fk_id_profissional) REFERENCES profissional (id_usuario),
    CONSTRAINT ck_treino_datas
        CHECK (data_programada IS NULL OR data_programada >= data_criacao)
) ENGINE=InnoDB;

CREATE TABLE item_treino (
    id_item_treino  INT           NOT NULL AUTO_INCREMENT,
    fk_id_treino    INT           NOT NULL,
    fk_id_exercicio INT           NOT NULL,
    series          INT           NOT NULL,
    repeticoes      INT           NOT NULL,
    carga_sugerida  DECIMAL(6,2)  NULL,
    tempo_descanso  TIME          NULL,

    CONSTRAINT pk_item_treino PRIMARY KEY (id_item_treino),
    CONSTRAINT fk_item_treino_treino
        FOREIGN KEY (fk_id_treino) REFERENCES treino (id_treino)
        ON DELETE CASCADE,
    CONSTRAINT fk_item_treino_exercicio
        FOREIGN KEY (fk_id_exercicio) REFERENCES exercicio (id_exercicio),
    CONSTRAINT ck_item_series     CHECK (series > 0),
    CONSTRAINT ck_item_repeticoes CHECK (repeticoes > 0),
    CONSTRAINT ck_item_carga      CHECK (carga_sugerida IS NULL OR carga_sugerida >= 0)
) ENGINE=InnoDB;

-- =====================================================================
-- 6. AULA e RESERVA_AULA
-- =====================================================================
CREATE TABLE aula (
    id_aula            INT          NOT NULL AUTO_INCREMENT,
    fk_id_academia     INT          NOT NULL,
    fk_id_profissional INT          NOT NULL,
    nome_aula          VARCHAR(100) NOT NULL,
    data_horario       DATETIME     NOT NULL,
    capacidade_maxima  INT          NOT NULL,

    CONSTRAINT pk_aula PRIMARY KEY (id_aula),
    CONSTRAINT fk_aula_academia
        FOREIGN KEY (fk_id_academia) REFERENCES academia (id_academia),
    CONSTRAINT fk_aula_profissional
        FOREIGN KEY (fk_id_profissional) REFERENCES profissional (id_usuario),
    CONSTRAINT ck_aula_capacidade CHECK (capacidade_maxima > 0)
) ENGINE=InnoDB;

CREATE TABLE reserva_aula (
    id_reserva_aula  INT      NOT NULL AUTO_INCREMENT,
    fk_id_aula       INT      NOT NULL,
    fk_id_aluno      INT      NOT NULL,
    data_agendamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status           ENUM('Confirmado','Cancelado') NOT NULL DEFAULT 'Confirmado',

    CONSTRAINT pk_reserva_aula PRIMARY KEY (id_reserva_aula),
    -- um aluno não reserva a mesma aula duas vezes
    CONSTRAINT uq_reserva_aula_aluno UNIQUE (fk_id_aula, fk_id_aluno),
    CONSTRAINT fk_reserva_aula_aula
        FOREIGN KEY (fk_id_aula) REFERENCES aula (id_aula),
    CONSTRAINT fk_reserva_aula_aluno
        FOREIGN KEY (fk_id_aluno) REFERENCES aluno (id_usuario)
) ENGINE=InnoDB;

-- =====================================================================
-- 7. AGENDAMENTO_AVALIACAO e AVALIACAO_FISICA
-- =====================================================================
CREATE TABLE agendamento_avaliacao (
    id_agendamento_avaliacao INT      NOT NULL AUTO_INCREMENT,
    fk_id_aluno              INT      NOT NULL,
    fk_id_profissional       INT      NOT NULL,
    data_horario             DATETIME NOT NULL,
    status                   ENUM('Agendado','Realizado','Cancelado') NOT NULL DEFAULT 'Agendado',

    CONSTRAINT pk_agendamento_avaliacao PRIMARY KEY (id_agendamento_avaliacao),
    CONSTRAINT fk_agend_aluno
        FOREIGN KEY (fk_id_aluno) REFERENCES aluno (id_usuario),
    CONSTRAINT fk_agend_profissional
        FOREIGN KEY (fk_id_profissional) REFERENCES profissional (id_usuario)
) ENGINE=InnoDB;

CREATE TABLE avaliacao_fisica (
    id_avaliacao                INT           NOT NULL AUTO_INCREMENT,
    fk_id_agendamento_avaliacao INT           NOT NULL,
    data_avaliacao              DATE          NOT NULL,
    peso                        DECIMAL(5,2)  NOT NULL,
    altura                      DECIMAL(3,2)  NOT NULL,
    percentual_gordura          DECIMAL(4,2)  NULL,
    massa_magra                 DECIMAL(5,2)  NULL,
    medidas_corporais           TEXT          NULL,
    observacoes_tecnicas        TEXT          NULL,

    CONSTRAINT pk_avaliacao_fisica PRIMARY KEY (id_avaliacao),
    -- relação 1:1 com o agendamento
    CONSTRAINT uq_avaliacao_agendamento UNIQUE (fk_id_agendamento_avaliacao),
    CONSTRAINT fk_avaliacao_agendamento
        FOREIGN KEY (fk_id_agendamento_avaliacao)
        REFERENCES agendamento_avaliacao (id_agendamento_avaliacao),
    CONSTRAINT ck_avaliacao_peso   CHECK (peso > 0),
    CONSTRAINT ck_avaliacao_altura CHECK (altura > 0),
    CONSTRAINT ck_avaliacao_gordura
        CHECK (percentual_gordura IS NULL OR percentual_gordura BETWEEN 0 AND 100)
) ENGINE=InnoDB;



-- AINDA NÃO REALIZADO !!!!!!!
-- =====================================================================
-- 8. TOTALIDADE DA GENERALIZAÇÃO
--    O MySQL não tem constraints deferidas, então o cadastro do
--    usuário + subtipo é feito em transação por procedures.
--    Use SEMPRE estas procedures para cadastrar usuários.
-- =====================================================================
DELIMITER $$

CREATE PROCEDURE sp_cadastrar_aluno (
    IN  p_fk_id_academia  INT,
    IN  p_nome            VARCHAR(100),
    IN  p_cpf             CHAR(11),
    IN  p_email           VARCHAR(100),
    IN  p_senha           VARCHAR(255),
    IN  p_telefone        CHAR(11),
    IN  p_data_nascimento DATE,
    IN  p_modalidade      VARCHAR(50),
    IN  p_objetivo        VARCHAR(150),
    OUT p_id_usuario      INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
        INSERT INTO usuario (fk_id_academia, nome, cpf, email, senha,
                             telefone, data_nascimento, tipo_perfil)
        VALUES (p_fk_id_academia, p_nome, p_cpf, p_email, p_senha,
                p_telefone, p_data_nascimento, 'Aluno');

        SET p_id_usuario = LAST_INSERT_ID();

        INSERT INTO aluno (id_usuario, modalidade_treino, objetivo)
        VALUES (p_id_usuario, p_modalidade, p_objetivo);
    COMMIT;
END$$

CREATE PROCEDURE sp_cadastrar_profissional (
    IN  p_fk_id_academia  INT,
    IN  p_nome            VARCHAR(100),
    IN  p_cpf             CHAR(11),
    IN  p_email           VARCHAR(100),
    IN  p_senha           VARCHAR(255),
    IN  p_telefone        CHAR(11),
    IN  p_data_nascimento DATE,
    IN  p_especialidade   VARCHAR(100),
    IN  p_registro        VARCHAR(50),
    OUT p_id_usuario      INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
        INSERT INTO usuario (fk_id_academia, nome, cpf, email, senha,
                             telefone, data_nascimento, tipo_perfil)
        VALUES (p_fk_id_academia, p_nome, p_cpf, p_email, p_senha,
                p_telefone, p_data_nascimento, 'Profissional');

        SET p_id_usuario = LAST_INSERT_ID();

        INSERT INTO profissional (id_usuario, especialidade, registro_profissional)
        VALUES (p_id_usuario, p_especialidade, p_registro);
    COMMIT;
END$$

DELIMITER ;

-- =====================================================================
-- Exemplo de uso:
-- INSERT INTO academia (nome_academia, email_corporativo, senha_adm, cnpj)
-- VALUES ('GYMtech Centro', 'contato@gymtech.com', 'hash', '12345678000199');
--
-- CALL sp_cadastrar_aluno(1, 'Maria Silva', '12345678901', 'maria@email.com',
--      'hash', '16999999999', '2000-05-10', 'Musculação', 'Hipertrofia', @id);
-- =====================================================================