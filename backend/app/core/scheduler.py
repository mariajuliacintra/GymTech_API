"""
Agendador diário de tarefas em segundo plano (APScheduler).

Roda dentro do próprio processo da API (iniciado e encerrado pelo `lifespan`
do FastAPI em `app/main.py`).

Por padrão, dispara todos os dias às 08:00 (no fuso da academia, `settings.TIMEZONE`)
a verificação de treinos próximos para envio de lembrete por e-mail aos alunos.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.tempo import FUSO
from app.services.notificacao_service import executar_rotina_diaria_treinos

logger = logging.getLogger("gymtech.scheduler")

_scheduler: Optional[BackgroundScheduler] = None


def iniciar_agendador() -> None:
    """Inicia o agendador diário caso `NOTIFICACAO_TREINO_ATIVO=true`."""
    global _scheduler

    if not settings.NOTIFICACAO_TREINO_ATIVO:
        logger.info("Agendador diário de notificações desativado (NOTIFICACAO_TREINO_ATIVO=false).")
        return

    if _scheduler is not None and _scheduler.running:
        return

    scheduler = BackgroundScheduler(timezone=FUSO)
    gatilho = CronTrigger(
        hour=settings.NOTIFICACAO_TREINO_HORA,
        minute=settings.NOTIFICACAO_TREINO_MINUTO,
        timezone=FUSO,
    )
    scheduler.add_job(
        executar_rotina_diaria_treinos,
        trigger=gatilho,
        id="notificar_treinos_proximos",
        name="Notificar alunos sobre treinos próximos",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Agendador diário iniciado: lembretes de treino todos os dias às %02d:%02d (%s), "
        "com %d dia(s) de antecedência.",
        settings.NOTIFICACAO_TREINO_HORA,
        settings.NOTIFICACAO_TREINO_MINUTO,
        settings.TIMEZONE,
        settings.NOTIFICACAO_TREINO_DIAS_ANTECEDENCIA,
    )


def encerrar_agendador() -> None:
    """Encerra o agendador de forma limpa ao desligar a API."""
    global _scheduler
    if _scheduler is not None:
        if _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("Agendador diário encerrado.")
        _scheduler = None
