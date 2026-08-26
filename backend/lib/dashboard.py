import calendar
import os
from datetime import date

from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client
from lib.cache import cached

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_PRINCIPAL = os.environ.get("BIGQUERY_TABLE", "base_consolidada")
DATE_COLUMN = os.environ.get("BIGQUERY_DATE_COLUMN", "data_pagamento")


def expandir_intervalo_meses(mes_inicio, mes_fim):
    """Expande um intervalo De/Até (ex: '2026-05' até '2026-07') na lista
    de meses correspondente: ['2026-05', '2026-06', '2026-07']. Se vierem
    invertidos, troca automaticamente."""
    ano_i, mes_i = (int(p) for p in mes_inicio.split("-"))
    ano_f, mes_f = (int(p) for p in mes_fim.split("-"))

    if (ano_i, mes_i) > (ano_f, mes_f):
        ano_i, mes_i, ano_f, mes_f = ano_f, mes_f, ano_i, mes_i

    meses = []
    ano, mes = ano_i, mes_i
    while (ano, mes) <= (ano_f, mes_f):
        meses.append(f"{ano:04d}-{mes:02d}")
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return meses


def mes_atual():
    return date.today().strftime("%Y-%m")


@cached()
def projecao_mes_atual(banco):
    """Projeção simples de fim de mês (run-rate): pega a produção líquida
    acumulada no mês corrente e extrapola pela proporção de dias já
    passados vs. dias totais do mês. Sempre usa o mês atual (não os meses
    do filtro do gráfico), pois é o que costuma fazer sentido operacionalmente."""
    hoje = date.today()
    dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    dias_passados = hoje.day

    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT SUM(vlr_liquido) AS total
        FROM {tabela}
        WHERE FORMAT_DATE('%Y-%m', {DATE_COLUMN}) = @mes
          AND (@banco IS NULL OR UPPER(banco) = @banco)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("mes", "STRING", mes_atual()),
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())
    producao_mtd = float(rows[0]["total"] or 0) if rows else 0.0

    if dias_passados == 0:
        return producao_mtd
    return producao_mtd / dias_passados * dias_no_mes


@cached()
def listar_meses_disponiveis(limite=24):
    """Meses com dados na tabela (para popular o seletor), mais recentes
    primeiro. Garante que o mês atual sempre apareça na lista, mesmo que
    ainda não tenha dados."""
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT DISTINCT FORMAT_DATE('%Y-%m', {DATE_COLUMN}) AS mes
        FROM {tabela}
        WHERE {DATE_COLUMN} IS NOT NULL
        ORDER BY mes DESC
        LIMIT @limite
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("limite", "INT64", limite)]
    )
    rows = client.query(query, job_config=job_config).result()
    meses = {row["mes"] for row in rows if row["mes"]}
    meses.add(mes_atual())
    return sorted(meses, reverse=True)


@cached()
def resumo_por_dia(banco, meses):
    """Soma de vlr_liquido por dia, dentro dos meses selecionados — para o
    gráfico (granularidade diária)."""
    if not meses:
        return []

    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT FORMAT_DATE('%Y-%m-%d', {DATE_COLUMN}) AS dia, SUM(vlr_liquido) AS total
        FROM {tabela}
        WHERE FORMAT_DATE('%Y-%m', {DATE_COLUMN}) IN UNNEST(@meses)
          AND (@banco IS NULL OR UPPER(banco) = @banco)
        GROUP BY dia
        ORDER BY dia
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("meses", "STRING", meses),
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [{"dia": row["dia"], "total": float(row["total"] or 0)} for row in rows]


def resumo_por_mes(banco, meses):
    """Soma de vlr_liquido por mês, para o gráfico."""
    if not meses:
        return []

    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT FORMAT_DATE('%Y-%m', {DATE_COLUMN}) AS mes, SUM(vlr_liquido) AS total
        FROM {tabela}
        WHERE FORMAT_DATE('%Y-%m', {DATE_COLUMN}) IN UNNEST(@meses)
          AND (@banco IS NULL OR UPPER(banco) = @banco)
        GROUP BY mes
        ORDER BY mes
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("meses", "STRING", meses),
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [{"mes": row["mes"], "total": float(row["total"] or 0)} for row in rows]


@cached()
def resumo_hierarquico(banco, meses):
    """Soma de vlr_liquido agrupada em banco -> convênio -> produto, para a
    tabela expansível (accordion) abaixo do gráfico."""
    if not meses:
        return []

    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT
          banco,
          IFNULL(convenio, '(sem convênio)') AS convenio,
          IFNULL(produto, '(sem produto)') AS produto,
          SUM(vlr_liquido) AS producao
        FROM {tabela}
        WHERE FORMAT_DATE('%Y-%m', {DATE_COLUMN}) IN UNNEST(@meses)
          AND (@banco IS NULL OR UPPER(banco) = @banco)
        GROUP BY banco, convenio, produto
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("meses", "STRING", meses),
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())

    arvore = {}
    for row in rows:
        b = row["banco"] or "(sem banco)"
        c = row["convenio"]
        p = row["produto"]
        v = float(row["producao"] or 0)

        banco_node = arvore.setdefault(b, {"total": 0.0, "convenios": {}})
        banco_node["total"] += v

        conv_node = banco_node["convenios"].setdefault(c, {"total": 0.0, "produtos": {}})
        conv_node["total"] += v
        conv_node["produtos"][p] = conv_node["produtos"].get(p, 0.0) + v

    resultado = []
    for banco_nome, banco_dado in sorted(arvore.items(), key=lambda kv: -kv[1]["total"]):
        convenios = []
        for conv_nome, conv_dado in sorted(banco_dado["convenios"].items(), key=lambda kv: -kv[1]["total"]):
            produtos = sorted(
                ({"nome": nome, "total": total} for nome, total in conv_dado["produtos"].items()),
                key=lambda p: -p["total"],
            )
            convenios.append({"nome": conv_nome, "total": conv_dado["total"], "produtos": produtos})
        resultado.append({"nome": banco_nome, "total": banco_dado["total"], "convenios": convenios})

    return resultado


def detalhamento_indicados(banco, meses):
    """Produção detalhada por Banco | Indicado (map_indicado) | Convênio |
    Produto — pra tela de Indicados. 'map_indicado' é a coluna de
    tratamento calculada em Manutenção → Cruzar dados (ainda vazia pra
    quem não foi cruzado ainda; aparece como '(sem indicado)')."""
    if not meses:
        return []

    from lib.manutencao import garantir_colunas_map
    garantir_colunas_map()

    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT
          banco,
          IFNULL(map_indicado, '(sem indicado)') AS indicado,
          IFNULL(convenio, '(sem convênio)') AS convenio,
          IFNULL(produto, '(sem produto)') AS produto,
          SUM(vlr_liquido) AS producao
        FROM {tabela}
        WHERE FORMAT_DATE('%Y-%m', {DATE_COLUMN}) IN UNNEST(@meses)
          AND (@banco IS NULL OR UPPER(banco) = @banco)
        GROUP BY banco, indicado, convenio, produto
        ORDER BY producao DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("meses", "STRING", meses),
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [
        {
            "banco": row["banco"],
            "indicado": row["indicado"],
            "convenio": row["convenio"],
            "produto": row["produto"],
            "producao": float(row["producao"] or 0),
        }
        for row in rows
    ]
