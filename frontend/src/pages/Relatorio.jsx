import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Download } from "../components/icons";
import { mesBr, mesAtual } from "../utils/format";

async function buscarBancos() {
  const { data } = await api.get("/bancos");
  return data;
}

async function buscarMeses() {
  const { data } = await api.get("/relatorio/meses");
  return data;
}

export default function Relatorio() {
  const atual = mesAtual();
  const [banco, setBanco] = useState("");
  const [mesInicio, setMesInicio] = useState(atual);
  const [mesFim, setMesFim] = useState(atual);
  const [codMaster, setCodMaster] = useState("");
  const [codIndicado, setCodIndicado] = useState("");
  const [contagem, setContagem] = useState(null);
  const [carregandoContagem, setCarregandoContagem] = useState(false);
  const [baixando, setBaixando] = useState(false);
  const [erro, setErro] = useState(null);

  const { data: bancos = [] } = useQuery({ queryKey: ["bancos"], queryFn: buscarBancos });
  const { data: meses = [] } = useQuery({ queryKey: ["relatorio-meses"], queryFn: buscarMeses });
  const mesesDisponiveis = [...meses].sort().reverse();

  function montarParams() {
    const params = { mes_inicio: mesInicio, mes_fim: mesFim };
    if (banco) params.banco = banco;
    if (codMaster) params.cod_master = codMaster;
    if (codIndicado) params.cod_indicado = codIndicado;
    return params;
  }

  async function handleAtualizarContagem(e) {
    e.preventDefault();
    setCarregandoContagem(true);
    setErro(null);
    try {
      const { data } = await api.get("/relatorio/contagem", { params: montarParams() });
      setContagem(data.total);
    } catch (err) {
      setErro(err?.response?.data?.erro || err.message);
    } finally {
      setCarregandoContagem(false);
    }
  }

  async function handleBaixar() {
    setBaixando(true);
    setErro(null);
    try {
      const response = await api.get("/relatorio/download", { params: montarParams(), responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      const dataStr = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
      link.setAttribute("download", `relatorio_producao_${dataStr}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setErro("Não foi possível gerar o arquivo.");
    } finally {
      setBaixando(false);
    }
  }

  return (
    <div className="fade-in">
      <PageHeader icon={<Download />} title="Relatório" subtitle="Baixe a produção do período em Excel." />

      <form onSubmit={handleAtualizarContagem} className="card card-fit">
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
            <label>Cód. Master</label>
            <input type="text" value={codMaster} onChange={(e) => setCodMaster(e.target.value)} placeholder="opcional" />
          </div>
          <div className="form-row">
            <label>Cód. Indicado</label>
            <input type="text" value={codIndicado} onChange={(e) => setCodIndicado(e.target.value)} placeholder="opcional" />
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <div className="filter-actions">
              <button type="submit" disabled={carregandoContagem}>
                {carregandoContagem ? "Atualizando…" : "Atualizar agora"}
              </button>
              <button type="button" onClick={handleBaixar} disabled={baixando}>
                <Download /> {baixando ? "Gerando…" : "Baixar .xlsx"}
              </button>
            </div>
          </div>
        </div>
      </form>

      {erro && (
        <div className="card error-card">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{erro}</p>
        </div>
      )}

      {contagem !== null && !erro && (
        <div className="card status-card-ok">
          <p style={{ margin: 0 }}>
            <span className="status-dot ok" />
            {contagem} registro(s) encontrado(s) para esse filtro.
          </p>
        </div>
      )}
    </div>
  );
}
