from flask import Blueprint, request, jsonify

from routes_auth import requer_papel, usuario_atual
from lib.usuarios import listar_usuarios, adicionar_usuario, excluir_usuario, PAPEIS_VALIDOS

bp_usuarios = Blueprint("usuarios", __name__, url_prefix="/api")


@bp_usuarios.route("/usuarios", methods=["GET"])
@requer_papel(["admin"])
def usuarios_listar():
    try:
        usuarios = listar_usuarios()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    # nunca devolve o hash da senha pro front
    return jsonify([{k: v for k, v in u.items() if k != "senha_hash"} for u in usuarios])


@bp_usuarios.route("/usuarios", methods=["POST"])
@requer_papel(["admin"])
def usuarios_salvar():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    nome = dados.get("nome") or email
    papel = dados.get("papel")
    senha = dados.get("senha") or None

    if not email or "@" not in email:
        return jsonify({"erro": "Informe um e-mail válido."}), 400
    if papel not in PAPEIS_VALIDOS:
        return jsonify({"erro": "Papel inválido."}), 400

    try:
        adicionar_usuario(email, nome, papel, criado_por=usuario_atual()["email"], senha=senha)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    return jsonify({"ok": True})


@bp_usuarios.route("/usuarios/<email>", methods=["DELETE"])
@requer_papel(["admin"])
def usuarios_excluir(email):
    email = email.strip().lower()
    if email == usuario_atual()["email"]:
        return jsonify({"erro": "Você não pode excluir seu próprio usuário."}), 400

    try:
        excluir_usuario(email)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    return jsonify({"ok": True})
