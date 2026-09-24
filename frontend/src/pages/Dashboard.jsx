import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Plot from "react-plotly.js";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Grid, Refresh, DollarSign, TrendingUp, Calendar } from "../components/icons";
import { brl, mesBr, mesAtual } from "../utils/format";

async function buscarBancos() {
  const { data } = await api.get("/bancos");
  return data;
}

async function buscarValoresMapeados() {
  const { data } = await api.get("/manutencao/valores-mapeados");
  return data;
}

async function buscarDashboard({ banco, mesInicio, mesFim, produto, nomeConvenio }) {
  const params = {};
  if (banco) params.banco = banco;
  if (mesInicio) params.mes_inicio = mesInicio;
  if (mesFim) params.mes_fim = mesFim;
  if (produto) params.produto = produto;
  if (nomeConvenio) params.nome_convenio = nomeConvenio;
  const { data } = await api.get("/dashboard", { params });
  return data;
}

function Accordion({ arvore }) {
  if (!arvore || arvore.length === 0) {
    return <p className="muted center" style={{ padding: "1.5rem 0" }}>Nenhum dado para os filtros selecionados.</p>;
  }
  return (
    <div className="accordion">
      {arvore.map((bancoItem) => (
        <details key={bancoItem.nome} className="accordion-item level-banco">
          <summary>
            <span>{bancoItem.nome}</span>
            <span className="mono">{brl(bancoItem.total)}</span>
          </summary>
          <div className="accordion-body">
            {bancoItem.convenios.map((conv) => (
              <details key={conv.nome} className="accordion-item level-convenio">
                <summary>
                  <span>{conv.nome}</span>
                  <span className="mono">{brl(conv.total)}</span>
                </summary>
                <div className="accordion-body">
                  <table>
                    <thead>
                      <tr>
                        <th>Produto</th>
                        <th className="align-right">Produção</th>
                      </tr>
                    </thead>
                    <tbody>
                      {conv.produtos.map((p) => (
                        <tr key={p.nome}>
                          <td>{p.nome}</td>
                          <td className="mono align-right">{brl(p.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const queryClient = useQueryClient();
  const atual = mesAtual();

  // Filtros "em edição" — mudam a cada clique no select, mas NÃO disparam
  // consulta nenhuma sozinhos.
  const [banco, setBanco] = useState("");
  const [mesInicio, setMesInicio] = useState(atual);
  const [mesFim, setMesFim] = useState(atual);
  const [produto, setProduto] = useState("");
  const [nomeConvenio, setNomeConvenio] = useState("");

  // Filtros REALMENTE aplicados na consulta — só mudam quando a pessoa
  // clica em "Atualizar agora". É isso que vai na queryKey.
  const [filtrosAplicados, setFiltrosAplicados] = useState({
    banco: "", mesInicio: atual, mesFim: atual, produto: "", nomeConvenio: "",
  });

  const { data: bancos = [] } = useQuery({ queryKey: ["bancos"], queryFn: buscarBancos });
  const { data: valoresMapeados = { map_produto: [] } } = useQuery({
    queryKey: ["valores-mapeados"],
    queryFn: buscarValoresMapeados,
  });

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery({
    // A chave inclui os filtros APLICADOS — cada combinação fica guardada
    // separadamente. Voltar pra uma combinação já vista antes é
    // instantâneo, sem nenhuma chamada nova ao servidor.
    queryKey: [
      "dashboard",
      filtrosAplicados.banco, filtrosAplicados.mesInicio, filtrosAplicados.mesFim,
      filtrosAplicados.produto, filtrosAplicados.nomeConvenio,
    ],
    queryFn: () => buscarDashboard(filtrosAplicados),
  });

  function handleAtualizar() {
    setFiltrosAplicados({ banco, mesInicio, mesFim, produto, nomeConvenio });
    // Garante que essa combinação específica seja buscada de novo mesmo
    // que já tivesse sido vista antes na sessão (o botão é "Atualizar
    // agora", não "usar o que já tem em cache").
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }

  const dadosDiarios = [...(data?.dados_diarios || [])].sort((a, b) => (a.dia > b.dia ? 1 : -1));
  const mesesDisponiveis = [...(data?.meses_disponiveis || [])].sort().reverse();
  const participacaoPorBanco = [...(data?.arvore || [])]
    .map((b) => ({ nome: b.nome, total: b.total }))
    .sort((a, b) => b.total - a.total);
  const totalGeralBancos = participacaoPorBanco.reduce((soma, b) => soma + b.total, 0);

  return (
    <div className="fade-in">
      <PageHeader
        icon={<Grid />}
        eyebrow="Painel de produção"
        title="Visão geral"
        subtitle="Produção líquida por dia, banco, convênio e produto."
      />

      <div className="card card-fit">
        <div className="filter-grid">
          <div className="form-row">
            <label>Banco</label>
            <select value={banco} onChange={(e) => setBanco(e.target.value)}>
              <option value="">Todos</option>
              {bancos.map((b) => (
                <option key={b.valor} value={b.valor}>{b.rotulo}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Período — de</label>
            <select value={mesInicio} onChange={(e) => setMesInicio(e.target.value)}>
              {mesesDisponiveis.map((m) => (
                <option key={m} value={m}>{mesBr(m)}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Período — até</label>
            <select value={mesFim} onChange={(e) => setMesFim(e.target.value)}>
              {mesesDisponiveis.map((m) => (
                <option key={m} value={m}>{mesBr(m)}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Produto</label>
            <select value={produto} onChange={(e) => setProduto(e.target.value)}>
              <option value="">Todos</option>
              {valoresMapeados.map_produto.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Nome Convênio</label>
            <input
              type="text"
              value={nomeConvenio}
              onChange={(e) => setNomeConvenio(e.target.value)}
              placeholder="Busca pelo nome original do convênio"
            />
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <div className="filter-actions">
              <button type="button" onClick={handleAtualizar}>
                <Refresh /> Atualizar agora
              </button>
            </div>
          </div>
        </div>
      </div>

      {isLoading && <div className="skeleton-block" />}

      {isError && (
        <div className="card error-card">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {data && !isError && (
        <>
          <div className="kpi-grid">
            <div className="card kpi-card card-accent">
              <div className="kpi-card-header">
                <p className="kpi-label">Produção líquida (período selecionado)</p>
                <span className="kpi-icon"><DollarSign /></span>
              </div>
              <p className="kpi-value">{brl(data.total_periodo)}</p>
            </div>
            <div className="card kpi-card">
              <div className="kpi-card-header">
                <p className="kpi-label">Produção / dia (média do período)</p>
                <span className="kpi-icon"><TrendingUp /></span>
              </div>
              <p className="kpi-value">{brl(data.media_diaria)}</p>
            </div>
            <div className="card kpi-card">
              <div className="kpi-card-header">
                <p className="kpi-label">Projeção produção — fim do mês</p>
                <span className="kpi-icon"><Calendar /></span>
              </div>
              <p className="kpi-value">{brl(data.projecao)}</p>
            </div>
          </div>

          <div className="split-grid">
            <div className="card">
              <p className="section-label">Produção líquida por dia{filtrosAplicados.banco ? ` · ${filtrosAplicados.banco}` : ""}</p>
              <Plot
                data={[
                  {
                    x: dadosDiarios.map((d) => d.dia),
                    y: dadosDiarios.map((d) => d.total),
                    type: "scatter",
                    mode: "lines+markers",
                    line: { color: "#6366f1", width: 2 },
                    marker: { size: 4, color: "#6366f1" },
                    fill: "tozeroy",
                    fillcolor: "rgba(99, 102, 241, 0.12)",
                    hovertemplate: "%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>",
                  },
                ]}
                layout={{
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { color: "#E4E7EE", family: "'DM Sans', -apple-system, sans-serif", size: 12 },
                  margin: { l: 40, r: 20, t: 20, b: 40 },
                  xaxis: {
                    gridcolor: "#232B3D",
                    zerolinecolor: "#232B3D",
                    linecolor: "#232B3D",
                    tickformat: "%d/%m",
                    hoverformat: "%d/%m/%Y",
                  },
                  yaxis: { gridcolor: "#232B3D", zerolinecolor: "#232B3D", linecolor: "#232B3D" },
                  hoverlabel: { bgcolor: "#1a2030", bordercolor: "#232B3D", font: { color: "#E4E7EE" } },
                  height: 300,
                  showlegend: false,
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: "100%" }}
              />
            </div>

            <div className="card">
              <p className="section-label">Participação por banco{filtrosAplicados.banco ? "" : " · produção líquida consolidada"}</p>
              {participacaoPorBanco.length === 0 ? (
                <p className="muted center" style={{ padding: "1.5rem 0" }}>Nenhum dado para os filtros selecionados.</p>
              ) : (
                <div className="participacao-lista">
                  {participacaoPorBanco.map((b) => {
                    const pct = totalGeralBancos > 0 ? (b.total / totalGeralBancos) * 100 : 0;
                    return (
                      <div key={b.nome}>
                        <div className="participacao-item-topo">
                          <span className="participacao-nome">{b.nome}</span>
                          <span className="participacao-pct">{pct.toFixed(1)}%</span>
                        </div>
                        <div className="participacao-barra-trilha">
                          <div className="participacao-barra-preenchida" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="participacao-valor">{brl(b.total)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <p className="section-label">Produção por banco, convênio e produto</p>
            <Accordion arvore={data.arvore} />
          </div>
        </>
      )}
    </div>
  );
}
