/**
 * Compact pt-BR relative-time labels matching the Processos screen:
 *   "há 9 horas", "há 3 dias", "em 4 dias", "em 8 horas", "—"
 */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const deltaSec = (then - now) / 1000;
  const abs = Math.abs(deltaSec);

  const past = deltaSec < 0;
  const prefix = past ? "há" : "em";

  const units: { unit: string; sing: string; plural: string; size: number }[] = [
    { unit: "min", sing: "minuto", plural: "minutos", size: 60 },
    { unit: "h", sing: "hora", plural: "horas", size: 3600 },
    { unit: "d", sing: "dia", plural: "dias", size: 86400 },
    { unit: "sem", sing: "semana", plural: "semanas", size: 604800 },
    { unit: "mês", sing: "mês", plural: "meses", size: 2_592_000 },
  ];

  let chosen = units[0];
  for (const u of units) {
    if (abs >= u.size) chosen = u;
  }
  const value = Math.max(1, Math.round(abs / chosen.size));
  const label = value === 1 ? chosen.sing : chosen.plural;
  return `${prefix} ${value} ${label}`;
}
