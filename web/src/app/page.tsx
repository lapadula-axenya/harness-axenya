import { Board } from "@/components/kanban/board";
import { MISSIONS } from "@/lib/mock-data";
import { Filter, LayoutGrid, Plus, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const pendingApprovals = MISSIONS.filter(
    (m) => m.state === "plan_review"
  ).length;
  const inProd = MISSIONS.filter((m) => m.state === "in_production").length;
  const driftAlerts = MISSIONS.filter((m) =>
    m.events.some((e) => e.kind === "drift_detected")
  ).length;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border/60 px-5 py-3">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-base font-semibold tracking-tight">
              Kanban de missões
            </h1>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              Cada coluna é um estado da missão. Arrasta o card pra transicionar
              · clica pra abrir.
            </p>
          </div>
          <div className="ml-2 hidden items-center gap-4 border-l border-border/60 pl-4 text-[11px] md:flex">
            <Stat
              label="Aprovações pendentes"
              value={pendingApprovals}
              accent="amber"
            />
            <Stat label="Em produção" value={inProd} accent="emerald" />
            <Stat label="Drift alerts" value={driftAlerts} accent="rose" />
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <Button size="sm" variant="ghost" className="h-8 gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5" /> Filtros
          </Button>
          <Button size="sm" variant="ghost" className="h-8 gap-1.5 text-xs">
            <SlidersHorizontal className="h-3.5 w-3.5" /> Agrupar
          </Button>
          <Button size="sm" variant="ghost" className="h-8 gap-1.5 text-xs">
            <LayoutGrid className="h-3.5 w-3.5" /> Visualização
          </Button>
          <Button size="sm" className="h-8 gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Nova missão
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden pt-3">
        <Board />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: "amber" | "emerald" | "rose";
}) {
  const colors = {
    amber: "text-amber-300",
    emerald: "text-emerald-300",
    rose: "text-rose-300",
  };
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`text-base font-semibold tabular-nums ${colors[accent]}`}
      >
        {value}
      </span>
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}
