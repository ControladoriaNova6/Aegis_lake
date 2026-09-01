from flask import Blueprint, request, jsonify

from routes_auth import login_required, requer_papel
from lib.mapeamento import (
    montar_grid_mapeamento,
    definir_linha_completa,
    excluir_todos_mapeamentos_do_banco,
    gerar_banco_tipo,
    banco_ja_existe,
    CAMPOS_MAPEAVEIS,
    CAMPOS_SEMPRE_OBRIGATORIOS,
    GRUPOS_ALTERNATIVOS_OBRIGATORIOS,
)

bp_parametros = Blueprint("parametros", __name__, url_prefix="/api")


@bp_parametros.route("/parametros")
@requer_papel(["admin", "editor"])
def parametros_listar():
    try:
        grid = montar_grid_mapeamento()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    return jsonify({
        "grid": grid,
        "campos_mapeaveis": CAMPOS_MAPEAVEIS,
        "campos_sempre_obrigatorios": CAMPOS_SEMPRE_OBRIGATORIOS,
        "grupos_alternativos": GRUPOS_ALTERNATIVOS_OBRIGATORIOS,
    })


@bp_parametros.route("/parametros", methods=["POST"])
@requer_papel(["admin", "editor"])
def parametros_salvar():
    dados = request.get_json(silent=True) or {}
    banco_tipo = (dados.get("banco_tipo") or "").strip()
    banco_nome = (dados.get("banco_nome") or "").strip()
    config_nome = (dados.get("config_nome") or "").strip()
    campos = {campo: dados.get(campo, "") for campo in CAMPOS_MAPEAVEIS}

    if not banco_nome:
        return jsonify({"ok": False, "erro": "Informe o nome do banco."}), 400
    if not config_nome:
        return jsonify({"ok": False, "erro": "Informe o nome da configuração."}), 400

    eh_novo = not banco_tipo
    if eh_novo:
        banco_tipo = gerar_banco_tipo(config_nome)
        if banco_ja_existe(banco_tipo):
            return jsonify({
                "ok": False,
                "erro": f'Já existe uma configuração chamada "{config_nome}". Use um nome diferente.',
            }), 400

    try:
        erros = definir_linha_completa(banco_tipo, banco_nome, config_nome, campos)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500

    if erros:
        return jsonify({"ok": False, "erro": " ".join(erros)}), 400

    return jsonify({"ok": True, "banco_tipo": banco_tipo})


@bp_parametros.route("/parametros/<banco_tipo>", methods=["DELETE"])
@requer_papel(["admin", "editor"])
def parametros_excluir(banco_tipo):
    try:
        excluir_todos_mapeamentos_do_banco(banco_tipo)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500
    return jsonify({"ok": True})
