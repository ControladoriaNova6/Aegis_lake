import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { ListIcon, Trash, Refresh } from "../components/icons";
import { useAuth } from "../context/AuthContext";

async function buscarLogs(busca) {
  const { data } = await api.get("/logs", { params: busca ? { q: busca } : {} });
  return data;
}

function formatarData(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR");
}

export default function Registros() {
  const queryClient = useQueryClient();
  const { usuario } = useAuth();
  const podeExcluir = usuario?.papel === "admin" || usuario?.papel === "editor";
  const [busca, setBusca] = useState("");
  const [buscaAtiva, setBuscaAtiva] = useState("");
  const [mensagem, setMensagem] = useState(null);

  const { data: logs = [], isLoading, isError, error } = useQuery({
    queryKey: ["logs", buscaAtiva],
    queryFn: () => buscarLogs(buscaAtiva),
  });

  const excluirMutation = useMutation({
    mutationFn: (log) => api.post("/logs/excluir", { log_id: log.log_id, banco_nome: log.banco_nome, arquivo_nome: log.arquivo_nome }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["logs"] });
      setMensagem({ ok: true, texto: `Removidas ${res.data.linhas_removidas} linha(s).` });
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  function handleBuscar(e) {
    e.preventDefault();
    setBuscaAtiva(busca);
  }

  function handleAtualizar() {
    queryClient.invalidateQueries({ queryKey: ["logs"] });
  }

  function handleExcluir(log) {
    if (!window.confirm(`Remover as linhas importadas em "${log.arquivo_original}" (${log.banco_nome})? Essa ação não pode ser desfeita.`)) {
      return;
    }
    excluirMutation.mutate(log);
  }

  return (
    <div className="fade-in">
      <PageHeader icon={<ListIcon />} title="Registros" subtitle="Histórico de importações — busque e exclua lotes." />

      <form onSubmit={handleBuscar} className="search-form">
        <input type="text" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por arquivo ou banco…" style={{ flex: 1 }} />
        <button type="submit">Buscar</button>
        <button type="button" onClick={handleAtualizar}><Refresh /> Atualizar agora</button>
      </form>

      {mensagem && (
        <div className={`fade-in ${mensagem.ok ? "card status-card-ok" : "card error-card"}`}>
          {mensagem.ok ? (
            <p style={{ margin: 0 }}><span className="status-dot ok" />{mensagem.texto}</p>
          ) : (
            <><p className="error-title">Não foi possível excluir</p><p className="muted small">{mensagem.texto}</p></>
          )}
        </div>
      )}

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card fade-in">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="card table-wrap fade-in" style={{ maxHeight: 640 }}>
          <table>
            <thead>
              <tr>
                <th>Data</th><th>Banco</th><th>Arquivo</th><th>Status</th><th>Importado por</th>
                <th className="align-right">Linhas</th><th className="align-right">Inseridas</th><th></th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr><td colSpan={8} className="muted center">Nenhum registro encontrado.</td></tr>
              )}
              {logs.map((log) => {
                const excluido = log.status === "revertido";
                return (
                  <tr key={log.log_id}>
                    <td className="mono small">{formatarData(log.timestamp)}</td>
                    <td className="small">{log.banco_nome}</td>
                    <td className="small">
                      {log.arquivo_original}
                      <br />
                      <span className="muted" style={{ fontSize: "0.72rem" }}>{log.arquivo_nome}</span>
                    </td>
                    <td className="small">
                      <span className={`status-dot ${log.status === "sucesso" ? "ok" : log.status === "erro" ? "err" : ""}`} />
                      {log.status}
                    </td>
                    <td className="small">{log.importado_por || "—"}</td>
                    <td className="mono small align-right">{log.total_linhas_arquivo}</td>
                    <td className="mono small align-right">{log.linhas_inseridas}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {excluido ? (
                        <span className="muted small">
                          Excluído por {log.excluido_por || "—"}
                          {log.excluido_em && <><br />{formatarData(log.excluido_em)}</>}
                        </span>
                      ) : (
                        podeExcluir && (
                          <button
                            className="btn-danger"
                            title="Excluir linhas dessa importação"
                            style={{ marginLeft: "0.5rem" }}
                            onClick={() => handleExcluir(log)}
                          >
                            <Trash />
                          </button>
                        )
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
