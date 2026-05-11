import { PROCESSES } from "@/lib/mock-processes";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Clock,
  Pause,
  Play,
  Plus,
  Repeat,
  Timer,
} from "lucide-react";
import { format, formatDistanceToNowStrict } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

// Computed at module load (not during render) so the lint rule against
// impure functions in render is happy.
const PROCESS_STATS = (() => {
  const now = Date.now();
  return {
    active: PROCESSES.filter((p) => p.status === "active").length,
    paused: PROCESSES.filter((p) => p.status === "paused").length,
    nextWithin1h: PROCESSES.filter(
      (p) =>
        p.status === "active" &&
        new Date(p.nextRunAt).getTime() - now < 60 * 60 * 1000
    ).length,
  };
})();

function StatusBadge({ status }: { status: "active" | "paused" | "error" }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 text-[10px] uppercase tracking-wider",
        status === "active" &&
          "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
        status === "paused" &&
          "border-zinc-400/40 bg-zinc-400/10 text-zinc-300",
        status === "error" && "border-rose-400/40 bg-rose-400/10 text-rose-300"
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status === "active" ? "ativo" : status === "paused" ? "pausado" : "erro"}
    </Badge>
  );
}

function LastRunBadge({
  status,
}: {
  status?: "ok" | "fail" | "partial";
}) {
  if (!status) return <span className="text-muted-foreground/60">—</span>;
  const map = {
    ok: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
    fail: "border-rose-400/40 bg-rose-400/10 text-rose-300",
    partial: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  };
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-[10px] uppercase tracking-wider",
        map[status]
      )}
    >
      {status}
    </Badge>
  );
}

export default function ProcessesPage() {
  const { active, paused, nextWithin1h } = PROCESS_STATS;

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Processos"
        description="Crons que disparam missions/agentes em horários definidos. Cada execução vira run rastreável no Langfuse e cada falha pode abrir mission de regressão."
        actions={
          <Button size="sm" className="gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Novo processo
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="mb-4 flex items-center gap-4 text-[11px] text-muted-foreground">
          <Stat label="Ativos" value={active} accent="emerald" />
          <Stat label="Pausados" value={paused} accent="zinc" />
          <Stat label="Próximos 1h" value={nextWithin1h} accent="amber" />
        </div>

        <div className="overflow-hidden rounded-lg border border-border/60 bg-card/30">
          <table className="w-full text-sm">
            <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">Processo</th>
                <th className="px-4 py-2.5 text-left font-medium">Schedule</th>
                <th className="px-4 py-2.5 text-left font-medium">Dispara</th>
                <th className="px-4 py-2.5 text-right font-medium">Success 30d</th>
                <th className="px-4 py-2.5 text-left font-medium">Última run</th>
                <th className="px-4 py-2.5 text-left font-medium">Próxima</th>
                <th className="px-4 py-2.5 text-left font-medium">Owner</th>
                <th className="px-4 py-2.5 text-left font-medium">Status</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {PROCESSES.map((p) => {
                const next = new Date(p.nextRunAt);
                const last = p.lastRunAt ? new Date(p.lastRunAt) : null;
                return (
                  <tr
                    key={p.id}
                    className="border-t border-border/40 hover:bg-card/60"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-start gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-foreground/10">
                          <Repeat className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-medium text-foreground">
                            {p.name}
                          </div>
                          <div className="line-clamp-1 text-[10.5px] text-muted-foreground">
                            {p.description}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-mono text-[11px] text-foreground/90">
                          {p.cron}
                        </span>
                        <span className="text-[10.5px] text-muted-foreground">
                          {p.cronHuman}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        {p.triggers.map((t) => (
                          <span
                            key={t.id}
                            className="inline-flex items-center gap-1 font-mono text-[10.5px] text-foreground/80"
                          >
                            <ArrowRight className="h-2.5 w-2.5 text-muted-foreground" />
                            {t.label}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={cn(
                          "tabular-nums",
                          p.successRate30d >= 0.95
                            ? "text-emerald-400"
                            : p.successRate30d >= 0.85
                              ? "text-amber-300"
                              : "text-rose-400"
                        )}
                      >
                        {(p.successRate30d * 100).toFixed(1)}%
                      </span>
                      <div className="text-[10px] text-muted-foreground">
                        {p.runs30d.toLocaleString("pt-BR")} runs
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <LastRunBadge status={p.lastRunStatus} />
                        {last && (
                          <span
                            className="text-[10.5px] text-muted-foreground"
                            title={format(last, "PPpp", { locale: ptBR })}
                          >
                            {formatDistanceToNowStrict(last, {
                              locale: ptBR,
                              addSuffix: true,
                            })}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span
                          title={format(next, "PPpp", { locale: ptBR })}
                          className={cn(
                            p.status === "paused" && "text-muted-foreground/40 line-through"
                          )}
                        >
                          {p.status === "paused"
                            ? "—"
                            : formatDistanceToNowStrict(next, {
                                locale: ptBR,
                                addSuffix: true,
                              })}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-xs">
                        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-foreground/10 text-[9px] font-medium">
                          {p.owner.initials}
                        </div>
                        <span className="text-muted-foreground">
                          {p.owner.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-muted-foreground"
                      >
                        {p.status === "paused" ? (
                          <Play className="h-3.5 w-3.5" />
                        ) : (
                          <Pause className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="mt-4 flex items-center gap-2 text-[11px] text-muted-foreground/80">
          <Timer className="h-3 w-3" />
          Schedules em cron padrão Unix. Toda execução grava em audit log e
          tem trace correspondente no Langfuse.
        </p>
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
  accent: "emerald" | "zinc" | "amber";
}) {
  const colors = {
    emerald: "text-emerald-300",
    zinc: "text-zinc-300",
    amber: "text-amber-300",
  };
  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-base font-semibold tabular-nums ${colors[accent]}`}>
        {value}
      </span>
      <span>{label}</span>
    </div>
  );
}
