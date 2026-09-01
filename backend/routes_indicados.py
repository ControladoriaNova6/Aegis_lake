import io

from flask import Blueprint, request, jsonify, send_file

from routes_auth import login_required, requer_papel
from lib.indicados import listar_indicados, adicionar_indicado, excluir_indicado
from lib.bancos_config import opcoes_banco_distintos
from lib.dashboard import (
    detalhamento_indicados,
    detalhamento_indicados_flat,
    listar_meses_disponiveis,
    mes_atual,
    expandir_intervalo_meses,
)

bp_indicados = Blueprint("indicados", __name__, url_prefix="/api")


@bp_indicados.route("/indicados")
@requer_papel(["admin", "editor"])
def indicados_listar():
    busca = request.args.get("q") or None
    try:
        return jsonify(listar_indicados(busca=busca))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_indicados.route("/indicados/detalhamento")
@requer_papel(["admin", "editor"])
def indicados_detalhamento():
    """Banco > Indicado > Convênio > Produto (hierárquico, com subtotal em
    cada nível) — só produção de indicados já cadastrados. Usado na tela
    de Indicados."""
    banco = request.args.get("banco") or None
    mes_inicio = request.args.get("mes_inicio") or mes_atual()
    mes_fim = request.args.get("mes_fim") or mes_atual()
    meses = expandir_intervalo_meses(mes_inicio, mes_fim)

    try:
        bancos = detalhamento_indicados(banco, meses)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    return jsonify({"bancos": bancos, "mes_inicio": mes_inicio, "mes_fim": mes_fim})


@bp_indicados.route("/indicados/detalhamento/download")
@requer_papel(["admin", "editor"])
def indicados_detalhamento_download():
    """Mesma consulta do detalhamento, em .xlsx pra baixar."""
    import pandas as pd
    from datetime import datetime

    banco = request.args.get("banco") or None
    mes_inicio = request.args.get("mes_inicio") or mes_atual()
    mes_fim = request.args.get("mes_fim") or mes_atual()
    meses = expandir_intervalo_meses(mes_inicio, mes_fim)

    try:
        linhas = detalhamento_indicados_flat(banco, meses)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    df = pd.DataFrame(linhas, columns=["banco", "indicado", "convenio", "produto", "producao"])
    df = df.rename(columns={
        "banco": "Banco", "indicado": "Indicado", "convenio": "Convênio",
        "produto": "Produto", "producao": "Produção",
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Detalhamento")
        workbook = writer.book
        worksheet = writer.sheets["Detalhamento"]
        formato_moeda = workbook.add_format({"num_format": "R$ #,##0.00"})
        worksheet.set_column("A:D", 22)
        worksheet.set_column("E:E", 16, formato_moeda)

    buffer.seek(0)
    nome_arquivo = f"detalhamento_indicados_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp_indicados.route("/indicados/meses")
@requer_papel(["admin", "editor"])
def indicados_meses():
    try:
        return jsonify(listar_meses_disponiveis())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500


@bp_indicados.route("/indicados", methods=["POST"])
@requer_papel(["admin", "editor"])
def indicados_adicionar():
    dados = request.get_json(silent=True) or {}
    banco = (dados.get("banco") or "").strip()
    cod_loja = dados.get("cod_loja")
    nome = dados.get("nome")
    usuario = (dados.get("usuario") or "").strip()

    if not banco or not usuario:
        return jsonify({"ok": False, "erro": "Preencha ao menos Banco e Usuário."}), 400
    if not cod_loja and not nome:
        return jsonify({"ok": False, "erro": "Preencha Cód. Loja ou Nome."}), 400

    try:
        adicionar_indicado(banco, cod_loja, nome, usuario)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500

    return jsonify({"ok": True})


@bp_indicados.route("/indicados/<id_>", methods=["DELETE"])
@requer_papel(["admin", "editor"])
def indicados_excluir(id_):
    try:
        excluir_indicado(id_)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "erro": str(exc)}), 500
    return jsonify({"ok": True})
