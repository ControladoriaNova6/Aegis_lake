import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { ListIcon } from "../components/icons";

async function buscarAuditoria() {
  const { data } = await api.get("/criterios/auditoria");
  return data;
}

const ACAO_LABEL = { criado: "Criado", editado: "Editado", excluido: "Excluído" };

export default function CriteriosHistorico() {
  const { data: eventos = [], isLoading, isError, error } = useQuery({
    queryKey: ["criterios-auditoria"],
    queryFn: buscarAuditoria,
  });

  return (
    <div className="fade-in">
      <PageHeader
        icon={<ListIcon />}
        title="Histórico de critérios"
        subtitle="Registro de cada alteração feita nos critérios de campanhas."
        action={<Link to="/campanhas/criterios" className="btn-link">Voltar pra Critérios</Link>}
      />

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card fade-in">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="card table-wrap fade-in">
          <table>
            <thead>
              <tr><th>Data</th><th>Ação</th><th>Convênio / Produto</th><th>Usuário</th></tr>
            </thead>
            <tbody>
              {eventos.length === 0 && (
                <tr><td colSpan={4} className="muted center">Nenhuma alteração registrada ainda.</td></tr>
              )}
              {eventos.map((ev) => (
                <tr key={ev.id}>
                  <td className="mono small">{ev.timestamp ? new Date(ev.timestamp).toLocaleString("pt-BR") : ""}</td>
                  <td className="small">{ACAO_LABEL[ev.acao] || ev.acao}</td>
                  <td className="small">{ev.dados?.convenio || "—"} / {ev.dados?.produto || "—"}</td>
                  <td className="small">{ev.usuario || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
