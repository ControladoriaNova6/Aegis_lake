import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Users, Plus, Trash, Refresh } from "../components/icons";
import { brl, mesBr, mesAtual } from "../utils/format";

async function buscarIndicados(busca) {
  const { data } = await api.get("/indicados", { params: busca ? { q: busca } : {} });
  return data;
}

async function buscarBancos() {
  const { data } = await api.get("/bancos");
  return data;
}

async function buscarMesesIndicados() {
  const { data } = await api.get("/indicados/meses");
  return data;
}

async function buscarDetalhamento({ banco, mesInicio, mesFim }) {
  const params = { mes_inicio: mesInicio, mes_fim: mesFim };
  if (banco) params.banco = banco;
  const { data } = await api.get("/indicados/detalhamento", { params });
  return data;
}

export default function Indicados() {
  const queryClient = useQueryClient();
  const [banco, setBanco] = useState("");
  const [codLoja, setCodLoja] = useState("");
  const [nome, setNome] = useState("");
  const [usuario, setUsuario] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaAtiva, setBuscaAtiva] = useState("");
  const [mensagem, setMensagem] = useState(null);

  const atual = mesAtual();
  const [filtroDetBanco, setFiltroDetBanco] = useState("");
  const [filtroDetMesInicio, setFiltroDetMesInicio] = useState(atual);
  const [filtroDetMesFim, setFiltroDetMesFim] = useState(atual);
  const [detalhamentoAplicado, setDetalhamentoAplicado] = useState({ banco: "", mesInicio: atual, mesFim: atual });

  const { data: bancos = [] } = useQuery({ queryKey: ["bancos"], queryFn: buscarBancos });
  const { data: mesesDetalhamento = [] } = useQuery({ queryKey: ["indicados-meses"], queryFn: buscarMesesIndicados });
  const { data: indicados = [], isLoading, isError, error } = useQuery({
    queryKey: ["indicados", buscaAtiva],
    queryFn: () => buscarIndicados(buscaAtiva),
  });

  const {
    data: detalhamento,
    isLoading: carregandoDetalhamento,
    isError: erroDetalhamento,
    error: erroDetalhamentoMsg,
  } = useQuery({
    queryKey: ["indicados-detalhamento", detalhamentoAplicado.banco, detalhamentoAplicado.mesInicio, detalhamentoAplicado.mesFim],
    queryFn: () => buscarDetalhamento(detalhamentoAplicado),
  });

  function handleAtualizarDetalhamento() {
    setDetalhamentoAplicado({ banco: filtroDetBanco, mesInicio: filtroDetMesInicio, mesFim: filtroDetMesFim });
    queryClient.invalidateQueries({ queryKey: ["indicados-detalhamento"] });
  }

  const adicionarMutation = useMutation({
    mutationFn: (dados) => api.post("/indicados", dados),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indicados"] });
      setMensagem({ ok: true, texto: "Indicado adicionado." });
      setCodLoja("");
      setNome("");
      setUsuario("");
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const excluirMutation = useMutation({
    mutationFn: (id) => api.delete(`/indicados/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indicados"] });
      setMensagem({ ok: true, texto: "Indicado removido." });
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  function handleAdicionar(e) {
    e.preventDefault();
    if (!banco || !usuario) {
      setMensagem({ ok: false, texto: "Preencha ao menos Banco e Usuário." });
      return;
    }
    if (!codLoja && !nome) {
      setMensagem({ ok: false, texto: "Preencha Cód. Loja ou Nome." });
      return;
    }
    adicionarMutation.mutate({ banco, cod_loja: codLoja, nome, usuario });
  }

  function handleBuscar(e) {
    e.preventDefault();
    setBuscaAtiva(busca);
  }

  return (
    <div className="fade-in">
      <PageHeader icon={<Users />} title="Indicados" subtitle="Base de indicados usada como referência (lookup) na importação." />

      {mensagem && (
        <div className={mensagem.ok ? "card status-card-ok" : "card error-card"}>
          {mensagem.ok ? (
            <p style={{ margin: 0 }}><span className="status-dot ok" />{mensagem.texto}</p>
          ) : (
            <><p className="error-title">Não foi possível salvar</p><p className="muted small">{mensagem.texto}</p></>
          )}
        </div>
      )}

      <form onSubmit={handleAdicionar} className="card card-accent-blue" autoComplete="off">
        <div className="filter-grid">
          <div className="form-row">
            <label>Banco</label>
            <select value={banco} onChange={(e) => setBanco(e.target.value)}>
              <option value="">Selecione…</option>
              {bancos.map((b) => <option key={b.valor} value={b.valor}>{b.rotulo}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Cód. Loja</label>
            <input type="text" value={codLoja} onChange={(e) => setCodLoja(e.target.value)} placeholder="opcional se tiver Nome" />
          </div>
          <div className="form-row">
            <label>Nome</label>
            <input type="text" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="opcional se tiver Cód. Loja" />
          </div>
          <div className="form-row">
            <label>Usuário</label>
            <input type="text" value={usuario} onChange={(e) => setUsuario(e.target.value)} />
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <button type="submit" disabled={adicionarMutation.isPending}>
              <Plus /> {adicionarMutation.isPending ? "Salvando…" : "Adicionar"}
            </button>
          </div>
        </div>
      </form>

      <form onSubmit={handleBuscar} className="search-form">
        <input type="text" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por banco, cód. loja, nome ou usuário…" style={{ flex: 1 }} />
        <button type="submit">Buscar</button>
      </form>

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="card table-wrap">
          <table>
            <thead>
              <tr><th>Banco</th><th>Cód. Loja</th><th>Nome</th><th>Usuário</th><th></th></tr>
            </thead>
            <tbody>
              {indicados.length === 0 && (
                <tr><td colSpan={5} className="muted center">Nenhum indicado encontrado.</td></tr>
              )}
              {indicados.map((i) => (
                <tr key={i.id}>
                  <td className="small">{i.banco}</td>
                  <td className="mono small">{i.cod_loja || "—"}</td>
                  <td className="small">{i.nome || "—"}</td>
                  <td className="small">{i.usuario}</td>
                  <td>
                    <button className="btn-danger" onClick={() => excluirMutation.mutate(i.id)}><Trash /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PageHeader
        icon={<Users />}
        title="Detalhamento por indicado"
        subtitle="Produção agrupada por Banco, Indicado (Map Indicado), Convênio e Produto."
      />

      <div className="card card-fit">
        <div className="filter-grid">
          <div className="form-row">
            <label>Banco</label>
            <select value={filtroDetBanco} onChange={(e) => setFiltroDetBanco(e.target.value)}>
              <option value="">Todos</option>
              {bancos.map((b) => <option key={b.valor} value={b.valor}>{b.rotulo}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Período — de</label>
            <select value={filtroDetMesInicio} onChange={(e) => setFiltroDetMesInicio(e.target.value)}>
              {[...mesesDetalhamento].sort().reverse().map((m) => <option key={m} value={m}>{mesBr(m)}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Período — até</label>
            <select value={filtroDetMesFim} onChange={(e) => setFiltroDetMesFim(e.target.value)}>
              {[...mesesDetalhamento].sort().reverse().map((m) => <option key={m} value={m}>{mesBr(m)}</option>)}
            </select>
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <button type="button" onClick={handleAtualizarDetalhamento}>
              <Refresh /> Atualizar agora
            </button>
          </div>
        </div>
      </div>

      <p className="muted small" style={{ margin: "0.75rem 0 1.5rem" }}>
        Mudar o filtro só é aplicado ao clicar em "Atualizar agora". "Indicado" ainda aparece como "(sem indicado)"
        pra produção que não passou pelo cruzamento de dados em Manutenção.
      </p>

      {carregandoDetalhamento && <div className="skeleton-block" />}
      {erroDetalhamento && (
        <div className="card error-card">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{erroDetalhamentoMsg?.response?.data?.erro || erroDetalhamentoMsg?.message}</p>
        </div>
      )}

      {detalhamento && !erroDetalhamento && (
        <div className="card table-wrap">
          <table>
            <thead>
              <tr><th>Banco</th><th>Indicado</th><th>Convênio</th><th>Produto</th><th className="align-right">Produção</th></tr>
            </thead>
            <tbody>
              {detalhamento.linhas.length === 0 && (
                <tr><td colSpan={5} className="muted center">Nenhum dado para os filtros selecionados.</td></tr>
              )}
              {detalhamento.linhas.map((l, idx) => (
                <tr key={idx}>
                  <td className="small">{l.banco}</td>
                  <td className="small">{l.indicado}</td>
                  <td className="small">{l.convenio}</td>
                  <td className="small">{l.produto}</td>
                  <td className="mono small align-right">{brl(l.producao)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
