from flask import Blueprint, request, jsonify

from routes_auth import login_required
from lib.dashboard import (
    listar_meses_disponiveis,
    resumo_por_dia,
    resumo_hierarquico,
    mes_atual,
    projecao_mes_atual,
    expandir_intervalo_meses,
)

bp_dashboard = Blueprint("dashboard", __name__, url_prefix="/api")


@bp_dashboard.route("/dashboard")
@login_required
def dashboard():
    banco = request.args.get("banco") or None
    mes_inicio = request.args.get("mes_inicio") or mes_atual()
    mes_fim = request.args.get("mes_fim") or mes_atual()

    meses_selecionados = expandir_intervalo_meses(mes_inicio, mes_fim)

    try:
        meses_disponiveis = listar_meses_disponiveis()
        dados_diarios = resumo_por_dia(banco, meses_selecionados)
        arvore = resumo_hierarquico(banco, meses_selecionados)
        projecao = projecao_mes_atual(banco)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    total_periodo = sum(d["total"] for d in dados_diarios)
    media_diaria = (total_periodo / len(dados_diarios)) if dados_diarios else 0

    return jsonify({
        "banco": banco or "",
        "mes_inicio": mes_inicio,
        "mes_fim": mes_fim,
        "meses_disponiveis": meses_disponiveis,
        "dados_diarios": dados_diarios,
        "arvore": arvore,
        "projecao": projecao,
        "total_periodo": total_periodo,
        "media_diaria": media_diaria,
    })
