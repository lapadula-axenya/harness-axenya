"use client";

import { Plus, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const NEW_MISSION_EVENT = "xenia:open-new-mission";

export function openNewMissionDialog() {
  window.dispatchEvent(new CustomEvent(NEW_MISSION_EVENT));
}

export function NewMissionTrigger({
  variant = "default",
  size = "sm",
  className,
  withSparkle = false,
  iconOnly = false,
  label = "Nova missão",
}: {
  variant?: "default" | "outline" | "ghost";
  size?: "sm" | "default" | "icon";
  className?: string;
  withSparkle?: boolean;
  iconOnly?: boolean;
  label?: string;
}) {
  return (
    <Button
      onClick={openNewMissionDialog}
      variant={variant}
      size={size}
      className={cn("gap-1.5 text-xs", className)}
    >
      {withSparkle ? (
        <Sparkles className="h-3.5 w-3.5" />
      ) : (
        <Plus className="h-3.5 w-3.5" />
      )}
      {!iconOnly && label}
    </Button>
  );
}
