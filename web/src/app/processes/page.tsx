import { Plus, Clock4 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProcessesTable } from "@/components/processes/processes-table";

export const dynamic = "force-dynamic";

export default function ProcessesPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start justify-between border-b border-border/60 px-7 py-6">
        <div className="max-w-2xl">
          <h1 className="text-lg font-semibold tracking-tight">Processos</h1>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Crons que disparam missions/agentes em horários definidos. Cada
            execução vira run rastreável no Langfuse e cada falha pode abrir
            mission de regressão.
          </p>
        </div>
        <Button size="sm" className="h-8 gap-1.5 text-xs">
          <Plus className="h-3.5 w-3.5" /> Novo processo
        </Button>
      </div>

      <div className="flex-1 overflow-auto px-7 py-5">
        <ProcessesTable />
        <div className="mt-6 flex items-center gap-2 text-[11px] text-muted-foreground/80">
          <Clock4 className="h-3 w-3" />
          <span>
            Schedules em cron padrão Unix. Toda execução grava em audit log e
            tem trace correspondente no Langfuse.
          </span>
        </div>
      </div>
    </div>
  );
}
