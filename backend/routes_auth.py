import functools

from flask import Blueprint, request, session, jsonify

from lib.usuarios import verificar_login, redefinir_propria_senha

bp_auth = Blueprint("auth", __name__, url_prefix="/api")


@bp_auth.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not email or not senha:
        return jsonify({"erro": "Informe e-mail e senha."}), 400

    try:
        usuario = verificar_login(email, senha)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": f"Não deu para consultar o BigQuery: {exc}"}), 500

    if not usuario:
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401

    session["usuario"] = usuario
    return jsonify(usuario)


@bp_auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp_auth.route("/me")
def me():
    usuario = session.get("usuario")
    if not usuario:
        return jsonify({"erro": "Não autenticado."}), 401
    return jsonify(usuario)


@bp_auth.route("/me/senha", methods=["POST"])
def trocar_minha_senha():
    usuario = session.get("usuario")
    if not usuario:
        return jsonify({"erro": "Não autenticado."}), 401

    dados = request.get_json(silent=True) or {}
    senha_atual = dados.get("senha_atual") or ""
    senha_nova = dados.get("senha_nova") or ""

    try:
        redefinir_propria_senha(usuario["email"], senha_atual, senha_nova)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": f"Não deu para consultar o BigQuery: {exc}"}), 500

    return jsonify({"ok": True})


def login_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("usuario"):
            return jsonify({"erro": "Não autenticado."}), 401
        return func(*args, **kwargs)

    return wrapper


def requer_papel(papeis_permitidos):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            usuario = session.get("usuario")
            if not usuario:
                return jsonify({"erro": "Não autenticado."}), 401
            if usuario.get("papel") not in papeis_permitidos:
                return jsonify({"erro": "Você não tem permissão para fazer isso."}), 403
            return func(*args, **kwargs)

        return wrapper

    return decorator


def usuario_atual():
    return session.get("usuario")
