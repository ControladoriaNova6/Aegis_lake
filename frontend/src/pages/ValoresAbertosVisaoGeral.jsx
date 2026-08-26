import { useQuery } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Grid } from "../components/icons";
import { brl } from "../utils/format";

async function buscarResumo() {
  const { data } = await api.get("/valores-abertos/resumo");
  return data;
}

export default function ValoresAbertosVisaoGeral() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["valores-abertos-resumo"],
    queryFn: buscarResumo,
  });

  return (
    <div className="fade-in">
      <PageHeader
        icon={<Grid />}
        title="Valores em aberto — Visão geral"
        subtitle="Panorama de recebimentos pendentes, previstos para hoje e em atraso."
      />

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card fade-in">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {data && !isError && (
        <>
          <div className="kpi-grid">
            <div className="card kpi-card card-accent-teal">
              <p className="kpi-label">Total pendente ({data.pendente_qtd} lançamento(s))</p>
              <p className="kpi-value">{brl(data.pendente_total)}</p>
            </div>
            <div className="card kpi-card card-accent-blue">
              <p className="kpi-label">Previsto para hoje</p>
              <p className="kpi-value">{brl(data.hoje_total)}</p>
            </div>
            <div className="card kpi-card card-accent-accent">
              <p className="kpi-label">Em atraso</p>
              <p className="kpi-value" style={{ color: data.atraso_total > 0 ? "var(--red)" : undefined }}>
                {brl(data.atraso_total)}
              </p>
            </div>
          </div>

          <div className="card">
            <p className="section-label">Previsto para hoje</p>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Banco</th><th>Categoria</th><th>Período</th><th className="align-right">Valor</th></tr></thead>
                <tbody>
                  {data.hoje_lista.length === 0 && (
                    <tr><td colSpan={4} className="muted center">Nada previsto para hoje.</td></tr>
                  )}
                  {data.hoje_lista.map((l) => (
                    <tr key={l.id}>
                      <td className="small">{l.banco}</td>
                      <td className="small">{l.categoria}</td>
                      <td className="small">{l.periodo_ref || "—"}</td>
                      <td className="mono small align-right">{brl(l.valor)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <p className="section-label">Em atraso</p>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Banco</th><th>Categoria</th><th>Período</th><th>Prevista</th><th className="align-right">Valor</th></tr></thead>
                <tbody>
                  {data.atraso_lista.length === 0 && (
                    <tr><td colSpan={5} className="muted center">Nenhum valor em atraso.</td></tr>
                  )}
                  {data.atraso_lista.map((l) => (
                    <tr key={l.id}>
                      <td className="small">{l.banco}</td>
                      <td className="small">{l.categoria}</td>
                      <td className="small">{l.periodo_ref || "—"}</td>
                      <td className="mono small" style={{ color: "var(--red)" }}>{l.data_prevista}</td>
                      <td className="mono small align-right">{brl(l.valor)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
