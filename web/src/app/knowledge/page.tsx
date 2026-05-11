"use client";

import { useMemo, useState } from "react";
import {
  Bot,
  FileText,
  Hash,
  Link as LinkIcon,
  Plus,
  Repeat,
  Search,
  ShieldCheck,
  User as UserIcon,
  Wrench,
  Kanban,
} from "lucide-react";
import { KNOWLEDGE, KNOWLEDGE_INDEX } from "@/lib/mock-knowledge";
import { KnowledgeTree } from "@/components/knowledge/tree";
import { Markdown } from "@/components/knowledge/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { format, formatDistanceToNowStrict } from "date-fns";
import { ptBR } from "date-fns/locale";
import type { EntityKind, EntityRef } from "@/lib/types";
import { cn } from "@/lib/utils";

const ENTITY_ICON: Record<EntityKind, React.ElementType> = {
  mission: Kanban,
  agent: Bot,
  skill: Wrench,
  process: Repeat,
  knowledge: FileText,
  user: UserIcon,
};

const ENTITY_LABEL: Record<EntityKind, string> = {
  mission: "Mission",
  agent: "Agente",
  skill: "Skill",
  process: "Processo",
  knowledge: "Documento",
  user: "Pessoa",
};

function EntityChip({ entity }: { entity: EntityRef }) {
  const Icon = ENTITY_ICON[entity.kind];
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-border/50 bg-background/60 px-1.5 py-1 text-[11px] text-foreground/90 hover:border-foreground/30 hover:bg-card">
      <Icon className="h-3 w-3 text-muted-foreground" />
      <span className="truncate font-mono">{entity.label}</span>
    </span>
  );
}

const DEFAULT_PATH = "onboarding/como-criar-uma-mission.md";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [selectedPath, setSelectedPath] = useState(DEFAULT_PATH);

  const filteredNodes = useMemo(() => {
    if (!query) return KNOWLEDGE;
    const q = query.toLowerCase();
    const matches = new Set<string>();
    // collect matching files
    for (const n of KNOWLEDGE) {
      if (n.kind === "file") {
        if (
          n.name.toLowerCase().includes(q) ||
          (n.body ?? "").toLowerCase().includes(q) ||
          (n.tags ?? []).some((t) => t.toLowerCase().includes(q))
        ) {
          matches.add(n.path);
          // propagate up to ancestors
          let p = n.parentPath;
          while (p) {
            matches.add(p);
            p = KNOWLEDGE_INDEX[p]?.parentPath;
          }
        }
      }
    }
    return KNOWLEDGE.filter((n) => matches.has(n.path) || n.kind === "folder" && n.children?.some((c) => matches.has(c)));
  }, [query]);

  const selected = KNOWLEDGE_INDEX[selectedPath];

  const stats = useMemo(() => {
    const files = KNOWLEDGE.filter((n) => n.kind === "file").length;
    const folders = KNOWLEDGE.filter((n) => n.kind === "folder").length;
    const tags = new Set<string>();
    for (const n of KNOWLEDGE) (n.tags ?? []).forEach((t) => tags.add(t));
    return { files, folders, tags: tags.size };
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-4 border-b border-border/60 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Conhecimento</h1>
          <p className="mt-0.5 max-w-2xl text-xs text-muted-foreground">
            Pastas e arquivos markdown da Axenya, linkados a agentes, processos,
            missions e skills. Cada doc é versionado e pode ser referenciado
            pelo Planner como contexto.
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Button size="sm" variant="ghost" className="h-8 gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Nova pasta
          </Button>
          <Button size="sm" className="h-8 gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Novo documento
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* TREE */}
        <aside className="flex w-64 shrink-0 flex-col border-r border-border/60 bg-card/30">
          <div className="border-b border-border/40 px-2.5 py-2.5">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar"
                className="h-7 w-full rounded border border-input bg-background/60 pl-7 pr-2 text-[12px] placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground/70">
              <span>{stats.folders} pastas · {stats.files} docs</span>
              <span>{stats.tags} tags</span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <KnowledgeTree
              nodes={filteredNodes}
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
            />
          </div>
        </aside>

        {/* CONTENT */}
        <main className="flex-1 overflow-y-auto">
          {selected?.kind === "file" ? (
            <article className="mx-auto max-w-3xl px-8 py-8">
              <div className="mb-5 flex items-center gap-2 text-[10.5px] text-muted-foreground">
                <span className="font-mono">{selected.path}</span>
                {selected.updatedAt && (
                  <>
                    <span className="text-muted-foreground/60">·</span>
                    <span title={format(new Date(selected.updatedAt), "PPpp", { locale: ptBR })}>
                      atualizado{" "}
                      {formatDistanceToNowStrict(new Date(selected.updatedAt), {
                        locale: ptBR,
                        addSuffix: true,
                      })}
                    </span>
                  </>
                )}
                {selected.author && (
                  <>
                    <span className="text-muted-foreground/60">·</span>
                    <span className="flex items-center gap-1.5">
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-foreground/10 text-[8.5px] font-medium">
                        {selected.author.initials}
                      </span>
                      {selected.author.name}
                    </span>
                  </>
                )}
              </div>

              {selected.tags && selected.tags.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-1">
                  {selected.tags.map((t) => (
                    <Badge
                      key={t}
                      variant="outline"
                      className="gap-1 text-[10px] uppercase tracking-wider"
                    >
                      <Hash className="h-2.5 w-2.5" />
                      {t}
                    </Badge>
                  ))}
                </div>
              )}

              <Markdown content={selected.body ?? ""} />

              <div className="mt-10 border-t border-border/40 pt-5 text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <ShieldCheck className="h-3 w-3" /> Doc visível para todos com
                  role ≥ <code className="font-mono">viewer</code> no workspace.
                </span>
              </div>
            </article>
          ) : (
            <div className="flex h-full items-center justify-center px-6">
              <div className="text-center">
                <FileText className="mx-auto h-8 w-8 text-muted-foreground/60" />
                <p className="mt-3 text-sm text-muted-foreground">
                  Selecione um documento na árvore.
                </p>
              </div>
            </div>
          )}
        </main>

        {/* LINKS PANEL */}
        {selected?.kind === "file" && (
          <aside className="hidden w-72 shrink-0 border-l border-border/60 bg-card/30 xl:flex xl:flex-col">
            <div className="border-b border-border/40 px-4 py-3">
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Linkado neste doc
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {selected.links && selected.links.length > 0 ? (
                <LinksGrouped refs={selected.links} />
              ) : (
                <p className="text-[11.5px] italic text-muted-foreground/70">
                  Sem referências saintes.
                </p>
              )}

              {selected.backlinks && selected.backlinks.length > 0 && (
                <>
                  <div className="mt-5 flex items-center gap-1.5 border-t border-border/30 pt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    <LinkIcon className="h-3 w-3" /> Quem aponta pra cá
                  </div>
                  <div className="mt-2 flex flex-col gap-1.5">
                    {selected.backlinks.map((r, i) => (
                      <EntityChip key={`${r.kind}:${r.id}:${i}`} entity={r} />
                    ))}
                  </div>
                </>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function LinksGrouped({ refs }: { refs: EntityRef[] }) {
  const byKind = refs.reduce<Record<string, EntityRef[]>>((acc, r) => {
    (acc[r.kind] = acc[r.kind] ?? []).push(r);
    return acc;
  }, {});
  const order: EntityKind[] = ["mission", "agent", "process", "skill", "user", "knowledge"];

  return (
    <div className="flex flex-col gap-4">
      {order
        .filter((k) => byKind[k])
        .map((k) => {
          const Icon = ENTITY_ICON[k];
          return (
            <div key={k}>
              <div
                className={cn(
                  "mb-1.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground"
                )}
              >
                <Icon className="h-3 w-3" />
                {ENTITY_LABEL[k]}
                <span className="text-muted-foreground/60">
                  · {byKind[k].length}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                {byKind[k].map((r, i) => (
                  <EntityChip key={`${r.kind}:${r.id}:${i}`} entity={r} />
                ))}
              </div>
            </div>
          );
        })}
    </div>
  );
}
