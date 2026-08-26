import logging
import threading

log = logging.getLogger(__name__)

_thread_iniciada = False
_lock = threading.Lock()


def _aquecer_uma_vez():
    """Roda as mesmas consultas que cada página faria com os filtros
    padrão (sem filtro nenhum, mês atual), pra deixar o cache já quente
    antes de alguém clicar na página. Sem TTL — isso roda só uma vez,
    quando o processo sobe; depois disso, só é refeito se alguém escrever
    algo (que limpa o cache) ou clicar em "Atualizar agora" numa tela."""
    from lib.dashboard import (
        listar_meses_disponiveis,
        resumo_por_dia,
        resumo_hierarquico,
        mes_atual,
        projecao_mes_atual,
    )
    from lib.visualizacao import listar_registros
    from lib.logs import listar_logs
    from lib.indicados import listar_indicados
    from lib.mapeamento import listar_mapeamento

    try:
        atual = mes_atual()
        listar_meses_disponiveis()
        resumo_por_dia(None, [atual])
        resumo_hierarquico(None, [atual])
        projecao_mes_atual(None)
    except Exception:
        log.exception("Falha ao aquecer cache do dashboard")

    try:
        listar_mapeamento()
    except Exception:
        log.exception("Falha ao aquecer cache de Parâmetros/mapeamento")

    try:
        listar_registros(banco=None, ade=None, limite=50, offset=0)
    except Exception:
        log.exception("Falha ao aquecer cache de Visualizar")

    try:
        listar_logs(busca=None)
    except Exception:
        log.exception("Falha ao aquecer cache de Logs")

    try:
        listar_indicados(busca=None)
    except Exception:
        log.exception("Falha ao aquecer cache de Indicados")


def iniciar_aquecimento_em_background():
    """Inicia (uma única vez por processo) uma thread que roda o
    aquecimento UMA VEZ, em paralelo, sem travar a subida do servidor."""
    global _thread_iniciada
    with _lock:
        if _thread_iniciada:
            return
        _thread_iniciada = True

    thread = threading.Thread(target=_aquecer_uma_vez, daemon=True, name="cache-warmup")
    thread.start()
