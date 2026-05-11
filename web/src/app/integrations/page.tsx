import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check, Plug, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

const INTEGRATIONS = [
  { name: "Slack", status: "connected", desc: "Triggers, approvals inline e DMs.", surface: "trigger + skill" },
  { name: "HubSpot", status: "connected", desc: "Webhooks, CRM read/write.", surface: "trigger + skill" },
  { name: "Google Workspace", status: "connected", desc: "SSO + Gmail/Calendar.", surface: "auth + skill" },
  { name: "Langfuse", status: "connected", desc: "Tracing, prompts, scores e datasets.", surface: "platform" },
  { name: "BigQuery", status: "connected", desc: "Source of truth para dados de sinistralidade.", surface: "skill" },
  { name: "Ksenia (interno)", status: "connected", desc: "Sistema legado de operação clínica.", surface: "skill" },
  { name: "Atlassian", status: "pending", desc: "Jira + Confluence.", surface: "skill" },
  { name: "Notion", status: "available", desc: "Espelho documental.", surface: "skill" },
  { name: "LiteLLM proxy", status: "connected", desc: "Roteamento de modelos + fallback ladder.", surface: "platform" },
];

export default function IntegrationsPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Integrações"
        description="Conectores que abastecem skills e triggers. Toda integração é versionada e tem ACL própria."
        actions={
          <Button size="sm" variant="outline" className="gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Adicionar conector
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {INTEGRATIONS.map((i) => (
            <div
              key={i.name}
              className="rounded-lg border border-border/60 bg-card/40 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-foreground/10">
                    <Plug className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground">{i.name}</h3>
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {i.surface}
                    </span>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] uppercase tracking-wider",
                    i.status === "connected" &&
                      "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
                    i.status === "pending" &&
                      "border-amber-400/40 bg-amber-400/10 text-amber-300",
                    i.status === "available" &&
                      "border-zinc-400/40 bg-zinc-400/10 text-zinc-300"
                  )}
                >
                  {i.status === "connected" && <Check className="mr-1 h-2.5 w-2.5" />}
                  {i.status}
                </Badge>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">{i.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
