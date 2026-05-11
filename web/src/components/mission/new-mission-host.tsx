"use client";

import { useEffect, useState } from "react";
import { NewMissionDialog } from "./new-mission-dialog";
import { NEW_MISSION_EVENT } from "./new-mission-trigger";
import { addCreatedMission } from "@/lib/mission-store";

/**
 * Mounted once at the layout root so the "Nova missão" trigger works from
 * any page. New missions land in the shared mission store; the Kanban board
 * (and any future view) subscribes to it.
 */
export function NewMissionHost() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener(NEW_MISSION_EVENT, handler);
    return () => window.removeEventListener(NEW_MISSION_EVENT, handler);
  }, []);

  return (
    <NewMissionDialog
      open={open}
      onOpenChange={setOpen}
      onCreated={(m) => addCreatedMission(m)}
    />
  );
}
