"use client";

import { useEffect, useReducer } from "react";
import type { Mission } from "./types";

/**
 * Singleton in-memory store for missions created during the session.
 * Real impl will be replaced by a server fetch / websocket subscription.
 */
let created: Mission[] = [];
const listeners = new Set<() => void>();

export function addCreatedMission(m: Mission): void {
  created = [m, ...created];
  for (const l of listeners) l();
}

export function getCreatedMissions(): Mission[] {
  return created;
}

export function useCreatedMissions(): Mission[] {
  const [, force] = useReducer((s: number) => s + 1, 0);
  useEffect(() => {
    listeners.add(force);
    return () => {
      listeners.delete(force);
    };
  }, []);
  return created;
}
