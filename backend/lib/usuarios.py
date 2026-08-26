import os
import threading
from datetime import datetime

import pandas as pd
from google.cloud import bigquery
from werkzeug.security import generate_password_hash, check_password_hash

from lib.bigquery_client import get_bigquery_client, erro_e_de_billing
from lib.cache import cached, invalidar_tudo

PROJECT = os.environ.get("BIGQUERY_PROJECT_ID")
DATASET = os.environ.get("BIGQUERY_DATASET", "base_bancos")
TABELA_USUARIOS = os.environ.get("BIGQUERY_USUARIOS_TABLE", "usuarios")

PAPEIS_VALIDOS = ["admin", "editor", "visualizador"]
PAPEIS_LABEL = {"admin": "Admin", "editor": "Editor", "visualizador": "Visualizador"}

SCHEMA_USUARIOS = [
    bigquery.SchemaField("email", "STRING"),
    bigquery.SchemaField("nome", "STRING"),
    bigquery.SchemaField("papel", "STRING"),
    bigquery.SchemaField("senha_hash", "STRING"),
    bigquery.SchemaField("criado_em", "TIMESTAMP"),
    bigquery.SchemaField("criado_por", "STRING"),
]

_tabela_garantida = False
_tabela_lock = threading.Lock()


def garantir_tabela_usuarios():
    """Confere/cria a tabela — só de verdade uma vez por processo — e faz
    o bootstrap do primeiro admin se a tabela estiver totalmente vazia."""
    global _tabela_garantida
    if _tabela_garantida:
        return

    with _tabela_lock:
        if _tabela_garantida:
            return

        client = get_bigquery_client()
        client.create_dataset(f"{PROJECT}.{DATASET}", exists_ok=True)
        table_id = f"{PROJECT}.{DATASET}.{TABELA_USUARIOS}"
        table = bigquery.Table(table_id, schema=SCHEMA_USUARIOS)
        client.create_table(table, exists_ok=True)

        _migrar_schema_se_necessario(client, table_id)
        _bootstrap_admin_inicial(client, table_id)

        _tabela_garantida = True


def _migrar_schema_se_necessario(client, table_id):
    """Se a tabela já existia de antes de 'senha_hash' existir (ex: quando
    o login era via Google), adiciona a coluna via ALTER TABLE (DDL,
    funciona mesmo sem billing habilitado)."""
    tabela = client.get_table(table_id)
    colunas_atuais = {campo.name for campo in tabela.schema}
    if "senha_hash" in colunas_atuais:
        return

    tabela.schema = list(tabela.schema) + [bigquery.SchemaField("senha_hash", "STRING")]
    client.update_table(tabela, ["schema"])


def _bootstrap_admin_inicial(client, table_id):
    """Se a tabela de usuários estiver totalmente vazia, cadastra
    automaticamente ADMIN_BOOTSTRAP_EMAIL/ADMIN_BOOTSTRAP_PASSWORD
    (.env.local) como o primeiro admin. Sem isso, ninguém consegue nunca
    logar nem cadastrar o primeiro usuário (efeito "ovo e galinha")."""
    email_inicial = os.environ.get("ADMIN_BOOTSTRAP_EMAIL")
    senha_inicial = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    if not email_inicial or not senha_inicial:
        return

    tabela = f"`{table_id}`"
    linhas = list(client.query(f"SELECT COUNT(*) AS total FROM {tabela}").result())
    if int(linhas[0]["total"] or 0) > 0:
        return

    df = pd.DataFrame([{
        "email": email_inicial.strip().lower(),
        "nome": "Administrador inicial",
        "papel": "admin",
        "senha_hash": generate_password_hash(senha_inicial),
        "criado_em": datetime.utcnow(),
        "criado_por": "sistema (bootstrap)",
    }])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()


@cached()
def listar_usuarios():
    garantir_tabela_usuarios()
    client = get_bigquery_client()
    tabela = f"`{PROJECT}.{DATASET}.{TABELA_USUARIOS}`"
    query = f"SELECT email, nome, papel, senha_hash, criado_em, criado_por FROM {tabela} ORDER BY email"
    rows = client.query(query).result()
    return [dict(row) for row in rows]


def obter_usuario_por_email(email):
    if not email:
        return None
    email = email.strip().lower()
    for usuario in listar_usuarios():
        if usuario["email"] == email:
            return usuario
    return None


def verificar_login(email, senha):
    """Confere e-mail + senha. Retorna o usuário (sem o hash da senha) se
    bater, ou None se e-mail não existir ou senha estiver errada."""
    usuario = obter_usuario_por_email(email)
    if not usuario or not usuario.get("senha_hash"):
        return None
    if not check_password_hash(usuario["senha_hash"], senha or ""):
        return None
    return {k: v for k, v in usuario.items() if k != "senha_hash"}


def adicionar_usuario(email, nome, papel, criado_por, senha=None):
    """Adiciona um usuário novo ou edita um já existente (upsert por
    e-mail). Se `senha` vier preenchida, define/reseta a senha; se vier
    vazia ao EDITAR um usuário que já existe, mantém a senha antiga. Pra
    um usuário NOVO, senha é obrigatória."""
    if papel not in PAPEIS_VALIDOS:
        raise ValueError(f'Papel inválido: "{papel}". Use um de: {", ".join(PAPEIS_VALIDOS)}.')

    garantir_tabela_usuarios()
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_USUARIOS}"

    existente = obter_usuario_por_email(email)

    if senha:
        senha_hash = generate_password_hash(senha)
    elif existente:
        senha_hash = existente.get("senha_hash")
    else:
        raise ValueError("Defina uma senha para o novo usuário.")

    _remover_usuario(client, table_id, email)

    df = pd.DataFrame([{
        "email": email.strip().lower(),
        "nome": nome.strip() or email.strip().lower(),
        "papel": papel,
        "senha_hash": senha_hash,
        "criado_em": datetime.utcnow(),
        "criado_por": criado_por,
    }])
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    invalidar_tudo()


def redefinir_propria_senha(email, senha_atual, senha_nova):
    """Troca a senha do próprio usuário, conferindo a senha atual antes de
    trocar (diferente de adicionar_usuario, que o admin usa pra resetar a
    senha de qualquer um sem precisar saber a antiga)."""
    email = (email or "").strip().lower()
    usuario = obter_usuario_por_email(email)
    if not usuario:
        raise ValueError("Usuário não encontrado.")

    if not check_password_hash(usuario.get("senha_hash") or "", senha_atual or ""):
        raise ValueError("Senha atual incorreta.")

    if not senha_nova or len(senha_nova) < 4:
        raise ValueError("A nova senha precisa ter pelo menos 4 caracteres.")

    adicionar_usuario(email, usuario.get("nome"), usuario.get("papel"), criado_por=email, senha=senha_nova)


def excluir_usuario(email):
    garantir_tabela_usuarios()
    client = get_bigquery_client()
    table_id = f"{PROJECT}.{DATASET}.{TABELA_USUARIOS}"
    _remover_usuario(client, table_id, email)
    invalidar_tudo()


def _remover_usuario(client, table_id, email):
    """DELETE com fallback via CREATE OR REPLACE TABLE (DDL) caso o
    projeto não tenha billing habilitado (mesmo padrão dos outros módulos)."""
    tabela = f"`{table_id}`"
    email_normalizado = email.strip().lower()

    try:
        query = f"DELETE FROM {tabela} WHERE email = @email"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("email", "STRING", email_normalizado)]
        )
        client.query(query, job_config=job_config).result()

    except Exception as exc:  # noqa: BLE001
        if not erro_e_de_billing(exc):
            raise

        rebuild_query = f"CREATE OR REPLACE TABLE {tabela} AS SELECT * FROM {tabela} WHERE email != @email"
        job_config2 = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("email", "STRING", email_normalizado)]
        )
        client.query(rebuild_query, job_config=job_config2).result()
