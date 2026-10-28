"""
Erros de regra de negócio.

Os services levantam estes erros (sem saber nada de HTTP) e o arquivo
core/handlers.py os traduz para a resposta certa (401, 403, 404, 409...).
"""
import math


class NegocioError(Exception):
    """Erro base das regras de negócio."""


class NaoAutenticadoError(NegocioError):
    """Não está logado ou o login/token é inválido (vira HTTP 401)."""


class NaoAutorizadoError(NegocioError):
    """Está logado, mas não tem permissão para isso (vira HTTP 403)."""


class NaoEncontradoError(NegocioError):
    """Algo que deveria existir não foi encontrado (vira HTTP 404)."""


class ConflitoError(NegocioError):
    """Dado em conflito com algo já cadastrado (vira HTTP 409)."""


class TentativasExcedidasError(NegocioError):
    """Muitas tentativas de login erradas; acesso bloqueado por um tempo (vira HTTP 429)."""

    def __init__(self, segundos_restantes: int):
        self.segundos_restantes = max(1, int(segundos_restantes))
        minutos = math.ceil(self.segundos_restantes / 60)
        plural = "minuto" if minutos == 1 else "minutos"
        super().__init__(
            "Muitas tentativas incorretas. Acesso bloqueado temporariamente. "
            f"Tente novamente em {minutos} {plural}."
        )


class VerificacaoInvalidaError(NegocioError):
    """Código/token de verificação inválido, expirado ou esgotado (vira HTTP 400)."""

    def __init__(self, mensagem: str = "Verificação inválida ou expirada. Solicite um novo código."):
        super().__init__(mensagem)


class ReenvioDeCodigoError(NegocioError):
    """Pediu um novo código cedo demais (vira HTTP 429)."""

    def __init__(self, segundos_restantes: int):
        self.segundos_restantes = max(1, int(segundos_restantes))
        super().__init__(
            f"Aguarde {self.segundos_restantes} segundos para solicitar um novo código."
        )


class ServicoIndisponivelError(NegocioError):
    """Serviço externo (e-mail) fora do ar ou não configurado (vira HTTP 503)."""


class DadoInvalidoError(NegocioError):
    """Valor enviado não é aceitável por uma regra que depende do banco (vira HTTP 422)."""
