import { AUDIT } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, FileClock, Filter } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

export default function AuditPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Audit log"
        description="Toda decisão de autorização e toda transição de missão fica aqui, append-only. Retenção: 1 ano hot, 3 anos archived em BigQuery."
        actions={
          <>
            <Button size="sm" variant="ghost" className="gap-1.5 text-xs">
              <Filter className="h-3.5 w-3.5" /> Filtros
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5 text-xs">
              <Download className="h-3.5 w-3.5" /> Export CSV
            </Button>
          </>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="overflow-hidden rounded-lg border border-border/60 bg-card/30">
          <table className="w-full text-sm">
            <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">Quando</th>
                <th className="px-4 py-2.5 text-left font-medium">Ator</th>
                <th className="px-4 py-2.5 text-left font-medium">Ação</th>
                <th className="px-4 py-2.5 text-left font-medium">Recurso</th>
                <th className="px-4 py-2.5 text-left font-medium">Decisão</th>
                <th className="px-4 py-2.5 text-left font-medium">Motivo</th>
              </tr>
            </thead>
            <tbody>
              {AUDIT.map((e) => (
                <tr
                  key={e.id}
                  className="border-t border-border/40 hover:bg-card/60"
                >
                  <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                    {format(new Date(e.at), "dd MMM HH:mm:ss", { locale: ptBR })}
                  </td>
                  <td className="px-4 py-2.5 text-foreground/90">
                    {e.actor}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[11.5px] text-foreground/80">
                    {e.action}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                    {e.resource}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] uppercase tracking-wider",
                        e.decision === "allow"
                          ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                          : "border-rose-400/40 bg-rose-400/10 text-rose-300"
                      )}
                    >
                      {e.decision}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5 italic text-muted-foreground">
                    {e.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center gap-2 rounded-md border border-amber-400/30 bg-amber-400/[0.04] px-3 py-2 text-xs text-amber-200/80">
          <FileClock className="h-3.5 w-3.5" />
          Audit log é imutável. Nenhum usuário (incluindo admin) pode editar ou apagar entradas.
        </div>
      </div>
    </div>
  );
}
