import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import api from "../api/client";

function TelaLogin({ onIrParaPrimeiroAcesso }) {
  const { login, loginErro, loginCarregando } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");

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
    <>
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

      <button
        type="button"
        className="btn-link"
        style={{ width: "100%", justifyContent: "center", marginTop: "0.75rem" }}
        onClick={onIrParaPrimeiroAcesso}
      >
        Primeiro acesso — criar minha senha
      </button>
    </>
  );
}

function TelaPrimeiroAcesso({ onVoltar }) {
  const [email, setEmail] = useState("");
  const [senhaNova, setSenhaNova] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setErro(null);

    if (senhaNova !== confirmar) {
      setErro("A confirmação não bate com a nova senha.");
      return;
    }

    setCarregando(true);
    try {
      await api.post("/primeiro-acesso", { email, senha_nova: senhaNova });
      setSucesso(true);
    } catch (err) {
      setErro(err?.response?.data?.erro || err.message);
    } finally {
      setCarregando(false);
    }
  }

  if (sucesso) {
    return (
      <>
        <p style={{ margin: "0 0 1.25rem" }}>
          <span className="status-dot ok" />Senha criada. Já dá pra entrar normalmente.
        </p>
        <button type="button" onClick={onVoltar} style={{ width: "100%", justifyContent: "center" }}>
          Ir para o login
        </button>
      </>
    );
  }

  return (
    <>
      <p className="muted small" style={{ margin: "0 0 1.5rem", textAlign: "center" }}>
        Informe o e-mail que o administrador já cadastrou pra você e crie sua senha.
      </p>

      {erro && (
        <p className="muted small" style={{ color: "var(--red)", marginBottom: "1rem" }}>
          {erro}
        </p>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>E-mail</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </div>
        <div className="form-row">
          <label>Nova senha</label>
          <input type="password" value={senhaNova} onChange={(e) => setSenhaNova(e.target.value)} required minLength={4} />
        </div>
        <div className="form-row">
          <label>Confirmar nova senha</label>
          <input type="password" value={confirmar} onChange={(e) => setConfirmar(e.target.value)} required minLength={4} />
        </div>
        <button type="submit" style={{ width: "100%", justifyContent: "center" }} disabled={carregando}>
          {carregando ? "Criando…" : "Criar senha"}
        </button>
      </form>

      <button
        type="button"
        className="btn-link"
        style={{ width: "100%", justifyContent: "center", marginTop: "0.75rem" }}
        onClick={onVoltar}
      >
        Voltar para o login
      </button>
    </>
  );
}

export default function Login() {
  const { usuario, carregando } = useAuth();
  const [modo, setModo] = useState("login"); // "login" | "primeiro-acesso"

  if (!carregando && usuario) {
    return <Navigate to="/" replace />;
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
        <img src="/aegis-logo.png" alt="Aegis" style={{ width: 52, height: "auto", display: "block", margin: "0 auto 1rem" }} />
        <p className="section-title" style={{ margin: "0 0 0.25rem", textAlign: "center" }}>
          Aegis
        </p>

        {modo === "login" ? (
          <TelaLogin onIrParaPrimeiroAcesso={() => setModo("primeiro-acesso")} />
        ) : (
          <TelaPrimeiroAcesso onVoltar={() => setModo("login")} />
        )}
      </div>
    </div>
  );
}
