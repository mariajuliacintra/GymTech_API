from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _vazio_vira_none(v: Optional[str]) -> Optional[str]:
    return v or None


class AvaliacaoFisicaCreate(BaseModel):
    """
    Criação da ficha (exclusivo do profissional).
    O id do agendamento não vem no corpo, mas na URL: POST /agendamentos/{id}/avaliacao
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    peso: Decimal = Field(gt=0, max_digits=5, decimal_places=2, description="Em kg, ex: 75.50")
    altura: Decimal = Field(gt=0, max_digits=3, decimal_places=2, description="Em metros, ex: 1.75")
    percentual_gordura: Optional[Decimal] = Field(default=None, ge=0, le=100, max_digits=4, decimal_places=2)
    massa_magra: Optional[Decimal] = Field(default=None, ge=0, max_digits=5, decimal_places=2)
    medidas_corporais: Optional[str] = Field(default=None, description="Texto livre (ex: Tórax: 98cm, Cintura: 80cm)")
    observacoes_tecnicas: Optional[str] = None

    _limpar_medidas = field_validator("medidas_corporais")(_vazio_vira_none)
    _limpar_obs = field_validator("observacoes_tecnicas")(_vazio_vira_none)


class AvaliacaoFisicaUpdate(BaseModel):
    """Atualização parcial da ficha (exclusivo do profissional que realizou)."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    peso: Optional[Decimal] = Field(default=None, gt=0, max_digits=5, decimal_places=2)
    altura: Optional[Decimal] = Field(default=None, gt=0, max_digits=3, decimal_places=2)
    percentual_gordura: Optional[Decimal] = Field(default=None, ge=0, le=100, max_digits=4, decimal_places=2)
    massa_magra: Optional[Decimal] = Field(default=None, ge=0, max_digits=5, decimal_places=2)
    medidas_corporais: Optional[str] = None
    observacoes_tecnicas: Optional[str] = None

    _limpar_medidas = field_validator("medidas_corporais")(_vazio_vira_none)
    _limpar_obs = field_validator("observacoes_tecnicas")(_vazio_vira_none)

    @model_validator(mode="after")
    def validar_envio(self) -> "AvaliacaoFisicaUpdate":
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        # Peso e altura não podem ser limpos (são NOT NULL)
        for campo in ("peso", "altura"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


class AvaliacaoFisicaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_avaliacao: int
    fk_id_agendamento_avaliacao: int
    data_avaliacao: date
    peso: float
    altura: float
    percentual_gordura: Optional[float]
    massa_magra: Optional[float]
    medidas_corporais: Optional[str]
    observacoes_tecnicas: Optional[str]

    @classmethod
    def from_orm_model(cls, avaliacao):
        return cls(
            id_avaliacao=avaliacao.id_avaliacao,
            fk_id_agendamento_avaliacao=avaliacao.fk_id_agendamento_avaliacao,
            data_avaliacao=avaliacao.data_avaliacao,
            peso=float(avaliacao.peso),
            altura=float(avaliacao.altura),
            percentual_gordura=float(avaliacao.percentual_gordura) if avaliacao.percentual_gordura is not None else None,
            massa_magra=float(avaliacao.massa_magra) if avaliacao.massa_magra is not None else None,
            medidas_corporais=avaliacao.medidas_corporais,
            observacoes_tecnicas=avaliacao.observacoes_tecnicas,
        )


class AvaliacaoFisicaCadastroResponse(AvaliacaoFisicaResponse):
    mensagem: str = "Avaliação física registrada com sucesso!"


class AvaliacaoFisicaUpdateResponse(AvaliacaoFisicaResponse):
    mensagem: str = "Avaliação física atualizada com sucesso!"


class AvaliacaoFisicaDetalheResponse(AvaliacaoFisicaResponse):
    mensagem: str = "Ficha de avaliação carregada com sucesso!"
