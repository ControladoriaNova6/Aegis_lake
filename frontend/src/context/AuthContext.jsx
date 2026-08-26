import { createContext, useContext } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const queryClient = useQueryClient();

  const {
    data: usuario,
    isLoading: carregando,
    isError,
  } = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data } = await api.get("/me");
      return data;
    },
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: async ({ email, senha }) => {
      const { data } = await api.post("/login", { email, senha });
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["me"], data);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      await api.post("/logout");
    },
    onSuccess: () => {
      // Limpa TODO o cache do React Query no logout — sem isso, a próxima
      // pessoa a logar nesse navegador poderia ver por um instante dados
      // em cache da sessão anterior.
      queryClient.setQueryData(["me"], null);
      queryClient.clear();
    },
  });

  const value = {
    usuario: isError ? null : usuario,
    carregando,
    login: loginMutation.mutateAsync,
    loginErro: loginMutation.error?.response?.data?.erro || null,
    loginCarregando: loginMutation.isPending,
    logout: logoutMutation.mutate,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth precisa ser usado dentro de um <AuthProvider>");
  }
  return ctx;
}
