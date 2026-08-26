"""Funções de manutenção/cruzamento de dados — usadas pela tela Admin →
Manutenção. Por enquanto só "Map Indicado" está implementado; "Map
Convênio" e "Map Produto" vêm depois, seguindo o mesmo padrão."""
import threading

from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client, erro_e_de_billing
from lib.indicados import carregar_todos_indicados
from lib.importador import PROJECT, DATASET, TABELA_PRINCIPAL

# Colunas de tratamento que a função de cruzar dados popula. Nenhuma
# delas nunca vem de arquivo importado — são sempre calculadas aqui.
COLUNAS_MAP = ["map_indicado", "map_convenio", "map_produto"]

_colunas_map_garantidas = False
_lock_colunas_map = threading.Lock()


def garantir_colunas_map():
    """A tabela principal já existia antes desse projeto — não é criada
    por nós. Se as colunas de tratamento ainda não existirem nela, tenta
    adicionar via ALTER TABLE (uma vez por processo). Mesmo padrão de
    lib/importador.py (garantir_coluna_indicado)."""
    global _colunas_map_garantidas
    if _colunas_map_garantidas:
        return

    with _lock_colunas_map:
        if _colunas_map_garantidas:
            return
        try:
            client = get_bigquery_client()
            table_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
            table = client.get_table(table_id)
            existentes = {f.name for f in table.schema}
            novas = [bigquery.SchemaField(c, "STRING") for c in COLUNAS_MAP if c not in existentes]
            if novas:
                table.schema = list(table.schema) + novas
                client.update_table(table, ["schema"])
        except Exception:  # noqa: BLE001
            pass
        _colunas_map_garantidas = True


def _codigos_indicados_validos():
    """Todos os códigos (cod_loja) de indicados já cadastrados, sem
    vazios/duplicatas."""
    df = carregar_todos_indicados()
    if df.empty or "cod_loja" not in df.columns:
        return []
    codigos = set(df["cod_loja"].dropna().astype(str).str.strip())
    codigos.discard("")
    return sorted(codigos)


def listar_valores_mapeados():
    """Valores distintos já existentes nas colunas de tratamento
    (map_indicado, map_convenio, map_produto) da base consolidada — usado
    pra popular os filtros opcionais de produção no cadastro de campanha.
    Enquanto essas colunas não tiverem dado (ou não existirem ainda),
    devolve listas vazias — não quebra nada, só significa que ainda não
    tem opção pra filtrar por ali."""
    garantir_colunas_map()
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"

    resultado = {}
    for coluna in COLUNAS_MAP:
        try:
            query = f"SELECT DISTINCT {coluna} AS valor FROM {tabela} WHERE {coluna} IS NOT NULL ORDER BY {coluna}"
            rows = client.query(query).result()
            resultado[coluna] = [r["valor"] for r in rows if r["valor"]]
        except Exception:  # noqa: BLE001
            resultado[coluna] = []
    return resultado


def executar_cruzamento_indicado():
    """Regra de negócio do Map Indicado: procura em cod_corretor,
    cod_master e cod_indicado (nessa ordem) por um código que bata com
    algum indicado cadastrado. Se bater, grava esse código (não o nome,
    o CÓDIGO mesmo) na coluna 'map_indicado'.

    Só mexe em linhas que AINDA não têm map_indicado preenchido — assim
    dá pra rodar de novo depois de cadastrar indicados novos, sem
    reprocessar (e sem sobrescrever) o que já tinha sido mapeado antes."""
    garantir_colunas_map()

    codigos = _codigos_indicados_validos()
    if not codigos:
        return {"linhas_atualizadas": 0, "codigos_considerados": 0, "mensagem": "Nenhum indicado cadastrado ainda."}

    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
    tabela = f"`{table_id}`"

    condicao_bateu = """(
            CAST(cod_corretor AS STRING) IN UNNEST(@codigos)
            OR CAST(cod_master AS STRING) IN UNNEST(@codigos)
            OR CAST(cod_indicado AS STRING) IN UNNEST(@codigos)
          )"""

    caso_valor = """CASE
            WHEN CAST(cod_corretor AS STRING) IN UNNEST(@codigos) THEN CAST(cod_corretor AS STRING)
            WHEN CAST(cod_master AS STRING) IN UNNEST(@codigos) THEN CAST(cod_master AS STRING)
            WHEN CAST(cod_indicado AS STRING) IN UNNEST(@codigos) THEN CAST(cod_indicado AS STRING)
            ELSE map_indicado
          END"""

    query = f"""
        UPDATE {tabela}
        SET map_indicado = {caso_valor}
        WHERE map_indicado IS NULL AND {condicao_bateu}
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("codigos", "STRING", codigos)]
    )

    linhas_atualizadas = None
    try:
        job = client.query(query, job_config=job_config)
        job.result()
        linhas_atualizadas = getattr(job, "num_dml_affected_rows", None)
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise

        # Sem billing habilitado, DML (UPDATE) é bloqueado — cai pro
        # caminho via DDL (CREATE OR REPLACE TABLE), mesmo padrão usado
        # nas exclusões do resto do sistema. Como reconstrói a tabela
        # inteira, não dá pra saber exatamente quantas linhas mudaram.
        rebuild_query = f"""
            CREATE OR REPLACE TABLE {tabela} AS
            SELECT * REPLACE (
              CASE
                WHEN map_indicado IS NOT NULL THEN map_indicado
                ELSE {caso_valor}
              END AS map_indicado
            )
            FROM {tabela}
        """
        job_config2 = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter("codigos", "STRING", codigos)]
        )
        client.query(rebuild_query, job_config=job_config2).result()

    return {"linhas_atualizadas": linhas_atualizadas, "codigos_considerados": len(codigos)}
