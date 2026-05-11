"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Clock,
  Pause,
  Play,
  Repeat,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import {
  processesApi,
  type Process,
  type ProcessLastStatus,
  type ProcessSummary,
} from "@/lib/api";
import { relativeTime } from "@/lib/time";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 8000;

export function ProcessesTable() {
  const [items, setItems] = useState<Process[] | null>(null);
  const [summary, setSummary] = useState<ProcessSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([
        processesApi.list(),
        processesApi.summary(),
      ]);
      setItems(list);
      setSummary(sum);
      setNowMs(Date.now());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar");
    }
  }, []);

  useEffect(() => {
    // Fetch-on-mount + polling. setState inside the body is intentional —
    // it is the canonical pattern for "subscribe to an external system"
    // (here: the backend), which React's docs call out as the legitimate use
    // of effects.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    const id = window.setInterval(load, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [load]);

  const onToggle = useCallback(
    async (p: Process) => {
      setPendingId(p.id);
      const next = p.status === "active" ? "pause" : "resume";
      try {
        const updated = await processesApi.setStatus(p.id, next);
        setItems((cur) =>
          cur ? cur.map((x) => (x.id === updated.id ? updated : x)) : cur,
        );
        toast.success(
          next === "pause"
            ? `Processo "${p.name}" pausado`
            : `Processo "${p.name}" reativado`,
        );
        await load();
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Falha ao mudar status",
        );
      } finally {
        setPendingId(null);
      }
    },
    [load],
  );

  const summaryCounts = useMemo(() => {
    if (summary) return summary;
    if (!items) return null;
    return {
      active: items.filter((p) => p.status === "active").length,
      paused: items.filter((p) => p.status === "paused").length,
      next_within_1h: items.filter(
        (p) =>
          p.status === "active" &&
          p.next_run_at &&
          new Date(p.next_run_at).getTime() - nowMs <= 3_600_000,
      ).length,
    };
  }, [items, summary, nowMs]);

  return (
    <div>
      <Stats summary={summaryCounts} />

      {error && (
        <div className="mb-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-md border border-border/60">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-border/60 text-[10px] uppercase tracking-[0.14em] text-muted-foreground/70">
              <Th className="w-[28%] pl-4">Processo</Th>
              <Th className="w-[14%]">Schedule</Th>
              <Th className="w-[16%]">Dispara</Th>
              <Th className="w-[10%]">
                <span className="block leading-tight">Success</span>
                <span className="block leading-tight text-[9px] tracking-[0.18em]">
                  30d
                </span>
              </Th>
              <Th className="w-[10%]">Última run</Th>
              <Th className="w-[8%]">Próxima</Th>
              <Th className="w-[10%]">Owner</Th>
              <Th className="w-[8%]">Status</Th>
              <Th className="w-[40px] pr-3"> </Th>
            </tr>
          </thead>
          <tbody>
            {items === null && <SkeletonRows />}
            {items?.length === 0 && (
              <tr>
                <td
                  colSpan={9}
                  className="px-4 py-10 text-center text-muted-foreground"
                >
                  Nenhum processo cadastrado ainda.
                </td>
              </tr>
            )}
            {items?.map((p) => (
              <ProcessRow
                key={p.id}
                process={p}
                pending={pendingId === p.id}
                onToggle={() => onToggle(p)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <th
      className={cn(
        "px-3 py-3 text-left font-medium align-bottom",
        className,
      )}
    >
      {children}
    </th>
  );
}

function Stats({ summary }: { summary: ProcessSummary | null }) {
  if (!summary) {
    return (
      <div className="mb-4 flex items-center gap-6 text-[11px] text-muted-foreground">
        <span>Carregando…</span>
      </div>
    );
  }
  return (
    <div className="mb-4 flex items-center gap-6 text-sm">
      <Counter value={summary.active} label="Ativos" tone="emerald" />
      <Counter value={summary.paused} label="Pausados" tone="amber" />
      <Counter
        value={summary.next_within_1h}
        label="Próximos 1h"
        tone="violet"
      />
    </div>
  );
}

function Counter({
  value,
  label,
  tone,
}: {
  value: number;
  label: string;
  tone: "emerald" | "amber" | "violet";
}) {
  const toneClass = {
    emerald: "text-emerald-300",
    amber: "text-amber-300",
    violet: "text-violet-300",
  }[tone];
  return (
    <div className="flex items-center gap-1.5">
      <span className={cn("text-base font-semibold tabular-nums", toneClass)}>
        {value}
      </span>
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}

function ProcessRow({
  process: p,
  pending,
  onToggle,
}: {
  process: Process;
  pending: boolean;
  onToggle: () => void;
}) {
  const active = p.status === "active";
  return (
    <tr className="group border-b border-border/40 last:border-b-0 hover:bg-muted/20">
      <td className="px-4 py-4 align-top">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border/60 bg-muted/30 text-muted-foreground">
            <Repeat className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <div className="truncate font-medium text-foreground">{p.name}</div>
            <div className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-muted-foreground/80">
              {p.description}
            </div>
          </div>
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <div className="font-mono text-[11px] text-foreground/90">
          {p.cron_expression}
        </div>
        <div className="mt-1 text-[11px] text-muted-foreground/80">
          {p.schedule_human}
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <div className="flex items-center gap-1.5 font-mono text-[11px] text-foreground/90">
          <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground/60" />
          <span className="truncate">{p.target_label}</span>
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <div className="font-semibold text-emerald-300 tabular-nums">
          {formatPercent(p.success_rate_30d)}
        </div>
        <div className="mt-0.5 text-[11px] text-muted-foreground/80 tabular-nums">
          {formatRuns(p.runs_30d)} runs
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <LastRunBadge status={p.last_run_status} />
        <div className="mt-1 text-[11px] text-muted-foreground/80">
          {relativeTime(p.last_run_at)}
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Clock className="h-3 w-3 shrink-0" />
          <span>{active ? relativeTime(p.next_run_at) : "—"}</span>
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium tabular-nums">
            {p.owner_initials}
          </span>
          <span className="truncate text-foreground/90">{p.owner_name}</span>
        </div>
      </td>
      <td className="px-3 py-4 align-top">
        <StatusPill status={p.status} />
      </td>
      <td className="pr-3 py-4 align-middle">
        <button
          type="button"
          onClick={onToggle}
          disabled={pending}
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors",
            "hover:bg-muted hover:text-foreground",
            "disabled:opacity-50",
          )}
          aria-label={active ? "Pausar processo" : "Reativar processo"}
          title={active ? "Pausar" : "Reativar"}
        >
          {active ? (
            <Pause className="h-3.5 w-3.5" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
        </button>
      </td>
    </tr>
  );
}

function LastRunBadge({ status }: { status: ProcessLastStatus | null }) {
  if (!status) {
    return <span className="text-[11px] text-muted-foreground">—</span>;
  }
  if (status === "ok") {
    return (
      <span className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium tracking-wide text-emerald-300">
        <CheckCircle2 className="h-3 w-3" /> OK
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="inline-flex items-center gap-1 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium tracking-wide text-amber-300">
        <AlertTriangle className="h-3 w-3" /> PARTIAL
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded border border-rose-500/30 bg-rose-500/10 px-1.5 py-0.5 text-[10px] font-medium tracking-wide text-rose-300">
      <XCircle className="h-3 w-3" /> FAILED
    </span>
  );
}

function StatusPill({ status }: { status: Process["status"] }) {
  if (status === "active") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-emerald-300">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        Ativo
      </span>
    );
  }
  if (status === "paused") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-muted-foreground/30 bg-muted/40 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/70" />
        Pausado
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/30 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
      Arquivado
    </span>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="border-b border-border/40 last:border-b-0">
          {Array.from({ length: 9 }).map((__, j) => (
            <td key={j} className="px-3 py-4">
              <div className="h-3 w-full animate-pulse rounded bg-muted/40" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

function formatPercent(n: number): string {
  return `${n.toFixed(1).replace(/\.0$/, ".0")}%`;
}

function formatRuns(n: number): string {
  // pt-BR-style grouping (2.880 not 2,880).
  return n.toLocaleString("pt-BR");
}
