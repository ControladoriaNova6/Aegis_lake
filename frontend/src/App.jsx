import { Routes, Route } from "react-router-dom";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Importar from "./pages/Importar";
import Registros from "./pages/Registros";
import Relatorio from "./pages/Relatorio";
import Parametros from "./pages/Parametros";
import Indicados from "./pages/Indicados";
import CampanhasVisaoGeral from "./pages/CampanhasVisaoGeral";
import CampanhasCadastro from "./pages/CampanhasCadastro";
import CampanhasCriterios from "./pages/CampanhasCriterios";
import CriteriosHistorico from "./pages/CriteriosHistorico";
import AdminUsuarios from "./pages/AdminUsuarios";
import Manutencao from "./pages/Manutencao";
import ValoresAbertosVisaoGeral from "./pages/ValoresAbertosVisaoGeral";
import ValoresAbertosCadastro from "./pages/ValoresAbertosCadastro";
import ValoresAbertosAcompanhamento from "./pages/ValoresAbertosAcompanhamento";

const SOMENTE_EDITOR_ADMIN = ["admin", "editor"];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />

        <Route
          path="/importar"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><Importar /></ProtectedRoute>}
        />
        <Route path="/logs" element={<Registros />} />
        <Route path="/relatorio" element={<Relatorio />} />
        <Route
          path="/parametros"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><Parametros /></ProtectedRoute>}
        />
        <Route
          path="/indicados"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><Indicados /></ProtectedRoute>}
        />

        <Route path="/campanhas" element={<CampanhasVisaoGeral />} />
        <Route
          path="/campanhas/cadastro"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><CampanhasCadastro /></ProtectedRoute>}
        />
        <Route
          path="/campanhas/criterios"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><CampanhasCriterios /></ProtectedRoute>}
        />
        <Route
          path="/campanhas/criterios/historico"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><CriteriosHistorico /></ProtectedRoute>}
        />

        <Route
          path="/admin/usuarios"
          element={<ProtectedRoute papeis={["admin"]}><AdminUsuarios /></ProtectedRoute>}
        />
        <Route
          path="/admin/manutencao"
          element={<ProtectedRoute papeis={["admin"]}><Manutencao /></ProtectedRoute>}
        />

        <Route
          path="/valores-abertos"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><ValoresAbertosVisaoGeral /></ProtectedRoute>}
        />
        <Route
          path="/valores-abertos/cadastro"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><ValoresAbertosCadastro /></ProtectedRoute>}
        />
        <Route
          path="/valores-abertos/acompanhamento"
          element={<ProtectedRoute papeis={SOMENTE_EDITOR_ADMIN}><ValoresAbertosAcompanhamento /></ProtectedRoute>}
        />
      </Route>
    </Routes>
  );
}
