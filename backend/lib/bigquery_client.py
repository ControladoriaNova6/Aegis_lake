import json
import os

from google.cloud import bigquery
from google.oauth2 import service_account

_client = None


def get_bigquery_client() -> bigquery.Client:
    """
    Retorna um cliente BigQuery único (singleton) para toda a aplicação.

    Suporta dois modos de autenticação:

    1) GOOGLE_CREDENTIALS_JSON — conteúdo INTEIRO do arquivo JSON da service
       account, colado como string em uma env var. É o modo recomendado para
       rodar na Vercel, já que lá não existe sistema de arquivos persistente
       para apontar um caminho de credenciais.

    2) GOOGLE_APPLICATION_CREDENTIALS — caminho para o arquivo .json na sua
       máquina. Mais simples para rodar localmente (é o padrão das
       bibliotecas do Google, então basta exportar essa variável).

    Use qualquer um dos dois — o código detecta automaticamente. Se nenhum
    estiver configurado corretamente, levanta um erro específico em
    português (em vez de deixar o erro genérico do Google, em inglês,
    aparecer sem contexto nenhum na tela)."""
    global _client
    if _client is not None:
        return _client

    project_id = os.environ.get("BIGQUERY_PROJECT_ID")
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not project_id:
        raise RuntimeError(
            "BIGQUERY_PROJECT_ID não está definido. Confira se o arquivo .env.local "
            "existe na raiz do projeto (mesma pasta do app.py) e se essa variável "
            "está preenchida lá."
        )

    if credentials_json:
        try:
            info = json.loads(credentials_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_CREDENTIALS_JSON não é um JSON válido. Confirme que "
                "colou o conteúdo completo do arquivo da service account."
            ) from exc

        credentials = service_account.Credentials.from_service_account_info(info)
        _client = bigquery.Client(
            project=project_id or info.get("project_id"),
            credentials=credentials,
        )

    elif credentials_path:
        if not os.path.isfile(credentials_path):
            raise RuntimeError(
                f'GOOGLE_APPLICATION_CREDENTIALS aponta para "{credentials_path}", mas esse '
                "arquivo não foi encontrado nesse caminho. Confira se o caminho ainda está "
                "correto — é comum isso quebrar depois de mover a pasta do projeto ou da "
                "credencial pra outro lugar."
            )
        _client = bigquery.Client(project=project_id)

    else:
        raise RuntimeError(
            "Nenhuma credencial do Google Cloud foi encontrada. No arquivo .env.local "
            "(na raiz do projeto, mesma pasta do app.py), preencha UMA destas duas opções:\n"
            "  - GOOGLE_APPLICATION_CREDENTIALS=caminho\\para\\sua-service-account.json\n"
            '  - GOOGLE_CREDENTIALS_JSON=<conteúdo inteiro do .json colado em uma linha só>\n'
            'Confira também se o arquivo se chama exatamente ".env.local" (não ".env.local.txt", '
            "erro comum quando ele é criado pelo Bloco de Notas)."
        )

    return _client


def erro_e_de_billing(exc):
    """Detecta se um erro do BigQuery é a restrição de 'DML não permitido
    sem billing habilitado' (comum em projetos no modo sandbox/gratuito),
    para que quem chama possa usar um caminho alternativo via DDL."""
    texto = str(exc).lower()
    return "billing" in texto or "dml queries are not allowed" in texto
