import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Bot, DollarSign, GitBranch, ShieldCheck } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Configurações"
        description="Workspace, modelos default, budget e governança."
      />
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <Card title="Workspace">
          <Row label="Nome" value="Axenya" />
          <Row label="Slug" value="axenya" mono />
          <Row label="Domínio SSO" value="axenya.com.br" mono />
          <Row label="Plano" value={<Badge variant="outline">enterprise</Badge>} />
        </Card>

        <Card title="Routing de modelos" icon={Bot}>
          <Row label="Modelo primário (default)" value="claude-sonnet-4-6" mono />
          <Row label="Fallback (default)" value="claude-opus-4-7" mono />
          <Row label="Proxy" value="LiteLLM self-host (3 réplicas)" />
          <Row label="Circuit breaker" value="vendor 5xx > 5% em 5 min → desvia" />
        </Card>

        <Card title="Budget" icon={DollarSign}>
          <Row label="Workspace cap mensal" value="$2,500" />
          <Row label="Cap por agente (default)" value="$500" />
          <Row label="Cap diário Planner" value="100 generations" />
          <Row label="Alerta a partir de" value="80% do cap" />
        </Card>

        <Card title="Governança" icon={ShieldCheck}>
          <Row label="Dual-control em PII/clinical" value="obrigatório" />
          <Row label="Audit retention hot" value="365 dias" />
          <Row label="Audit retention archived" value="3 anos em BigQuery" />
          <Row label="SSO MFA" value="delegado ao Google Workspace" />
        </Card>

        <Card title="Versão" icon={GitBranch}>
          <Row label="Frontend" value="web@0.5.0" mono />
          <Row label="Harness" value="xenia-harness@phase-4" mono />
          <Row label="Branch ativa" value="claude/define-platform-scope-hiLQm" mono />
        </Card>
      </div>
    </div>
  );
}

function Card({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon?: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-card/30">
      <div className="flex items-center gap-2 border-b border-border/40 px-4 py-2.5">
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h2>
      </div>
      <div className="divide-y divide-border/30">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-[12.5px]" : ""}>{value}</span>
    </div>
  );
}
