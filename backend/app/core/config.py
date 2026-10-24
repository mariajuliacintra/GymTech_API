"""
Configurações da aplicação.

Lê as variáveis do arquivo .env (que fica na pasta backend/) e as
disponibiliza em um único objeto: `settings`.
Assim, nenhuma senha ou dado sensível fica escrito dentro do código.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/core/config.py  ->  sobe 3 níveis até a pasta "backend"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    APP_NAME: str = "GYMtech API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "gymtech")

    # JWT (login). A SECRET_KEY assina os tokens: quem a conhece consegue
    # forjar um login, por isso ela NÃO tem valor padrão e fica só no .env.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Limite de tentativas de login erradas (vale para academia, aluno e profissional).
    LOGIN_MAX_TENTATIVAS: int = int(os.getenv("LOGIN_MAX_TENTATIVAS", "5"))
    LOGIN_BLOQUEIO_MINUTOS: int = int(os.getenv("LOGIN_BLOQUEIO_MINUTOS", "15"))

    # Códigos de verificação enviados por e-mail (esqueci a senha / confirmar alterações).
    CODIGO_TTL_MINUTOS: int = int(os.getenv("CODIGO_TTL_MINUTOS", "10"))  # validade do código
    CODIGO_MAX_TENTATIVAS: int = int(os.getenv("CODIGO_MAX_TENTATIVAS", "5"))  # erros até invalidar
    CODIGO_REENVIO_SEGUNDOS: int = int(os.getenv("CODIGO_REENVIO_SEGUNDOS", "60"))  # intervalo entre envios
    CODIGO_BLOQUEIO_MINUTOS: int = int(os.getenv("CODIGO_BLOQUEIO_MINUTOS", "15"))  # espera após errar demais

    # Envio de e-mail (SMTP). Vazio = não configurado (veja services/email_service.py).
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")  # se vazio, usa o SMTP_USER
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


settings = Settings()

if len(settings.SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY ausente ou curta demais no arquivo .env (mínimo 32 caracteres).\n"
        "Gere uma com:  py -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "e coloque no .env assim:  SECRET_KEY=valor_gerado"
    )
