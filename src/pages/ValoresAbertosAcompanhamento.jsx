import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { ListIcon } from "../components/icons";
import { brl } from "../utils/format";

async function buscarLancamentos() {
  const { data } = await api.get("/valores-abertos");
  return data;
}

function formatarData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR");
}

export default function ValoresAbertosAcompanhamento() {
  const queryClient = useQueryClient();
  const [filtroStatus, setFiltroStatus] = useState("aberto");
  const [mensagem, setMensagem] = useState(null);

  const { data: lancamentos = [], isLoading, isError, error } = useQuery({
    queryKey: ["valores-abertos"],
    queryFn: buscarLancamentos,
  });

  function invalidar() {
    queryClient.invalidateQueries({ queryKey: ["valores-abertos"] });
  }

  const recebidoMutation = useMutation({
    mutationFn: (id) => api.put(`/valores-abertos/${id}/recebido`),
    onSuccess: () => {
      invalidar();
      setMensagem({ ok: true, texto: "Marcado como recebido." });
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const reabrirMutation = useMutation({
    mutationFn: (id) => api.put(`/valores-abertos/${id}/reabrir`),
    onSuccess: () => {
      invalidar();
      setMensagem({ ok: true, texto: "Lançamento voltou para em aberto." });
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const filtrados = lancamentos.filter((l) => (filtroStatus === "todos" ? true : l.status === filtroStatus));
  const hoje = new Date().toISOString().slice(0, 10);

  return (
    <div className="fade-in">
      <PageHeader
        icon={<ListIcon />}
        title="Valores em aberto — Acompanhamento"
        subtitle="Todos os lançamentos, quem cadastrou, quem recebeu — e a ação de marcar como recebido."
      />

      {mensagem && (
        <div className={`fade-in ${mensagem.ok ? "card status-card-ok" : "card error-card"}`}>
          {mensagem.ok ? (
            <p style={{ margin: 0 }}><span className="status-dot ok" />{mensagem.texto}</p>
          ) : (
            <><p className="error-title">Não foi possível concluir</p><p className="muted small">{mensagem.texto}</p></>
          )}
        </div>
      )}

      <div className="card card-fit">
        <div className="form-row">
          <label>Status</label>
          <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
            <option value="aberto">Em aberto</option>
            <option value="recebido">Recebidos</option>
            <option value="todos">Todos</option>
          </select>
        </div>
      </div>

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
              <tr>
                <th>Banco</th><th>Categoria</th><th>Período</th><th className="align-right">Valor</th>
                <th>Prevista</th><th>Criado por</th><th>Recebido por</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filtrados.length === 0 && (
                <tr><td colSpan={8} className="muted center">Nenhum lançamento encontrado.</td></tr>
              )}
              {filtrados.map((l) => {
                const atrasado = l.status === "aberto" && l.data_prevista && l.data_prevista < hoje;
                return (
                  <tr key={l.id}>
                    <td className="small">{l.banco}</td>
                    <td className="small">{l.categoria}</td>
                    <td className="small">{l.periodo_ref || "—"}</td>
                    <td className="mono small align-right">{brl(l.valor)}</td>
                    <td className="mono small">
                      {l.data_prevista}
                      {atrasado && <><br /><span style={{ color: "var(--red)", fontSize: "0.7rem" }}>Em atraso</span></>}
                    </td>
                    <td className="small">{l.criado_por}</td>
                    <td className="small">
                      {l.status === "recebido" ? (
                        <>
                          {l.recebido_por}
                          <br />
                          <span className="muted" style={{ fontSize: "0.72rem" }}>{formatarData(l.recebido_em)}</span>
                        </>
                      ) : "—"}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {l.status === "recebido" ? (
                        <button className="btn-link" onClick={() => reabrirMutation.mutate(l.id)}>
                          Voltar para em aberto
                        </button>
                      ) : (
                        <button type="button" onClick={() => recebidoMutation.mutate(l.id)}>
                          Marcar recebido
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
