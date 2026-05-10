import { PageHeader } from "@/components/page-header";
import { AGENTS } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Play, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

export default function EvalsPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Evals & drift"
        description="Rubric DSL escrita pelo Planner como parte do plano. Suite roda em CI + sample online; drift > 2σ abre missão automática de regressão."
        actions={
          <Button size="sm" className="gap-1.5 text-xs">
            <Play className="h-3.5 w-3.5" /> Rodar suite
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-2">
          {AGENTS.map((a) => {
            const drifted = !!a.lastDriftAlert;
            return (
              <div
                key={a.slug}
                className="rounded-lg border border-border/60 bg-card/40 p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-foreground">{a.name}</h3>
                      {drifted && (
                        <Badge
                          variant="outline"
                          className="gap-1 border-rose-400/40 bg-rose-400/10 text-[9.5px] uppercase tracking-wider text-rose-300"
                        >
                          <TrendingDown className="h-2.5 w-2.5" /> drift
                        </Badge>
                      )}
                    </div>
                    <div className="font-mono text-[10.5px] text-muted-foreground">
                      {a.slug}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-semibold tabular-nums">
                      {(a.successRate * 100).toFixed(0)}%
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      score 30d
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex h-20 items-end gap-0.5">
                  {Array.from({ length: 30 }, (_, i) => {
                    const base = a.successRate;
                    const noise =
                      Math.sin((i + a.slug.length) * 0.6) * 0.05 +
                      Math.cos((i + a.slug.length) * 1.1) * 0.025;
                    const drop = i >= 26 && drifted ? -0.16 : 0;
                    const v = Math.max(0.3, Math.min(1, base + noise + drop));
                    return (
                      <div
                        key={i}
                        className={cn(
                          "flex-1 rounded-t-sm",
                          v < 0.78 ? "bg-rose-400/70" : "bg-emerald-400/40"
                        )}
                        style={{ height: `${v * 100}%` }}
                      />
                    );
                  })}
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
                  <span>30d atrás</span>
                  <span>hoje</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
