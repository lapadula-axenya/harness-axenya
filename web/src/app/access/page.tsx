import { PageHeader } from "@/components/page-header";
import { USERS } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Shield, UserPlus } from "lucide-react";
import { cn } from "@/lib/utils";

const ACL_MATRIX = [
  {
    agent: "triagem_lead",
    operators: ["sofia", "bia", "rafa"],
    approvers: ["rafa", "estevao"],
    skills: ["hubspot.read_contact", "hubspot.update_contact", "apollo.lookup", "slack.post"],
  },
  {
    agent: "triagem_email_aline",
    operators: ["aline", "bia"],
    approvers: ["aline", "rafa"],
    skills: ["gmail.read", "gmail.draft"],
  },
  {
    agent: "planner",
    operators: ["sofia", "bia", "estevao", "rafa", "aline", "mariano"],
    approvers: ["sofia", "estevao"],
    skills: [],
  },
  {
    agent: "aderencia_planos",
    operators: ["aline"],
    approvers: ["aline", "rafa"],
    skills: ["bigquery.sinistralidade_v2", "slack.dm"],
  },
];

const ROLES = ["viewer", "pm", "approver", "admin", "auditor"] as const;

export default function AccessPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Acessos & ACL"
        description="SSO Google, RBAC com 5 papéis, ACL fina por agente × skill × recurso. Toda decisão de autorização vira linha no audit log."
        actions={
          <Button size="sm" className="gap-1.5 text-xs">
            <UserPlus className="h-3.5 w-3.5" /> Convidar
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <section>
          <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Usuários do workspace
          </h2>
          <div className="overflow-hidden rounded-lg border border-border/60 bg-card/30">
            <table className="w-full text-sm">
              <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 text-left font-medium">Pessoa</th>
                  <th className="px-4 py-2.5 text-left font-medium">Email</th>
                  <th className="px-4 py-2.5 text-left font-medium">Papel</th>
                  <th className="px-4 py-2.5 text-right font-medium">Agentes operáveis</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(USERS).map((u) => {
                  const operable = ACL_MATRIX.filter((row) =>
                    row.operators.some((id) => USERS[id]?.id === u.id)
                  ).length;
                  return (
                    <tr
                      key={u.id}
                      className="border-t border-border/40 hover:bg-card/60"
                    >
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-foreground/10 text-[10px] font-medium">
                            {u.initials}
                          </div>
                          <span className="font-medium text-foreground">{u.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                        {u.email}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px] uppercase tracking-wider",
                            u.role === "admin" &&
                              "border-violet-400/40 bg-violet-400/10 text-violet-300",
                            u.role === "approver" &&
                              "border-amber-400/40 bg-amber-400/10 text-amber-300",
                            u.role === "pm" &&
                              "border-blue-400/40 bg-blue-400/10 text-blue-300",
                            u.role === "auditor" &&
                              "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
                            u.role === "viewer" &&
                              "border-zinc-400/40 bg-zinc-400/10 text-zinc-300"
                          )}
                        >
                          {u.role}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
                        {operable}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            ACL fina: agente → operadores · aprovadores · skills
          </h2>
          <div className="space-y-2.5">
            {ACL_MATRIX.map((row) => (
              <div
                key={row.agent}
                className="rounded-lg border border-border/60 bg-card/40 p-3.5"
              >
                <div className="flex items-center justify-between">
                  <code className="text-sm font-medium text-foreground">
                    {row.agent}
                  </code>
                  <div className="flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
                    <Shield className="h-3 w-3" />
                    {row.operators.length} operadores · {row.approvers.length}{" "}
                    aprovadores · {row.skills.length} skills
                  </div>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  <Cell title="Operadores" items={row.operators} kind="user" />
                  <Cell title="Aprovadores" items={row.approvers} kind="user" />
                  <Cell title="Skills" items={row.skills} kind="skill" />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="text-[11px] text-muted-foreground/80">
          <p>
            <span className="text-foreground/80">Roles disponíveis:</span>{" "}
            {ROLES.join(" · ")}. ACL é resolvida via Oso (biblioteca Polar)
            cacheada localmente; meta de p99 &lt; 5ms.
          </p>
        </section>
      </div>
    </div>
  );
}

function Cell({
  title,
  items,
  kind,
}: {
  title: string;
  items: string[];
  kind: "user" | "skill";
}) {
  return (
    <div className="rounded border border-border/40 bg-background/40 px-2.5 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {title}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {items.length === 0 ? (
          <span className="text-[11px] italic text-muted-foreground/60">
            —
          </span>
        ) : (
          items.map((id) => (
            <span
              key={id}
              className={cn(
                "rounded px-1.5 py-0.5 text-[10.5px]",
                kind === "user"
                  ? "bg-foreground/10 text-foreground/90"
                  : "bg-muted/60 font-mono text-[10px] text-foreground/80"
              )}
            >
              {kind === "user" ? USERS[id]?.name ?? id : id}
            </span>
          ))
        )}
      </div>
    </div>
  );
}
