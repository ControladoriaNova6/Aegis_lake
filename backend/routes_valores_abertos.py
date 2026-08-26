from flask import Blueprint, request, jsonify

from routes_auth import requer_papel, usuario_atual
from lib.valores_abertos import (
    listar_valores_abertos,
    criar_lancamento,
    marcar_recebido,
    reabrir_lancamento,
    resumo_valores_abertos,
    CATEGORIAS_VALIDAS,
)

bp_valores_abertos = Blueprint("valores_abertos", __name__, url_prefix="/api")

PAPEIS_PERMITIDOS = ["admin", "editor"]


@bp_valores_abertos.route("/valores-abertos")
@requer_papel(PAPEIS_PERMITIDOS)
def valores_abertos_listar():
    try:
        return jsonify(listar_valores_abertos())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_valores_abertos.route("/valores-abertos/categorias")
@requer_papel(PAPEIS_PERMITIDOS)
def valores_abertos_categorias():
    return jsonify(CATEGORIAS_VALIDAS)


@bp_valores_abertos.route("/valores-abertos/resumo")
@requer_papel(PAPEIS_PERMITIDOS)
def valores_abertos_resumo():
    try:
        return jsonify(resumo_valores_abertos())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_valores_abertos.route("/valores-abertos", methods=["POST"])
@requer_papel(PAPEIS_PERMITIDOS)
def valores_abertos_criar():
    dados = request.get_json(silent=True) or {}
    campanha_id = dados.get("campanha_id")
    try:
        novo_id = criar_lancamento(dados, criado_por=usuario_atual()["email"], campanha_id=campanha_id)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"id": novo_id})


@bp_valores_abertos.route("/valores-abertos/<id_>/recebido", methods=["PUT"])
@requer_papel(PAPEIS_PERMITIDOS)
def valores_abertos_marcar_recebido(id_):
    try:
        marcar_recebido(id_, usuario_atual()["email"])
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})


@bp_valores_abertos.route("/valores-abertos/<id_>/reabrir", methods=["PUT"])
@requer_papel(PAPEIS_PERMITIDOS)
def valores_abertos_reabrir(id_):
    try:
        reabrir_lancamento(id_)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})
