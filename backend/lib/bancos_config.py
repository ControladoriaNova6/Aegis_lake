import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config_bancos.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as _f:
    CONFIG_BANCOS = json.load(_f)


def opcoes_banco():
    """Lista (chave_config, rótulo amigável) para popular o seletor de bancos,
    ordenada alfabeticamente pelo rótulo."""
    opcoes = []
    for chave, cfg in CONFIG_BANCOS.items():
        rotulo = cfg.get("fixos", {}).get("banco") or chave
        opcoes.append((chave, rotulo))
    return sorted(opcoes, key=lambda x: x[1])


def opcoes_config():
    """(banco_tipo, config_nome) — usado no seletor de CONFIGURAÇÃO de
    importação (tela Importar). Um mesmo banco pode ter mais de uma
    configuração (ex: dois layouts de arquivo diferentes)."""
    from lib.mapeamento import configs_existentes

    try:
        return configs_existentes()
    except Exception:
        return opcoes_banco()


def opcoes_banco_distintos():
    """Nomes de banco (dado real) distintos, para os filtros de Indicados,
    Visualizar, Relatório e Dashboard — diferente de opcoes_config(), que
    lista configurações de importação (podem repetir o mesmo banco)."""
    from lib.mapeamento import bancos_nomes_distintos

    try:
        nomes = bancos_nomes_distintos()
    except Exception:
        nomes = []

    if not nomes:
        nomes = sorted({nome for _, nome in opcoes_banco()})

    return [(nome, nome) for nome in nomes]
