import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { ExternalLink, GitBranch, Sparkles } from "lucide-react";

const PROMPTS = [
  { slug: "planner", versions: 8, prod: "v1.2.1", model: "claude-sonnet-4-6", lastEdit: "1d atrás" },
  { slug: "classifier_lead", versions: 14, prod: "v1.4.2", model: "claude-sonnet-4-6", lastEdit: "3d atrás" },
  { slug: "email_classifier_clinical", versions: 3, prod: "v0.3.1", model: "claude-opus-4-7", lastEdit: "12h atrás" },
  { slug: "reembolso_classifier", versions: 1, prod: "v0.1.0", model: "claude-sonnet-4-6", lastEdit: "5h atrás" },
];

export default function PromptLibraryPage() {
  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Prompt library"
        description="Storage e versionamento via Langfuse Prompts. Promote, rollback e diff entre versões. Cada mission em produção snapshot a versão usada."
        actions={
          <Button size="sm" variant="outline" className="gap-1.5 text-xs">
            <ExternalLink className="h-3.5 w-3.5" /> Abrir no Langfuse
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="overflow-hidden rounded-lg border border-border/60 bg-card/30">
          <table className="w-full text-sm">
            <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">Slug</th>
                <th className="px-4 py-2.5 text-left font-medium">Versão em prod</th>
                <th className="px-4 py-2.5 text-left font-medium">Modelo default</th>
                <th className="px-4 py-2.5 text-right font-medium">Versões</th>
                <th className="px-4 py-2.5 text-left font-medium">Última edição</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {PROMPTS.map((p) => (
                <tr
                  key={p.slug}
                  className="border-t border-border/40 hover:bg-card/60"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-3.5 w-3.5 text-muted-foreground" />
                      <code className="text-[12.5px] text-foreground">
                        {p.slug}
                      </code>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      <GitBranch className="h-3 w-3 text-muted-foreground" />
                      {p.prod}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{p.model}</td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {p.versions}
                  </td>
                  <td className="px-4 py-3 text-[11px] text-muted-foreground">
                    {p.lastEdit}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button size="sm" variant="ghost" className="h-7 text-xs">
                      diff · rollback
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-muted-foreground/80">
          Storage é Langfuse Prompts. A camada local controla promote/rollback,
          ACL e snapshots em missions de produção.
        </p>
      </div>
    </div>
  );
}
