from flask import Blueprint, request, jsonify

from routes_auth import requer_papel, usuario_atual
from lib.mapeamento_categorias import (
    listar_categorias,
    criar_categoria,
    excluir_categoria,
    listar_regras,
    criar_regra,
    excluir_regra,
    executar_mapeamento,
    listar_registros_mapeamento,
    LOCAIS_VALIDOS,
)

bp_mapeamento_categorias = Blueprint("mapeamento_categorias", __name__, url_prefix="/api")

# Só Admin — essa tela mexe direto na base consolidada (dado bruto do
# data lake), e o resultado dela é usado por Campanhas, Indicados etc.
PAPEIS = ["admin"]


@bp_mapeamento_categorias.route("/mapeamento/categorias")
@requer_papel(PAPEIS)
def mapeamento_categorias_listar():
    try:
        return jsonify(listar_categorias())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_mapeamento_categorias.route("/mapeamento/categorias", methods=["POST"])
@requer_papel(PAPEIS)
def mapeamento_categorias_criar():
    dados = request.get_json(silent=True) or {}
    try:
        novo_id = criar_categoria(
            dados.get("nome"), dados.get("local_enquadramento"), criado_por=usuario_atual()["email"],
        )
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"id": novo_id})


@bp_mapeamento_categorias.route("/mapeamento/categorias/<id_>", methods=["DELETE"])
@requer_papel(PAPEIS)
def mapeamento_categorias_excluir(id_):
    try:
        excluir_categoria(id_, executado_por=usuario_atual()["email"])
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})


@bp_mapeamento_categorias.route("/mapeamento/regras")
@requer_papel(PAPEIS)
def mapeamento_regras_listar():
    categoria_id = request.args.get("categoria_id") or None
    try:
        return jsonify(listar_regras(categoria_id=categoria_id))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_mapeamento_categorias.route("/mapeamento/regras", methods=["POST"])
@requer_papel(PAPEIS)
def mapeamento_regras_criar():
    dados = request.get_json(silent=True) or {}
    try:
        novo_id = criar_regra(
            dados.get("categoria_id"),
            dados.get("descricao"),
            bool(dados.get("busca_convenio")),
            bool(dados.get("busca_produto")),
            bool(dados.get("busca_tabela")),
            criado_por=usuario_atual()["email"],
        )
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"id": novo_id})


@bp_mapeamento_categorias.route("/mapeamento/regras/<id_>", methods=["DELETE"])
@requer_papel(PAPEIS)
def mapeamento_regras_excluir(id_):
    try:
        excluir_regra(id_, executado_por=usuario_atual()["email"])
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})


@bp_mapeamento_categorias.route("/mapeamento/executar", methods=["POST"])
@requer_papel(PAPEIS)
def mapeamento_executar():
    """Roda o motor manualmente — esse é o único jeito de disparar esse
    motor agora (não roda mais sozinho após uma importação; ver histórico
    de decisão no chat/commit). `local` opcional no corpo ("map_convenio"
    ou "map_produto") pra rodar só um dos dois."""
    dados = request.get_json(silent=True) or {}
    local = dados.get("local") or None
    if local and local not in LOCAIS_VALIDOS:
        return jsonify({"erro": f'"local" inválido — use um de: {", ".join(LOCAIS_VALIDOS)}.'}), 400

    try:
        resultado = executar_mapeamento(local, executado_por=usuario_atual()["email"])
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True, "resultado": resultado})


@bp_mapeamento_categorias.route("/mapeamento/registros")
@requer_papel(PAPEIS)
def mapeamento_registros_listar():
    """Histórico (append-only) de execuções do motor e exclusões de
    categoria/regra — pra auditar quem fez o quê e quando, já que o
    mapeamento nunca deve ser sobrescrito silenciosamente."""
    try:
        return jsonify(listar_registros_mapeamento())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
