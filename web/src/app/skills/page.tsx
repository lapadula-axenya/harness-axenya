import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

const SKILLS = [
  {
    name: "hubspot.read_contact",
    description: "Lê um contato do HubSpot por ID/email.",
    tags: ["pii"],
    agents: ["triagem_lead"],
    transport: "mcp",
  },
  {
    name: "hubspot.update_contact",
    description: "Atualiza propriedades de contato (whitelist).",
    tags: ["pii"],
    agents: ["triagem_lead"],
    transport: "mcp",
  },
  {
    name: "gmail.read",
    description: "Lê mensagens não-lidas de uma mailbox específica.",
    tags: ["pii", "clinical_data"],
    agents: ["triagem_email_aline"],
    transport: "mcp",
  },
  {
    name: "gmail.draft",
    description: "Cria rascunho de resposta — nunca envia direto.",
    tags: ["pii"],
    agents: ["triagem_email_aline"],
    transport: "mcp",
  },
  {
    name: "slack.post",
    description: "Posta mensagem em canal Slack.",
    tags: [],
    agents: ["triagem_lead"],
    transport: "http",
  },
  {
    name: "slack.dm",
    description: "Envia DM para usuário.",
    tags: [],
    agents: [],
    transport: "http",
  },
  {
    name: "bigquery.sinistralidade_v2",
    description: "View whitelisted de sinistralidade agregada por empresa.",
    tags: ["financial"],
    agents: [],
    transport: "http",
  },
  {
    name: "apollo.lookup",
    description: "Enriquece lead com dados de Apollo.io.",
    tags: ["pii"],
    agents: ["triagem_lead"],
    transport: "http",
  },
  {
    name: "ksenia.reembolso_fila",
    description: "Lista pedidos de reembolso pendentes no sistema interno.",
    tags: ["pii", "financial", "clinical_data"],
    agents: [],
    transport: "http",
  },
];

export default function SkillsPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Skills"
        description="Capabilities que agentes podem invocar. Cada skill tem sensitivity tags e ACL — definida por workspace e por agente."
        actions={
          <Button size="sm" className="gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Registrar skill
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SKILLS.map((s) => (
            <div
              key={s.name}
              className="rounded-lg border border-border/60 bg-card/40 p-3.5 transition-colors hover:bg-card/70"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded bg-foreground/10">
                    <Wrench className="h-3.5 w-3.5" />
                  </div>
                  <code className="text-[12.5px] font-medium text-foreground">
                    {s.name}
                  </code>
                </div>
                <Badge
                  variant="outline"
                  className="text-[9px] uppercase tracking-wider"
                >
                  {s.transport}
                </Badge>
              </div>
              <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                {s.description}
              </p>
              <div className="mt-3 flex flex-wrap gap-1">
                {s.tags.map((t) => (
                  <Badge
                    key={t}
                    variant="outline"
                    className={cn(
                      "text-[9px] uppercase tracking-wider",
                      "border-rose-400/30 bg-rose-400/10 text-rose-300"
                    )}
                  >
                    {t}
                  </Badge>
                ))}
                {s.tags.length === 0 && (
                  <span className="text-[10px] text-muted-foreground/60">
                    sem tags sensíveis
                  </span>
                )}
              </div>
              <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                <span>
                  {s.agents.length} agente{s.agents.length === 1 ? "" : "s"}
                </span>
                {s.agents.length > 0 && (
                  <span className="truncate font-mono text-[10px]">
                    {s.agents.join(", ")}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
