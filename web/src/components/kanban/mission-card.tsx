"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  AlertTriangle,
  CircleDot,
  Clock,
  DollarSign,
  GitBranch,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import type { Mission } from "@/lib/types";
import { cn } from "@/lib/utils";
import { formatDistanceToNowStrict } from "date-fns";
import { ptBR } from "date-fns/locale";

const priorityColor: Record<Mission["priority"], string> = {
  high: "bg-rose-400/80",
  medium: "bg-amber-400/80",
  low: "bg-zinc-500/70",
};

const priorityLabel: Record<Mission["priority"], string> = {
  high: "alta",
  medium: "média",
  low: "baixa",
};

export function MissionCard({
  mission,
  onOpen,
  isOverlay,
}: {
  mission: Mission;
  onOpen?: () => void;
  isOverlay?: boolean;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: mission.id, data: { mission } });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  const lastEvent = mission.events[mission.events.length - 1];
  const isDrift = mission.events.some((e) => e.kind === "drift_detected");
  const isAutoGen = mission.title.startsWith("Alerta de drift");
  const successRate =
    mission.metrics.runsTotal > 0
      ? mission.metrics.runsSuccess / mission.metrics.runsTotal
      : null;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={(e) => {
        // only trigger open on plain click (dnd will set isDragging during drag)
        if (!isDragging && onOpen) {
          e.stopPropagation();
          onOpen();
        }
      }}
      className={cn(
        "group cursor-grab rounded-md border border-border/70 bg-card p-3 shadow-sm transition-colors",
        "hover:border-foreground/30 hover:bg-card/80",
        isOverlay && "rotate-1 shadow-2xl ring-1 ring-foreground/20",
        isDragging && "cursor-grabbing"
      )}
    >
      <div className="flex items-start gap-2">
        <div
          className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", priorityColor[mission.priority])}
          title={`Prioridade ${priorityLabel[mission.priority]}`}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            {isAutoGen && (
              <Sparkles className="h-3 w-3 shrink-0 text-amber-400" />
            )}
            {isDrift && (
              <TrendingDown className="h-3 w-3 shrink-0 text-rose-400" />
            )}
            <h3 className="line-clamp-2 text-[13px] font-medium leading-tight text-foreground">
              {mission.title}
            </h3>
          </div>
          {mission.agentSlug && (
            <div className="mt-1.5 flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
              <GitBranch className="h-2.5 w-2.5" />
              <span className="truncate">
                {mission.agentSlug}
                {mission.agentVersion ? `@${mission.agentVersion}` : ""}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="mt-2.5 flex items-center justify-between gap-2 text-[10.5px] text-muted-foreground">
        <div className="flex items-center gap-2.5">
          {successRate !== null && (
            <span className="flex items-center gap-1 tabular-nums">
              <CircleDot
                className={cn(
                  "h-2.5 w-2.5",
                  successRate >= 0.95
                    ? "text-emerald-400"
                    : successRate >= 0.8
                      ? "text-amber-400"
                      : "text-rose-400"
                )}
              />
              {(successRate * 100).toFixed(1)}%
            </span>
          )}
          {mission.metrics.costUsdMtd > 0 && (
            <span className="flex items-center gap-0.5 tabular-nums">
              <DollarSign className="h-2.5 w-2.5" />
              {mission.metrics.costUsdMtd.toFixed(2)}
            </span>
          )}
          {mission.state === "plan_review" && mission.plan && (
            <span className="flex items-center gap-1 rounded bg-amber-400/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-300">
              <AlertTriangle className="h-2.5 w-2.5" />
              aguarda aprovação
            </span>
          )}
        </div>
        <span className="flex items-center gap-1 whitespace-nowrap text-muted-foreground/70">
          <Clock className="h-2.5 w-2.5" />
          {formatDistanceToNowStrict(new Date(mission.updatedAt), {
            locale: ptBR,
            addSuffix: false,
          })}
        </span>
      </div>

      {lastEvent?.kind === "comment" &&
        lastEvent.payload &&
        "message" in lastEvent.payload && (
          <div className="mt-2 rounded border-l-2 border-amber-400/60 bg-amber-400/[0.04] px-2 py-1 text-[10.5px] text-amber-200/90 line-clamp-2">
            🤖 {String(lastEvent.payload.message)}
          </div>
        )}

      <div className="mt-2.5 flex items-center justify-between">
        <div className="flex items-center -space-x-1.5">
          <div className="flex h-5 w-5 items-center justify-center rounded-full border border-border/60 bg-muted text-[9px] font-medium text-foreground">
            {mission.createdBy.initials}
          </div>
          {mission.assignee && mission.assignee.id !== mission.createdBy.id && (
            <div className="flex h-5 w-5 items-center justify-center rounded-full border border-border/60 bg-muted text-[9px] font-medium text-foreground">
              {mission.assignee.initials}
            </div>
          )}
        </div>
        <span className="font-mono text-[9.5px] text-muted-foreground/60">
          {mission.id}
        </span>
      </div>
    </div>
  );
}
