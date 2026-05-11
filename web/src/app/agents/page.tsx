import { AGENTS } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Bot,
  ChevronRight,
  CircleDot,
  DollarSign,
  GitBranch,
  Plus,
  TrendingDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function AgentsPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Agentes"
        description="Cada agente é um YAML versionado + prompt registrado em Langfuse. A versão em produção pode ser revertida com 1 clique."
        actions={
          <Button size="sm" className="gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Novo agente
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="overflow-hidden rounded-lg border border-border/60 bg-card/30">
          <table className="w-full text-sm">
            <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">Agente</th>
                <th className="px-4 py-2.5 text-left font-medium">Versão</th>
                <th className="px-4 py-2.5 text-left font-medium">Modelo</th>
                <th className="px-4 py-2.5 text-right font-medium">Success 30d</th>
                <th className="px-4 py-2.5 text-right font-medium">Custo 30d</th>
                <th className="px-4 py-2.5 text-left font-medium">Owner</th>
                <th className="px-4 py-2.5 text-left font-medium">Status</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {AGENTS.map((a) => (
                <tr
                  key={a.slug}
                  className="border-t border-border/40 transition-colors hover:bg-card/60"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-foreground/10">
                        <Bot className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-foreground">
                            {a.name}
                          </span>
                          {a.lastDriftAlert && (
                            <TrendingDown
                              className="h-3 w-3 text-rose-400"
                              aria-label="drift alert"
                            />
                          )}
                        </div>
                        <div className="font-mono text-[10.5px] text-muted-foreground">
                          {a.slug}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      <GitBranch className="h-3 w-3 text-muted-foreground" />
                      {a.version}
                      <span className="text-muted-foreground/60">
                        ({a.versionsCount} versões)
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="font-mono text-xs">{a.primaryModel}</span>
                      {a.fallbackModel && (
                        <span className="font-mono text-[10px] text-muted-foreground">
                          ↳ {a.fallbackModel}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span
                      className={cn(
                        "tabular-nums",
                        a.successRate >= 0.95
                          ? "text-emerald-400"
                          : a.successRate >= 0.8
                            ? "text-amber-300"
                            : "text-rose-400"
                      )}
                    >
                      {(a.successRate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex items-center gap-0.5 tabular-nums">
                      <DollarSign className="h-3 w-3 text-muted-foreground" />
                      {a.costUsd30d.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-foreground/10 text-[10px] font-medium">
                        {a.owner.initials}
                      </div>
                      <span className="text-muted-foreground">
                        {a.owner.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] uppercase tracking-wider",
                        a.state === "active" &&
                          "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
                        a.state === "shadow" &&
                          "border-violet-400/40 bg-violet-400/10 text-violet-300",
                        a.state === "paused" &&
                          "border-zinc-400/40 bg-zinc-400/10 text-zinc-300"
                      )}
                    >
                      <CircleDot className="mr-1 h-2.5 w-2.5" />
                      {a.state}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    <ChevronRight className="h-4 w-4" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span>Total: {AGENTS.length} agentes</span>
          <span className="text-muted-foreground/60">·</span>
          <span>
            Drift active:{" "}
            <span className="text-rose-300">
              {AGENTS.filter((a) => a.lastDriftAlert).length}
            </span>
          </span>
          <span className="text-muted-foreground/60">·</span>
          <span>
            Custo total 30d:{" "}
            <span className="text-foreground">
              ${AGENTS.reduce((s, a) => s + a.costUsd30d, 0).toFixed(2)}
            </span>
          </span>
        </div>

        <p className="mt-6 text-[11px] text-muted-foreground/70">
          O Last drift refers to the agent triagem_lead, gerando uma mission
          automática no Kanban (
          <span className="font-mono">m_005</span>). Snapshot a versão em produção é
          mantido em Langfuse Prompts; rollback é uma chamada idempotente.
        </p>
      </div>
    </div>
  );
}
