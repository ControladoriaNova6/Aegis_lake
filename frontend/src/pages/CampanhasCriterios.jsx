import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import { Settings, Plus, Trash } from "../components/icons";
import { percentual } from "../utils/format";

const FORM_VAZIO = {
  prod_cod: "", convenio: "", produto: "", valor_base: "liquido", tabela: "", descr_tabela: "",
  prazo_min: "", prazo_max: "", valor_min: "", valor_max: "", data_inicio: "", data_fim: "",
  status: "ativo", perc_especial: "",
};

const CAMPOS_NUMERO = ["prazo_min", "prazo_max", "valor_min", "valor_max", "perc_especial"];

async function buscarCampanhas() {
  const { data } = await api.get("/campanhas");
  return data;
}
async function buscarCriterios() {
  const { data } = await api.get("/criterios");
  return data;
}
async function buscarBancos() {
  const { data } = await api.get("/bancos");
  return data;
}

function bloqueado(status) {
  return status === "Finalizada" || status === "Em Apuração";
}

export default function CampanhasCriterios() {
  const queryClient = useQueryClient();
  const [filtroBanco, setFiltroBanco] = useState("");
  const [filtroCampanha, setFiltroCampanha] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [modalCampanha, setModalCampanha] = useState(null);
  const [editandoCriterioId, setEditandoCriterioId] = useState(null);
  const [form, setForm] = useState(FORM_VAZIO);
  const [mensagem, setMensagem] = useState(null);

  const { data: campanhas = [], isLoading, isError, error } = useQuery({ queryKey: ["campanhas"], queryFn: buscarCampanhas });
  const { data: criterios = [] } = useQuery({ queryKey: ["criterios"], queryFn: buscarCriterios });
  const { data: bancos = [] } = useQuery({ queryKey: ["bancos"], queryFn: buscarBancos });

  const campanhasFiltradas = campanhas.filter((c) => {
    if (filtroBanco && c.banco !== filtroBanco) return false;
    if (filtroCampanha && !c.campanha.toLowerCase().includes(filtroCampanha.toLowerCase())) return false;
    if (filtroStatus && c.status !== filtroStatus) return false;
    return true;
  });

  function criteriosDaCampanha(campanhaId) {
    return criterios.filter((c) => c.campanha_id === campanhaId);
  }

  function invalidar() {
    queryClient.invalidateQueries({ queryKey: ["criterios"] });
  }

  const salvarMutation = useMutation({
    mutationFn: ({ id, dados }) => (id ? api.put(`/criterios/${id}`, dados) : api.post("/criterios", dados)),
    onSuccess: (res) => {
      invalidar();
      const total = res?.data?.total_criados;
      setMensagem({
        ok: true,
        texto: total && total > 1 ? `${total} critérios salvos (um por código informado em Tabela).` : "Critério salvo.",
      });
      fecharModal();
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const excluirMutation = useMutation({
    mutationFn: (id) => api.delete(`/criterios/${id}`),
    onSuccess: () => {
      invalidar();
      setMensagem({ ok: true, texto: "Critério removido." });
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  function abrirNovoCriterio(campanha) {
    setModalCampanha(campanha);
    setEditandoCriterioId(null);
    setForm({ ...FORM_VAZIO, valor_base: campanha.base_producao || "liquido" });
    setMensagem(null);
  }

  function abrirEditarCriterio(campanha, criterio) {
    setModalCampanha(campanha);
    setEditandoCriterioId(criterio.id);
    const novo = { ...FORM_VAZIO };
    Object.keys(FORM_VAZIO).forEach((campo) => {
      if (campo === "valor_base") {
        novo[campo] = criterio.valor_base || campanha.base_producao || "liquido";
        return;
      }
      novo[campo] = criterio[campo] ?? (campo === "status" ? "ativo" : "");
    });
    setForm(novo);
    setMensagem(null);
  }

  function fecharModal() {
    setModalCampanha(null);
    setEditandoCriterioId(null);
    setForm(FORM_VAZIO);
  }

  function handleChange(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  function handleSalvar(e) {
    e.preventDefault();
    const dados = {
      campanha_id: modalCampanha.id,
      banco: modalCampanha.banco,
      campanha: modalCampanha.campanha,
      ...form,
    };
    CAMPOS_NUMERO.forEach((c) => {
      dados[c] = dados[c] === "" ? null : Number(dados[c]);
    });
    salvarMutation.mutate({ id: editandoCriterioId, dados });
  }

  function handleExcluirCriterio(id) {
    if (window.confirm("Remover este critério?")) {
      excluirMutation.mutate(id);
    }
  }

  return (
    <div className="fade-in">
      <PageHeader
        icon={<Settings />}
        title="Critérios"
        subtitle="Regras de negócio que ligam cada campanha a convênio/produto/tabela."
        action={<Link to="/campanhas/criterios/historico" className="btn-link">Ver histórico de alterações</Link>}
      />

      {mensagem && (
        <div className={`fade-in ${mensagem.ok ? "card status-card-ok" : "card error-card"}`}>
          {mensagem.ok ? (
            <p style={{ margin: 0 }}><span className="status-dot ok" />{mensagem.texto}</p>
          ) : (
            <><p className="error-title">Não foi possível salvar</p><p className="muted small">{mensagem.texto}</p></>
          )}
        </div>
      )}

      <div className="card card-fit">
        <p className="section-label">Filtros</p>
        <div className="filter-grid">
          <div className="form-row">
            <label>Banco</label>
            <select value={filtroBanco} onChange={(e) => setFiltroBanco(e.target.value)}>
              <option value="">Todos</option>
              {bancos.map((b) => <option key={b.valor} value={b.valor}>{b.rotulo}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Campanha</label>
            <input type="text" value={filtroCampanha} onChange={(e) => setFiltroCampanha(e.target.value)} placeholder="Buscar por nome…" />
          </div>
          <div className="form-row">
            <label>Status</label>
            <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
              <option value="">Todos</option>
              <option value="Vigente">Vigente</option>
              <option value="Finalizada">Finalizada</option>
              <option value="Em Apuração">Em Apuração</option>
            </select>
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
        <div className="card table-wrap fade-in">
          <table>
            <thead>
              <tr><th>Banco</th><th>Campanha</th><th>Status</th><th>Critérios cadastrados</th><th></th></tr>
            </thead>
            <tbody>
              {campanhasFiltradas.length === 0 && (
                <tr><td colSpan={5} className="muted center">Nenhuma campanha encontrada.</td></tr>
              )}
              {campanhasFiltradas.map((c) => {
                const criteriosDela = criteriosDaCampanha(c.id);
                const trava = bloqueado(c.status);
                return (
                  <tr key={c.id}>
                    <td className="small">{c.banco}</td>
                    <td className="small">{c.campanha}</td>
                    <td className="small">
                      <span className={`status-dot ${c.status === "Vigente" ? "ok" : c.status === "Finalizada" ? "" : "warn"}`} />
                      {c.status}
                    </td>
                    <td className="small">{criteriosDela.length}</td>
                    <td>
                      <button
                        className="btn-link"
                        disabled={trava}
                        title={trava ? `Não é possível editar critérios de campanha ${c.status}` : "Cadastrar critério"}
                        onClick={() => abrirNovoCriterio(c)}
                      >
                        <Plus /> Cadastrar critério
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {modalCampanha && (
        <Modal onClose={fecharModal} width={620}>
            <p className="section-title" style={{ marginTop: 0 }}>
              {editandoCriterioId ? "Editar" : "Novo"} critério — {modalCampanha.campanha}
            </p>

            <form onSubmit={handleSalvar}>
              <table className="form-table">
                <tbody>
                  <tr>
                    <td className="form-table-label">Cód. produto</td>
                    <td><input type="text" value={form.prod_cod} onChange={(e) => handleChange("prod_cod", e.target.value)} /></td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Convênio</td>
                    <td><input type="text" value={form.convenio} onChange={(e) => handleChange("convenio", e.target.value)} /></td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Produto</td>
                    <td><input type="text" value={form.produto} onChange={(e) => handleChange("produto", e.target.value)} /></td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Valor base</td>
                    <td>
                      <select value={form.valor_base} onChange={(e) => handleChange("valor_base", e.target.value)}>
                        <option value="liquido">Líquido (vlr_liquido)</option>
                        <option value="bruto">Bruto (vlr_bruto)</option>
                      </select>
                    </td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Tabela</td>
                    <td>
                      <input
                        type="text"
                        value={form.tabela}
                        onChange={(e) => handleChange("tabela", e.target.value)}
                        placeholder="ex: 59855;569856;5895"
                      />
                      <span className="muted small" style={{ display: "block", marginTop: "0.25rem" }}>
                        Pra cadastrar vários códigos de uma vez, separe por <span className="mono">;</span> — cada um vira
                        um critério.
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Descr. tabela</td>
                    <td><input type="text" value={form.descr_tabela} onChange={(e) => handleChange("descr_tabela", e.target.value)} /></td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Prazo (meses)</td>
                    <td>
                      <div className="field-group-row">
                        <input type="number" placeholder="Mín." value={form.prazo_min} onChange={(e) => handleChange("prazo_min", e.target.value)} />
                        <span className="field-group-sep">até</span>
                        <input type="number" placeholder="Máx." value={form.prazo_max} onChange={(e) => handleChange("prazo_max", e.target.value)} />
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Valor (R$)</td>
                    <td>
                      <div className="field-group-row">
                        <input type="number" placeholder="Mín." value={form.valor_min} onChange={(e) => handleChange("valor_min", e.target.value)} />
                        <span className="field-group-sep">até</span>
                        <input type="number" placeholder="Máx." value={form.valor_max} onChange={(e) => handleChange("valor_max", e.target.value)} />
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Vigência</td>
                    <td>
                      <div className="field-group-row">
                        <input type="date" value={form.data_inicio || ""} onChange={(e) => handleChange("data_inicio", e.target.value)} />
                        <span className="field-group-sep">até</span>
                        <input type="date" value={form.data_fim || ""} onChange={(e) => handleChange("data_fim", e.target.value)} />
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="form-table-label">% especial</td>
                    <td>
                      <div className="input-suffix-group">
                        <input type="number" step="0.01" value={form.perc_especial} onChange={(e) => handleChange("perc_especial", e.target.value)} />
                        <span className="input-suffix">%</span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="form-table-label">Status</td>
                    <td>
                      <select value={form.status} onChange={(e) => handleChange("status", e.target.value)}>
                        <option value="ativo">Ativo</option>
                        <option value="nao_contabilizar">Não contabilizar</option>
                      </select>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div className="filter-actions" style={{ marginTop: "1rem" }}>
                <button type="submit" disabled={salvarMutation.isPending}>
                  {salvarMutation.isPending ? "Salvando…" : "Salvar"}
                </button>
                <button type="button" className="btn-link" onClick={fecharModal}>Cancelar</button>
              </div>
            </form>

            {criteriosDaCampanha(modalCampanha.id).length > 0 && (
              <>
                <p className="section-label" style={{ marginTop: "1.5rem" }}>Critérios já cadastrados nessa campanha</p>
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Convênio</th><th>Produto</th><th>Tabela</th><th>Base</th><th>% especial</th><th></th></tr></thead>
                    <tbody>
                      {criteriosDaCampanha(modalCampanha.id).map((crit) => (
                        <tr key={crit.id}>
                          <td className="small">{crit.convenio}</td>
                          <td className="small">{crit.produto}</td>
                          <td className="mono small">{crit.tabela}</td>
                          <td className="small">{crit.valor_base === "bruto" ? "Bruto" : "Líquido"}</td>
                          <td className="mono small">{percentual(crit.perc_especial)}</td>
                          <td style={{ whiteSpace: "nowrap" }}>
                            <button className="btn-link" onClick={() => abrirEditarCriterio(modalCampanha, crit)} style={{ marginRight: "0.4rem" }}>
                              <Settings />
                            </button>
                            <button className="btn-danger" onClick={() => handleExcluirCriterio(crit.id)}>
                              <Trash />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
        </Modal>
      )}
    </div>
  );
}
