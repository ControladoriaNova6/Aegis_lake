import { createPortal } from "react-dom";

/**
 * Modal renderizado via portal direto em document.body.
 *
 * Por quê: nossas páginas usam `.fade-in`/`.card` com animação de
 * entrada (translateY). Mesmo depois de terminar, o navegador mantém um
 * `transform: translateY(0)` computado nesses elementos (efeito do
 * `animation-fill-mode: both`) — e QUALQUER transform diferente de
 * "none" num ancestral cria um novo "containing block" pra elementos
 * `position: fixed`. Resultado: um modal renderizado dentro de uma
 * dessas páginas para de se centralizar na tela de verdade e passa a se
 * centralizar dentro da caixa do ancestral (parece "puxado" pra cima).
 * Renderizando via portal direto no body, o modal nunca fica dentro
 * dessa hierarquia — sempre centraliza na tela, não importa a página.
 */
export default function Modal({ onClose, width = 620, children }) {
  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" style={{ width, maxHeight: "85vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>,
    document.body
  );
}
