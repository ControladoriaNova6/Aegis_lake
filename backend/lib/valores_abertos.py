"""Valores em Aberto — lançamentos de valores que vão ser recebidos (alguns
manuais, outros no futuro computados pelo sistema, como campanhas).
Mesmo padrão de storage/upsert usado em lib/campanhas.py."""
import os
import threading
import uuid
from datetime import date, datetime

import pandas as pd
from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client, erro_e_de_billing
from lib.cache import cached, invalidar_tudo

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_VALORES_ABERTOS = os.environ.get("BIGQUERY_VALORES_ABERTOS_TABLE", "valores_abertos")

CATEGORIAS_VALIDAS = ["Nota Fiscal", "Campanha", "Bônus", "Diferido", "Colchão", "Outro"]

STATUS_VALIDOS = ["aberto", "recebido"]

CAMPOS_LANCAMENTO = ["banco", "categoria", "periodo_ref", "valor", "data_prevista"]

SCHEMA_VALORES_ABERTOS = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("banco", "STRING"),
    bigquery.SchemaField("categoria", "STRING"),
    bigquery.SchemaField("periodo_ref", "STRING"),
    bigquery.SchemaField("valor", "FLOAT64"),
    bigquery.SchemaField("data_prevista", "DATE"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("campanha_id", "STRING"),  # preenchido só quando vier do botão em Cadastro de campanha
    bigquery.SchemaField("criado_por", "STRING"),
    bigquery.SchemaField("criado_em", "TIMESTAMP"),
    bigquery.SchemaField("recebido_por", "STRING"),
    bigquery.SchemaField("recebido_em", "TIMESTAMP"),
]

_tabela_garantida = False
_lock = threading.Lock()


def _garantir_tabela():
    global _tabela_garantida
    if _tabela_garantida:
        return
    with _lock:
        if _tabela_garantida:
            return
        client = get_bigquery_client()
        client.create_dataset(f"{PROJECT}.{DATASET}", exists_ok=True)
        table_id = f"{PROJECT}.{DATASET}.{TABELA_VALORES_ABERTOS}"
        table = bigquery.Table(table_id, schema=SCHEMA_VALORES_ABERTOS)
        client.create_table(table, exists_ok=True)

        tabela = client.get_table(table_id)
        colunas_atuais = {f.name for f in tabela.schema}
        campos_novos = [c for c in SCHEMA_VALORES_ABERTOS if c.name not in colunas_atuais]
        if campos_novos:
            tabela.schema = list(tabela.schema) + campos_novos
            client.update_table(tabela, ["schema"])

        _tabela_garantida = True


def _remover_por_id(id_):
    client = get_bigquery_client()
    tabela_id = f"{PROJECT}.{DATASET}.{TABELA_VALORES_ABERTOS}"
    tabela = f"`{tabela_id}`"
    try:
        client.query(
            f"DELETE FROM {tabela} WHERE id = @id",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("id", "STRING", id_)]
            ),
        ).result()
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise
        client.query(
            f"CREATE OR REPLACE TABLE {tabela} AS SELECT * FROM {tabela} WHERE id != @id",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("id", "STRING", id_)]
            ),
        ).result()


@cached()
def listar_valores_abertos():
    _garantir_tabela()
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_VALORES_ABERTOS}`"
    colunas = ", ".join(
        ["id"] + CAMPOS_LANCAMENTO
        + ["status", "campanha_id", "criado_por", "criado_em", "recebido_por", "recebido_em"]
    )
    rows = client.query(f"SELECT {colunas} FROM {tabela} ORDER BY data_prevista").result()
    return [dict(row) for row in rows]


def _para_date(valor):
    """Converte "2026-08-20" (string do <input type="date">) em
    datetime.date de verdade — sem isso, a carga real no BigQuery falha
    (a coluna vai como STRING, não bate com o tipo DATE da tabela)."""
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str):
        return datetime.strptime(valor.strip()[:10], "%Y-%m-%d").date()
    return valor


def criar_lancamento(dados, criado_por, campanha_id=None):
    if dados.get("categoria") not in CATEGORIAS_VALIDAS:
        raise ValueError(f'Categoria inválida. Use uma de: {", ".join(CATEGORIAS_VALIDAS)}.')
    if not dados.get("banco"):
        raise ValueError("Informe o banco.")
    if dados.get("valor") in (None, ""):
        raise ValueError("Informe o valor.")
    if not dados.get("data_prevista"):
        raise ValueError("Informe a data prevista.")

    _garantir_tabela()
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_VALORES_ABERTOS}"

    linha = {campo: dados.get(campo) for campo in CAMPOS_LANCAMENTO}
    linha["valor"] = float(linha["valor"])
    linha["data_prevista"] = _para_date(linha["data_prevista"])
    linha.update({
        "id": uuid.uuid4().hex,
        "status": "aberto",
        "campanha_id": campanha_id,
        "criado_por": criado_por,
        "criado_em": datetime.utcnow(),
        "recebido_por": None,
        "recebido_em": None,
    })

    df = pd.DataFrame([linha])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    invalidar_tudo()
    return linha["id"]


def _mudar_status(id_, novo_status, usuario):
    """Marca como recebido ou volta pra aberto — regrava a linha inteira
    (mesmo padrão upsert do resto do sistema)."""
    lancamentos = listar_valores_abertos()
    alvo = next((l for l in lancamentos if l["id"] == id_), None)
    if not alvo:
        raise ValueError("Lançamento não encontrado.")

    _garantir_tabela()
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_VALORES_ABERTOS}"

    _remover_por_id(id_)

    novo = dict(alvo)
    novo["status"] = novo_status
    if novo_status == "recebido":
        novo["recebido_por"] = usuario
        novo["recebido_em"] = datetime.utcnow()
    else:
        novo["recebido_por"] = None
        novo["recebido_em"] = None

    df = pd.DataFrame([novo])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    invalidar_tudo()


def marcar_recebido(id_, usuario):
    _mudar_status(id_, "recebido", usuario)


def reabrir_lancamento(id_):
    _mudar_status(id_, "aberto", None)


def excluir_lancamento(id_):
    lancamentos = listar_valores_abertos()
    alvo = next((l for l in lancamentos if l["id"] == id_), None)
    if not alvo:
        raise ValueError("Lançamento não encontrado.")
    _garantir_tabela()
    _remover_por_id(id_)
    invalidar_tudo()


def sincronizar_valores_abertos_de_campanhas():
    """Motor ETL simples: para cada lançamento em aberto que veio de uma
    campanha (campanha_id preenchido), atualiza o valor e a data
    prevista com a projeção mais atual dessa campanha (valor_campanha_previsto
    e data_fim, recalculados na hora). Lançamentos já marcados como
    "recebido" não são tocados — o dinheiro já entrou, não faz sentido
    o sistema reescrever o valor depois disso.

    Pensado pra ser chamado manualmente (botão em Manutenção) ou de um
    agendador/cron no futuro, sempre que a produção subjacente às
    campanhas for atualizada (nova importação de base, por exemplo)."""
    from lib.campanhas import calcular_cenarios_campanha, listar_campanhas

    lancamentos = [
        l for l in listar_valores_abertos()
        if l.get("campanha_id") and l.get("status") == "aberto"
    ]
    if not lancamentos:
        return {"verificados": 0, "atualizados": 0, "campanhas_nao_encontradas": 0}

    campanhas = {c["id"]: c for c in listar_campanhas()}
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_VALORES_ABERTOS}"

    atualizados = 0
    nao_encontradas = 0
    for lanc in lancamentos:
        campanha = campanhas.get(lanc["campanha_id"])
        if not campanha:
            nao_encontradas += 1
            continue

        cenarios = calcular_cenarios_campanha(campanha["id"])
        novo_valor = cenarios["valor_campanha_previsto"]
        nova_data = _para_date(campanha.get("data_fim"))

        if lanc.get("valor") == novo_valor and lanc.get("data_prevista") == nova_data:
            continue  # já está em dia, evita regravação desnecessária

        _garantir_tabela()
        _remover_por_id(lanc["id"])
        novo = dict(lanc)
        novo["valor"] = novo_valor
        novo["data_prevista"] = nova_data
        pd_frame = pd.DataFrame([novo])
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
        client.load_table_from_dataframe(pd_frame, table_id, job_config=job_config).result()
        atualizados += 1

    invalidar_tudo()
    return {"verificados": len(lancamentos), "atualizados": atualizados, "campanhas_nao_encontradas": nao_encontradas}


def resumo_valores_abertos():
    """Números pro dashboard de Visão geral: total pendente, previsto pra
    hoje, e em atraso — cada um com a lista de lançamentos por trás."""
    lancamentos = [l for l in listar_valores_abertos() if l["status"] == "aberto"]
    hoje = date.today()

    def _para_data(valor):
        if isinstance(valor, date):
            return valor
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, str) and valor:
            return datetime.strptime(valor[:10], "%Y-%m-%d").date()
        return None

    pendente_total = sum(l["valor"] for l in lancamentos)

    hoje_lista = [l for l in lancamentos if _para_data(l["data_prevista"]) == hoje]
    hoje_total = sum(l["valor"] for l in hoje_lista)

    atraso_lista = [l for l in lancamentos if (_para_data(l["data_prevista"]) or hoje) < hoje]
    atraso_total = sum(l["valor"] for l in atraso_lista)

    return {
        "pendente_total": pendente_total,
        "pendente_qtd": len(lancamentos),
        "hoje_total": hoje_total,
        "hoje_lista": sorted(hoje_lista, key=lambda l: l["banco"] or ""),
        "atraso_total": atraso_total,
        "atraso_lista": sorted(atraso_lista, key=lambda l: l["data_prevista"] or ""),
    }
