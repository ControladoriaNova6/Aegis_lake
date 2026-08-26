from flask import Blueprint, jsonify

from routes_auth import login_required
from lib.bancos_config import opcoes_banco_distintos

bp_bancos = Blueprint("bancos", __name__, url_prefix="/api")


@bp_bancos.route("/bancos")
@login_required
def bancos():
    try:
        opcoes = opcoes_banco_distintos()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify([{"valor": valor, "rotulo": rotulo} for valor, rotulo in opcoes])
