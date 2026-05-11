"use client";

import { useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { MissionCard } from "./mission-card";
import { COLUMN_META, COLUMN_ORDER, MISSIONS } from "@/lib/mock-data";
import type { Mission, MissionState } from "@/lib/types";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { MissionDetail } from "@/components/mission/mission-detail";

const VALID_TRANSITIONS: Record<MissionState, MissionState[]> = {
  idea: ["plan_drafting", "archived"],
  plan_drafting: ["plan_review", "idea", "archived"],
  plan_review: ["executing", "plan_drafting", "archived"],
  executing: ["qa", "paused", "archived"],
  qa: ["in_production", "executing", "archived"],
  in_production: ["paused", "archived"],
  paused: ["executing", "archived"],
  archived: [],
};

function DroppableColumn({
  state,
  missions,
  onOpen,
}: {
  state: MissionState;
  missions: Mission[];
  onOpen: (id: string) => void;
}) {
  const meta = COLUMN_META[state];
  const { setNodeRef } = useSortable({
    id: `column:${state}`,
    data: { columnId: state, type: "column" },
  });

  return (
    <div className="flex h-full w-[300px] shrink-0 flex-col">
      <div className={cn("rounded-t-md bg-card/40 px-3 pb-2 pt-3", meta.tint)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground/90">
              {meta.label}
            </h2>
            <span className="rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] tabular-nums text-foreground/70">
              {missions.length}
            </span>
          </div>
          <button
            className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            onClick={() => toast("Em breve: criar mission direto na coluna")}
            aria-label="Adicionar"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
        <p className="mt-1 line-clamp-1 text-[10.5px] text-muted-foreground/80">
          {meta.description}
        </p>
      </div>

      <div
        ref={setNodeRef}
        className="flex-1 space-y-2 overflow-y-auto rounded-b-md border-x border-b border-border/40 bg-card/20 p-2"
      >
        <SortableContext
          items={missions.map((m) => m.id)}
          strategy={verticalListSortingStrategy}
        >
          {missions.length === 0 && (
            <div className="flex h-24 items-center justify-center rounded border border-dashed border-border/40 text-[11px] text-muted-foreground/60">
              vazio
            </div>
          )}
          {missions.map((m) => (
            <MissionCard
              key={m.id}
              mission={m}
              onOpen={() => onOpen(m.id)}
            />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}

export function Board() {
  const [missions, setMissions] = useState<Mission[]>(MISSIONS);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [openMissionId, setOpenMissionId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const byColumn = useMemo(() => {
    const map: Record<MissionState, Mission[]> = {
      idea: [],
      plan_drafting: [],
      plan_review: [],
      executing: [],
      qa: [],
      in_production: [],
      paused: [],
      archived: [],
    };
    for (const m of missions) {
      if (m.state === "paused" || m.state === "archived") continue;
      map[m.state].push(m);
    }
    return map;
  }, [missions]);

  const activeMission = activeId ? missions.find((m) => m.id === activeId) : null;
  const openMission = openMissionId
    ? missions.find((m) => m.id === openMissionId)
    : null;

  const handleDragStart = (e: DragStartEvent) => {
    setActiveId(String(e.active.id));
  };

  const handleDragEnd = (e: DragEndEvent) => {
    setActiveId(null);
    if (!e.over) return;
    const activeMissionId = String(e.active.id);
    const overId = String(e.over.id);

    const activeMission = missions.find((m) => m.id === activeMissionId);
    if (!activeMission) return;

    let targetColumn: MissionState | null = null;
    if (overId.startsWith("column:")) {
      targetColumn = overId.slice("column:".length) as MissionState;
    } else {
      const overMission = missions.find((m) => m.id === overId);
      if (overMission) targetColumn = overMission.state;
    }
    if (!targetColumn) return;
    if (activeMission.state === targetColumn) return;

    if (!VALID_TRANSITIONS[activeMission.state].includes(targetColumn)) {
      toast.error(
        `Transição inválida: ${COLUMN_META[activeMission.state].label} → ${COLUMN_META[targetColumn].label}`,
        {
          description:
            "A state machine não permite esse movimento. Use as ações dentro do card.",
        }
      );
      return;
    }

    setMissions((prev) =>
      prev.map((m) =>
        m.id === activeMissionId
          ? { ...m, state: targetColumn!, updatedAt: new Date().toISOString() }
          : m
      )
    );
    toast.success(
      `Movido para ${COLUMN_META[targetColumn].label}`,
      { description: activeMission.title }
    );
  };

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex h-full gap-3 overflow-x-auto px-5 pb-5">
          {COLUMN_ORDER.map((state) => (
            <DroppableColumn
              key={state}
              state={state}
              missions={byColumn[state]}
              onOpen={setOpenMissionId}
            />
          ))}
        </div>

        <DragOverlay>
          {activeMission && (
            <div className="w-[284px]">
              <MissionCard mission={activeMission} isOverlay />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <MissionDetail
        mission={openMission ?? null}
        onOpenChange={(open) => !open && setOpenMissionId(null)}
      />
    </>
  );
}

