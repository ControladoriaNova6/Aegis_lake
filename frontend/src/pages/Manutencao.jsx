import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import api from "../api/client";
import PageHeader from "../components/PageHeader";
import { Settings } from "../components/icons";

export default function Manutencao() {
  const [resultado, setResultado] = useState(null);
  const [resultadoSync, setResultadoSync] = useState(null);

  const cruzarIndicadoMutation = useMutation({
    mutationFn: () => api.post("/manutencao/cruzar-indicado"),
    onSuccess: (res) => setResultado({ ok: true, ...res.data }),
    onError: (err) => setResultado({ ok: false, erro: err?.response?.data?.erro || err.message }),
  });

  const sincronizarValoresCampanhasMutation = useMutation({
    mutationFn: () => api.post("/manutencao/sincronizar-valores-campanhas"),
    onSuccess: (res) => setResultadoSync({ ok: true, ...res.data }),
    onError: (err) => setResultadoSync({ ok: false, erro: err?.response?.data?.erro || err.message }),
  });

  return (
    <div className="fade-in">
      <PageHeader icon={<Settings />} title="Manutenção" subtitle="Ferramentas administrativas para operações de dados." />

      {resultado && (
        <div className={`fade-in ${resultado.ok ? "card status-card-ok" : "card error-card"}`}>
          {resultado.ok ? (
            <>
              <p style={{ margin: "0 0 0.4rem" }}><span className="status-dot ok" />Cruzamento concluído.</p>
              <p className="muted small" style={{ margin: 0 }}>
                {resultado.codigos_considerados} código(s) de indicado considerado(s).{" "}
                {resultado.linhas_atualizadas != null
                  ? `${resultado.linhas_atualizadas} linha(s) atualizada(s).`
                  : "Tabela atualizada."}
              </p>
            </>
          ) : (
            <>
              <p className="error-title">Não foi possível concluir</p>
              <p className="muted small">{resultado.erro}</p>
            </>
          )}
        </div>
      )}

      <div className="card">
        <p className="section-title" style={{ marginTop: 0 }}>Map Indicado</p>
        <p className="muted small" style={{ marginBottom: "1rem" }}>
          Procura em <span className="mono">cod_corretor</span>, <span className="mono">cod_master</span> e{" "}
          <span className="mono">cod_indicado</span> por um código que bata com algum indicado cadastrado. Quando
          bate, grava esse código na coluna <span className="mono">map_indicado</span>. Só processa linhas que ainda
          não têm essa coluna preenchida — rodar de novo depois de cadastrar novos indicados é seguro.
        </p>
        <button type="button" onClick={() => cruzarIndicadoMutation.mutate()} disabled={cruzarIndicadoMutation.isPending}>
          {cruzarIndicadoMutation.isPending ? "Cruzando…" : "Rodar cruzamento — Map Indicado"}
        </button>
      </div>

      <div className="card">
        <p className="section-title" style={{ marginTop: 0 }}>Map Convênio / Map Produto</p>
        <p className="muted small" style={{ marginBottom: "1rem" }}>
          Em desenvolvimento, seguindo o mesmo padrão do Map Indicado.
        </p>
        <button type="button" disabled title="Em breve">
          Em breve
        </button>
      </div>

      <div className="card">
        <p className="section-title" style={{ marginTop: 0 }}>Sincronizar valores de campanhas</p>
        <p className="muted small" style={{ marginBottom: "1rem" }}>
          Atualiza todo lançamento em <span className="mono">Valores em Aberto</span> que veio do botão "Adicionar
          aos valores em aberto" de uma campanha, recalculando o valor previsto (e a data prevista) com a projeção
          mais atual dessa campanha. Lançamentos já marcados como "recebido" não são alterados. Rode isso sempre que
          a produção subjacente às campanhas for atualizada (nova importação de base, por exemplo).
        </p>
        <button
          type="button"
          onClick={() => sincronizarValoresCampanhasMutation.mutate()}
          disabled={sincronizarValoresCampanhasMutation.isPending}
        >
          {sincronizarValoresCampanhasMutation.isPending ? "Sincronizando…" : "Sincronizar valores de campanhas"}
        </button>

        {resultadoSync && (
          <div className={`fade-in ${resultadoSync.ok ? "card status-card-ok" : "card error-card"}`} style={{ marginTop: "1rem" }}>
            {resultadoSync.ok ? (
              <>
                <p style={{ margin: "0 0 0.4rem" }}><span className="status-dot ok" />Sincronização concluída.</p>
                <p className="muted small" style={{ margin: 0 }}>
                  {resultadoSync.verificados} lançamento(s) verificado(s), {resultadoSync.atualizados} atualizado(s).
                  {resultadoSync.campanhas_nao_encontradas > 0
                    ? ` ${resultadoSync.campanhas_nao_encontradas} lançamento(s) apontam pra campanha(s) que não existem mais.`
                    : ""}
                </p>
              </>
            ) : (
              <>
                <p className="error-title">Não foi possível concluir</p>
                <p className="muted small">{resultadoSync.erro}</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
