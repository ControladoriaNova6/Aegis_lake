import os

from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client
from lib.cache import cached

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_PRINCIPAL = os.environ.get("BIGQUERY_TABLE", "base_consolidada")

COLUNAS_EXIBICAO = [
    "data_pagamento",
    "banco",
    "ade",
    "convenio",
    "produto",
    "vlr_liquido",
    "vlr_bruto",
    "prazo",
    "usuario",
    "arquivo_origem",
]


@cached()
def listar_registros(banco=None, ade=None, limite=100, offset=0):
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"
    colunas = ", ".join(COLUNAS_EXIBICAO)

    query = f"""
        SELECT {colunas}
        FROM {tabela}
        WHERE (@banco IS NULL OR UPPER(banco) = @banco)
          AND (@ade IS NULL OR ade = @ade)
        ORDER BY data_pagamento DESC
        LIMIT @limite OFFSET @offset
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("banco", "STRING", banco.upper() if banco else None),
            bigquery.ScalarQueryParameter("ade", "STRING", ade or None),
            bigquery.ScalarQueryParameter("limite", "INT64", limite),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]
