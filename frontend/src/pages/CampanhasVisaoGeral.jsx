import { useQuery } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Megaphone } from "../components/icons";
import { brl } from "../utils/format";

async function buscarCampanhas() {
  const { data } = await api.get("/campanhas");
  return data;
}

async function buscarCriterios() {
  const { data } = await api.get("/criterios");
  return data;
}

export default function CampanhasVisaoGeral() {
  const { data: campanhas = [], isLoading, isError, error } = useQuery({
    queryKey: ["campanhas"],
    queryFn: buscarCampanhas,
  });
  const { data: criterios = [] } = useQuery({ queryKey: ["criterios"], queryFn: buscarCriterios });

  const vigentes = campanhas.filter((c) => c.status === "Vigente");

  return (
    <div className="fade-in">
      <PageHeader icon={<Megaphone />} title="Campanhas — Visão geral" subtitle="Consolidado do que foi cadastrado." />

      {isLoading && <div className="skeleton-block" />}

      {isError && (
        <div className="card error-card fade-in">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          <div className="kpi-grid">
            <div className="card kpi-card card-accent-teal">
              <p className="kpi-label">Campanhas cadastradas</p>
              <p className="kpi-value">{campanhas.length}</p>
            </div>
            <div className="card kpi-card card-accent-blue">
              <p className="kpi-label">Campanhas vigentes</p>
              <p className="kpi-value">{vigentes.length}</p>
            </div>
            <div className="card kpi-card card-accent-accent">
              <p className="kpi-label">Critérios cadastrados</p>
              <p className="kpi-value">{criterios.length}</p>
            </div>
          </div>

          <div className="card">
            <p className="section-label">Campanhas cadastradas</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Banco</th>
                    <th>Campanha</th>
                    <th>Período</th>
                    <th>Faixas → metas</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {campanhas.length === 0 && (
                    <tr>
                      <td colSpan={5} className="muted center">Nenhuma campanha cadastrada ainda.</td>
                    </tr>
                  )}
                  {campanhas.map((c) => (
                    <tr key={c.id}>
                      <td className="small">{c.banco}</td>
                      <td className="small">{c.campanha}</td>
                      <td className="mono small">{c.data_inicio || ""} — {c.data_fim || ""}</td>
                      <td className="mono small">
                        {(c.faixas_metas || []).map((fm) => `${brl(fm.faixa)} → ${brl(fm.meta)}`).join(" | ") || "—"}
                      </td>
                      <td className="small">
                        <span className={`status-dot ${c.status === "Vigente" ? "ok" : c.status === "Finalizada" ? "" : "warn"}`} />
                        {c.status || "Vigente"}
                      </td>
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
