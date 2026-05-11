import { MISSIONS, COLUMN_META } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Filter } from "lucide-react";
import { NewMissionTrigger } from "@/components/mission/new-mission-trigger";
import { formatDistanceToNowStrict } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

export default function MissionsPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Todas as missões"
        description="Listagem completa de missões em todos os estados — incluindo arquivadas e pausadas."
        actions={
          <>
            <Button size="sm" variant="ghost" className="gap-1.5 text-xs">
              <Filter className="h-3.5 w-3.5" /> Filtros
            </Button>
            <NewMissionTrigger />
          </>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="overflow-hidden rounded-lg border border-border/60 bg-card/30">
          <table className="w-full text-sm">
            <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">ID</th>
                <th className="px-4 py-2.5 text-left font-medium">Título</th>
                <th className="px-4 py-2.5 text-left font-medium">Estado</th>
                <th className="px-4 py-2.5 text-left font-medium">Owner</th>
                <th className="px-4 py-2.5 text-left font-medium">Agente</th>
                <th className="px-4 py-2.5 text-right font-medium">Runs</th>
                <th className="px-4 py-2.5 text-right font-medium">Custo MTD</th>
                <th className="px-4 py-2.5 text-left font-medium">Atualizada</th>
              </tr>
            </thead>
            <tbody>
              {MISSIONS.map((m) => (
                <tr
                  key={m.id}
                  className="border-t border-border/40 hover:bg-card/60"
                >
                  <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                    {m.id}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-foreground/90">
                      {m.title}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] uppercase tracking-wider",
                        COLUMN_META[m.state].tint
                      )}
                    >
                      {COLUMN_META[m.state].label}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-foreground/10 text-[9px] font-medium">
                        {m.createdBy.initials}
                      </div>
                      <span className="text-muted-foreground">
                        {m.createdBy.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                    {m.agentSlug
                      ? `${m.agentSlug}${m.agentVersion ? "@" + m.agentVersion : ""}`
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {m.metrics.runsTotal > 0
                      ? m.metrics.runsTotal.toLocaleString("pt-BR")
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {m.metrics.costUsdMtd > 0
                      ? `$${m.metrics.costUsdMtd.toFixed(2)}`
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-[11px] text-muted-foreground">
                    {formatDistanceToNowStrict(new Date(m.updatedAt), {
                      locale: ptBR,
                      addSuffix: true,
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
