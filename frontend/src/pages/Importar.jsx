import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Upload } from "../components/icons";

async function buscarConfigs() {
  const { data } = await api.get("/configs");
  return data;
}

export default function Importar() {
  const { data: configs = [] } = useQuery({ queryKey: ["configs"], queryFn: buscarConfigs });
  const [bancoTipo, setBancoTipo] = useState("");
  const [arquivo, setArquivo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!bancoTipo || !arquivo) {
      setResultado({ ok: false, erro: "Selecione uma configuração e anexe um arquivo." });
      return;
    }

    const formData = new FormData();
    formData.append("banco_tipo", bancoTipo);
    formData.append("arquivo", arquivo);

    setEnviando(true);
    setResultado(null);
    try {
      const { data } = await api.post("/importar", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResultado(data);
    } catch (err) {
      setResultado({ ok: false, erro: err?.response?.data?.erro || err.message });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fade-in">
      <PageHeader icon={<Upload />} title="Importar" subtitle="Envie um arquivo de produção pra consolidar na base." />

      <form onSubmit={handleSubmit} className="card card-fit" style={{ maxWidth: 480 }}>
        <div className="form-row">
          <label>Configuração de importação</label>
          <select value={bancoTipo} onChange={(e) => setBancoTipo(e.target.value)} required>
            <option value="">Selecione…</option>
            {configs.map((c) => (
              <option key={c.valor} value={c.valor}>{c.rotulo}</option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Arquivo (.xlsx ou .csv)</label>
          <input type="file" accept=".xlsx,.xls,.csv" onChange={(e) => setArquivo(e.target.files?.[0] || null)} required />
        </div>
        <button type="submit" disabled={enviando} style={{ width: "100%", justifyContent: "center" }}>
          {enviando ? "Importando…" : "Importar"}
        </button>
      </form>

      {resultado && (
        <div className={resultado.ok ? "card status-card-ok" : "card error-card"}>
          {resultado.ok ? (
            <>
              <p style={{ margin: "0 0 0.5rem" }}>
                <span className="status-dot ok" />
                Arquivo <strong>{resultado.arquivo_original}</strong> importado como{" "}
                <strong>{resultado.banco_nome}</strong>.
              </p>
              <ul className="muted small" style={{ margin: 0, paddingLeft: "1.2rem" }}>
                <li>{resultado.total_linhas} linha(s) no arquivo</li>
                <li>{resultado.inseridas} inserida(s)</li>
                <li>{resultado.duplicadas} duplicada(s) (ignoradas)</li>
                <li>{resultado.linhas_rejeitadas} rejeitada(s) por campo obrigatório vazio</li>
              </ul>

              {resultado.colunas_origem_ausentes && Object.keys(resultado.colunas_origem_ausentes).length > 0 && (
                <div style={{ marginTop: "0.75rem" }}>
                  <p className="muted small" style={{ margin: "0 0 0.3rem", color: "var(--red)" }}>
                    Colunas de origem não encontradas no arquivo:
                  </p>
                  <ul className="muted small" style={{ margin: 0, paddingLeft: "1.2rem" }}>
                    {Object.entries(resultado.colunas_origem_ausentes).map(([campo, origem]) => (
                      <li key={campo}>
                        <span className="mono">{campo}</span> (esperava a coluna <span className="mono">{origem}</span>)
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {resultado.grupos_obrigatorios_vazios && Object.keys(resultado.grupos_obrigatorios_vazios).length > 0 && (
                <div style={{ marginTop: "0.75rem" }}>
                  <p className="muted small" style={{ margin: "0 0 0.3rem" }}>Linhas rejeitadas por par obrigatório vazio:</p>
                  <ul className="muted small" style={{ margin: 0, paddingLeft: "1.2rem" }}>
                    {Object.entries(resultado.grupos_obrigatorios_vazios).map(([par, qtd]) => (
                      <li key={par}><span className="mono">{par}</span>: {qtd} linha(s)</li>
                    ))}
                  </ul>
                </div>
              )}

              {resultado.colunas_opcionais_vazias && Object.keys(resultado.colunas_opcionais_vazias).length > 0 && (
                <div style={{ marginTop: "0.75rem" }}>
                  <p className="muted small" style={{ margin: "0 0 0.3rem" }}>Campos opcionais vazios (informativo):</p>
                  <ul className="muted small" style={{ margin: 0, paddingLeft: "1.2rem" }}>
                    {Object.entries(resultado.colunas_opcionais_vazias).map(([campo, qtd]) => (
                      <li key={campo}><span className="mono">{campo}</span>: {qtd} linha(s)</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <>
              <p className="error-title">Não deu para importar</p>
              <p className="muted small">{resultado.erro}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
