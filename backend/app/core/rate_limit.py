"""
Limite de tentativas de login.

Regra: a cada conta (academia, ou usuário aluno/profissional) são permitidas
no máximo 5 tentativas seguidas. Na 5ª tentativa errada, a conta fica
bloqueada por 15 minutos (valores configuráveis no .env). Um login correto
zera a contagem. E-mails que não existem também são contados, assim a
resposta é igual para e-mail existente e inexistente.

ATENÇÃO: as contagens ficam na MEMÓRIA do servidor. Ao reiniciar a API
tudo é zerado, e se houver vários processos (workers) cada um conta
separado. Para produção, o ideal é guardar isso no Redis ou no banco.
"""
import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Hashable, Optional

from app.core.config import settings
from app.core.exceptions import TentativasExcedidasError


@dataclass
class _Entrada:
    tentativas: int
    ultima: float
    bloqueado_ate: Optional[float] = None


class LimitadorTentativas:
    def __init__(
        self,
        max_tentativas: int,
        bloqueio_segundos: int,
        max_entradas: int = 10_000,
        relogio: Callable[[], float] = time.monotonic,
    ):
        if max_tentativas < 1:
            raise ValueError("max_tentativas deve ser pelo menos 1")
        self._max = max_tentativas
        self._bloqueio = bloqueio_segundos
        self._max_entradas = max_entradas
        self._relogio = relogio
        self._entradas: dict[Hashable, _Entrada] = {}
        self._lock = threading.Lock()  # a API atende várias requisições ao mesmo tempo

    def iniciar_tentativa(self, chave: Hashable) -> None:
        """
        Chamar ANTES de conferir a senha. Se a chave está bloqueada, levanta
        TentativasExcedidasError. Senão, conta esta tentativa; ao contar a
        última permitida, já deixa o bloqueio armado (assim requisições
        simultâneas não furam o limite). Um login correto chama limpar().
        """
        with self._lock:
            agora = self._relogio()
            entrada = self._entradas.get(chave)

            if entrada is not None:
                if entrada.bloqueado_ate is not None:
                    if agora < entrada.bloqueado_ate:
                        raise TentativasExcedidasError(math.ceil(entrada.bloqueado_ate - agora))
                    entrada = None  # o bloqueio terminou: recomeça do zero
                elif agora - entrada.ultima >= self._bloqueio:
                    entrada = None  # muito tempo sem errar: recomeça do zero

            if entrada is None:
                if len(self._entradas) >= self._max_entradas:
                    self._purgar(agora)
                entrada = _Entrada(tentativas=0, ultima=agora)
                self._entradas[chave] = entrada

            entrada.tentativas += 1
            entrada.ultima = agora
            if entrada.tentativas >= self._max:
                entrada.bloqueado_ate = agora + self._bloqueio

    def tentativas_restantes(self, chave: Hashable) -> int:
        with self._lock:
            entrada = self._entradas.get(chave)
            usadas = entrada.tentativas if entrada else 0
            return max(0, self._max - usadas)

    def segundos_de_bloqueio(self, chave: Hashable) -> int:
        with self._lock:
            entrada = self._entradas.get(chave)
            if entrada is None or entrada.bloqueado_ate is None:
                return 0
            return max(1, math.ceil(entrada.bloqueado_ate - self._relogio()))

    def limpar(self, chave: Hashable) -> None:
        """Login correto: zera a contagem."""
        with self._lock:
            self._entradas.pop(chave, None)

    def _purgar(self, agora: float) -> None:
        """Evita que o dicionário cresça sem limite (ex.: milhões de e-mails inventados)."""
        for chave in [
            k
            for k, e in self._entradas.items()
            if (e.bloqueado_ate is not None and agora >= e.bloqueado_ate)
            or (e.bloqueado_ate is None and agora - e.ultima >= self._bloqueio)
        ]:
            del self._entradas[chave]

        if len(self._entradas) >= self._max_entradas:
            # ainda cheio: descarta as mais antigas entre as que NÃO estão bloqueadas
            candidatas = sorted(
                (k for k, e in self._entradas.items() if e.bloqueado_ate is None),
                key=lambda k: self._entradas[k].ultima,
            )
            for chave in candidatas[: len(self._entradas) - self._max_entradas + 1]:
                del self._entradas[chave]


limitador_login = LimitadorTentativas(
    max_tentativas=settings.LOGIN_MAX_TENTATIVAS,
    bloqueio_segundos=settings.LOGIN_BLOQUEIO_MINUTOS * 60,
)
