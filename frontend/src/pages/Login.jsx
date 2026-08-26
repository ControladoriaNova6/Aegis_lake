import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { usuario, carregando, login, loginErro, loginCarregando } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");

  if (!carregando && usuario) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await login({ email, senha });
      navigate("/");
    } catch {
      // o erro já fica disponível via loginErro
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--base)",
      }}
    >
      <div className="card" style={{ width: 340 }}>
        <div className="brand-mark" style={{ margin: "0 auto 1rem" }}>
          AE
        </div>
        <p className="section-title" style={{ margin: "0 0 0.25rem", textAlign: "center" }}>
          Aegis
        </p>
        <p className="muted small" style={{ margin: "0 0 1.5rem", textAlign: "center" }}>
          Entre com seu e-mail e senha.
        </p>

        {loginErro && (
          <p className="muted small" style={{ color: "var(--red)", marginBottom: "1rem" }}>
            {loginErro}
          </p>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>E-mail</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="form-row">
            <label>Senha</label>
            <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
          </div>
          <button type="submit" style={{ width: "100%", justifyContent: "center" }} disabled={loginCarregando}>
            {loginCarregando ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
