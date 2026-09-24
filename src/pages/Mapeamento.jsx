import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import { Table, Plus, Trash, Refresh } from "../components/icons";

const LOCAL_LABEL = { map_convenio: "Convênio", map_produto: "Produto" };

async function buscarCategorias() {
  const { data } = await api.get("/mapeamento/categorias");
  return data;
}
async function buscarRegras(categoriaId) {
  const { data } = await api.get("/mapeamento/regras", { params: categoriaId ? { categoria_id: categoriaId } : {} });
  return data;
}

async function buscarRegistros() {
  const { data } = await api.get("/mapeamento/registros");
  return data;
}

function dataHoraBr(valor) {
  if (!valor) return "—";
  const d = new Date(valor);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Mapeamento() {
  const queryClient = useQueryClient();

  const [nomeCategoria, setNomeCategoria] = useState("");
  const [localCategoria, setLocalCategoria] = useState("map_convenio");
  const [mensagemCategoria, setMensagemCategoria] = useState(null);

  const [modalCategoria, setModalCategoria] = useState(null);
  const [descricaoRegra, setDescricaoRegra] = useState("");
  const [buscaConvenio, setBuscaConvenio] = useState(true);
  const [buscaProduto, setBuscaProduto] = useState(false);
  const [buscaTabela, setBuscaTabela] = useState(false);
  const [mensagemRegra, setMensagemRegra] = useState(null);

  const [resultadoMotor, setResultadoMotor] = useState(null);

  const { data: categorias = [], isLoading, isError, error } = useQuery({
    queryKey: ["mapeamento-categorias"],
    queryFn: buscarCategorias,
  });
  const { data: regras = [] } = useQuery({
    queryKey: ["mapeamento-regras", modalCategoria?.id],
    queryFn: () => buscarRegras(modalCategoria?.id),
    enabled: !!modalCategoria,
  });
  const { data: registros = [] } = useQuery({
    queryKey: ["mapeamento-registros"],
    queryFn: buscarRegistros,
  });

  function invalidar() {
    queryClient.invalidateQueries({ queryKey: ["mapeamento-categorias"] });
    queryClient.invalidateQueries({ queryKey: ["mapeamento-regras"] });
    queryClient.invalidateQueries({ queryKey: ["mapeamento-registros"] });
  }

  const criarCategoriaMutation = useMutation({
    mutationFn: (dados) => api.post("/mapeamento/categorias", dados),
    onSuccess: () => {
      invalidar();
      setMensagemCategoria({ ok: true, texto: "Categoria criada." });
      setNomeCategoria("");
    },
    onError: (err) => setMensagemCategoria({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const excluirCategoriaMutation = useMutation({
    mutationFn: (id) => api.delete(`/mapeamento/categorias/${id}`),
    onSuccess: () => {
      invalidar();
      setMensagemCategoria({ ok: true, texto: "Categoria excluída — dados que ela tinha preenchido na base foram revertidos." });
    },
    onError: (err) => setMensagemCategoria({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const criarRegraMutation = useMutation({
    mutationFn: (dados) => api.post("/mapeamento/regras", dados),
    onSuccess: () => {
      invalidar();
      setMensagemRegra({ ok: true, texto: "Regra criada." });
      setDescricaoRegra("");
    },
    onError: (err) => setMensagemRegra({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const excluirRegraMutation = useMutation({
    mutationFn: (id) => api.delete(`/mapeamento/regras/${id}`),
    onSuccess: () => {
      invalidar();
      setMensagemRegra({ ok: true, texto: "Regra excluída — os dados que só ela preenchia foram revertidos (e reprocessados com as regras que sobraram)." });
    },
    onError: (err) => setMensagemRegra({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const rodarMotorMutation = useMutation({
    mutationFn: () => api.post("/mapeamento/executar", {}),
    onSuccess: (res) => {
      setResultadoMotor({ ok: true, ...res.data.resultado });
      queryClient.invalidateQueries({ queryKey: ["mapeamento-registros"] });
    },
    onError: (err) => setResultadoMotor({ ok: false, erro: err?.response?.data?.erro || err.message }),
  });

  function handleCriarCategoria(e) {
    e.preventDefault();
    criarCategoriaMutation.mutate({ nome: nomeCategoria, local_enquadramento: localCategoria });
  }

  function abrirCategoria(cat) {
    setModalCategoria(cat);
    setDescricaoRegra("");
    setBuscaConvenio(true);
    setBuscaProduto(false);
    setBuscaTabela(false);
    setMensagemRegra(null);
  }

  function fecharModal() {
    setModalCategoria(null);
  }

  function handleCriarRegra(e) {
    e.preventDefault();
    if (!buscaConvenio && !buscaProduto && !buscaTabela) {
      setMensagemRegra({ ok: false, texto: "Escolha ao menos um campo pra busca: Convênio, Produto ou Tabela." });
      return;
    }
    criarRegraMutation.mutate({
      categoria_id: modalCategoria.id,
      descricao: descricaoRegra,
      busca_convenio: buscaConvenio,
      busca_produto: buscaProduto,
      busca_tabela: buscaTabela,
    });
  }

  return (
    <div className="fade-in">
      <PageHeader
        icon={<Table />}
        title="Mapeamento"
        subtitle='Categorias e regras de busca que tratam Convênio e Produto brutos em valores padronizados (map_convenio / map_produto), usados pelo resto do sistema.'
      />

      <div className="card">
        <p className="section-title" style={{ marginTop: 0 }}>Rodar motor agora</p>
        <button type="button" onClick={() => rodarMotorMutation.mutate()} disabled={rodarMotorMutation.isPending}>
          <Refresh /> {rodarMotorMutation.isPending ? "Rodando…" : "Rodar Mapeamento"}
        </button>

        {resultadoMotor && (
          <div className={`fade-in ${resultadoMotor.ok ? "card status-card-ok" : "card error-card"}`} style={{ marginTop: "1rem" }}>
            {resultadoMotor.ok ? (
              <>
                <p style={{ margin: "0 0 0.4rem" }}><span className="status-dot ok" />Mapeamento concluído.</p>
                {["map_convenio", "map_produto"].map((loc) => {
                  const r = resultadoMotor[loc];
                  if (!r) return null;
                  const semEfeito = r.categorias_consideradas > 0 && r.linhas_elegiveis_antes === r.linhas_elegiveis_depois && r.linhas_elegiveis_antes > 0;
                  return (
                    <p key={loc} className="muted small" style={{ margin: "0 0 0.3rem" }}>
                      <strong>{LOCAL_LABEL[loc]}:</strong> {r.categorias_consideradas} categoria(s) considerada(s)
                      {r.linhas_marcadas != null ? `, ${r.linhas_marcadas} linha(s) afetada(s)` : ""}.
                      {" "}Linhas ainda sem tratamento: {r.linhas_elegiveis_antes} antes → {r.linhas_elegiveis_depois} depois.
                      {semEfeito && (
                        <span style={{ color: "var(--red)", display: "block" }}>
                          ⚠ Não mudou nada — confira se as regras cadastradas realmente têm um termo que aparece nessas
                          linhas (Convênio/Produto/Tabela), ou se as linhas já estão em conflito (veja a coluna de
                          conflito na base).
                        </span>
                      )}
                    </p>
                  );
                })}
              </>
            ) : (
              <><p className="error-title">Não foi possível concluir</p><p className="muted small">{resultadoMotor.erro}</p></>
            )}
          </div>
        )}
      </div>

      {mensagemCategoria && (
        <div className={`fade-in ${mensagemCategoria.ok ? "card status-card-ok" : "card error-card"}`}>
          {mensagemCategoria.ok ? (
            <p style={{ margin: 0 }}><span className="status-dot ok" />{mensagemCategoria.texto}</p>
          ) : (
            <><p className="error-title">Não foi possível salvar</p><p className="muted small">{mensagemCategoria.texto}</p></>
          )}
        </div>
      )}

      <form onSubmit={handleCriarCategoria} className="card card-accent-blue" autoComplete="off">
        <p className="section-label" style={{ marginTop: 0 }}>Nova categoria</p>
        <div className="filter-grid">
          <div className="form-row">
            <label>Nome da categoria</label>
            <input
              type="text"
              value={nomeCategoria}
              onChange={(e) => setNomeCategoria(e.target.value)}
              placeholder="ex: INSS"
              required
            />
          </div>
          <div className="form-row">
            <label>Local de enquadramento</label>
            <select value={localCategoria} onChange={(e) => setLocalCategoria(e.target.value)}>
              <option value="map_convenio">Map Convênio</option>
              <option value="map_produto">Map Produto</option>
            </select>
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <button type="submit" disabled={criarCategoriaMutation.isPending}>
              <Plus /> {criarCategoriaMutation.isPending ? "Salvando…" : "Criar categoria"}
            </button>
          </div>
        </div>
      </form>

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="card table-wrap fade-in">
          <table>
            <thead>
              <tr><th>Nome</th><th>Local de enquadramento</th><th>Regras cadastradas</th><th>Criada em</th><th></th></tr>
            </thead>
            <tbody>
              {categorias.length === 0 && (
                <tr><td colSpan={5} className="muted center">Nenhuma categoria cadastrada.</td></tr>
              )}
              {categorias.map((c) => (
                <tr key={c.id}>
                  <td className="small">{c.nome}</td>
                  <td className="small">{LOCAL_LABEL[c.local_enquadramento] || c.local_enquadramento}</td>
                  <td className="small">{c.total_regras}</td>
                  <td className="mono small">{dataHoraBr(c.criado_em)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn-link" onClick={() => abrirCategoria(c)} title="Ver / cadastrar regras" style={{ marginRight: "0.4rem" }}>
                      {c.total_regras > 0 ? "Ver / editar regras" : "Cadastrar regra"}
                    </button>
                    <button
                      className="btn-danger"
                      onClick={() => {
                        if (window.confirm(`Excluir a categoria "${c.nome}"? Isso apaga as regras dela e reverte (limpa) o que ela já tinha preenchido na base.`)) {
                          excluirCategoriaMutation.mutate(c.id);
                        }
                      }}
                      title="Excluir categoria"
                    >
                      <Trash />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalCategoria && (
        <Modal onClose={fecharModal} width={620}>
          <p className="section-title" style={{ marginTop: 0 }}>
            Regras — {modalCategoria.nome} <span className="muted small">({LOCAL_LABEL[modalCategoria.local_enquadramento]})</span>
          </p>

          {mensagemRegra && (
            <div className={mensagemRegra.ok ? "card status-card-ok" : "card error-card"} style={{ marginBottom: "1rem" }}>
              {mensagemRegra.ok ? (
                <p style={{ margin: 0 }}><span className="status-dot ok" />{mensagemRegra.texto}</p>
              ) : (
                <><p className="error-title">Não foi possível salvar</p><p className="muted small">{mensagemRegra.texto}</p></>
              )}
            </div>
          )}

          <form onSubmit={handleCriarRegra}>
            <table className="form-table">
              <tbody>
                <tr>
                  <td className="form-table-label">Descrição (o que buscar)</td>
                  <td>
                    <input
                      type="text"
                      value={descricaoRegra}
                      onChange={(e) => setDescricaoRegra(e.target.value)}
                      placeholder="ex: INSS"
                      required
                    />
                  </td>
                </tr>
                <tr>
                  <td className="form-table-label">Buscar em</td>
                  <td>
                    <label style={{ display: "block" }}>
                      <input type="checkbox" checked={buscaConvenio} onChange={(e) => setBuscaConvenio(e.target.checked)} /> Convênio
                    </label>
                    <label style={{ display: "block" }}>
                      <input type="checkbox" checked={buscaProduto} onChange={(e) => setBuscaProduto(e.target.checked)} /> Produto
                    </label>
                    <label style={{ display: "block" }}>
                      <input type="checkbox" checked={buscaTabela} onChange={(e) => setBuscaTabela(e.target.checked)} /> Tabela
                    </label>
                  </td>
                </tr>
              </tbody>
            </table>

            <div className="filter-actions" style={{ marginTop: "1rem" }}>
              <button type="submit" disabled={criarRegraMutation.isPending}>
                <Plus /> {criarRegraMutation.isPending ? "Salvando…" : "Adicionar regra"}
              </button>
              <button type="button" className="btn-link" onClick={fecharModal}>Fechar</button>
            </div>
          </form>

          {regras.length > 0 && (
            <>
              <p className="section-label" style={{ marginTop: "1.5rem" }}>Regras já cadastradas nessa categoria</p>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Descrição</th><th>Campos</th><th>Criada em</th><th></th></tr></thead>
                  <tbody>
                    {regras.map((r) => (
                      <tr key={r.id}>
                        <td className="mono small">{r.descricao}</td>
                        <td className="small">
                          {[r.busca_convenio && "Convênio", r.busca_produto && "Produto", r.busca_tabela && "Tabela"].filter(Boolean).join(", ")}
                        </td>
                        <td className="mono small">{dataHoraBr(r.criado_em)}</td>
                        <td>
                          <button
                            className="btn-danger"
                            onClick={() => {
                              if (window.confirm("Remover essa regra? Os dados que só ela preenchia serão revertidos.")) {
                                excluirRegraMutation.mutate(r.id);
                              }
                            }}
                          >
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

      <div className="card table-wrap fade-in">
        <p className="section-title" style={{ marginTop: 0 }}>Registro (auditoria)</p>
        <table>
          <thead>
            <tr><th>Quando</th><th>Ação</th><th>Local</th><th>Detalhe</th><th>Categorias</th><th>Linhas (antes → depois)</th><th>Por</th></tr>
          </thead>
          <tbody>
            {registros.length === 0 && (
              <tr><td colSpan={7} className="muted center">Nenhum registro ainda.</td></tr>
            )}
            {registros.map((r) => (
              <tr key={r.id}>
                <td className="mono small">{dataHoraBr(r.executado_em)}</td>
                <td className="small">{{ executar: "Executar motor", excluir_categoria: "Excluir categoria", excluir_regra: "Excluir regra" }[r.acao] || r.acao}</td>
                <td className="small">{LOCAL_LABEL[r.local_enquadramento] || r.local_enquadramento || "—"}</td>
                <td className="small">{r.detalhe || "—"}</td>
                <td className="small">{r.categorias_consideradas ?? "—"}</td>
                <td className="mono small">
                  {r.linhas_elegiveis_antes != null ? `${r.linhas_elegiveis_antes} → ${r.linhas_elegiveis_depois}` : "—"}
                </td>
                <td className="small">{r.executado_por || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
