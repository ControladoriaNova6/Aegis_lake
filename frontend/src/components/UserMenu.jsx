import { useState, useRef, useEffect } from "react";

import { useAuth } from "../context/AuthContext";
import ModalRedefinirSenha from "./ModalRedefinirSenha";
import Modal from "./Modal";

export default function UserMenu() {
  const { usuario, logout } = useAuth();
  const [aberto, setAberto] = useState(false);
  const [modalSenha, setModalSenha] = useState(false);
  const [painelAberto, setPainelAberto] = useState(null); // 'notificacoes' | 'solicitacoes' | null
  const ref = useRef(null);

  useEffect(() => {
    function handleClickFora(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setAberto(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  if (!usuario) return null;

  const inicial = (usuario.nome || usuario.email || "?").trim().charAt(0).toUpperCase();

  return (
    <div className="user-menu" ref={ref}>
      <button
        type="button"
        className="user-menu-avatar"
        onClick={() => setAberto((a) => !a)}
        title={usuario.nome || usuario.email}
      >
        {inicial}
      </button>

      {aberto && (
        <div className="user-menu-dropdown">
          <div className="user-menu-header">
            <p className="user-nome">{usuario.nome || usuario.email}</p>
            <p className="user-papel">{usuario.email}</p>
          </div>

          <button type="button" className="user-menu-item" onClick={() => { setModalSenha(true); setAberto(false); }}>
            Redefinir senha
          </button>
          <button type="button" className="user-menu-item" onClick={() => { setPainelAberto("notificacoes"); setAberto(false); }}>
            Notificações
          </button>
          <button type="button" className="user-menu-item" onClick={() => { setPainelAberto("solicitacoes"); setAberto(false); }}>
            Solicitações
          </button>

          <div className="user-menu-divider" />

          <button type="button" className="user-menu-item user-menu-item-danger" onClick={() => logout()}>
            Sair
          </button>
        </div>
      )}

      {modalSenha && <ModalRedefinirSenha onClose={() => setModalSenha(false)} />}

      {painelAberto && (
        <Modal onClose={() => setPainelAberto(null)} width={360}>
            <p className="section-title" style={{ marginTop: 0 }}>
              {painelAberto === "notificacoes" ? "Notificações" : "Solicitações"}
            </p>
            <p className="muted small">
              {painelAberto === "notificacoes"
                ? "Nenhuma notificação por enquanto."
                : "Nenhuma solicitação por enquanto."}
            </p>
            <button type="button" onClick={() => setPainelAberto(null)} style={{ marginTop: "1rem" }}>
              Fechar
            </button>
        </Modal>
      )}
    </div>
  );
}
