import os
import threading

from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_LOGS = os.environ.get("BIGQUERY_LOGS_TABLE", "import_logs")

LOGS_SCHEMA = [
    bigquery.SchemaField("log_id", "STRING"),
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
    bigquery.SchemaField("banco_tipo", "STRING"),
    bigquery.SchemaField("banco_nome", "STRING"),
    bigquery.SchemaField("arquivo_nome", "STRING"),
    bigquery.SchemaField("arquivo_original", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("total_linhas_arquivo", "INT64"),
    bigquery.SchemaField("linhas_inseridas", "INT64"),
    bigquery.SchemaField("linhas_duplicadas_ignoradas", "INT64"),
    bigquery.SchemaField("mensagem_erro", "STRING"),
    bigquery.SchemaField("importado_por", "STRING"),
    bigquery.SchemaField("excluido_por", "STRING"),
    bigquery.SchemaField("excluido_em", "TIMESTAMP"),
]

_tabela_garantida = False
_tabela_lock = threading.Lock()


def garantir_tabela_logs():
    """Confere/cria o dataset e a tabela — só de verdade UMA VEZ por
    processo, pra não repetir essas chamadas de setup em toda consulta."""
    global _tabela_garantida
    if _tabela_garantida:
        return

    with _tabela_lock:
        if _tabela_garantida:
            return

        client = get_bigquery_client()
        dataset_id = f"{PROJECT}.{DATASET}"
        client.create_dataset(dataset_id, exists_ok=True)

        table_id = f"{PROJECT}.{DATASET}.{TABELA_LOGS}"
        table = bigquery.Table(table_id, schema=LOGS_SCHEMA)
        client.create_table(table, exists_ok=True)

        _migrar_schema_se_necessario(client, table_id)

        _tabela_garantida = True


def _migrar_schema_se_necessario(client, table_id):
    """Se a tabela já existia de antes dos campos de auditoria existirem,
    adiciona as colunas via ALTER TABLE (DDL, funciona mesmo sem billing)."""
    tabela = client.get_table(table_id)
    colunas_atuais = {campo.name for campo in tabela.schema}
    campos_novos = [
        campo for campo in LOGS_SCHEMA
        if campo.name not in colunas_atuais
    ]
    if not campos_novos:
        return

    tabela.schema = list(tabela.schema) + campos_novos
    client.update_table(tabela, ["schema"])
