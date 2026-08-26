import os
from datetime import datetime

from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client, erro_e_de_billing
from lib.cache import cached, invalidar_tudo
from lib.setup import garantir_tabela_logs

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_PRINCIPAL = os.environ.get("BIGQUERY_TABLE", "base_consolidada")
TABELA_LOGS = os.environ.get("BIGQUERY_LOGS_TABLE", "import_logs")
COLUNA_ARQUIVO = "arquivo_origem"


@cached()
def listar_logs(busca=None, limite=200):
    garantir_tabela_logs()
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_LOGS}`"

    query = f"""
        SELECT log_id, timestamp, banco_tipo, banco_nome, arquivo_nome, arquivo_original, status,
               total_linhas_arquivo, linhas_inseridas, linhas_duplicadas_ignoradas,
               mensagem_erro, importado_por, excluido_por, excluido_em
        FROM {tabela}
        WHERE (@busca IS NULL
               OR LOWER(arquivo_nome) LIKE CONCAT('%', LOWER(@busca), '%')
               OR LOWER(banco_nome) LIKE CONCAT('%', LOWER(@busca), '%'))
        ORDER BY timestamp DESC
        LIMIT @limite
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("busca", "STRING", busca or None),
            bigquery.ScalarQueryParameter("limite", "INT64", limite),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def excluir_por_log(log_id, banco_nome, arquivo_nome, excluido_por=None):
    """Remove da tabela principal as linhas daquele banco + arquivo de origem,
    e marca o log correspondente como 'revertido' (guardando quem excluiu e
    quando).

    Tenta primeiro o caminho normal (DELETE/UPDATE via DML). Se o projeto
    não tiver billing habilitado, o BigQuery bloqueia DML — nesse caso,
    cai automaticamente para um caminho alternativo via DDL
    (CREATE OR REPLACE TABLE), que o BigQuery permite mesmo sem billing."""
    client = get_bigquery_client()
    banco_up = banco_nome.upper()
    agora = datetime.utcnow()

    tabela_principal_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
    tabela_principal = f"`{tabela_principal_id}`"

    try:
        delete_query = f"""
            DELETE FROM {tabela_principal}
            WHERE UPPER(banco) = @banco AND {COLUNA_ARQUIVO} = @arquivo
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("banco", "STRING", banco_up),
                bigquery.ScalarQueryParameter("arquivo", "STRING", arquivo_nome),
            ]
        )
        job = client.query(delete_query, job_config=job_config)
        job.result()
        linhas_removidas = job.num_dml_affected_rows or 0

    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise

        # ── fallback sem DML (projeto sem billing habilitado) ──────────
        contagem_query = f"""
            SELECT COUNT(*) AS total FROM {tabela_principal}
            WHERE UPPER(banco) = @banco AND {COLUNA_ARQUIVO} = @arquivo
        """
        job_config_contagem = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("banco", "STRING", banco_up),
                bigquery.ScalarQueryParameter("arquivo", "STRING", arquivo_nome),
            ]
        )
        resultado_contagem = list(client.query(contagem_query, job_config=job_config_contagem).result())
        linhas_removidas = int(resultado_contagem[0]["total"] or 0) if resultado_contagem else 0

        rebuild_query = f"""
            CREATE OR REPLACE TABLE `{tabela_principal_id}` AS
            SELECT * FROM {tabela_principal}
            WHERE NOT (UPPER(banco) = @banco AND {COLUNA_ARQUIVO} = @arquivo)
        """
        job_config_rebuild = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("banco", "STRING", banco_up),
                bigquery.ScalarQueryParameter("arquivo", "STRING", arquivo_nome),
            ]
        )
        client.query(rebuild_query, job_config=job_config_rebuild).result()

    # ── marca o log como revertido (mesmo esquema de fallback) ─────────
    tabela_logs_id = f"{PROJECT}.{DATASET}.{TABELA_LOGS}"
    tabela_logs = f"`{tabela_logs_id}`"

    try:
        update_query = f"""
            UPDATE {tabela_logs}
            SET status = 'revertido', excluido_por = @excluido_por, excluido_em = @excluido_em
            WHERE log_id = @log_id
        """
        job_config2 = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("log_id", "STRING", log_id),
                bigquery.ScalarQueryParameter("excluido_por", "STRING", excluido_por),
                bigquery.ScalarQueryParameter("excluido_em", "TIMESTAMP", agora),
            ]
        )
        client.query(update_query, job_config=job_config2).result()

    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise

        colunas_logs = [
            "log_id", "timestamp", "banco_tipo", "banco_nome", "arquivo_nome",
            "arquivo_original", "status", "total_linhas_arquivo",
            "linhas_inseridas", "linhas_duplicadas_ignoradas", "mensagem_erro",
            "importado_por", "excluido_por", "excluido_em",
        ]

        def _coluna_sql(col):
            if col == "status":
                return "IF(log_id = @log_id, 'revertido', status) AS status"
            if col == "excluido_por":
                return "IF(log_id = @log_id, @excluido_por, excluido_por) AS excluido_por"
            if col == "excluido_em":
                return "IF(log_id = @log_id, @excluido_em, excluido_em) AS excluido_em"
            return col

        select_colunas = ", ".join(_coluna_sql(col) for col in colunas_logs)
        rebuild_logs_query = f"""
            CREATE OR REPLACE TABLE `{tabela_logs_id}` AS
            SELECT {select_colunas}
            FROM {tabela_logs}
        """
        job_config_rebuild2 = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("log_id", "STRING", log_id),
                bigquery.ScalarQueryParameter("excluido_por", "STRING", excluido_por),
                bigquery.ScalarQueryParameter("excluido_em", "TIMESTAMP", agora),
            ]
        )
        client.query(rebuild_logs_query, job_config=job_config_rebuild2).result()

    invalidar_tudo()
    return linhas_removidas
