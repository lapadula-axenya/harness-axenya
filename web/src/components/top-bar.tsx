"use client";

import { Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NewMissionTrigger } from "@/components/mission/new-mission-trigger";

export function TopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/95 px-5 backdrop-blur">
      <div className="flex flex-1 items-center gap-3">
        <div className="relative flex w-full max-w-md items-center">
          <Search className="absolute left-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            placeholder="Buscar missões, agentes, runs…"
            className="h-8 w-full rounded-md border border-input bg-muted/30 pl-8 pr-2 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <kbd className="absolute right-2 hidden rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground md:inline-block">
            ⌘K
          </kbd>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <NewMissionTrigger
          variant="outline"
          withSparkle
          className="h-8 border-border bg-muted/30 font-medium"
        />
        <Button
          size="icon"
          variant="ghost"
          className="relative h-8 w-8 text-muted-foreground"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-destructive" />
        </Button>
      </div>
    </header>
  );
}
