"""
Segurança: senhas (hash) e tokens de login (JWT).

SENHA: nunca guardamos a senha em texto puro, apenas o "hash" dela.
O hash é uma versão embaralhada que não dá para desfazer; para conferir
um login, comparamos a senha digitada com o hash guardado.

TOKEN (JWT): depois de logar, a pessoa recebe um token assinado com a
SECRET_KEY. Ela o envia em cada requisição e a API confere a assinatura
e a validade, sem precisar pedir a senha de novo.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import NaoAutenticadoError

# Valores do campo "tipo" dentro do token (quem está logado).
TIPO_TOKEN_ACADEMIA = "academia"


# ------------------------------------------------------------------ senha
def gerar_hash_senha(senha: str) -> str:
    """Transforma a senha em um hash bcrypt (60 caracteres, cabe no VARCHAR(255))."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere se a senha digitada corresponde ao hash guardado."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        # Hash inválido (ex.: senha antiga salva em texto puro) ou senha
        # grande demais para o bcrypt: tratamos como "senha não confere".
        return False


# ------------------------------------------------------------------ token
def criar_token_acesso(sub: str, tipo: str) -> tuple[str, int]:
    """
    Cria o token de login.
    sub:  identificador de quem logou (id), sempre como texto.
    tipo: quem é (ex.: "academia").
    Devolve (token, segundos_até_expirar).
    """
    agora = datetime.now(timezone.utc)
    expira = agora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "tipo": tipo, "iat": agora, "exp": expira}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def decodificar_token(token: str) -> dict:
    """Confere assinatura e validade do token e devolve o seu conteúdo."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "tipo"]},
        )
    except jwt.PyJWTError as exc:
        raise NaoAutenticadoError("Token inválido ou expirado.") from exc
