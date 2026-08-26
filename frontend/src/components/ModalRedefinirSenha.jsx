import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import api from "../api/client";
import Modal from "./Modal";

export default function ModalRedefinirSenha({ onClose }) {
  const [senhaAtual, setSenhaAtual] = useState("");
  const [senhaNova, setSenhaNova] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);

  const mutation = useMutation({
    mutationFn: (dados) => api.post("/me/senha", dados),
    onSuccess: () => setSucesso(true),
    onError: (err) => setErro(err?.response?.data?.erro || err.message),
  });

  function handleSubmit(e) {
    e.preventDefault();
    setErro(null);

    if (senhaNova !== confirmar) {
      setErro("A confirmação não bate com a nova senha.");
      return;
    }
    mutation.mutate({ senha_atual: senhaAtual, senha_nova: senhaNova });
  }

  return (
    <Modal onClose={onClose} width={360}>
        <p className="section-title" style={{ marginTop: 0 }}>Redefinir senha</p>

        {sucesso ? (
          <>
            <p style={{ margin: "0 0 1rem" }}>
              <span className="status-dot ok" />Senha alterada com sucesso.
            </p>
            <button type="button" onClick={onClose} style={{ width: "100%", justifyContent: "center" }}>
              Fechar
            </button>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            {erro && (
              <p className="muted small" style={{ color: "var(--red)", marginBottom: "1rem" }}>
                {erro}
              </p>
            )}
            <div className="form-row">
              <label>Senha atual</label>
              <input type="password" value={senhaAtual} onChange={(e) => setSenhaAtual(e.target.value)} required autoFocus />
            </div>
            <div className="form-row">
              <label>Nova senha</label>
              <input type="password" value={senhaNova} onChange={(e) => setSenhaNova(e.target.value)} required minLength={4} />
            </div>
            <div className="form-row">
              <label>Confirmar nova senha</label>
              <input type="password" value={confirmar} onChange={(e) => setConfirmar(e.target.value)} required minLength={4} />
            </div>
            <div className="filter-actions" style={{ marginTop: "1rem" }}>
              <button type="submit" disabled={mutation.isPending} style={{ flex: 1, justifyContent: "center" }}>
                {mutation.isPending ? "Salvando…" : "Salvar nova senha"}
              </button>
              <button type="button" className="btn-link" onClick={onClose}>Cancelar</button>
            </div>
          </form>
        )}
    </Modal>
  );
}
