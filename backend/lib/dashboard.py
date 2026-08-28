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
    """Produção detalhada por Banco > Indicado > Convênio > Produto, já
    em formato hierárquico (níveis aninhados, cada um com subtotal) —
    pra montar uma "planilha dinâmica" (agrupar/expandir) na tela de
    Indicados. Só entra produção de indicados JÁ CADASTRADOS (linhas sem
    map_indicado ficam de fora por completo — não aparece um grupo
    "sem indicado"). 'map_indicado'/'map_convenio'/'map_produto' são as
    colunas de tratamento calculadas em Manutenção → Cruzar dados."""
    if not meses:
        return []

    linhas = _consultar_producao_por_indicado(banco, meses)
    nomes_por_codigo = _nomes_indicados_por_codigo()

    bancos_map = {}
    for row in linhas:
        banco_nome = row["banco"]
        codigo = row["indicado_codigo"]
        nome_indicado = nomes_por_codigo.get(str(codigo), str(codigo))
        convenio = row["convenio"]
        produto = row["produto"]
        producao = row["producao"]

        banco_node = bancos_map.setdefault(banco_nome, {"nome": banco_nome, "total": 0.0, "indicados": {}})
        banco_node["total"] += producao

        indicado_node = banco_node["indicados"].setdefault(
            codigo, {"nome": nome_indicado, "codigo": codigo, "total": 0.0, "convenios": {}}
        )
        indicado_node["total"] += producao

        convenio_node = indicado_node["convenios"].setdefault(convenio, {"nome": convenio, "total": 0.0, "produtos": []})
        convenio_node["total"] += producao
        convenio_node["produtos"].append({"nome": produto, "total": producao})

    resultado = []
    for banco_node in sorted(bancos_map.values(), key=lambda b: -b["total"]):
        indicados_lista = []
        for indicado_node in sorted(banco_node["indicados"].values(), key=lambda i: -i["total"]):
            convenios_lista = sorted(indicado_node["convenios"].values(), key=lambda c: -c["total"])
            for conv in convenios_lista:
                conv["produtos"].sort(key=lambda p: -p["total"])
            indicados_lista.append({**indicado_node, "convenios": convenios_lista})
        resultado.append({**banco_node, "indicados": indicados_lista})

    return resultado


def detalhamento_indicados_flat(banco, meses):
    """Mesma consulta de detalhamento_indicados, em formato de lista
    plana (uma linha por Banco/Indicado/Convênio/Produto) — usado pra
    gerar a planilha de download."""
    if not meses:
        return []

    linhas = _consultar_producao_por_indicado(banco, meses)
    nomes_por_codigo = _nomes_indicados_por_codigo()

    return [
        {
            "banco": row["banco"],
            "indicado": nomes_por_codigo.get(str(row["indicado_codigo"]), str(row["indicado_codigo"])),
            "convenio": row["convenio"],
            "produto": row["produto"],
            "producao": row["producao"],
        }
        for row in linhas
    ]


def _consultar_producao_por_indicado(banco, meses):
    """Consulta base compartilhada por detalhamento_indicados e
    detalhamento_indicados_flat — só produção de indicados cadastrados
    (map_indicado IS NOT NULL)."""
    from lib.manutencao import garantir_colunas_map
    garantir_colunas_map()

    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    query = f"""
        SELECT
          banco,
          map_indicado AS indicado_codigo,
          IFNULL(map_convenio, '—') AS convenio,
          IFNULL(map_produto, '—') AS produto,
          SUM(vlr_liquido) AS producao
        FROM {tabela}
        WHERE FORMAT_DATE('%Y-%m', {DATE_COLUMN}) IN UNNEST(@meses)
          AND (@banco IS NULL OR UPPER(banco) = @banco)
          AND map_indicado IS NOT NULL
        GROUP BY banco, indicado_codigo, convenio, produto
        ORDER BY banco, indicado_codigo, producao DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("meses", "STRING", meses),
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
        ]
    )
    rows = client.query(query, job_config=job_config).result()

    # "map_indicado IS NOT NULL" só garante que a produção passou pelo
    # cruzamento — mas o código encontrado pode não corresponder a
    # NENHUM indicado que ainda esteja cadastrado (ex: foi excluído
    # depois do cruzamento). Filtra de novo aqui pra garantir que só
    # aparece produção de indicado REALMENTE cadastrado agora.
    codigos_cadastrados = set(_nomes_indicados_por_codigo().keys())

    return [
        {
            "banco": row["banco"],
            "indicado_codigo": row["indicado_codigo"],
            "convenio": row["convenio"],
            "produto": row["produto"],
            "producao": float(row["producao"] or 0),
        }
        for row in rows
        if str(row["indicado_codigo"]) in codigos_cadastrados
    ]


def _nomes_indicados_por_codigo():
    """Código (cod_loja) → nome cadastrado, pra não mostrar só o código
    cru na planilha de detalhamento."""
    from lib.indicados import listar_indicados
    try:
        indicados_cadastrados = listar_indicados()
    except Exception:  # noqa: BLE001
        return {}
    return {
        str(i.get("cod_loja")): (i.get("nome") or i.get("usuario") or str(i.get("cod_loja")))
        for i in indicados_cadastrados if i.get("cod_loja")
    }
