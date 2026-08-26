from flask import Blueprint, request, jsonify

from routes_auth import login_required, requer_papel, usuario_atual
from lib.logs import listar_logs, excluir_por_log

bp_logs = Blueprint("logs", __name__, url_prefix="/api")


@bp_logs.route("/logs")
@login_required
def logs_listar():
    busca = request.args.get("q") or None
    try:
        return jsonify(listar_logs(busca=busca))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_logs.route("/logs/excluir", methods=["POST"])
@requer_papel(["admin", "editor"])
def logs_excluir():
    dados = request.get_json(silent=True) or {}
    log_id = dados.get("log_id")
    banco_nome = dados.get("banco_nome")
    arquivo_nome = dados.get("arquivo_nome")

    if not log_id or not banco_nome or not arquivo_nome:
        return jsonify({"ok": False, "erro": "Dados insuficientes para excluir."}), 400

    try:
        linhas_removidas = excluir_por_log(log_id, banco_nome, arquivo_nome, excluido_por=usuario_atual()["email"])
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500

    return jsonify({"ok": True, "linhas_removidas": linhas_removidas})
