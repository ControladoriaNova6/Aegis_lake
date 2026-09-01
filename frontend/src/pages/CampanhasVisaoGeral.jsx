import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Megaphone, Refresh } from "../components/icons";
import { brl, mesBr, mesAtual, percentual } from "../utils/format";

async function buscarBancos() {
  const { data } = await api.get("/bancos");
  return data;
}

async function buscarMeses() {
  const { data } = await api.get("/relatorio/meses");
  return data;
}

function mesParaDataInicio(mes) {
  return mes ? `${mes}-01` : null;
}

function mesParaDataFim(mes) {
  if (!mes) return null;
  const [ano, m] = mes.split("-").map(Number);
  const ultimoDia = new Date(ano, m, 0).getDate();
  return `${mes}-${String(ultimoDia).padStart(2, "0")}`;
}

async function buscarAtingimento({ banco, mesInicio, mesFim, campanha }) {
  const params = {};
  if (banco) params.banco = banco;
  if (mesInicio) params.data_inicio = mesParaDataInicio(mesInicio);
  if (mesFim) params.data_fim = mesParaDataFim(mesFim);
  if (campanha) params.campanha = campanha;
  const { data } = await api.get("/campanhas/atingimento", { params });
  return data;
}

function StatusChip({ status }) {
  return (
    <>
      <span className={`status-dot ${status === "Vigente" ? "ok" : status === "Finalizada" ? "" : "warn"}`} />
      {status || "Vigente"}
    </>
  );
}

export default function CampanhasVisaoGeral() {
  const queryClient = useQueryClient();
  const atual = mesAtual();

  const [banco, setBanco] = useState("");
  const [mesInicio, setMesInicio] = useState(atual);
  const [mesFim, setMesFim] = useState(atual);
  const [campanha, setCampanha] = useState("");
  const [filtrosAplicados, setFiltrosAplicados] = useState({ banco: "", mesInicio: atual, mesFim: atual, campanha: "" });

  // Controles de exibição da tabela — a quantidade de colunas (3 blocos ×
  // várias métricas) quebra visualmente em telas menores, então dá pra
  // esconder blocos inteiros e/ou reduzir o espaçamento das células.
  const [escala, setEscala] = useState(1);
  const [mostrarProjecao, setMostrarProjecao] = useState(true);
  const [mostrarOportunidades, setMostrarOportunidades] = useState(true);

  const { data: bancos = [] } = useQuery({ queryKey: ["bancos"], queryFn: buscarBancos });
  const { data: meses = [] } = useQuery({ queryKey: ["relatorio-meses"], queryFn: buscarMeses });

  const {
    data: campanhas = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["campanhas-atingimento", filtrosAplicados.banco, filtrosAplicados.mesInicio, filtrosAplicados.mesFim, filtrosAplicados.campanha],
    queryFn: () => buscarAtingimento(filtrosAplicados),
  });

  function handleAtualizar() {
    setFiltrosAplicados({ banco, mesInicio, mesFim, campanha });
    queryClient.invalidateQueries({ queryKey: ["campanhas-atingimento"] });
  }

  const mesesDisponiveis = [...meses].sort().reverse();
  const somaValorCampanha = campanhas.reduce((soma, c) => soma + (c.valor_campanha_atual || 0), 0);
  const somaProvisoes = campanhas.reduce((soma, c) => soma + (c.valor_campanha_previsto || 0), 0);
  const ativas = campanhas.filter((c) => c.status === "Vigente");

  return (
    <div className="fade-in">
      <PageHeader icon={<Megaphone />} title="Campanhas — Visão geral" subtitle="Produção real do período comparada às faixas de meta de cada campanha." />

      <div className="card card-fit">
        <p className="section-label">Filtros</p>
        <div className="filter-grid">
          <div className="form-row">
            <label>Banco</label>
            <select value={banco} onChange={(e) => setBanco(e.target.value)}>
              <option value="">Todos</option>
              {bancos.map((b) => <option key={b.valor} value={b.valor}>{b.rotulo}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Período — de</label>
            <select value={mesInicio} onChange={(e) => setMesInicio(e.target.value)}>
              {mesesDisponiveis.map((m) => <option key={m} value={m}>{mesBr(m)}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Período — até</label>
            <select value={mesFim} onChange={(e) => setMesFim(e.target.value)}>
              {mesesDisponiveis.map((m) => <option key={m} value={m}>{mesBr(m)}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Campanha</label>
            <input type="text" value={campanha} onChange={(e) => setCampanha(e.target.value)} placeholder="Buscar por nome…" />
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <button type="button" onClick={handleAtualizar}>
              <Refresh /> Atualizar agora
            </button>
          </div>
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
        <>
          <div className="kpi-grid">
            <div className="card kpi-card card-accent-teal">
              <p className="kpi-label">Soma de valor de campanha (produção no período)</p>
              <p className="kpi-value">{brl(somaValorCampanha)}</p>
            </div>
            <div className="card kpi-card card-accent-blue">
              <p className="kpi-label">Soma Provisões (projeção até o fim da campanha)</p>
              <p className="kpi-value">{brl(somaProvisoes)}</p>
            </div>
            <div className="card kpi-card card-accent-accent">
              <p className="kpi-label">Campanhas Ativas</p>
              <p className="kpi-value">{ativas.length}</p>
            </div>
          </div>

          <div className="card table-wrap-x">
            <div className="table-toolbar">
              <p className="section-label" style={{ margin: 0 }}>Campanhas no período filtrado</p>
              <div className="table-toolbar-controls">
                <label className="table-toolbar-checkbox">
                  <input type="checkbox" checked={mostrarProjecao} onChange={(e) => setMostrarProjecao(e.target.checked)} />
                  Projeção
                </label>
                <label className="table-toolbar-checkbox">
                  <input type="checkbox" checked={mostrarOportunidades} onChange={(e) => setMostrarOportunidades(e.target.checked)} />
                  Oportunidades
                </label>
                <label className="table-toolbar-slider">
                  Densidade
                  <input
                    type="range"
                    min="0.8"
                    max="1.3"
                    step="0.05"
                    value={escala}
                    onChange={(e) => setEscala(Number(e.target.value))}
                  />
                </label>
              </div>
            </div>
            <table className="table-blocos" style={{ "--tabela-escala": escala }}>
              <thead>
                <tr>
                  <th rowSpan={2}>Banco</th>
                  <th rowSpan={2}>Campanha</th>
                  <th rowSpan={2}>Convênio</th>
                  <th rowSpan={2}>Produto</th>
                  <th rowSpan={2}>Status</th>
                  <th colSpan={4} className="bloco-header bloco-atual bloco-divisor">Cenário Atual</th>
                  {mostrarProjecao && <th colSpan={5} className="bloco-header bloco-projecao bloco-divisor">Projeção</th>}
                  {mostrarOportunidades && <th colSpan={5} className="bloco-header bloco-oportunidade bloco-divisor">Oportunidades</th>}
                </tr>
                <tr>
                  {/* Cenário Atual */}
                  <th className="align-right bloco-atual bloco-divisor">Produção</th>
                  <th className="align-right bloco-atual">Valor Campanha</th>
                  <th className="align-right bloco-atual">Faixa</th>
                  <th className="align-right bloco-atual">Meta</th>
                  {/* Projeção */}
                  {mostrarProjecao && (
                    <>
                      <th className="align-right bloco-projecao bloco-divisor">Produção</th>
                      <th className="align-right bloco-projecao">Valor Campanha</th>
                      <th className="align-right bloco-projecao">Faixa</th>
                      <th className="align-right bloco-projecao">Meta</th>
                      <th className="align-right bloco-projecao">% Atingimento</th>
                    </>
                  )}
                  {/* Oportunidades */}
                  {mostrarOportunidades && (
                    <>
                      <th className="align-right bloco-oportunidade bloco-divisor">Produção nec.</th>
                      <th className="align-right bloco-oportunidade">Faixa</th>
                      <th className="align-right bloco-oportunidade">Meta</th>
                      <th className="align-right bloco-oportunidade">Valor Campanha</th>
                      <th className="align-right bloco-oportunidade">% Atingimento</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {campanhas.length === 0 && (
                  <tr><td colSpan={5 + 4 + (mostrarProjecao ? 5 : 0) + (mostrarOportunidades ? 5 : 0)} className="muted center">Nenhuma campanha encontrada para esse filtro.</td></tr>
                )}
                {campanhas.map((c) => (
                  <tr key={c.id}>
                    <td className="small">{c.banco}</td>
                    <td className="small">{c.campanha}</td>
                    <td className="small">{c.filtro_map_convenio?.length ? c.filtro_map_convenio.join(", ") : "Todos"}</td>
                    <td className="small">{c.filtro_map_produto?.length ? c.filtro_map_produto.join(", ") : "Todos"}</td>
                    <td className="small"><StatusChip status={c.status} /></td>

                    {/* Cenário Atual */}
                    <td className="mono small align-right bloco-atual bloco-divisor">{brl(c.producao_atual)}</td>
                    <td className="mono small align-right bloco-atual">{brl(c.valor_campanha_atual)}</td>
                    <td className="mono small align-right bloco-atual">{percentual(c.faixa_atingida || 0)}</td>
                    <td className="mono small align-right bloco-atual">{brl(c.meta_atingida)}</td>

                    {/* Projeção */}
                    {mostrarProjecao && (
                      <>
                        <td className="mono small align-right bloco-projecao bloco-divisor">{brl(c.producao_prevista)}</td>
                        <td className="mono small align-right bloco-projecao">{brl(c.valor_campanha_previsto)}</td>
                        <td className="mono small align-right bloco-projecao">{percentual(c.faixa_prevista || 0)}</td>
                        <td className="mono small align-right bloco-projecao">{brl(c.meta_prevista_valor)}</td>
                        <td className="mono small align-right bloco-projecao">{percentual(c.percentual_atingimento_projecao)}</td>
                      </>
                    )}

                    {/* Oportunidades */}
                    {mostrarOportunidades && (
                      c.teto_atingido ? (
                        <td colSpan={5} className="small bloco-oportunidade bloco-divisor">
                          Teto da campanha atingido
                        </td>
                      ) : (
                        <>
                          <td className="mono small align-right bloco-oportunidade bloco-divisor">{c.producao_necessaria_oportunidade != null ? brl(c.producao_necessaria_oportunidade) : "—"}</td>
                          <td className="mono small align-right bloco-oportunidade">{c.proxima_faixa != null ? percentual(c.proxima_faixa) : "—"}</td>
                          <td className="mono small align-right bloco-oportunidade">{c.proxima_meta != null ? brl(c.proxima_meta) : "—"}</td>
                          <td className="mono small align-right bloco-oportunidade">{c.valor_campanha_oportunidade != null ? brl(c.valor_campanha_oportunidade) : "—"}</td>
                          <td className="mono small align-right bloco-oportunidade">{percentual(c.percentual_atingimento_oportunidade)}</td>
                        </>
                      )
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
