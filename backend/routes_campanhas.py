from flask import Blueprint, request, jsonify

from routes_auth import login_required, requer_papel, usuario_atual
from lib.campanhas import (
    listar_campanhas,
    salvar_campanha,
    excluir_campanha,
    atualizar_status_campanha,
    listar_criterios,
    salvar_criterio,
    excluir_criterio,
    listar_auditoria_criterios,
    listar_campanhas_com_atingimento,
    CAMPOS_CAMPANHA,
    CAMPOS_CRITERIO,
    CAMPOS_FILTRO_PRODUCAO,
    STATUS_CAMPANHA_VALIDOS,
)

bp_campanhas = Blueprint("campanhas", __name__, url_prefix="/api")


# ─────────────────────────────────────────────────────────────────────────
# Campanhas
# ─────────────────────────────────────────────────────────────────────────
@bp_campanhas.route("/campanhas", methods=["GET"])
@login_required
def campanhas_listar():
    try:
        return jsonify(listar_campanhas())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_campanhas.route("/campanhas/atingimento")
@login_required
def campanhas_atingimento():
    """Campanhas + produção real do período + avaliação de faixa/meta —
    usado na Visão geral de Campanhas (cards e tabela)."""
    banco = request.args.get("banco") or None
    data_inicio = request.args.get("data_inicio") or None
    data_fim = request.args.get("data_fim") or None
    busca_campanha = request.args.get("campanha") or None

    try:
        linhas = listar_campanhas_com_atingimento(
            banco=banco, data_inicio=data_inicio, data_fim=data_fim, busca_campanha=busca_campanha,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    return jsonify(linhas)


@bp_campanhas.route("/campanhas", methods=["POST"])
@requer_papel(["admin", "editor"])
def campanhas_criar():
    dados = request.get_json(silent=True) or {}
    if not dados.get("banco") or not dados.get("campanha"):
        return jsonify({"erro": "Preencha ao menos Banco e Campanha."}), 400

    corpo = {campo: dados.get(campo) for campo in CAMPOS_CAMPANHA}
    corpo["faixas_metas"] = dados.get("faixas_metas") or []
    for campo in CAMPOS_FILTRO_PRODUCAO:
        corpo[campo] = dados.get(campo) or []
    try:
        novo_id = salvar_campanha(corpo, criado_por=usuario_atual()["email"])
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"id": novo_id})


@bp_campanhas.route("/campanhas/<id_campanha>", methods=["PUT"])
@requer_papel(["admin", "editor"])
def campanhas_editar(id_campanha):
    dados = request.get_json(silent=True) or {}
    if not dados.get("banco") or not dados.get("campanha"):
        return jsonify({"erro": "Preencha ao menos Banco e Campanha."}), 400

    corpo = {campo: dados.get(campo) for campo in CAMPOS_CAMPANHA}
    corpo["faixas_metas"] = dados.get("faixas_metas") or []
    for campo in CAMPOS_FILTRO_PRODUCAO:
        corpo[campo] = dados.get(campo) or []
    try:
        salvar_campanha(corpo, criado_por=usuario_atual()["email"], id_existente=id_campanha)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"id": id_campanha})


@bp_campanhas.route("/campanhas/<id_campanha>/status", methods=["PUT"])
@requer_papel(["admin", "editor"])
def campanhas_trocar_status(id_campanha):
    dados = request.get_json(silent=True) or {}
    novo_status = dados.get("status")
    if novo_status not in STATUS_CAMPANHA_VALIDOS:
        return jsonify({"erro": f'Status inválido. Use um de: {", ".join(STATUS_CAMPANHA_VALIDOS)}.'}), 400

    try:
        atualizar_status_campanha(id_campanha, novo_status, atualizado_por=usuario_atual()["email"])
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})


@bp_campanhas.route("/campanhas/<id_campanha>", methods=["DELETE"])
@requer_papel(["admin", "editor"])
def campanhas_excluir(id_campanha):
    try:
        excluir_campanha(id_campanha)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# Critérios
# ─────────────────────────────────────────────────────────────────────────
@bp_campanhas.route("/criterios", methods=["GET"])
@login_required
def criterios_listar():
    try:
        return jsonify(listar_criterios())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_campanhas.route("/criterios", methods=["POST"])
@requer_papel(["admin", "editor"])
def criterios_criar():
    dados = request.get_json(silent=True) or {}
    if not dados.get("banco") or not dados.get("campanha"):
        return jsonify({"erro": "Preencha ao menos Banco e Campanha."}), 400

    # A "Tabela" aceita vários códigos separados por ";" — cada código
    # vira um critério (linha) separado, com os demais campos repetidos.
    tabela_bruta = (dados.get("tabela") or "").strip()
    codigos_tabela = [c.strip() for c in tabela_bruta.split(";") if c.strip()] or [""]

    ids_criados = []
    ultimo_erro = None
    for codigo in codigos_tabela:
        corpo = {campo: dados.get(campo) for campo in CAMPOS_CRITERIO}
        corpo["tabela"] = codigo
        try:
            novo_id = salvar_criterio(corpo, criado_por=usuario_atual()["email"])
            ids_criados.append(novo_id)
        except ValueError as exc:
            ultimo_erro = str(exc)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"erro": str(exc)}), 500

    if not ids_criados:
        return jsonify({"erro": ultimo_erro or "Não foi possível salvar."}), 400

    return jsonify({"id": ids_criados[0], "ids": ids_criados, "total_criados": len(ids_criados)})


@bp_campanhas.route("/criterios/<id_criterio>", methods=["PUT"])
@requer_papel(["admin", "editor"])
def criterios_editar(id_criterio):
    dados = request.get_json(silent=True) or {}
    if not dados.get("banco") or not dados.get("campanha"):
        return jsonify({"erro": "Preencha ao menos Banco e Campanha."}), 400

    corpo = {campo: dados.get(campo) for campo in CAMPOS_CRITERIO}
    try:
        salvar_criterio(corpo, criado_por=usuario_atual()["email"], id_existente=id_criterio)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"id": id_criterio})


@bp_campanhas.route("/criterios/<id_criterio>", methods=["DELETE"])
@requer_papel(["admin", "editor"])
def criterios_excluir(id_criterio):
    try:
        excluir_criterio(id_criterio, excluido_por=usuario_atual()["email"])
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"ok": True})


@bp_campanhas.route("/criterios/auditoria", methods=["GET"])
@login_required
def criterios_auditoria():
    campanha_id = request.args.get("campanha_id") or None
    try:
        return jsonify(listar_auditoria_criterios(campanha_id=campanha_id))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
