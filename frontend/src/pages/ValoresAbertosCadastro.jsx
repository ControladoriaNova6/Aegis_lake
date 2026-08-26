import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Plus } from "../components/icons";
import { brl } from "../utils/format";

const FORM_VAZIO = { banco: "", categoria: "", periodo_ref: "", valor: "", data_prevista: "" };

async function buscarBancos() {
  const { data } = await api.get("/bancos");
  return data;
}
async function buscarCategorias() {
  const { data } = await api.get("/valores-abertos/categorias");
  return data;
}
async function buscarLancamentos() {
  const { data } = await api.get("/valores-abertos");
  return data;
}

export default function ValoresAbertosCadastro() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(FORM_VAZIO);
  const [mensagem, setMensagem] = useState(null);

  const { data: bancos = [] } = useQuery({ queryKey: ["bancos"], queryFn: buscarBancos });
  const { data: categorias = [] } = useQuery({ queryKey: ["valores-abertos-categorias"], queryFn: buscarCategorias });
  const { data: lancamentos = [], isLoading, isError, error } = useQuery({
    queryKey: ["valores-abertos"],
    queryFn: buscarLancamentos,
  });

  const criarMutation = useMutation({
    mutationFn: (dados) => api.post("/valores-abertos", dados),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["valores-abertos"] });
      setMensagem({ ok: true, texto: "Lançamento adicionado." });
      setForm(FORM_VAZIO);
    },
    onError: (err) => setMensagem({ ok: false, texto: err?.response?.data?.erro || err.message }),
  });

  function handleChange(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  function handleSalvar(e) {
    e.preventDefault();
    if (!form.banco || !form.categoria || !form.valor || !form.data_prevista) {
      setMensagem({ ok: false, texto: "Preencha Banco, Categoria, Valor e Data prevista." });
      return;
    }
    criarMutation.mutate(form);
  }

  const recentes = [...lancamentos].sort((a, b) => (a.criado_em < b.criado_em ? 1 : -1)).slice(0, 10);

  return (
    <div className="fade-in">
      <PageHeader
        icon={<Plus />}
        title="Valores em aberto — Cadastro"
        subtitle="Lançamentos manuais: notas fiscais, campanhas, bônus, diferido, colchão e outros valores fora da contabilização padrão."
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

      <form onSubmit={handleSalvar} className="card card-accent-blue">
        <p className="section-title" style={{ marginTop: 0 }}>Novo lançamento</p>
        <div className="filter-grid">
          <div className="form-row">
            <label>Banco</label>
            <select value={form.banco} onChange={(e) => handleChange("banco", e.target.value)}>
              <option value="">Selecione…</option>
              {bancos.map((b) => <option key={b.valor} value={b.valor}>{b.rotulo}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Categoria</label>
            <select value={form.categoria} onChange={(e) => handleChange("categoria", e.target.value)}>
              <option value="">Selecione…</option>
              {categorias.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Período de referência</label>
            <input type="text" value={form.periodo_ref} onChange={(e) => handleChange("periodo_ref", e.target.value)} placeholder="ex: 2026-08" />
          </div>
          <div className="form-row">
            <label>Valor</label>
            <input type="number" step="0.01" value={form.valor} onChange={(e) => handleChange("valor", e.target.value)} />
          </div>
          <div className="form-row">
            <label>Data prevista</label>
            <input type="date" value={form.data_prevista} onChange={(e) => handleChange("data_prevista", e.target.value)} />
          </div>
          <div className="form-row form-row-action">
            <label>&nbsp;</label>
            <button type="submit" disabled={criarMutation.isPending}>
              <Plus /> {criarMutation.isPending ? "Salvando…" : "Adicionar"}
            </button>
          </div>
        </div>
      </form>

      {isLoading && <div className="skeleton-block" />}
      {isError && (
        <div className="card error-card fade-in">
          <p className="error-title">Não deu para consultar o BigQuery</p>
          <p className="muted small">{error?.response?.data?.erro || error?.message}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="card table-wrap fade-in">
          <p className="section-label">Últimos lançamentos cadastrados</p>
          <table>
            <thead>
              <tr><th>Banco</th><th>Categoria</th><th>Período</th><th className="align-right">Valor</th><th>Prevista</th><th>Criado por</th><th>Status</th></tr>
            </thead>
            <tbody>
              {recentes.length === 0 && (
                <tr><td colSpan={7} className="muted center">Nenhum lançamento cadastrado ainda.</td></tr>
              )}
              {recentes.map((l) => (
                <tr key={l.id}>
                  <td className="small">{l.banco}</td>
                  <td className="small">{l.categoria}</td>
                  <td className="small">{l.periodo_ref || "—"}</td>
                  <td className="mono small align-right">{brl(l.valor)}</td>
                  <td className="mono small">{l.data_prevista}</td>
                  <td className="small">{l.criado_por}</td>
                  <td className="small">
                    <span className={`status-dot ${l.status === "recebido" ? "ok" : "warn"}`} />
                    {l.status === "recebido" ? "Recebido" : "Em aberto"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
