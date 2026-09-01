import io
from datetime import datetime

import pandas as pd
from flask import Blueprint, request, jsonify, send_file

from routes_auth import login_required, requer_papel
from lib.relatorio import limites_do_intervalo, contar_relatorio, gerar_relatorio_df, COLUNAS_DATA
from lib.dashboard import listar_meses_disponiveis, mes_atual

bp_relatorio = Blueprint("relatorio", __name__, url_prefix="/api")


def _params_do_request(args):
    banco = args.get("banco") or None
    mes_inicio = args.get("mes_inicio") or mes_atual()
    mes_fim = args.get("mes_fim") or mes_atual()
    cod_master = args.get("cod_master") or None
    cod_indicado = args.get("cod_indicado") or None
    data_inicio, data_fim = limites_do_intervalo(mes_inicio, mes_fim)
    return banco, data_inicio, data_fim, cod_master, cod_indicado, mes_inicio, mes_fim


@bp_relatorio.route("/relatorio/meses")
@requer_papel(["admin", "editor"])
def relatorio_meses():
    try:
        meses = listar_meses_disponiveis()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify(meses)


@bp_relatorio.route("/relatorio/contagem")
@requer_papel(["admin", "editor"])
def relatorio_contagem():
    banco, data_inicio, data_fim, cod_master, cod_indicado, mes_inicio, mes_fim = _params_do_request(request.args)
    try:
        total = contar_relatorio(banco, data_inicio, data_fim, cod_master, cod_indicado)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500
    return jsonify({"total": total, "mes_inicio": mes_inicio, "mes_fim": mes_fim})


@bp_relatorio.route("/relatorio/download")
@requer_papel(["admin", "editor"])
def relatorio_download():
    banco, data_inicio, data_fim, cod_master, cod_indicado, _, _ = _params_do_request(request.args)

    try:
        df = gerar_relatorio_df(banco, data_inicio, data_fim, cod_master, cod_indicado)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 500

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Relatório")
        workbook = writer.book
        worksheet = writer.sheets["Relatório"]
        formato_data = workbook.add_format({"num_format": "dd/mm/yyyy"})

        for idx, coluna in enumerate(df.columns):
            if coluna in COLUNAS_DATA:
                worksheet.set_column(idx, idx, 14, formato_data)
            else:
                worksheet.set_column(idx, idx, 16)

    buffer.seek(0)
    nome_arquivo = f"relatorio_producao_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
