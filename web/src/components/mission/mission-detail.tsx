"use client";

import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Clock,
  Copy,
  DollarSign,
  Download,
  ExternalLink,
  GitBranch,
  Sparkles,
  X,
} from "lucide-react";
import type { Mission, MissionEvent } from "@/lib/types";
import { COLUMN_META } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import { formatDistanceToNowStrict, format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useState } from "react";

function StateBadge({ state }: { state: Mission["state"] }) {
  const m = COLUMN_META[state];
  return (
    <Badge
      variant="outline"
      className={cn(
        "border-border bg-card text-[10.5px] uppercase tracking-wider",
        m.tint
      )}
    >
      {m.label}
    </Badge>
  );
}

function Section({
  title,
  right,
  children,
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border/60 bg-card/40">
      <div className="flex items-center justify-between border-b border-border/40 px-3 py-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h3>
        {right}
      </div>
      <div className="px-3 py-3 text-sm">{children}</div>
    </div>
  );
}

function PlanTab({ mission }: { mission: Mission }) {
  const plan = mission.plan;
  if (!plan) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border/50 bg-card/20 text-sm">
        <Sparkles className="h-6 w-6 text-muted-foreground" />
        <div className="text-center">
          <p className="text-foreground/90">Plano ainda não gerado.</p>
          <p className="mt-1 text-xs text-muted-foreground">
            O Planner pode gerar um plano a partir da intent abaixo.
          </p>
        </div>
        <Button size="sm" className="mt-1">
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          Gerar plano com Planner
        </Button>
        <div className="mt-4 w-full rounded border border-border/40 bg-muted/30 p-3 text-xs text-foreground/80">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Intent
          </span>
          <p className="mt-1 leading-relaxed">{mission.intent}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between rounded-md border border-border/40 bg-muted/20 px-3 py-2">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Versão</span>
          <span className="font-mono">v{plan.version}</span>
          <span className="text-muted-foreground/60">·</span>
          <span className="text-muted-foreground">por</span>
          <span className="font-mono">{plan.generatedBy}</span>
          <span className="text-muted-foreground/60">·</span>
          <span className="text-muted-foreground">confidence</span>
          <span
            className={cn(
              "font-mono tabular-nums",
              plan.confidence >= 0.85
                ? "text-emerald-400"
                : plan.confidence >= 0.7
                  ? "text-amber-400"
                  : "text-rose-400"
            )}
          >
            {(plan.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs">
            <Copy className="h-3 w-3" /> JSON
          </Button>
          <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs">
            <GitBranch className="h-3 w-3" /> diff vs v{Math.max(plan.version - 1, 1)}
          </Button>
        </div>
      </div>

      <Section title="Escopo">
        <p className="leading-relaxed text-foreground/90">{plan.scope}</p>
      </Section>

      <Section title="Não está no escopo">
        <ul className="space-y-1.5">
          {plan.nonScope.map((n, i) => (
            <li key={i} className="flex items-start gap-2 text-foreground/80">
              <X className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-400/80" />
              <span>{n}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        title="Skills necessárias"
        right={
          <span className="text-[10.5px] text-muted-foreground">
            {plan.requiredSkills.length} skills
          </span>
        }
      >
        <div className="grid gap-2 sm:grid-cols-2">
          {plan.requiredSkills.map((s) => (
            <div
              key={s.name}
              className="rounded border border-border/40 bg-background/40 px-2 py-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-foreground">
                  {s.name}
                </span>
                {s.existsInRegistry ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-amber-400" />
                )}
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {s.description}
              </p>
              {s.sensitivityTags.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {s.sensitivityTags.map((t) => (
                    <Badge
                      key={t}
                      variant="outline"
                      className="border-rose-400/30 bg-rose-400/10 text-[9px] uppercase tracking-wider text-rose-300"
                    >
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </Section>

      <Section title="Fluxo (YAML gerado)">
        <pre className="overflow-x-auto rounded bg-background/60 p-3 font-mono text-[11px] leading-relaxed text-foreground/85">
          {plan.flowYaml}
        </pre>
      </Section>

      <Section title="Pontos de aprovação humana">
        {plan.approvalPoints.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Sem aprovações inline — execução é totalmente autônoma.
          </p>
        ) : (
          <ul className="space-y-2">
            {plan.approvalPoints.map((a, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded border border-border/40 bg-background/40 px-2 py-1.5 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-foreground/90">{a.step}</span>
                  <span className="text-muted-foreground/60">quando</span>
                  <span className="font-mono text-amber-300">{a.condition}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <span className="rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
                    {a.approverRole}
                  </span>
                  <span className="tabular-nums">SLA {a.slaHours}h</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Riscos">
        <ul className="space-y-2">
          {plan.risks.map((r, i) => (
            <li
              key={i}
              className="rounded border border-border/40 bg-background/40 px-3 py-2"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm text-foreground/90">{r.risk}</p>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] uppercase tracking-wider",
                    r.severity === "high" &&
                      "border-rose-400/40 bg-rose-400/10 text-rose-300",
                    r.severity === "medium" &&
                      "border-amber-400/40 bg-amber-400/10 text-amber-300",
                    r.severity === "low" &&
                      "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                  )}
                >
                  {r.severity}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                <span className="text-foreground/60">Mitigação:</span>{" "}
                {r.mitigation}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      {mission.state === "plan_review" && plan.status === "pending" && (
        <div className="sticky bottom-0 -mx-4 -mb-4 border-t border-border bg-background/95 px-4 py-3 backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-muted-foreground">
              Plano aguarda decisão. Aprovação é registrada com motivo no audit log.
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" className="text-xs">
                Pedir alterações
              </Button>
              <Button size="sm" variant="outline" className="text-xs">
                Rejeitar
              </Button>
              <Button size="sm" className="text-xs">
                <Check className="mr-1.5 h-3.5 w-3.5" /> Aprovar plano
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EventIcon({ kind }: { kind: MissionEvent["kind"] }) {
  const map: Record<MissionEvent["kind"], { color: string; label: string }> = {
    state_change: { color: "text-blue-300", label: "→" },
    plan_generated: { color: "text-amber-300", label: "✦" },
    comment: { color: "text-zinc-300", label: "💬" },
    run_started: { color: "text-emerald-300", label: "▶" },
    run_step: { color: "text-zinc-400", label: "·" },
    run_completed: { color: "text-emerald-300", label: "✓" },
    eval_failed: { color: "text-rose-400", label: "✕" },
    eval_passed: { color: "text-emerald-300", label: "✓" },
    approval_decided: { color: "text-blue-300", label: "✓" },
    drift_detected: { color: "text-rose-400", label: "⚠" },
  };
  const m = map[kind];
  return (
    <span className={cn("inline-flex h-4 w-4 items-center justify-center text-xs", m.color)}>
      {m.label}
    </span>
  );
}

function ExecutionTab({ mission }: { mission: Mission }) {
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Runs (total)" value={mission.metrics.runsTotal.toLocaleString("pt-BR")} />
        <Stat
          label="Success rate"
          value={
            mission.metrics.runsTotal > 0
              ? `${((mission.metrics.runsSuccess / mission.metrics.runsTotal) * 100).toFixed(1)}%`
              : "—"
          }
        />
        <Stat
          label="p95 latency"
          value={
            mission.metrics.p95LatencyMs
              ? `${(mission.metrics.p95LatencyMs / 1000).toFixed(1)}s`
              : "—"
          }
        />
        <Stat
          label="Última run"
          value={
            mission.metrics.lastRunAt
              ? formatDistanceToNowStrict(new Date(mission.metrics.lastRunAt), {
                  locale: ptBR,
                  addSuffix: true,
                })
              : "—"
          }
        />
      </div>

      <Section
        title="Timeline"
        right={
          <Button size="sm" variant="ghost" className="h-6 gap-1 text-[10.5px]">
            <ExternalLink className="h-3 w-3" /> Abrir no Langfuse
          </Button>
        }
      >
        {mission.events.length === 0 ? (
          <p className="text-xs text-muted-foreground">Sem eventos ainda.</p>
        ) : (
          <ol className="relative space-y-2 pl-4">
            <div className="absolute bottom-1 left-1.5 top-1 w-px bg-border/60" />
            {[...mission.events]
              .reverse()
              .map((e) => {
                const ts = new Date(e.createdAt);
                const isRun =
                  e.kind === "run_started" || e.kind === "run_completed";
                const runId =
                  (e.payload && "runId" in e.payload && (e.payload.runId as string)) ||
                  null;
                const expanded = runId && expandedRun === runId;
                return (
                  <li key={e.id} className="relative">
                    <span className="absolute -left-3 top-1 h-2.5 w-2.5 rounded-full border border-border bg-card" />
                    <div className="ml-1 flex items-start gap-2 rounded border border-border/40 bg-background/40 px-2.5 py-1.5">
                      <EventIcon kind={e.kind} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-foreground/90">
                              {humanizeEvent(e)}
                            </span>
                            {runId && (
                              <span className="font-mono text-[10px] text-muted-foreground/70">
                                {runId}
                              </span>
                            )}
                          </div>
                          <span
                            className="font-mono text-[10px] tabular-nums text-muted-foreground/70"
                            title={format(ts, "PPpp", { locale: ptBR })}
                          >
                            {format(ts, "HH:mm:ss")}
                          </span>
                        </div>
                        {isRun && runId && (
                          <button
                            onClick={() =>
                              setExpandedRun((curr) =>
                                curr === runId ? null : runId
                              )
                            }
                            className="mt-1 inline-flex items-center gap-1 text-[10.5px] text-muted-foreground hover:text-foreground"
                          >
                            {expanded ? (
                              <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ChevronRight className="h-3 w-3" />
                            )}
                            {expanded ? "esconder steps" : "ver outputs intermediários"}
                          </button>
                        )}
                        {expanded && (
                          <div className="mt-1.5 space-y-1 rounded border border-border/30 bg-background/60 p-2 font-mono text-[10.5px] text-muted-foreground">
                            <div>
                              <span className="text-foreground/70">[01]</span>{" "}
                              enrich → apollo.lookup ({" "}
                              <span className="text-emerald-400">200</span>, 412ms,
                              $0.001)
                            </div>
                            <div>
                              <span className="text-foreground/70">[02]</span>{" "}
                              classify → claude-sonnet-4-6 (1.8s, $0.012, score 0.81)
                            </div>
                            <div>
                              <span className="text-foreground/70">[03]</span>{" "}
                              hubspot.update_contact ({" "}
                              <span className="text-emerald-400">200</span>, 220ms)
                            </div>
                            <div>
                              <span className="text-foreground/70">[04]</span>{" "}
                              slack.post → #comercial ({" "}
                              <span className="text-emerald-400">200</span>, 180ms)
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
          </ol>
        )}
      </Section>
    </div>
  );
}

function humanizeEvent(e: MissionEvent): string {
  switch (e.kind) {
    case "plan_generated":
      return `Plano v${(e.payload as { version?: number }).version ?? "?"} gerado`;
    case "comment":
      return (e.actor?.name ?? "Sistema") + " comentou";
    case "run_started":
      return "Run iniciada";
    case "run_completed":
      return `Run concluída · $${((e.payload as { costUsd?: number }).costUsd ?? 0).toFixed(3)}`;
    case "run_step":
      return `Step ${(e.payload as { step?: string }).step ?? ""}`;
    case "eval_passed":
      return `Eval passou · score ${(e.payload as { score?: number }).score?.toFixed(2)}`;
    case "eval_failed":
      return "Eval falhou";
    case "drift_detected":
      const p = e.payload as { from?: number; to?: number };
      return `Drift detectado · ${p.from?.toFixed(2)} → ${p.to?.toFixed(2)}`;
    case "state_change":
      return "Transição de estado";
    case "approval_decided":
      return "Aprovação decidida";
  }
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/40 bg-card/40 px-3 py-2">
      <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 text-lg font-medium tabular-nums">{value}</div>
    </div>
  );
}

function ApprovalsTab({ mission }: { mission: Mission }) {
  return (
    <div className="space-y-3">
      <Section title="Decisões registradas">
        {mission.approvals.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Nenhuma aprovação registrada para esta missão ainda.
          </p>
        ) : (
          <ol className="space-y-2">
            {mission.approvals.map((a) => (
              <li
                key={a.id}
                className="rounded border border-border/40 bg-background/40 px-3 py-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] uppercase tracking-wider",
                        a.decision === "approved" &&
                          "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
                        a.decision === "rejected" &&
                          "border-rose-400/40 bg-rose-400/10 text-rose-300",
                        a.decision === "changes_requested" &&
                          "border-amber-400/40 bg-amber-400/10 text-amber-300"
                      )}
                    >
                      {a.decision === "approved"
                        ? "aprovado"
                        : a.decision === "rejected"
                          ? "rejeitado"
                          : "pediu alterações"}
                    </Badge>
                    <span className="text-muted-foreground/80">
                      {a.type === "plan"
                        ? "plano"
                        : a.type === "production_promote"
                          ? "promover prod"
                          : "gate de execução"}
                    </span>
                  </div>
                  <span
                    className="text-muted-foreground/70"
                    title={a.decidedAt}
                  >
                    {format(new Date(a.decidedAt), "dd MMM yyyy, HH:mm", {
                      locale: ptBR,
                    })}
                  </span>
                </div>
                <div className="mt-1.5 text-sm text-foreground/90">
                  <span className="text-muted-foreground">Por:</span>{" "}
                  {a.decidedBy.name}
                </div>
                <div className="mt-0.5 text-xs italic text-muted-foreground">
                  &ldquo;{a.reason}&rdquo;
                </div>
              </li>
            ))}
          </ol>
        )}
      </Section>

      <div className="flex items-center justify-between rounded border border-amber-400/30 bg-amber-400/[0.04] px-3 py-2 text-xs text-amber-200/80">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-3.5 w-3.5" />
          Audit log é append-only. Toda decisão é exportável para auditoria externa.
        </div>
        <Button size="sm" variant="ghost" className="h-7 gap-1 text-[10.5px]">
          <Download className="h-3 w-3" /> CSV
        </Button>
      </div>
    </div>
  );
}

function EvalsTab({ mission }: { mission: Mission }) {
  const rubric = mission.plan?.evalRubric ?? [];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Stat
          label="Score médio"
          value={
            mission.metrics.avgEvalScore !== undefined
              ? mission.metrics.avgEvalScore.toFixed(2)
              : "—"
          }
        />
        <Stat label="Checks no rubric" value={String(rubric.length)} />
        <Stat
          label="Drift status"
          value={
            mission.events.some((e) => e.kind === "drift_detected")
              ? "alerta"
              : "estável"
          }
        />
      </div>

      <Section title="Rubric do plano">
        {rubric.length === 0 ? (
          <p className="text-xs text-muted-foreground">Rubric ainda não definida.</p>
        ) : (
          <ul className="space-y-2">
            {rubric.map((c) => (
              <li
                key={c.id}
                className="rounded border border-border/40 bg-background/40 px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2 text-xs">
                    <Badge
                      variant="outline"
                      className={cn(
                        "shrink-0 text-[10px] uppercase tracking-wider",
                        c.kind === "deterministic"
                          ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                          : "border-violet-400/30 bg-violet-400/10 text-violet-300"
                      )}
                    >
                      {c.kind === "deterministic" ? "det" : "judge"}
                    </Badge>
                    <span className="truncate text-foreground/90">
                      {c.description}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs tabular-nums">
                    <span className="text-muted-foreground">
                      peso {c.weight.toFixed(2)}
                    </span>
                    {c.lastScore !== undefined && (
                      <span
                        className={cn(
                          "font-mono",
                          c.lastScore >= 0.9
                            ? "text-emerald-400"
                            : c.lastScore >= 0.7
                              ? "text-amber-400"
                              : "text-rose-400"
                        )}
                      >
                        {c.lastScore.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Drift (últimos 30 dias)">
        <div className="flex h-32 items-end gap-1">
          {Array.from({ length: 30 }, (_, i) => {
            const base = mission.metrics.avgEvalScore ?? 0.85;
            const noise = Math.sin(i * 0.7) * 0.05 + Math.cos(i * 1.3) * 0.025;
            const dropAtEnd = i >= 27 && mission.agentSlug === "triagem_lead" ? -0.18 : 0;
            const v = Math.max(0.3, Math.min(1, base + noise + dropAtEnd));
            const drifted = v < 0.78;
            return (
              <div
                key={i}
                className={cn(
                  "flex-1 rounded-t-sm",
                  drifted ? "bg-rose-400/70" : "bg-emerald-400/40"
                )}
                style={{ height: `${v * 100}%` }}
                title={`d-${30 - i}: ${v.toFixed(2)}`}
              />
            );
          })}
        </div>
        <div className="mt-2 flex items-center justify-between text-[10.5px] text-muted-foreground">
          <span>30 dias atrás</span>
          <span>hoje</span>
        </div>
      </Section>
    </div>
  );
}

function CostTab({ mission }: { mission: Mission }) {
  const estimate = mission.plan?.costEstimate;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Stat
          label="Custo MTD"
          value={`$${mission.metrics.costUsdMtd.toFixed(2)}`}
        />
        <Stat
          label="$/run estimado"
          value={estimate ? `$${estimate.perRunUsd.toFixed(3)}` : "—"}
        />
        <Stat
          label="Estimativa mensal"
          value={estimate ? `$${estimate.monthlyUsd.toFixed(2)}` : "—"}
        />
      </div>

      <Section title="Premissas do plano">
        {estimate ? (
          <p className="text-sm text-foreground/85">
            {estimate.volumeAssumption}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Estimativa só é gerada após o Planner produzir o plano.
          </p>
        )}
      </Section>

      <Section title="Custo por modelo (últimos 30d)">
        <div className="space-y-2">
          {[
            { name: "claude-sonnet-4-6", usd: 142.1, color: "bg-foreground/70" },
            { name: "claude-opus-4-7 (fallback)", usd: 18.3, color: "bg-foreground/40" },
            { name: "apollo.lookup (skill)", usd: 8.0, color: "bg-foreground/25" },
          ].map((row) => {
            const max = 142.1;
            return (
              <div key={row.name}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-foreground/80">{row.name}</span>
                  <span className="font-mono tabular-nums text-foreground/90">
                    ${row.usd.toFixed(2)}
                  </span>
                </div>
                <div className="mt-1 h-1.5 w-full rounded-full bg-muted/40">
                  <div
                    className={cn("h-full rounded-full", row.color)}
                    style={{ width: `${(row.usd / max) * 100}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}

export function MissionDetail({
  mission,
  onOpenChange,
}: {
  mission: Mission | null;
  onOpenChange: (open: boolean) => void;
}) {
  if (!mission) return null;

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="max-h-[92vh] w-[min(960px,95vw)] max-w-[960px] gap-0 overflow-hidden bg-background p-0"
      >
        <div className="border-b border-border/60 bg-card/40 px-6 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[10.5px] uppercase tracking-wider text-muted-foreground">
              <span className="font-mono">{mission.id}</span>
              <span className="text-muted-foreground/60">·</span>
              <StateBadge state={mission.state} />
              <span className="text-muted-foreground/60">·</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDistanceToNowStrict(new Date(mission.updatedAt), {
                  locale: ptBR,
                  addSuffix: true,
                })}
              </span>
            </div>
            <button
              onClick={() => onOpenChange(false)}
              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <DialogTitle className="mt-2 text-xl font-semibold tracking-tight">
            {mission.title}
          </DialogTitle>
          <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted-foreground">
            {mission.intent}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
            {mission.agentSlug && (
              <span className="flex items-center gap-1 font-mono">
                <GitBranch className="h-3 w-3" />
                {mission.agentSlug}
                {mission.agentVersion ? `@${mission.agentVersion}` : ""}
              </span>
            )}
            <span className="flex items-center gap-1">
              <CircleDot className="h-3 w-3 text-emerald-400" />
              criado por {mission.createdBy.name}
            </span>
            {mission.metrics.costUsdMtd > 0 && (
              <span className="flex items-center gap-1 tabular-nums">
                <DollarSign className="h-3 w-3" />
                {mission.metrics.costUsdMtd.toFixed(2)} MTD
              </span>
            )}
          </div>
        </div>

        <Tabs defaultValue="plan" className="flex flex-col overflow-hidden">
          <div className="border-b border-border/60 px-6">
            <TabsList className="h-10 bg-transparent p-0">
              <TabsTrigger value="plan">Plano</TabsTrigger>
              <TabsTrigger value="execution">Execução</TabsTrigger>
              <TabsTrigger value="approvals">
                Aprovações
                {mission.approvals.length > 0 && (
                  <span className="ml-1.5 rounded bg-foreground/10 px-1.5 text-[10px]">
                    {mission.approvals.length}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="evals">Evals</TabsTrigger>
              <TabsTrigger value="cost">Custo</TabsTrigger>
            </TabsList>
          </div>

          <div className="overflow-y-auto px-6 py-4">
            <TabsContent value="plan" className="mt-0">
              <PlanTab mission={mission} />
            </TabsContent>
            <TabsContent value="execution" className="mt-0">
              <ExecutionTab mission={mission} />
            </TabsContent>
            <TabsContent value="approvals" className="mt-0">
              <ApprovalsTab mission={mission} />
            </TabsContent>
            <TabsContent value="evals" className="mt-0">
              <EvalsTab mission={mission} />
            </TabsContent>
            <TabsContent value="cost" className="mt-0">
              <CostTab mission={mission} />
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
