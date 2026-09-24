"""Mapeamento de Convênio/Produto (tela "Mapeamento", admin) — trata os
dados brutos da base consolidada em duas colunas padronizadas
(map_convenio / map_produto), que o resto do sistema (Campanhas,
Indicados etc) usa como fonte da verdade pra convênio/produto.

Duas entidades:
  - Categoria: o valor final que vai ser gravado (ex: "INSS"), e em qual
    coluna de tratamento ela escreve (map_convenio OU map_produto — nunca
    as duas).
  - Regra: uma busca (ex: procurar "INSS" em Convênio/Produto/Tabela) que,
    ao bater, aplica a categoria dona dela. Uma categoria pode ter várias
    regras (N:1).

Motor (executar_mapeamento): procura os termos das regras nos campos
escolhidos (contém, sem diferenciar maiúscula/minúscula) e só preenche
linhas que AINDA estão com a coluna de tratamento vazia — nunca
sobrescreve o que já foi preenchido antes (mesma regra do Map Indicado).
Se mais de uma categoria bater na mesma linha, NENHUMA é aplicada — a
linha fica marcada na coluna de conflito (map_convenio_conflito /
map_produto_conflito) com os nomes das categorias em disputa, pra dar
pra revisar manualmente (ajustando as regras pra ficarem mais
específicas) sem o sistema "adivinhar" qual delas está certa.
"""
import os
import threading
import uuid
from datetime import datetime

import pandas as pd
from google.cloud import bigquery

from lib.bigquery_client import get_bigquery_client, erro_e_de_billing
from lib.cache import cached, invalidar_tudo
from lib.importador import PROJECT as _P, DATASET as _D, TABELA_PRINCIPAL as _TP

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID", _P)
DATASET = os.environ.get("BIGQUERY_DATASET", _D)
TABELA_PRINCIPAL = os.environ.get("BIGQUERY_TABLE", _TP)

TABELA_CATEGORIAS = "map_categorias"
TABELA_REGRAS = "map_regras"

LOCAIS_VALIDOS = ["map_convenio", "map_produto"]
LOCAL_LABEL = {"map_convenio": "Convênio", "map_produto": "Produto"}

SCHEMA_CATEGORIAS = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("nome", "STRING"),
    bigquery.SchemaField("local_enquadramento", "STRING"),
    bigquery.SchemaField("criado_em", "TIMESTAMP"),
    bigquery.SchemaField("criado_por", "STRING"),
]

SCHEMA_REGRAS = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("categoria_id", "STRING"),
    bigquery.SchemaField("descricao", "STRING"),
    bigquery.SchemaField("busca_convenio", "BOOL"),
    bigquery.SchemaField("busca_produto", "BOOL"),
    bigquery.SchemaField("busca_tabela", "BOOL"),
    bigquery.SchemaField("criado_em", "TIMESTAMP"),
    bigquery.SchemaField("criado_por", "STRING"),
]

TABELA_REGISTROS = "map_registros"

# Registro (auditoria) de tudo que mexe no mapeamento — o próprio motor
# NUNCA sobrescreve/edita dado já tratado; a única forma de "desfazer"
# algo é excluir a categoria/regra (que reverte só o que ela preencheu) e
# rodar de novo. Esse log é só leitura pra fora daqui: cada linha é uma
# ação (execução do motor, exclusão de categoria ou de regra), pra dar
# pra auditar depois quem fez o quê e quando — mesmo padrão da tela de
# Registros (importação) e da auditoria de Critérios.
SCHEMA_REGISTROS = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("acao", "STRING"),  # "executar" | "excluir_categoria" | "excluir_regra"
    bigquery.SchemaField("local_enquadramento", "STRING"),
    bigquery.SchemaField("detalhe", "STRING"),
    bigquery.SchemaField("categorias_consideradas", "INT64"),
    bigquery.SchemaField("linhas_elegiveis_antes", "INT64"),
    bigquery.SchemaField("linhas_elegiveis_depois", "INT64"),
    bigquery.SchemaField("linhas_marcadas", "INT64"),
    bigquery.SchemaField("executado_em", "TIMESTAMP"),
    bigquery.SchemaField("executado_por", "STRING"),
]

_tabelas_garantidas = set()
_lock = threading.Lock()


def _garantir_tabela(nome_tabela, schema):
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
        _tabelas_garantidas.add(nome_tabela)


def _garantir_colunas_conflito():
    """As colunas map_convenio/map_produto (sem conflito) já são criadas
    por lib.manutencao.garantir_colunas_map(); aqui só garantimos as DUAS
    colunas extras de conflito, que são específicas desse motor."""
    from lib.manutencao import garantir_colunas_map

    garantir_colunas_map()
    try:
        client = get_bigquery_client()
        table_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
        table = client.get_table(table_id)
        existentes = {f.name for f in table.schema}
        novas = [
            bigquery.SchemaField(c, "STRING")
            for c in ("map_convenio_conflito", "map_produto_conflito")
            if c not in existentes
        ]
        if novas:
            table.schema = list(table.schema) + novas
            client.update_table(table, ["schema"])
    except Exception:  # noqa: BLE001
        pass


def _remover_por_id(nome_tabela, id_):
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


def _remover_por_categoria(nome_tabela, categoria_id):
    """Apaga TODAS as regras de uma categoria de uma vez (usado ao
    excluir a categoria inteira)."""
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{nome_tabela}"
    tabela = f"`{table_id}`"
    try:
        query = f"DELETE FROM {tabela} WHERE categoria_id = @categoria_id"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("categoria_id", "STRING", categoria_id)]
        )
        client.query(query, job_config=job_config).result()
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise
        rebuild_query = f"CREATE OR REPLACE TABLE {tabela} AS SELECT * FROM {tabela} WHERE categoria_id != @categoria_id"
        job_config2 = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("categoria_id", "STRING", categoria_id)]
        )
        client.query(rebuild_query, job_config=job_config2).result()


# ─────────────────────────────────────────────────────────────────────────
# Categorias
# ─────────────────────────────────────────────────────────────────────────
@cached()
def listar_categorias():
    _garantir_tabela(TABELA_CATEGORIAS, SCHEMA_CATEGORIAS)
    _garantir_tabela(TABELA_REGRAS, SCHEMA_REGRAS)
    client = get_bigquery_client()
    tabela_cat = f"`{PROJECT}.{DATASET}.{TABELA_CATEGORIAS}`"
    tabela_reg = f"`{PROJECT}.{DATASET}.{TABELA_REGRAS}`"

    query = f"""
        SELECT
            C.id, C.nome, C.local_enquadramento, C.criado_em, C.criado_por,
            COUNT(R.id) AS total_regras
        FROM {tabela_cat} AS C
        LEFT JOIN {tabela_reg} AS R ON R.categoria_id = C.id
        GROUP BY C.id, C.nome, C.local_enquadramento, C.criado_em, C.criado_por
        ORDER BY C.nome
    """
    rows = client.query(query).result()
    return [dict(row) for row in rows]


def criar_categoria(nome, local_enquadramento, criado_por):
    nome = (nome or "").strip()
    if not nome:
        raise ValueError('O campo "Nome da categoria" é obrigatório.')
    if local_enquadramento not in LOCAIS_VALIDOS:
        raise ValueError('Local de enquadramento inválido — use "map_convenio" ou "map_produto".')

    _garantir_tabela(TABELA_CATEGORIAS, SCHEMA_CATEGORIAS)
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_CATEGORIAS}"

    id_novo = uuid.uuid4().hex
    linha = pd.DataFrame([{
        "id": id_novo,
        "nome": nome,
        "local_enquadramento": local_enquadramento,
        "criado_em": datetime.utcnow(),
        "criado_por": criado_por,
    }])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(linha, table_id, job_config=job_config).result()

    invalidar_tudo()
    return id_novo


def excluir_categoria(id_, executado_por=None):
    """Apaga a categoria, todas as suas regras, E reverte (limpa) tudo
    que essa categoria já tinha preenchido na base consolidada — tanto na
    coluna de tratamento quanto na de conflito, já que as regras dela não
    existem mais pra entrar em disputa com outra categoria."""
    categorias = listar_categorias()
    alvo = next((c for c in categorias if c["id"] == id_), None)
    if not alvo:
        raise ValueError("Categoria não encontrada.")

    _reverter_dados_da_categoria(alvo["nome"], alvo["local_enquadramento"])
    _remover_por_categoria(TABELA_REGRAS, id_)
    _remover_por_id(TABELA_CATEGORIAS, id_)
    invalidar_tudo()

    _registrar(
        acao="excluir_categoria",
        executado_por=executado_por,
        local_enquadramento=alvo["local_enquadramento"],
        detalhe=f'Categoria "{alvo["nome"]}" excluída — dados revertidos.',
    )

    # Como sobrou espaço vazio (tudo que só essa categoria preenchia
    # voltou a NULL), reprocessa esse local — se restar exatamente 1
    # categoria concorrendo numa linha que antes estava em conflito com a
    # que acabou de ser excluída, ela já sai preenchida corretamente.
    executar_mapeamento(alvo["local_enquadramento"], executado_por=executado_por)


def _reverter_dados_da_categoria(nome_categoria, local_enquadramento):
    """Limpa (NULL) a coluna de tratamento e a de conflito em toda linha
    onde essa categoria aparece — seja como valor aplicado, seja como
    uma das concorrentes num conflito registrado."""
    _garantir_colunas_conflito()
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
    tabela = f"`{table_id}`"
    coluna = local_enquadramento
    coluna_conflito = f"{local_enquadramento}_conflito"

    query = f"""
        UPDATE {tabela}
        SET
            {coluna} = IF({coluna} = @nome, NULL, {coluna}),
            {coluna_conflito} = IF(
                {coluna_conflito} IS NOT NULL AND {coluna_conflito} LIKE CONCAT('%', @nome, '%'),
                NULL,
                {coluna_conflito}
            )
        WHERE {coluna} = @nome
           OR ({coluna_conflito} IS NOT NULL AND {coluna_conflito} LIKE CONCAT('%', @nome, '%'))
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("nome", "STRING", nome_categoria)])
    try:
        client.query(query, job_config=job_config).result()
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise
        rebuild_query = f"""
            CREATE OR REPLACE TABLE {tabela} AS
            SELECT * REPLACE(
                IF({coluna} = @nome, NULL, {coluna}) AS {coluna},
                IF({coluna_conflito} IS NOT NULL AND {coluna_conflito} LIKE CONCAT('%', @nome, '%'), NULL, {coluna_conflito}) AS {coluna_conflito}
            )
            FROM {tabela}
        """
        client.query(rebuild_query, job_config=job_config).result()


# ─────────────────────────────────────────────────────────────────────────
# Regras
# ─────────────────────────────────────────────────────────────────────────
@cached()
def listar_regras(categoria_id=None):
    _garantir_tabela(TABELA_REGRAS, SCHEMA_REGRAS)
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_REGRAS}`"
    query = f"""
        SELECT id, categoria_id, descricao, busca_convenio, busca_produto, busca_tabela, criado_em, criado_por
        FROM {tabela}
        WHERE (@categoria_id IS NULL OR categoria_id = @categoria_id)
        ORDER BY criado_em
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("categoria_id", "STRING", categoria_id or None)]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def criar_regra(categoria_id, descricao, busca_convenio, busca_produto, busca_tabela, criado_por):
    descricao = (descricao or "").strip()
    if not descricao:
        raise ValueError('O campo "Descrição" (o que vai ser procurado) é obrigatório.')
    if not (busca_convenio or busca_produto or busca_tabela):
        raise ValueError("Escolha ao menos um campo pra fazer a busca: Convênio, Produto ou Tabela.")

    categorias = listar_categorias()
    if not any(c["id"] == categoria_id for c in categorias):
        raise ValueError("Categoria não encontrada.")

    _garantir_tabela(TABELA_REGRAS, SCHEMA_REGRAS)
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_REGRAS}"

    id_novo = uuid.uuid4().hex
    linha = pd.DataFrame([{
        "id": id_novo,
        "categoria_id": categoria_id,
        "descricao": descricao,
        "busca_convenio": bool(busca_convenio),
        "busca_produto": bool(busca_produto),
        "busca_tabela": bool(busca_tabela),
        "criado_em": datetime.utcnow(),
        "criado_por": criado_por,
    }])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(linha, table_id, job_config=job_config).result()

    invalidar_tudo()
    return id_novo


def excluir_regra(id_, executado_por=None):
    """Apaga só essa regra — e reverte (NULL) apenas as linhas que ESSA
    regra específica bateria, dentro do que hoje está marcado com o nome
    da categoria dela (outras regras da mesma categoria continuam
    intactas). Depois reprocessa o local pra essas linhas voltarem a ser
    preenchidas pelas regras que sobraram, se alguma ainda bater."""
    regras = listar_regras()
    alvo = next((r for r in regras if r["id"] == id_), None)
    if not alvo:
        raise ValueError("Regra não encontrada.")

    categorias = listar_categorias()
    categoria = next((c for c in categorias if c["id"] == alvo["categoria_id"]), None)
    if categoria:
        _reverter_dados_da_regra(alvo, categoria["nome"], categoria["local_enquadramento"])

    _remover_por_id(TABELA_REGRAS, id_)
    invalidar_tudo()

    if categoria:
        _registrar(
            acao="excluir_regra",
            executado_por=executado_por,
            local_enquadramento=categoria["local_enquadramento"],
            detalhe=f'Regra "{alvo["descricao"]}" da categoria "{categoria["nome"]}" excluída — dados revertidos.',
        )
        executar_mapeamento(categoria["local_enquadramento"], executado_por=executado_por)


def _reverter_dados_da_regra(regra, nome_categoria, local_enquadramento):
    _garantir_colunas_conflito()
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
    tabela = f"`{table_id}`"
    coluna = local_enquadramento

    condicao_regra = _condicao_regra_sql("@descricao", regra["busca_convenio"], regra["busca_produto"], regra["busca_tabela"])

    query = f"""
        UPDATE {tabela} AS T
        SET T.{coluna} = NULL
        WHERE T.{coluna} = @nome AND {condicao_regra}
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("nome", "STRING", nome_categoria),
        bigquery.ScalarQueryParameter("descricao", "STRING", regra["descricao"]),
    ])
    try:
        client.query(query, job_config=job_config).result()
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise
        rebuild_query = f"""
            CREATE OR REPLACE TABLE {tabela} AS
            SELECT * REPLACE(
                IF(T.{coluna} = @nome AND {condicao_regra}, NULL, T.{coluna}) AS {coluna}
            )
            FROM {tabela} AS T
        """
        client.query(rebuild_query, job_config=job_config).result()


def _condicao_regra_sql(descricao_param, busca_convenio, busca_produto, busca_tabela, alias="T"):
    """Monta a condição SQL "essa regra bate nessa linha", combinando os
    campos escolhidos com OR (contém, sem diferenciar maiúscula/
    minúscula). descricao_param é literalmente o texto do parâmetro SQL
    (ex: '@descricao' ou 'R.descricao', dependendo se é comparado contra
    um valor fixo ou contra a coluna de outra tabela numa junção)."""
    partes = []
    if busca_convenio:
        partes.append(f"LOWER(IFNULL({alias}.convenio, '')) LIKE CONCAT('%', LOWER({descricao_param}), '%')")
    if busca_produto:
        partes.append(f"LOWER(IFNULL({alias}.produto, '')) LIKE CONCAT('%', LOWER({descricao_param}), '%')")
    if busca_tabela:
        partes.append(
            f"(LOWER(IFNULL(CAST({alias}.cod_tabela AS STRING), '')) LIKE CONCAT('%', LOWER({descricao_param}), '%')"
            f" OR LOWER(IFNULL({alias}.tabela, '')) LIKE CONCAT('%', LOWER({descricao_param}), '%'))"
        )
    if not partes:
        return "FALSE"
    return "(" + " OR ".join(partes) + ")"


# ─────────────────────────────────────────────────────────────────────────
# Registro (auditoria) — histórico append-only de tudo que mexeu no
# mapeamento. Nunca é editado nem apagado por aqui; é só consulta.
# ─────────────────────────────────────────────────────────────────────────
def _registrar(acao, executado_por, local_enquadramento=None, detalhe=None, categorias_consideradas=None,
               linhas_elegiveis_antes=None, linhas_elegiveis_depois=None, linhas_marcadas=None):
    _garantir_tabela(TABELA_REGISTROS, SCHEMA_REGISTROS)
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_REGISTROS}"
    linha = pd.DataFrame([{
        "id": uuid.uuid4().hex,
        "acao": acao,
        "local_enquadramento": local_enquadramento,
        "detalhe": detalhe,
        "categorias_consideradas": categorias_consideradas,
        "linhas_elegiveis_antes": linhas_elegiveis_antes,
        "linhas_elegiveis_depois": linhas_elegiveis_depois,
        "linhas_marcadas": linhas_marcadas,
        "executado_em": datetime.utcnow(),
        "executado_por": executado_por,
    }])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(linha, table_id, job_config=job_config).result()


@cached()
def listar_registros_mapeamento():
    _garantir_tabela(TABELA_REGISTROS, SCHEMA_REGISTROS)
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_REGISTROS}`"
    rows = client.query(f"SELECT * FROM {tabela} ORDER BY executado_em DESC LIMIT 500").result()
    return [dict(row) for row in rows]


def _contar_linhas_nulas(local_enquadramento):
    """Quantas linhas da base consolidada ainda estão sem essa coluna de
    tratamento preenchida — usado como diagnóstico antes/depois de cada
    execução do motor, pra ficar visível quando algo não teve efeito
    nenhum (em vez de só "não deu erro, mas também não mudou nada")."""
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}`"
    query = f"SELECT COUNT(*) AS total FROM {tabela} WHERE {local_enquadramento} IS NULL"
    return list(client.query(query).result())[0]["total"]


# ─────────────────────────────────────────────────────────────────────────
# Motor
# ─────────────────────────────────────────────────────────────────────────
def executar_mapeamento(local=None, executado_por=None):
    """Roda o motor de busca. `local` = "map_convenio", "map_produto" ou
    None (roda os dois). Só mexe em linhas onde a coluna de tratamento
    ainda está vazia; se mais de uma categoria bater na mesma linha,
    nenhuma é aplicada e a linha é marcada na coluna de conflito com os
    nomes das categorias em disputa (separados por "; ") — pra dar pra
    revisar manualmente, sem o sistema escolher uma ao acaso.

    Cada execução fica registrada (ver listar_registros_mapeamento),
    incluindo quantas linhas ainda estavam sem tratamento ANTES e DEPOIS
    de rodar — assim dá pra perceber na hora se o motor rodou mas não
    teve efeito nenhum (ex: colunas map_convenio/map_produto não
    existindo de verdade na base, ou nenhuma regra realmente batendo),
    em vez de só "não deu erro"."""
    _garantir_colunas_conflito()
    locais = [local] if local else LOCAIS_VALIDOS

    resultado = {}
    for loc in locais:
        antes = _contar_linhas_nulas(loc)
        resultado[loc] = _executar_mapeamento_local(loc)
        depois = _contar_linhas_nulas(loc)
        resultado[loc]["linhas_elegiveis_antes"] = antes
        resultado[loc]["linhas_elegiveis_depois"] = depois
        _registrar(
            acao="executar",
            executado_por=executado_por,
            local_enquadramento=loc,
            detalhe=None,
            categorias_consideradas=resultado[loc]["categorias_consideradas"],
            linhas_elegiveis_antes=antes,
            linhas_elegiveis_depois=depois,
            linhas_marcadas=resultado[loc]["linhas_marcadas"],
        )

    invalidar_tudo()
    return resultado


def _executar_mapeamento_local(local_enquadramento):
    categorias = [c for c in listar_categorias() if c["local_enquadramento"] == local_enquadramento]
    if not categorias:
        return {"categorias_consideradas": 0, "linhas_marcadas": None, "conflitos_gerados": None}

    regras = [r for r in listar_regras() if r["categoria_id"] in {c["id"] for c in categorias}]
    if not regras:
        return {"categorias_consideradas": len(categorias), "linhas_marcadas": 0, "conflitos_gerados": 0}

    nome_por_categoria = {c["id"]: c["nome"] for c in categorias}

    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_PRINCIPAL}"
    tabela = f"`{table_id}`"
    tabela_regras = f"`{PROJECT}.{DATASET}.{TABELA_REGRAS}`"
    tabela_categorias = f"`{PROJECT}.{DATASET}.{TABELA_CATEGORIAS}`"
    coluna = local_enquadramento
    coluna_conflito = f"{local_enquadramento}_conflito"

    condicao_join = f"""(
        (R.busca_convenio AND LOWER(IFNULL(P.convenio, '')) LIKE CONCAT('%', LOWER(R.descricao), '%'))
        OR (R.busca_produto AND LOWER(IFNULL(P.produto, '')) LIKE CONCAT('%', LOWER(R.descricao), '%'))
        OR (R.busca_tabela AND (
              LOWER(IFNULL(CAST(P.cod_tabela AS STRING), '')) LIKE CONCAT('%', LOWER(R.descricao), '%')
              OR LOWER(IFNULL(P.tabela, '')) LIKE CONCAT('%', LOWER(R.descricao), '%')
        ))
    )"""

    subquery_candidatos = f"""
        SELECT
            P.banco AS banco, P.ade AS ade,
            ARRAY_AGG(DISTINCT C.nome) AS categorias,
            COUNT(DISTINCT C.nome) AS qtd
        FROM {tabela} AS P
        JOIN {tabela_regras} AS R ON {condicao_join}
        JOIN {tabela_categorias} AS C ON C.id = R.categoria_id AND C.local_enquadramento = @local
        WHERE P.{coluna} IS NULL
        GROUP BY banco, ade
    """

    merge_query = f"""
        MERGE {tabela} AS T
        USING ({subquery_candidatos}) AS M
        ON T.banco = M.banco AND T.ade = M.ade
        WHEN MATCHED AND M.qtd = 1 THEN
          UPDATE SET {coluna} = M.categorias[OFFSET(0)]
        WHEN MATCHED AND M.qtd > 1 THEN
          UPDATE SET {coluna_conflito} = ARRAY_TO_STRING(M.categorias, '; ')
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("local", "STRING", local_enquadramento)]
    )

    try:
        job = client.query(merge_query, job_config=job_config)
        job.result()
        linhas_afetadas = getattr(job, "num_dml_affected_rows", None)
        return {
            "categorias_consideradas": len(categorias),
            "linhas_marcadas": linhas_afetadas,
            "conflitos_gerados": None,
        }
    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise

        # Sem billing habilitado, MERGE (DML) é bloqueado — mesmo
        # fallback via CREATE OR REPLACE TABLE usado no resto do sistema.
        rebuild_query = f"""
            CREATE OR REPLACE TABLE {tabela} AS
            SELECT
                P.* REPLACE(
                    CASE
                        WHEN P.{coluna} IS NOT NULL THEN P.{coluna}
                        WHEN M.qtd = 1 THEN M.categorias[OFFSET(0)]
                        ELSE P.{coluna}
                    END AS {coluna},
                    CASE
                        WHEN P.{coluna} IS NULL AND M.qtd > 1 THEN ARRAY_TO_STRING(M.categorias, '; ')
                        ELSE P.{coluna_conflito}
                    END AS {coluna_conflito}
                )
            FROM {tabela} AS P
            LEFT JOIN ({subquery_candidatos}) AS M
              ON P.banco = M.banco AND P.ade = M.ade
        """
        client.query(rebuild_query, job_config=job_config).result()
        return {
            "categorias_consideradas": len(categorias),
            "linhas_marcadas": None,
            "conflitos_gerados": None,
        }
