import { useState, useRef, useEffect } from "react";

export default function MultiSelectDropdown({ options, selected, onChange, placeholder = "Todos" }) {
  const [aberto, setAberto] = useState(false);
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

  function alternar(valor) {
    if (selected.includes(valor)) {
      onChange(selected.filter((v) => v !== valor));
    } else {
      onChange([...selected, valor]);
    }
  }

  function limpar(e) {
    e.stopPropagation();
    onChange([]);
  }

  const resumo =
    selected.length === 0 ? placeholder : selected.length === 1 ? selected[0] : `${selected.length} selecionados`;

  return (
    <div className="multiselect" ref={ref}>
      <button type="button" className="multiselect-trigger" onClick={() => setAberto((a) => !a)}>
        <span className={selected.length === 0 ? "muted" : ""}>{resumo}</span>
        <span className="multiselect-caret">▾</span>
      </button>

      {aberto && (
        <div className="multiselect-dropdown">
          {options.length === 0 ? (
            <p className="muted small" style={{ padding: "0.5rem 0.6rem", margin: 0 }}>
              Nenhuma opção disponível ainda.
            </p>
          ) : (
            <>
              {options.map((opt) => (
                <label key={opt} className="multiselect-option">
                  <input type="checkbox" checked={selected.includes(opt)} onChange={() => alternar(opt)} />
                  <span>{opt}</span>
                </label>
              ))}
              {selected.length > 0 && (
                <button type="button" className="multiselect-clear" onClick={limpar}>
                  Limpar seleção
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
