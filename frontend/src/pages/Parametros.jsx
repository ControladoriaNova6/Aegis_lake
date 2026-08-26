import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import { Settings, Plus, Trash } from "../components/icons";

async function buscarParametros() {
  const { data } = await api.get("/parametros");
  return data;
}

function linhaVazia(camposMapeaveis) {
  const campos = {};
  camposMapeaveis.forEach((c) => (campos[c] = ""));
  return { banco_tipo: "", banco_nome: "", config_nome: "", campos };
}

function contarCamposPreenchidos(campos) {
  return Object.values(campos).filter((v) => v !== "" && v != null).length;
}

function validar(linha, camposSempreObrigatorios, gruposAlternativos) {
  const erros = {};
  if (!linha.banco_nome) erros.banco_nome = "Obrigatório";
  if (!linha.config_nome) erros.config_nome = "Obrigatório";

  camposSempreObrigatorios.forEach((c) => {
    if (!linha.campos[c]) erros[c] = "Obrigatório";
  });

  gruposAlternativos.forEach(([a, b]) => {
    if (!linha.campos[a] && !linha.campos[b]) {
      erros[a] = `Preencha esse ou "${b}"`;
      erros[b] = `Preencha esse ou "${a}"`;
    }
  });

  return erros;
}

function LinhaComErro({ label, valor, erro, onChange, placeholder }) {
  return (
    <tr>
      <td className="form-table-label">{label}</td>
      <td>
        <input type="text" value={valor} onChange={onChange} className={erro ? "input-com-erro" : ""} placeholder={placeholder} />
        {erro && <span className="field-error">{erro}</span>}
      </td>
    </tr>
  );
}

function FormularioConfig({ linha, setLinha, camposMapeaveis, camposSempreObrigatorios, camposEmGrupo, erros }) {
  function handleChangeCampo(campo, valor) {
    setLinha((l) => ({ ...l, campos: { ...l.campos, [campo]: valor } }));
  }

  return (
    <table className="form-table">
      <tbody>
        <LinhaComErro
          label="Config"
          valor={linha.config_nome}
          erro={erros.config_nome}
          onChange={(e) => setLinha((l) => ({ ...l, config_nome: e.target.value }))}
          placeholder="Nome da configuração"
        />
        <LinhaComErro
          label="Banco"
          valor={linha.banco_nome}
          erro={erros.banco_nome}
          onChange={(e) => setLinha((l) => ({ ...l, banco_nome: e.target.value }))}
          placeholder="Nome do banco"
        />
        {camposMapeaveis.map((c) => (
          <LinhaComErro
            key={c}
            label={
              <span className={camposSempreObrigatorios.includes(c) ? "req-simples" : camposEmGrupo.has(c) ? "req-grupo" : ""}>
                {c}
              </span>
            }
            valor={linha.campos[c] || ""}
            erro={erros[c]}
            onChange={(e) => handleChangeCampo(c, e.target.value)}
          />
        ))}
      </tbody>
    </table>
  );
}

export default function Parametros() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({ queryKey: ["parametros"], queryFn: buscarParametros });
  const [modalAberto, setModalAberto] = useState(null); // { modo: "nova" | "editar", linha }
  const [erros, setErros] = useState({});
  const [mensagem, setMensagem] = useState(null);

  const camposMapeaveis = data?.campos_mapeaveis || [];
  const camposSempreObrigatorios = data?.campos_sempre_obrigatorios || [];
  const gruposAlternativos = data?.grupos_alternativos || [];
  const camposEmGrupo = new Set(gruposAlternativos.flat());
  const grid = data?.grid || [];

  const salvarMutation = useMutation({
    mutationFn: (linha) => api.post("/parametros", { banco_tipo: linha.banco_tipo, banco_nome: linha.banco_nome, config_nome: linha.config_nome, ...linha.campos }),
    onSuccess: (_, linha) => {
      queryClient.invalidateQueries({ queryKey: ["parametros"] });
      setMensagem({ ok: true, texto: `Configuração "${linha.config_nome}" salva.` });
      fecharModal();
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  const excluirMutation = useMutation({
    mutationFn: (bancoTipo) => api.delete(`/parametros/${encodeURIComponent(bancoTipo)}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parametros"] });
      setMensagem({ ok: true, texto: "Configuração removida." });
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  function abrirNova() {
    setModalAberto({ modo: "nova", linha: linhaVazia(camposMapeaveis) });
    setErros({});
    setMensagem(null);
  }

  function abrirEdicao(linha) {
    setModalAberto({ modo: "editar", linha: { ...linha, campos: { ...linha.campos } } });
    setErros({});
    setMensagem(null);
  }

  function fecharModal() {
    setModalAberto(null);
    setErros({});
  }

  function handleSalvar(e) {
    e.preventDefault();
    const erros = validar(modalAberto.linha, camposSempreObrigatorios, gruposAlternativos);
    setErros(erros);
    if (Object.keys(erros).length > 0) return;
    salvarMutation.mutate(modalAberto.linha);
  }

  function handleExcluir(linha) {
    if (window.confirm(`Remover toda a configuração "${linha.config_nome}"?`)) {
      excluirMutation.mutate(linha.banco_tipo);
      if (modalAberto?.linha.banco_tipo === linha.banco_tipo) fecharModal();
    }
  }

  return (
    <div className="fade-in">
      <PageHeader
        icon={<Settings />}
        title="Parâmetros"
        subtitle="De-para de cada configuração de importação."
        action={
          <button type="button" onClick={abrirNova}>
            <Plus /> Nova configuração
          </button>
        }
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

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card fade-in">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {/* ── Listagem: somente leitura, com botão de editar/excluir por linha ── */}
      {!isLoading && !isError && (
        <div className="card table-wrap fade-in">
          <table>
            <thead>
              <tr>
                <th>Config</th>
                <th>Banco</th>
                <th>Campos mapeados</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {grid.length === 0 && (
                <tr><td colSpan={4} className="muted center">Nenhuma configuração cadastrada ainda.</td></tr>
              )}
              {grid.map((linha) => (
                <tr key={linha.banco_tipo}>
                  <td className="small">{linha.config_nome}</td>
                  <td className="small">{linha.banco_nome}</td>
                  <td className="mono small">{contarCamposPreenchidos(linha.campos)} / {camposMapeaveis.length}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn-link" title="Editar" onClick={() => abrirEdicao(linha)} style={{ marginRight: "0.4rem" }}>
                      <Settings /> Editar
                    </button>
                    <button className="btn-danger" title="Excluir" onClick={() => handleExcluir(linha)}>
                      <Trash />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Nova / Editar: sempre em modal central, formato de formulário ── */}
      {modalAberto && (
        <Modal onClose={fecharModal} width={560}>
          <p className="section-title" style={{ marginTop: 0 }}>
            {modalAberto.modo === "nova" ? "Nova configuração" : `Editando "${modalAberto.linha.config_nome}"`}
          </p>
          <form onSubmit={handleSalvar}>
            <FormularioConfig
              linha={modalAberto.linha}
              setLinha={(atualizar) => setModalAberto((m) => ({ ...m, linha: typeof atualizar === "function" ? atualizar(m.linha) : atualizar }))}
              camposMapeaveis={camposMapeaveis}
              camposSempreObrigatorios={camposSempreObrigatorios}
              camposEmGrupo={camposEmGrupo}
              erros={erros}
            />
            <div className="filter-actions" style={{ marginTop: "1rem" }}>
              <button type="submit" disabled={salvarMutation.isPending}>
                {salvarMutation.isPending ? "Salvando…" : modalAberto.modo === "nova" ? "Adicionar configuração" : "Salvar alterações"}
              </button>
              <button type="button" className="btn-link" onClick={fecharModal}>Cancelar</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
