"""
Códigos de verificação enviados por e-mail (6 dígitos).

Regras:
  - o código vale CODIGO_TTL_MINUTOS (padrão 10) e só pode ser usado uma vez;
  - só o último código pedido vale (pedir outro invalida o anterior);
  - erros de digitação são contados: ao chegar em CODIGO_MAX_TENTATIVAS (5) o
    código é invalidado E pedir outro fica bloqueado por CODIGO_BLOQUEIO_MINUTOS.
    Sem esse bloqueio, dava para pedir um código novo a cada 5 chutes e
    descobrir os 6 dígitos por tentativa e erro;
  - entre um envio e outro é preciso esperar CODIGO_REENVIO_SEGUNDOS (60),
    para ninguém usar a API para lotar a caixa de entrada de outra pessoa.

O código nunca é guardado em texto puro: só um HMAC dele (com a SECRET_KEY).

ATENÇÃO (igual ao limitador de login): tudo fica na MEMÓRIA do servidor.
Ao reiniciar a API os códigos pendentes se perdem (a pessoa pede outro), e
com vários processos (workers) o código pedido em um não vale no outro.
Para produção com vários workers, troque por Redis ou por uma tabela no banco;
só esta classe precisa mudar.
"""
import hashlib
import hmac
import math
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable, Hashable

from app.core.config import settings
from app.core.exceptions import ReenvioDeCodigoError


@dataclass
class _Codigo:
    hash: str
    expira_em: float
    liberar_novo_em: float  # antes disso, não dá para emitir outro código
    tentativas: int = 0
    valido: bool = True


class ArmazenamentoCodigos:
    def __init__(
        self,
        ttl_segundos: int,
        max_tentativas: int,
        reenvio_segundos: int,
        bloqueio_segundos: int,
        max_entradas: int = 10_000,
        relogio: Callable[[], float] = time.monotonic,
    ):
        self._ttl = ttl_segundos
        self._max = max_tentativas
        self._reenvio = reenvio_segundos
        self._bloqueio = bloqueio_segundos
        self._max_entradas = max_entradas
        self._relogio = relogio
        self._entradas: dict[Hashable, _Codigo] = {}
        self._lock = threading.Lock()  # a API atende várias requisições ao mesmo tempo

    def _hash(self, chave: tuple, codigo: str) -> str:
        mensagem = "|".join(map(str, chave)) + "|" + codigo
        return hmac.new(
            settings.SECRET_KEY.encode(), mensagem.encode(), hashlib.sha256
        ).hexdigest()

    def emitir(self, chave: tuple) -> str:
        """Gera um código novo (invalidando o anterior). Se for cedo demais, levanta ReenvioDeCodigoError."""
        with self._lock:
            agora = self._relogio()
            atual = self._entradas.get(chave)
            if atual is not None and agora < atual.liberar_novo_em:
                raise ReenvioDeCodigoError(math.ceil(atual.liberar_novo_em - agora))

            if len(self._entradas) >= self._max_entradas:
                self._purgar(agora)

            codigo = f"{secrets.randbelow(10**6):06d}"
            self._entradas[chave] = _Codigo(
                hash=self._hash(chave, codigo),
                expira_em=agora + self._ttl,
                liberar_novo_em=agora + self._reenvio,
            )
            return codigo

    def conferir(self, chave: tuple, codigo: str) -> bool:
        """
        True se o código está certo. NÃO o consome (chame consumir() depois que
        a operação der certo: assim um erro de negócio, como e-mail já em uso,
        não obriga a pessoa a pedir outro código). Código errado conta como tentativa.
        """
        with self._lock:
            agora = self._relogio()
            entrada = self._entradas.get(chave)
            if entrada is None or not entrada.valido or agora >= entrada.expira_em:
                return False

            if hmac.compare_digest(entrada.hash, self._hash(chave, codigo)):
                return True

            entrada.tentativas += 1
            if entrada.tentativas >= self._max:
                entrada.valido = False
                entrada.liberar_novo_em = max(entrada.liberar_novo_em, agora + self._bloqueio)
            return False

    def consumir(self, chave: tuple) -> None:
        """Marca o código como usado. A entrada fica, para continuar valendo o intervalo de reenvio."""
        with self._lock:
            entrada = self._entradas.get(chave)
            if entrada is not None:
                entrada.valido = False

    def descartar(self, chave: tuple) -> None:
        """Esquece o código (usado quando o e-mail não pôde ser enviado: nada a esperar)."""
        with self._lock:
            self._entradas.pop(chave, None)

    def _purgar(self, agora: float) -> None:
        """Evita que o dicionário cresça sem limite."""
        for chave in [
            k
            for k, e in self._entradas.items()
            if agora >= e.expira_em and agora >= e.liberar_novo_em
        ]:
            del self._entradas[chave]

        if len(self._entradas) >= self._max_entradas:
            # ainda cheio: descarta os mais antigos que não estão em bloqueio
            candidatas = sorted(
                (k for k, e in self._entradas.items() if agora >= e.liberar_novo_em),
                key=lambda k: self._entradas[k].expira_em,
            )
            for chave in candidatas[: len(self._entradas) - self._max_entradas + 1]:
                del self._entradas[chave]


armazenamento_codigos = ArmazenamentoCodigos(
    ttl_segundos=settings.CODIGO_TTL_MINUTOS * 60,
    max_tentativas=settings.CODIGO_MAX_TENTATIVAS,
    reenvio_segundos=settings.CODIGO_REENVIO_SEGUNDOS,
    bloqueio_segundos=settings.CODIGO_BLOQUEIO_MINUTOS * 60,
)
