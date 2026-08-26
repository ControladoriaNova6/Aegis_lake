from flask import Blueprint, request, jsonify

from routes_auth import login_required, requer_papel, usuario_atual
from lib.bancos_config import opcoes_config
from lib.importador import processar_importacao

bp_importar = Blueprint("importar", __name__, url_prefix="/api")


@bp_importar.route("/configs")
@login_required
def configs():
    try:
        opcoes = opcoes_config()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify([{"valor": valor, "rotulo": rotulo} for valor, rotulo in opcoes])


@bp_importar.route("/importar", methods=["POST"])
@requer_papel(["admin", "editor"])
def importar():
    banco_tipo = request.form.get("banco_tipo")
    arquivo = request.files.get("arquivo")

    if not banco_tipo or not arquivo or not arquivo.filename:
        return jsonify({"ok": False, "erro": "Selecione uma configuração e anexe um arquivo."}), 400

    try:
        resultado = processar_importacao(banco_tipo, arquivo, importado_por=usuario_atual()["email"])
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500

    return jsonify(resultado)
