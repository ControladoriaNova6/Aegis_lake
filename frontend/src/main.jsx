import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "./theme.css";
import "./style.css";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";

// staleTime: Infinity é a peça-chave — o React Query NUNCA refaz uma
// consulta automaticamente só porque você trocou de tela e voltou. Uma
// vez que o dado de uma chave (ex: ["dashboard", filtros]) foi buscado
// nessa aba do navegador, ele fica ali, instantâneo, até: (a) você chamar
// refetch()/invalidateQueries() explicitamente (ex: botão "Atualizar
// agora"), ou (b) uma mutação (salvar/excluir algo) invalidar essa chave.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: Infinity,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
