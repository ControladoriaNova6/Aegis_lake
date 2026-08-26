from flask import Blueprint, jsonify

from routes_auth import login_required, requer_papel
from lib.manutencao import executar_cruzamento_indicado, listar_valores_mapeados

bp_manutencao = Blueprint("manutencao", __name__, url_prefix="/api")


@bp_manutencao.route("/manutencao/cruzar-indicado", methods=["POST"])
@requer_papel(["admin"])
def manutencao_cruzar_indicado():
    try:
        resultado = executar_cruzamento_indicado()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500
    return jsonify({"ok": True, **resultado})


@bp_manutencao.route("/manutencao/valores-mapeados")
@login_required
def manutencao_valores_mapeados():
    """Usado pelo Cadastro de Campanha pra popular os filtros opcionais
    de produção (Map Indicado/Convênio/Produto). Aberto a qualquer
    usuário logado (não só admin), já que Editor também cadastra
    campanha."""
    try:
        return jsonify(listar_valores_mapeados())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
