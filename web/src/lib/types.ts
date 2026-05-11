export type MissionState =
  | "idea"
  | "plan_drafting"
  | "plan_review"
  | "executing"
  | "qa"
  | "in_production"
  | "paused"
  | "archived";

export type Priority = "high" | "medium" | "low";

export type Role = "viewer" | "pm" | "approver" | "admin" | "auditor";

export type SkillSensitivity = "clinical_data" | "pii" | "financial" | "none";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatarUrl?: string;
  initials: string;
}

export interface Skill {
  name: string;
  description: string;
  sensitivityTags: SkillSensitivity[];
  existsInRegistry: boolean;
}

export interface EvalCheck {
  id: string;
  kind: "deterministic" | "llm_judge";
  description: string;
  weight: number;
  lastScore?: number;
}

export interface ApprovalPoint {
  step: string;
  condition: string;
  approverRole: Role;
  slaHours: number;
}

export interface MissionPlan {
  id: string;
  version: number;
  status: "draft" | "pending" | "approved" | "rejected" | "superseded";
  generatedBy: string;
  scope: string;
  nonScope: string[];
  flowYaml: string;
  requiredSkills: Skill[];
  evalRubric: EvalCheck[];
  approvalPoints: ApprovalPoint[];
  costEstimate: {
    perRunUsd: number;
    monthlyUsd: number;
    volumeAssumption: string;
  };
  risks: { risk: string; mitigation: string; severity: "low" | "medium" | "high" }[];
  confidence: number;
  followUpQuestions: string[];
}

export interface MissionEvent {
  id: string;
  kind:
    | "state_change"
    | "plan_generated"
    | "comment"
    | "run_started"
    | "run_step"
    | "run_completed"
    | "eval_failed"
    | "eval_passed"
    | "approval_decided"
    | "drift_detected";
  actor?: { id: string; name: string };
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface Approval {
  id: string;
  type: "plan" | "execution_gate" | "production_promote";
  decision: "approved" | "rejected" | "changes_requested";
  decidedBy: { id: string; name: string };
  reason: string;
  decidedAt: string;
}

export interface Mission {
  id: string;
  title: string;
  intent: string;
  state: MissionState;
  priority: Priority;
  createdBy: User;
  assignee?: User;
  plan?: MissionPlan;
  events: MissionEvent[];
  approvals: Approval[];
  agentSlug?: string;
  agentVersion?: string;
  createdAt: string;
  updatedAt: string;
  // running totals
  metrics: {
    runsTotal: number;
    runsSuccess: number;
    costUsdMtd: number;
    avgEvalScore?: number;
    p95LatencyMs?: number;
    lastRunAt?: string;
  };
}

export interface Agent {
  slug: string;
  name: string;
  description: string;
  version: string;
  versionsCount: number;
  owner: User;
  state: "active" | "shadow" | "paused";
  primaryModel: string;
  fallbackModel?: string;
  missionsActive: number;
  costUsd30d: number;
  successRate: number;
  lastDriftAlert?: string;
}

export interface AuditEntry {
  id: string;
  at: string;
  actor: string;
  action: string;
  resource: string;
  decision: "allow" | "deny";
  reason: string;
}

export type EntityKind =
  | "mission"
  | "agent"
  | "skill"
  | "process"
  | "knowledge"
  | "user";

export interface EntityRef {
  kind: EntityKind;
  id: string;
  label: string;
}

export interface Process {
  id: string;
  slug: string;
  name: string;
  description: string;
  cron: string;
  cronHuman: string;
  timezone: string;
  triggers: EntityRef[]; // agentes ou missions que ele dispara
  outputChannel?: string;
  owner: User;
  status: "active" | "paused" | "error";
  lastRunAt?: string;
  lastRunStatus?: "ok" | "fail" | "partial";
  nextRunAt: string;
  runs30d: number;
  successRate30d: number;
  avgDurationMs?: number;
  knowledgeRefs: string[]; // paths para arquivos em /knowledge
}

export type KnowledgeNodeKind = "folder" | "file";

export interface KnowledgeNode {
  id: string;
  kind: KnowledgeNodeKind;
  name: string;
  path: string;
  parentPath?: string;
  children?: string[]; // ids
  updatedAt?: string;
  author?: User;
  body?: string; // markdown
  links?: EntityRef[]; // entidades referenciadas
  backlinks?: EntityRef[]; // entidades que apontam para este doc
  tags?: string[];
}

