import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, papeis }) {
  const { usuario, carregando } = useAuth();

  if (carregando) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p className="muted">Carregando…</p>
      </div>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace />;
  }

  if (papeis && !papeis.includes(usuario.papel)) {
    return (
      <div className="card error-card">
        <p className="error-title">Acesso restrito</p>
        <p className="muted small">
          Você não tem permissão para acessar esta página. Fale com um administrador se acha que isso é um engano.
        </p>
      </div>
    );
  }

  return children;
}
