export function brl(valor) {
  const numero = Number(valor);
  if (Number.isNaN(numero)) return "—";
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function mesBr(mes) {
  if (!mes || typeof mes !== "string" || !mes.includes("-")) return mes;
  const [ano, m] = mes.split("-");
  return `${m}/${ano}`;
}

export function mesAtual() {
  const agora = new Date();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  return `${agora.getFullYear()}-${mes}`;
}

export function percentual(valor) {
  const numero = Number(valor);
  if (valor === "" || valor === null || valor === undefined || Number.isNaN(numero)) return "—";
  return `${numero.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}
