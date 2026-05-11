"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Kanban,
  Bot,
  Wrench,
  Shield,
  ListChecks,
  LineChart,
  FileClock,
  Sparkles,
  Plug,
  Settings,
  Repeat,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navMain = [
  { href: "/", label: "Kanban", icon: Kanban, badge: "8" },
  { href: "/missions", label: "Todas missões", icon: ListChecks },
  { href: "/agents", label: "Agentes", icon: Bot, badge: "4" },
  { href: "/processes", label: "Processos", icon: Repeat, badge: "8" },
  { href: "/skills", label: "Skills", icon: Wrench },
  { href: "/evals", label: "Evals & drift", icon: LineChart, badge: "1" },
];

const navOps = [
  { href: "/audit", label: "Audit log", icon: FileClock },
  { href: "/access", label: "Acessos & ACL", icon: Shield },
  { href: "/integrations", label: "Integrações", icon: Plug },
];

const navSystem = [
  { href: "/prompt-library", label: "Prompt library", icon: Sparkles },
  { href: "/settings", label: "Configurações", icon: Settings },
];

function Section({
  title,
  items,
  pathname,
}: {
  title: string;
  items: { href: string; label: string; icon: React.ElementType; badge?: string }[];
  pathname: string;
}) {
  return (
    <div className="px-2">
      <div className="px-2 pb-1 pt-3 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground/60">
        {title}
      </div>
      <nav className="flex flex-col gap-0.5">
        {items.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-foreground" : "text-muted-foreground"
                )}
              />
              <span className="flex-1 truncate">{label}</span>
              {badge && (
                <span className="rounded-full bg-foreground/10 px-1.5 py-0.5 text-[10px] tabular-nums text-foreground/70">
                  {badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-foreground text-background">
          <span className="font-semibold tracking-tight">X</span>
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-medium tracking-tight">Xenia</span>
          <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            Axenya · workspace
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pb-4">
        <Section title="Trabalho" items={navMain} pathname={pathname} />
        <Section title="Governança" items={navOps} pathname={pathname} />
        <Section title="Sistema" items={navSystem} pathname={pathname} />
      </div>

      <div className="border-t border-sidebar-border px-3 py-3">
        <div className="flex items-center gap-2 rounded-md bg-sidebar-accent/50 px-2 py-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-foreground/10 text-[11px] font-medium">
            SL
          </div>
          <div className="flex min-w-0 flex-1 flex-col leading-tight">
            <span className="truncate text-xs font-medium">Sofia Lapadula</span>
            <span className="truncate text-[10px] text-muted-foreground">
              admin · axenya.com.br
            </span>
          </div>
        </div>
        <div className="mt-2 px-1 text-[10px] text-muted-foreground/70">
          v0.5 · build 4fe4ddf
        </div>
      </div>
    </aside>
  );
}
