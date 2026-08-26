import json
import os
import threading
import uuid
from datetime import datetime

import pandas as pd
from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client, erro_e_de_billing
from lib.cache import cached, invalidar_tudo

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_CAMPANHAS = os.environ.get("BIGQUERY_CAMPANHAS_TABLE", "campanhas")
TABELA_CRITERIOS = os.environ.get("BIGQUERY_CRITERIOS_TABLE", "campanhas_criterios")

# ─────────────────────────────────────────────────────────────────────────
# Campanhas
# ─────────────────────────────────────────────────────────────────────────
CAMPOS_CAMPANHA = ["banco", "campanha", "data_inicio", "data_fim", "status", "base_producao"]
CAMPOS_CAMPANHA_NUMERO = []
CAMPOS_CAMPANHA_DATA = ["data_inicio", "data_fim"]

STATUS_CAMPANHA_VALIDOS = ["Vigente", "Finalizada", "Em Apuração"]
STATUS_CAMPANHA_PADRAO = "Vigente"

BASE_PRODUCAO_VALIDOS = ["liquido", "bruto"]
BASE_PRODUCAO_PADRAO = "liquido"

SCHEMA_CAMPANHAS = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("banco", "STRING"),
    bigquery.SchemaField("campanha", "STRING"),
    bigquery.SchemaField("data_inicio", "DATE"),
    bigquery.SchemaField("data_fim", "DATE"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("faixas_metas", "STRING"),  # JSON: [{"faixa": 1000, "meta": 50}, ...]
    # Qual coluna da base consolidada conta como produção pro atingimento
    # de meta por padrão nessa campanha: "liquido" (vlr_liquido) ou
    # "bruto" (vlr_bruto). Cada critério pode ter o seu próprio valor
    # (ver SCHEMA_CRITERIOS.valor_base) — esse aqui é só o padrão da
    # campanha como um todo.
    bigquery.SchemaField("base_producao", "STRING"),
    # Filtro opcional de QUAL produção conta pro atingimento de meta dessa
    # campanha. Cada um é uma lista de valores (JSON) — vazio/ausente
    # significa "não filtra por esse critério" (considera tudo). Os
    # valores vêm das colunas de tratamento map_indicado/map_convenio/
    # map_produto (calculadas em Manutenção → Cruzar dados), que ainda
    # não estão totalmente povoadas — a rota já fica pronta pra quando
    # estiverem.
    bigquery.SchemaField("filtro_map_indicado", "STRING"),
    bigquery.SchemaField("filtro_map_convenio", "STRING"),
    bigquery.SchemaField("filtro_map_produto", "STRING"),
    bigquery.SchemaField("criado_em", "TIMESTAMP"),
    bigquery.SchemaField("criado_por", "STRING"),
]

# ─────────────────────────────────────────────────────────────────────────
# Critérios
# ─────────────────────────────────────────────────────────────────────────
CAMPOS_CRITERIO = [
    "campanha_id", "banco", "campanha", "prod_cod", "convenio", "produto", "valor_base",
    "tabela", "descr_tabela", "prazo_min", "prazo_max", "valor_min", "valor_max",
    "data_inicio", "data_fim", "status", "perc_especial",
]
# "valor_base" NÃO é mais um número digitado — é a escolha de qual coluna
# da base consolidada esse critério considera como produção: "liquido"
# (vlr_liquido) ou "bruto" (vlr_bruto). Por isso saiu da lista de campos
# numéricos.
CAMPOS_CRITERIO_NUMERO = ["prazo_min", "prazo_max", "valor_min", "valor_max", "perc_especial"]
CAMPOS_CRITERIO_DATA = ["data_inicio", "data_fim"]

SCHEMA_CRITERIOS = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("campanha_id", "STRING"),
    bigquery.SchemaField("banco", "STRING"),
    bigquery.SchemaField("campanha", "STRING"),
    bigquery.SchemaField("prod_cod", "STRING"),
    bigquery.SchemaField("convenio", "STRING"),
    bigquery.SchemaField("produto", "STRING"),
    bigquery.SchemaField("valor_base", "STRING"),
    bigquery.SchemaField("tabela", "STRING"),
    bigquery.SchemaField("descr_tabela", "STRING"),
    bigquery.SchemaField("prazo_min", "FLOAT64"),
    bigquery.SchemaField("prazo_max", "FLOAT64"),
    bigquery.SchemaField("valor_min", "FLOAT64"),
    bigquery.SchemaField("valor_max", "FLOAT64"),
    bigquery.SchemaField("data_inicio", "DATE"),
    bigquery.SchemaField("data_fim", "DATE"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("perc_especial", "FLOAT64"),
    bigquery.SchemaField("criado_em", "TIMESTAMP"),
    bigquery.SchemaField("criado_por", "STRING"),
]

STATUS_CAMPANHA_BLOQUEIA_EDICAO = ["Finalizada", "Em Apuração"]

# ─────────────────────────────────────────────────────────────────────────
# Auditoria de critérios (histórico de alterações)
# ─────────────────────────────────────────────────────────────────────────
TABELA_AUDITORIA = os.environ.get("BIGQUERY_AUDITORIA_CRITERIOS_TABLE", "campanhas_criterios_auditoria")

SCHEMA_AUDITORIA = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("criterio_id", "STRING"),
    bigquery.SchemaField("campanha_id", "STRING"),
    bigquery.SchemaField("acao", "STRING"),  # "criado" | "editado" | "excluido"
    bigquery.SchemaField("dados", "STRING"),  # JSON com o estado salvo
    bigquery.SchemaField("usuario", "STRING"),
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
]

_tabelas_garantidas = set()
_lock = threading.Lock()


def _migrar_schema_generico(client, table_id, schema_completo):
    """Adiciona colunas novas via ALTER TABLE se a tabela já existia sem
    elas (mesmo padrão usado em lib/usuarios.py e lib/setup.py)."""
    tabela = client.get_table(table_id)
    colunas_atuais = {campo.name for campo in tabela.schema}
    campos_novos = [c for c in schema_completo if c.name not in colunas_atuais]
    if not campos_novos:
        return
    tabela.schema = list(tabela.schema) + campos_novos
    client.update_table(tabela, ["schema"])


def _garantir_tabela(nome_tabela, schema):
    """Confere/cria a tabela — só de verdade uma vez por processo (mesmo
    padrão usado em lib/mapeamento.py, lib/setup.py, lib/indicados.py)."""
    if nome_tabela in _tabelas_garantidas:
        return
    with _lock:
        if nome_tabela in _tabelas_garantidas:
            return
        client = get_bigquery_client()
        client.create_dataset(f"{PROJECT}.{DATASET}", exists_ok=True)
        table_id = f"{PROJECT}.{DATASET}.{nome_tabela}"
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table, exists_ok=True)
        _migrar_schema_generico(client, table_id, schema)
        _tabelas_garantidas.add(nome_tabela)


def _remover_por_id(nome_tabela, id_):
    """DELETE com fallback via CREATE OR REPLACE TABLE (DDL) caso o
    projeto não tenha billing habilitado."""
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{nome_tabela}"
    tabela = f"`{table_id}`"

    try:
        query = f"DELETE FROM {tabela} WHERE id = @id"
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("id", "STRING", id_)])
        client.query(query, job_config=job_config).result()
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise
        rebuild_query = f"CREATE OR REPLACE TABLE {tabela} AS SELECT * FROM {tabela} WHERE id != @id"
        job_config2 = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("id", "STRING", id_)])
        client.query(rebuild_query, job_config=job_config2).result()


def _preparar_linha(dados, campos, campos_numero):
    linha = {}
    for campo in campos:
        valor = dados.get(campo)
        if campo in campos_numero:
            linha[campo] = float(valor) if valor not in (None, "") else None
        else:
            linha[campo] = (valor or "").strip() if isinstance(valor, str) else valor
    return linha


# ─────────────────────────────────────────────────────────────────────────
# API pública: campanhas
# ─────────────────────────────────────────────────────────────────────────
CAMPOS_FILTRO_PRODUCAO = ["filtro_map_indicado", "filtro_map_convenio", "filtro_map_produto"]


@cached()
def listar_campanhas():
    _garantir_tabela(TABELA_CAMPANHAS, SCHEMA_CAMPANHAS)
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_CAMPANHAS}`"
    colunas = ", ".join(["id"] + CAMPOS_CAMPANHA + ["faixas_metas"] + CAMPOS_FILTRO_PRODUCAO + ["criado_em", "criado_por"])
    rows = client.query(f"SELECT {colunas} FROM {tabela} ORDER BY banco, campanha").result()

    resultado = []
    for row in rows:
        item = dict(row)
        bruto = item.get("faixas_metas")
        try:
            item["faixas_metas"] = json.loads(bruto) if bruto else []
        except (TypeError, ValueError):
            item["faixas_metas"] = []

        for campo in CAMPOS_FILTRO_PRODUCAO:
            bruto_filtro = item.get(campo)
            try:
                item[campo] = json.loads(bruto_filtro) if bruto_filtro else []
            except (TypeError, ValueError):
                item[campo] = []

        resultado.append(item)
    return resultado


def salvar_campanha(dados, criado_por, id_existente=None):
    """Cria uma campanha nova (id_existente=None) ou edita uma já
    existente (substitui a linha antiga pelo id). Campanha nova sempre
    nasce com status "Vigente", a menos que outro status válido seja
    explicitamente informado."""
    _garantir_tabela(TABELA_CAMPANHAS, SCHEMA_CAMPANHAS)
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_CAMPANHAS}"

    id_final = id_existente or uuid.uuid4().hex
    if id_existente:
        _remover_por_id(TABELA_CAMPANHAS, id_existente)

    linha = _preparar_linha(dados, CAMPOS_CAMPANHA, CAMPOS_CAMPANHA_NUMERO)

    if linha.get("status") not in STATUS_CAMPANHA_VALIDOS:
        linha["status"] = STATUS_CAMPANHA_PADRAO

    if linha.get("base_producao") not in BASE_PRODUCAO_VALIDOS:
        linha["base_producao"] = BASE_PRODUCAO_PADRAO

    faixas_metas = dados.get("faixas_metas") or []
    linha["faixas_metas"] = json.dumps(faixas_metas)

    for campo in CAMPOS_FILTRO_PRODUCAO:
        valores = dados.get(campo) or []
        linha[campo] = json.dumps(valores)

    linha.update({"id": id_final, "criado_em": datetime.utcnow(), "criado_por": criado_por})

    df = pd.DataFrame([linha])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    invalidar_tudo()
    return id_final


def atualizar_status_campanha(id_, novo_status, atualizado_por):
    """Muda só o status de uma campanha já existente, preservando todo o
    resto (regrava a linha inteira, já que é assim que o upsert funciona)."""
    if novo_status not in STATUS_CAMPANHA_VALIDOS:
        raise ValueError(f'Status inválido: "{novo_status}". Use um de: {", ".join(STATUS_CAMPANHA_VALIDOS)}.')

    campanhas = listar_campanhas()
    alvo = next((c for c in campanhas if c["id"] == id_), None)
    if not alvo:
        raise ValueError("Campanha não encontrada.")

    dados = {campo: alvo.get(campo) for campo in CAMPOS_CAMPANHA}
    dados["status"] = novo_status
    dados["faixas_metas"] = alvo.get("faixas_metas") or []

    return salvar_campanha(dados, criado_por=atualizado_por, id_existente=id_)


def excluir_campanha(id_):
    _garantir_tabela(TABELA_CAMPANHAS, SCHEMA_CAMPANHAS)
    _remover_por_id(TABELA_CAMPANHAS, id_)
    invalidar_tudo()


# ─────────────────────────────────────────────────────────────────────────
# API pública: critérios
# ─────────────────────────────────────────────────────────────────────────
def _registrar_auditoria(criterio_id, campanha_id, acao, dados, usuario):
    _garantir_tabela(TABELA_AUDITORIA, SCHEMA_AUDITORIA)
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_AUDITORIA}"

    linha = pd.DataFrame([{
        "id": uuid.uuid4().hex,
        "criterio_id": criterio_id,
        "campanha_id": campanha_id,
        "acao": acao,
        "dados": json.dumps(dados, default=str),
        "usuario": usuario,
        "timestamp": datetime.utcnow(),
    }])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(linha, table_id, job_config=job_config).result()


@cached()
def listar_auditoria_criterios(campanha_id=None):
    _garantir_tabela(TABELA_AUDITORIA, SCHEMA_AUDITORIA)
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_AUDITORIA}`"
    query = f"""
        SELECT id, criterio_id, campanha_id, acao, dados, usuario, timestamp
        FROM {tabela}
        WHERE (@campanha_id IS NULL OR campanha_id = @campanha_id)
        ORDER BY timestamp DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("campanha_id", "STRING", campanha_id)]
    )
    rows = client.query(query, job_config=job_config).result()
    resultado = []
    for row in rows:
        item = dict(row)
        try:
            item["dados"] = json.loads(item["dados"]) if item.get("dados") else {}
        except (TypeError, ValueError):
            item["dados"] = {}
        resultado.append(item)
    return resultado


def _validar_campanha_editavel(campanha_id):
    """Regra de negócio: não é possível criar/editar/excluir um critério de
    uma campanha marcada como Finalizada ou Em Apuração."""
    if not campanha_id:
        return
    campanhas = listar_campanhas()
    alvo = next((c for c in campanhas if c["id"] == campanha_id), None)
    if alvo and alvo.get("status") in STATUS_CAMPANHA_BLOQUEIA_EDICAO:
        raise ValueError(
            f'Não é possível editar critérios de uma campanha "{alvo.get("status")}". '
            "Mude o status da campanha antes, se realmente precisar editar."
        )


@cached()
def listar_criterios():
    _garantir_tabela(TABELA_CRITERIOS, SCHEMA_CRITERIOS)
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_CRITERIOS}`"
    colunas = ", ".join(["id"] + CAMPOS_CRITERIO + ["criado_em", "criado_por"])
    rows = client.query(f"SELECT {colunas} FROM {tabela} ORDER BY banco, campanha").result()
    return [dict(row) for row in rows]


def salvar_criterio(dados, criado_por, id_existente=None):
    campanha_id = dados.get("campanha_id")
    _validar_campanha_editavel(campanha_id)

    _garantir_tabela(TABELA_CRITERIOS, SCHEMA_CRITERIOS)
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_CRITERIOS}"

    id_final = id_existente or uuid.uuid4().hex
    if id_existente:
        _remover_por_id(TABELA_CRITERIOS, id_existente)

    linha = _preparar_linha(dados, CAMPOS_CRITERIO, CAMPOS_CRITERIO_NUMERO)

    if linha.get("valor_base") not in BASE_PRODUCAO_VALIDOS:
        # Se o critério não escolheu explicitamente, herda o padrão da
        # campanha (e se nem a campanha tiver, cai no padrão geral).
        campanha_relacionada = next((c for c in listar_campanhas() if c["id"] == campanha_id), None)
        linha["valor_base"] = (campanha_relacionada or {}).get("base_producao") or BASE_PRODUCAO_PADRAO

    linha.update({"id": id_final, "criado_em": datetime.utcnow(), "criado_por": criado_por})

    df = pd.DataFrame([linha])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    _registrar_auditoria(id_final, campanha_id, "editado" if id_existente else "criado", linha, criado_por)

    invalidar_tudo()
    return id_final


def excluir_criterio(id_, excluido_por=None):
    criterios = listar_criterios()
    alvo = next((c for c in criterios if c["id"] == id_), None)
    campanha_id = alvo.get("campanha_id") if alvo else None
    _validar_campanha_editavel(campanha_id)

    _garantir_tabela(TABELA_CRITERIOS, SCHEMA_CRITERIOS)
    _remover_por_id(TABELA_CRITERIOS, id_)

    _registrar_auditoria(id_, campanha_id, "excluido", alvo or {}, excluido_por)

    invalidar_tudo()
