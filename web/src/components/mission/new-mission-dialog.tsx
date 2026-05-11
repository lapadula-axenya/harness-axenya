"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CircleDot,
  DollarSign,
  ExternalLink,
  GitBranch,
  Loader2,
  Network,
  Sparkles,
  TriangleAlert,
  Wrench,
  X,
} from "lucide-react";
import type { Mission, MissionPlan, Priority } from "@/lib/types";
import { CURRENT_USER } from "@/lib/mock-data";
import { KNOWLEDGE } from "@/lib/mock-knowledge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

type Step = "intent" | "generating" | "plan" | "request_changes" | "done";

interface SampleIntent {
  title: string;
  intent: string;
}

const SAMPLES: SampleIntent[] = [
  {
    title: "Triagem de inbox comercial@",
    intent:
      "A cada novo email no comercial@axenya.com.br, classificar em FAQ / lead-novo / suporte-cliente. Para FAQ, redigir resposta com template e enfileirar para minha aprovação. Para os outros, encaminhar.",
  },
  {
    title: "Onboarding de empresa cliente",
    intent:
      "Quando uma empresa é marcada como 'closed-won' no HubSpot, criar workspace dela no nosso sistema, enviar contrato, agendar kickoff e abrir thread no Slack #cs.",
  },
  {
    title: "Alerta de queda de adesão",
    intent:
      "Semanalmente, identificar empresas cliente com queda de adesão > 15% mês a mês e abrir mission de investigação com contexto pré-preenchido para o time de CS.",
  },
];

const KNOWLEDGE_OPTIONS = KNOWLEDGE.filter((n) => n.kind === "file").slice(0, 8);

// Phases shown during the "Planner working" animation.
const PHASES = [
  { id: 1, label: "Analisando intent", icon: Sparkles, ms: 800 },
  { id: 2, label: "Cruzando com a context library", icon: Network, ms: 1100 },
  { id: 3, label: "Identificando skills necessárias", icon: Wrench, ms: 900 },
  { id: 4, label: "Estimando custo & gerando rubric", icon: DollarSign, ms: 950 },
] as const;

function buildMockPlan(intent: string, title: string): MissionPlan {
  const lower = (intent + " " + title).toLowerCase();
  const wantsSlack = /slack|notificar/.test(lower);
  const wantsEmail = /email|inbox|caixa|gmail/.test(lower);
  const wantsHubspot = /hubspot|lead|crm/.test(lower);
  const wantsBQ = /sinistralidade|aderência|adesão|relatório|report/.test(lower);
  const wantsApproval = /aprov|human|exceç|review/.test(lower);

  type SkillRow = MissionPlan["requiredSkills"][number];
  const skills: SkillRow[] = [];
  if (wantsEmail)
    skills.push({
      name: "gmail.read",
      description: "Lê mensagens novas da caixa especificada.",
      sensitivityTags: ["pii"],
      existsInRegistry: true,
    });
  if (wantsEmail)
    skills.push({
      name: "gmail.draft",
      description: "Cria rascunho de resposta — nunca envia direto.",
      sensitivityTags: ["pii"],
      existsInRegistry: true,
    });
  if (wantsHubspot)
    skills.push({
      name: "hubspot.read_contact",
      description: "Lê contato do HubSpot por ID.",
      sensitivityTags: ["pii"],
      existsInRegistry: true,
    });
  if (wantsHubspot)
    skills.push({
      name: "hubspot.update_contact",
      description: "Atualiza propriedades whitelisted.",
      sensitivityTags: ["pii"],
      existsInRegistry: true,
    });
  if (wantsBQ)
    skills.push({
      name: "bigquery.curated_query",
      description: "Roda query em views curated whitelisted.",
      sensitivityTags: ["financial"],
      existsInRegistry: true,
    });
  if (wantsSlack)
    skills.push({
      name: "slack.post",
      description: "Posta em canal Slack.",
      sensitivityTags: [],
      existsInRegistry: true,
    });
  if (skills.length === 0)
    skills.push({
      name: "core.generic_classifier",
      description: "Classifier genérico.",
      sensitivityTags: [],
      existsInRegistry: true,
    });

  const sensitive = skills.some((s) =>
    s.sensitivityTags.some((t) => t === "pii" || t === "clinical_data")
  );

  const approvalPoints = [];
  if (wantsApproval || sensitive)
    approvalPoints.push({
      step: "decide",
      condition: "always",
      approverRole: "approver" as const,
      slaHours: sensitive ? 4 : 24,
    });

  const baseCost = 0.012 + skills.length * 0.008;
  const monthly = Math.round(baseCost * 30 * 12 * 100) / 100;

  const confidence = (() => {
    if (intent.length < 40) return 0.58; // muito vago
    if (sensitive && !wantsApproval) return 0.71;
    return 0.86;
  })();

  return {
    id: `p_${Math.random().toString(36).slice(2, 8)}`,
    version: 1,
    status: "pending",
    generatedBy: "planner@v1.2.1",
    scope:
      `Executar fluxo conforme intent fornecido pelo PM, com triggers, ` +
      `transformações e output canalizado para os destinos apropriados. ` +
      `Skills sensíveis foram identificadas e cobertas por approval point.`,
    nonScope: [
      "Não envia comunicação externa sem aprovação humana.",
      "Não cria deal/proposta — apenas atualiza propriedades existentes.",
      "Não retro-processa registros anteriores ao deploy.",
    ],
    flowYaml:
      `# fluxo gerado pelo Planner v1.2.1\nnodes:\n  - id: ingest\n    skill: ${skills[0].name}\n  - id: decide\n    agent: classifier\n  - id: act\n    skill: ${skills[skills.length - 1].name}\nedges:\n  - ingest -> decide\n  - decide -> act`,
    requiredSkills: skills,
    evalRubric: [
      {
        id: "e1",
        kind: "deterministic",
        description: "Output bate com schema esperado",
        weight: 0.4,
      },
      {
        id: "e2",
        kind: "llm_judge",
        description: "Decisão é coerente com o input",
        weight: 0.4,
      },
      {
        id: "e3",
        kind: "deterministic",
        description: "Skill destino retornou 2xx",
        weight: 0.2,
      },
    ],
    approvalPoints,
    costEstimate: {
      perRunUsd: Math.round(baseCost * 1000) / 1000,
      monthlyUsd: monthly,
      volumeAssumption: "≈ 10 execuções/dia (estimativa conservadora)",
    },
    risks: [
      {
        risk: sensitive
          ? "Skill toca dado pessoal — risco LGPD"
          : "Dependência de API externa indisponível",
        mitigation: sensitive
          ? "ACL restritiva + dual-control no approval"
          : "Circuit breaker + fallback queue",
        severity: sensitive ? "high" : "medium",
      },
      {
        risk: "Custo escalando se volume real for >10x estimado",
        mitigation: "Budget cap por mission + alerta a 80%",
        severity: "medium",
      },
    ],
    confidence,
    followUpQuestions:
      confidence < 0.7
        ? [
            "Quem é o approver de exceções neste fluxo?",
            intent.length < 40
              ? "A intent está bem genérica — pode detalhar trigger e output esperados?"
              : "Existe limite de volume diário que devo respeitar?",
          ]
        : [],
  };
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (mission: Mission) => void;
}

export function NewMissionDialog({ open, onOpenChange, onCreated }: Props) {
  const [step, setStep] = useState<Step>("intent");
  const [title, setTitle] = useState("");
  const [intent, setIntent] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [linkedDocs, setLinkedDocs] = useState<string[]>([]);
  const [activePhase, setActivePhase] = useState(0);
  const [plan, setPlan] = useState<MissionPlan | null>(null);
  const [changeReason, setChangeReason] = useState("");
  const [approveReason, setApproveReason] = useState("");
  const [createdId, setCreatedId] = useState<string | null>(null);

  // Reset when closed
  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setStep("intent");
        setTitle("");
        setIntent("");
        setPriority("medium");
        setLinkedDocs([]);
        setActivePhase(0);
        setPlan(null);
        setChangeReason("");
        setApproveReason("");
        setCreatedId(null);
      }, 250);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Phase animation during "generating".
  // activePhase already starts at 0 from initial state / dialog reset.
  useEffect(() => {
    if (step !== "generating") return;
    let cancelled = false;
    let elapsed = 0;
    const timers: ReturnType<typeof setTimeout>[] = [];
    PHASES.forEach((p, i) => {
      elapsed += p.ms;
      timers.push(
        setTimeout(() => {
          if (!cancelled) setActivePhase(i + 1);
        }, elapsed)
      );
    });
    const total = PHASES.reduce((s, p) => s + p.ms, 0);
    timers.push(
      setTimeout(() => {
        if (cancelled) return;
        setPlan(buildMockPlan(intent, title));
        setStep("plan");
      }, total + 200)
    );
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, [step, intent, title]);

  const canSubmitIntent = title.trim().length > 3 && intent.trim().length > 20;

  function startGeneration() {
    setStep("generating");
  }

  function applySample(s: SampleIntent) {
    setTitle(s.title);
    setIntent(s.intent);
  }

  function toggleDoc(path: string) {
    setLinkedDocs((curr) =>
      curr.includes(path) ? curr.filter((d) => d !== path) : [...curr, path]
    );
  }

  function approve() {
    if (!plan) return;
    const id = `m_${Math.floor(Math.random() * 9000 + 1000)}`;
    const now = new Date().toISOString();
    const mission: Mission = {
      id,
      title: title.trim(),
      intent: intent.trim(),
      state: "executing",
      priority,
      createdBy: CURRENT_USER,
      assignee: CURRENT_USER,
      plan: { ...plan, status: "approved" },
      events: [
        {
          id: `ev_${id}_1`,
          kind: "plan_generated",
          payload: { version: 1, ms: 3950 },
          createdAt: now,
        },
        {
          id: `ev_${id}_2`,
          kind: "approval_decided",
          actor: { id: CURRENT_USER.id, name: CURRENT_USER.name },
          payload: { decision: "approved" },
          createdAt: now,
        },
        {
          id: `ev_${id}_3`,
          kind: "run_started",
          payload: { runId: `r_${Math.floor(Math.random() * 100000)}` },
          createdAt: now,
        },
      ],
      approvals: [
        {
          id: `a_${id}_1`,
          type: "plan",
          decision: "approved",
          decidedBy: { id: CURRENT_USER.id, name: CURRENT_USER.name },
          reason: approveReason.trim() || "Plano coerente com o intent. Custo ok.",
          decidedAt: now,
        },
      ],
      createdAt: now,
      updatedAt: now,
      metrics: {
        runsTotal: 0,
        runsSuccess: 0,
        costUsdMtd: 0,
      },
    };
    setCreatedId(id);
    onCreated(mission);
    setStep("done");
    toast.success(`Mission ${id} criada e em execução`, {
      description: mission.title,
    });
  }

  function requestChanges() {
    setStep("request_changes");
  }

  function submitChanges() {
    // Coloca a mission em plan_drafting com a request do PM
    const id = `m_${Math.floor(Math.random() * 9000 + 1000)}`;
    const now = new Date().toISOString();
    const mission: Mission = {
      id,
      title: title.trim(),
      intent: intent.trim(),
      state: "plan_drafting",
      priority,
      createdBy: CURRENT_USER,
      assignee: CURRENT_USER,
      events: [
        {
          id: `ev_${id}_1`,
          kind: "plan_generated",
          payload: { version: 1, ms: 3950 },
          createdAt: now,
        },
        {
          id: `ev_${id}_2`,
          kind: "comment",
          actor: { id: CURRENT_USER.id, name: CURRENT_USER.name },
          payload: { message: changeReason.trim() || "Pediu alterações no plano." },
          createdAt: now,
        },
      ],
      approvals: [],
      createdAt: now,
      updatedAt: now,
      metrics: { runsTotal: 0, runsSuccess: 0, costUsdMtd: 0 },
    };
    setCreatedId(id);
    onCreated(mission);
    setStep("done");
    toast.message(`Mission ${id} em Plano em desenho`, {
      description: "Planner vai re-gerar com seus comentários.",
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="max-h-[92vh] w-[min(820px,95vw)] max-w-[820px] gap-0 overflow-hidden bg-background p-0"
      >
        <div className="flex items-center justify-between border-b border-border/60 bg-card/40 px-5 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-foreground/10">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <DialogTitle className="text-sm font-medium tracking-tight">
              Nova missão
            </DialogTitle>
            <StepIndicator step={step} />
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[calc(92vh-110px)] overflow-y-auto">
          {step === "intent" && (
            <IntentStep
              title={title}
              setTitle={setTitle}
              intent={intent}
              setIntent={setIntent}
              priority={priority}
              setPriority={setPriority}
              linkedDocs={linkedDocs}
              toggleDoc={toggleDoc}
              applySample={applySample}
            />
          )}
          {step === "generating" && <GeneratingStep activePhase={activePhase} />}
          {step === "plan" && plan && (
            <PlanStep plan={plan} priority={priority} title={title} />
          )}
          {step === "request_changes" && plan && (
            <RequestChangesStep
              plan={plan}
              changeReason={changeReason}
              setChangeReason={setChangeReason}
            />
          )}
          {step === "done" && createdId && (
            <DoneStep
              missionId={createdId}
              state={plan?.confidence && plan.confidence >= 0.7 && approveReason !== "__rejected" ? "executing" : "plan_drafting"}
            />
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border/60 bg-card/30 px-5 py-3">
          <div className="text-[11px] text-muted-foreground">
            Toda decisão aqui vira linha imutável no audit log.
          </div>
          <div className="flex items-center gap-1.5">
            {step === "intent" && (
              <Button
                size="sm"
                className="gap-1.5 text-xs"
                disabled={!canSubmitIntent}
                onClick={startGeneration}
              >
                Gerar plano com Planner <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            )}
            {step === "plan" && plan && (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-xs"
                  onClick={requestChanges}
                >
                  Pedir alterações
                </Button>
                <input
                  value={approveReason}
                  onChange={(e) => setApproveReason(e.target.value)}
                  placeholder="Motivo da aprovação (opcional)"
                  className="h-8 w-56 rounded-md border border-input bg-background/60 px-2 text-xs placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <Button
                  size="sm"
                  className="gap-1.5 text-xs"
                  onClick={approve}
                  disabled={plan.confidence < 0.7}
                >
                  <Check className="h-3.5 w-3.5" />
                  Aprovar plano
                </Button>
              </>
            )}
            {step === "request_changes" && (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  className="gap-1.5 text-xs"
                  onClick={() => setStep("plan")}
                >
                  <ArrowLeft className="h-3.5 w-3.5" /> Voltar
                </Button>
                <Button
                  size="sm"
                  className="gap-1.5 text-xs"
                  disabled={changeReason.trim().length < 5}
                  onClick={submitChanges}
                >
                  Enviar para Planner regenerar{" "}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
            {step === "done" && (
              <Button
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => onOpenChange(false)}
              >
                Ir para o Kanban
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function StepIndicator({ step }: { step: Step }) {
  const sequence: { id: Step; label: string }[] = [
    { id: "intent", label: "Intent" },
    { id: "generating", label: "Planner" },
    { id: "plan", label: "Plano" },
    { id: "done", label: "Em produção" },
  ];
  // map request_changes back to plan visually
  const currentId = step === "request_changes" ? "plan" : step;
  const currentIdx = sequence.findIndex((s) => s.id === currentId);
  return (
    <div className="ml-3 flex items-center gap-1.5 border-l border-border/60 pl-3 text-[10.5px] text-muted-foreground">
      {sequence.map((s, i) => (
        <span key={s.id} className="flex items-center gap-1.5">
          <span
            className={cn(
              "rounded px-1.5 py-0.5 font-medium uppercase tracking-wider",
              i === currentIdx && "bg-foreground/10 text-foreground",
              i < currentIdx && "text-foreground/70",
              i > currentIdx && "text-muted-foreground/50"
            )}
          >
            {s.label}
          </span>
          {i < sequence.length - 1 && (
            <span className="text-muted-foreground/40">›</span>
          )}
        </span>
      ))}
    </div>
  );
}

// ─────────────────────── INTENT STEP ───────────────────────

function IntentStep({
  title,
  setTitle,
  intent,
  setIntent,
  priority,
  setPriority,
  linkedDocs,
  toggleDoc,
  applySample,
}: {
  title: string;
  setTitle: (s: string) => void;
  intent: string;
  setIntent: (s: string) => void;
  priority: Priority;
  setPriority: (p: Priority) => void;
  linkedDocs: string[];
  toggleDoc: (path: string) => void;
  applySample: (s: SampleIntent) => void;
}) {
  return (
    <div className="space-y-5 px-6 py-5">
      <div>
        <Label>Título</Label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex.: Triagem do inbox comercial@"
          className="mt-1 h-9 w-full rounded-md border border-input bg-background/60 px-3 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      <div>
        <Label>O que você quer que aconteça</Label>
        <textarea
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          rows={5}
          placeholder="Descreva em linguagem natural. Quanto mais específico em trigger, ação e output esperado, melhor o plano."
          className="mt-1 w-full resize-none rounded-md border border-input bg-background/60 px-3 py-2 text-sm leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <div className="mt-1 flex items-center justify-between text-[10.5px] text-muted-foreground">
          <span>
            {intent.length} caracteres ·{" "}
            {intent.length < 40 ? "tente especificar mais" : "ok"}
          </span>
          <span>O Planner vai consumir esse texto em ~3-4s</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Prioridade</Label>
          <div className="mt-1 flex gap-1.5">
            {(["high", "medium", "low"] as Priority[]).map((p) => (
              <button
                key={p}
                onClick={() => setPriority(p)}
                className={cn(
                  "flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md border text-xs transition-colors",
                  priority === p
                    ? "border-foreground/40 bg-foreground/10 text-foreground"
                    : "border-border bg-background/40 text-muted-foreground hover:text-foreground"
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    p === "high" && "bg-rose-400/80",
                    p === "medium" && "bg-amber-400/80",
                    p === "low" && "bg-zinc-400/80"
                  )}
                />
                {p === "high" ? "alta" : p === "medium" ? "média" : "baixa"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <Label>Documentos de contexto</Label>
          <div className="mt-1 flex h-9 items-center text-[11px] text-muted-foreground">
            {linkedDocs.length === 0
              ? "Opcional · selecione abaixo"
              : `${linkedDocs.length} doc${linkedDocs.length > 1 ? "s" : ""} linkado${linkedDocs.length > 1 ? "s" : ""}`}
          </div>
        </div>
      </div>

      <div>
        <Label icon={BookOpen}>Documentos de contexto (opcional)</Label>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          O Planner vai consumir esses docs como contexto autoritativo. Use
          para runbooks, PRDs e políticas.
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {KNOWLEDGE_OPTIONS.map((k) => {
            const active = linkedDocs.includes(k.path);
            return (
              <button
                key={k.path}
                onClick={() => toggleDoc(k.path)}
                className={cn(
                  "rounded border px-2 py-1 text-[11px] transition-colors",
                  active
                    ? "border-foreground/40 bg-foreground/10 text-foreground"
                    : "border-border bg-background/40 text-muted-foreground hover:text-foreground"
                )}
              >
                {k.name}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <Label icon={Sparkles}>Intents exemplo</Label>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          Casos reais Axenya — clique pra preencher.
        </p>
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {SAMPLES.map((s) => (
            <button
              key={s.title}
              onClick={() => applySample(s)}
              className="rounded-md border border-border/60 bg-card/40 px-3 py-2.5 text-left transition-colors hover:border-foreground/30 hover:bg-card"
            >
              <div className="text-xs font-medium text-foreground">
                {s.title}
              </div>
              <div className="mt-1 line-clamp-2 text-[10.5px] text-muted-foreground">
                {s.intent}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Label({
  children,
  icon: Icon,
}: {
  children: React.ReactNode;
  icon?: React.ElementType;
}) {
  return (
    <label className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </label>
  );
}

// ─────────────────────── GENERATING STEP ───────────────────────

function GeneratingStep({ activePhase }: { activePhase: number }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12">
      <div className="relative flex h-16 w-16 items-center justify-center">
        <div className="absolute inset-0 animate-ping rounded-full bg-foreground/10" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-foreground/30 bg-card/60">
          <Sparkles className="h-7 w-7 text-foreground" />
        </div>
      </div>
      <h3 className="mt-5 text-base font-medium tracking-tight">
        Planner está rascunhando o plano
      </h3>
      <p className="mt-1 max-w-md text-center text-[12px] text-muted-foreground">
        Versão{" "}
        <code className="font-mono text-foreground/80">planner@v1.2.1</code>{" "}
        executando no harness com fallback ladder Sonnet→Opus.
      </p>

      <ul className="mt-7 flex w-full max-w-md flex-col gap-2">
        {PHASES.map((p, i) => {
          const Icon = p.icon;
          const isActive = i === activePhase;
          const isDone = i < activePhase;
          return (
            <li
              key={p.id}
              className={cn(
                "flex items-center gap-3 rounded-md border px-3 py-2 text-xs transition-all",
                isDone && "border-emerald-400/30 bg-emerald-400/[0.04]",
                isActive && "border-foreground/30 bg-card animate-pulse",
                !isActive && !isDone && "border-border/40 bg-background/30 opacity-60"
              )}
            >
              <span className="flex h-6 w-6 items-center justify-center">
                {isDone ? (
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                ) : isActive ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                )}
              </span>
              <span
                className={cn(
                  "flex-1",
                  isDone ? "text-foreground/80" : "text-foreground/90"
                )}
              >
                {p.label}
              </span>
              {isDone && (
                <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                  {p.ms}ms
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ─────────────────────── PLAN STEP ───────────────────────

function PlanStep({
  plan,
  priority,
  title,
}: {
  plan: MissionPlan;
  priority: Priority;
  title: string;
}) {
  const sensitive = plan.requiredSkills.some((s) =>
    s.sensitivityTags.some((t) => t === "pii" || t === "clinical_data")
  );
  const lowConfidence = plan.confidence < 0.7;

  return (
    <div className="space-y-4 px-6 py-5">
      <div className="rounded-md border border-border/60 bg-card/40 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  priority === "high" && "bg-rose-400/80",
                  priority === "medium" && "bg-amber-400/80",
                  priority === "low" && "bg-zinc-400/80"
                )}
              />
              <h3 className="truncate text-sm font-medium text-foreground">
                {title}
              </h3>
            </div>
            <div className="mt-1 flex items-center gap-2 text-[10.5px] text-muted-foreground">
              <span className="font-mono">{plan.generatedBy}</span>
              <span className="text-muted-foreground/60">·</span>
              <span>v{plan.version}</span>
              <span className="text-muted-foreground/60">·</span>
              <span className="flex items-center gap-1">
                <CircleDot
                  className={cn(
                    "h-2.5 w-2.5",
                    plan.confidence >= 0.85
                      ? "text-emerald-400"
                      : plan.confidence >= 0.7
                        ? "text-amber-400"
                        : "text-rose-400"
                  )}
                />
                confidence{" "}
                <span className="font-mono tabular-nums">
                  {(plan.confidence * 100).toFixed(0)}%
                </span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Button size="sm" variant="ghost" className="h-7 gap-1 text-[10.5px]">
              <GitBranch className="h-3 w-3" /> JSON
            </Button>
          </div>
        </div>
      </div>

      {lowConfidence && (
        <div className="flex items-start gap-2 rounded-md border border-amber-400/30 bg-amber-400/[0.04] px-3 py-2">
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
          <div className="flex-1 text-xs text-amber-200/90">
            <p className="font-medium">
              Confidence baixa — Planner pediu esclarecimento
            </p>
            <ul className="mt-2 space-y-1">
              {plan.followUpQuestions.map((q, i) => (
                <li key={i} className="leading-relaxed">
                  &middot; {q}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[10.5px] text-amber-200/70">
              O botão Aprovar fica desabilitado até confidence ≥ 0.7. Responda
              via comentário ou edite a intent.
            </p>
          </div>
        </div>
      )}

      <PlanBox title="Escopo" body={plan.scope} />
      <PlanBox
        title="Não está no escopo"
        items={plan.nonScope.map((n) => ({ icon: X, label: n, tone: "rose" as const }))}
      />

      <PlanBox
        title="Skills necessárias"
        extra={
          sensitive && (
            <Badge
              variant="outline"
              className="gap-1 border-rose-400/40 bg-rose-400/10 text-[9.5px] uppercase tracking-wider text-rose-300"
            >
              <ShieldAlert /> dual-control
            </Badge>
          )
        }
      >
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {plan.requiredSkills.map((s) => (
            <div
              key={s.name}
              className="rounded border border-border/40 bg-background/40 px-2.5 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <code className="text-[12.5px] font-medium text-foreground">
                  {s.name}
                </code>
                {s.existsInRegistry ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-amber-400" />
                )}
              </div>
              <p className="mt-1 text-[10.5px] text-muted-foreground">
                {s.description}
              </p>
              {s.sensitivityTags.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {s.sensitivityTags.map((t) => (
                    <Badge
                      key={t}
                      variant="outline"
                      className="border-rose-400/30 bg-rose-400/10 text-[9px] uppercase tracking-wider text-rose-300"
                    >
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </PlanBox>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MiniStat
          icon={DollarSign}
          label="Custo / run"
          value={`$${plan.costEstimate.perRunUsd.toFixed(3)}`}
        />
        <MiniStat
          icon={DollarSign}
          label="Estimativa mensal"
          value={`$${plan.costEstimate.monthlyUsd.toFixed(2)}`}
        />
        <MiniStat
          icon={Check}
          label="Eval checks"
          value={String(plan.evalRubric.length)}
        />
      </div>

      <PlanBox
        title="Pontos de aprovação humana"
        body={
          plan.approvalPoints.length === 0
            ? "Nenhum — execução totalmente autônoma."
            : undefined
        }
      >
        {plan.approvalPoints.length > 0 && (
          <ul className="space-y-1.5">
            {plan.approvalPoints.map((a, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded border border-border/40 bg-background/40 px-2 py-1.5 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-foreground/90">{a.step}</span>
                  <span className="text-muted-foreground/60">quando</span>
                  <span className="font-mono text-amber-300">{a.condition}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <span className="rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
                    {a.approverRole}
                  </span>
                  <span className="tabular-nums">SLA {a.slaHours}h</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </PlanBox>

      <PlanBox title="Riscos">
        <ul className="space-y-1.5">
          {plan.risks.map((r, i) => (
            <li
              key={i}
              className="rounded border border-border/40 bg-background/40 px-2.5 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-foreground/85">{r.risk}</p>
                <Badge
                  variant="outline"
                  className={cn(
                    "shrink-0 text-[9.5px] uppercase tracking-wider",
                    r.severity === "high" &&
                      "border-rose-400/40 bg-rose-400/10 text-rose-300",
                    r.severity === "medium" &&
                      "border-amber-400/40 bg-amber-400/10 text-amber-300",
                    r.severity === "low" &&
                      "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                  )}
                >
                  {r.severity}
                </Badge>
              </div>
              <p className="mt-1 text-[10.5px] text-muted-foreground">
                <span className="text-foreground/60">Mitigação:</span>{" "}
                {r.mitigation}
              </p>
            </li>
          ))}
        </ul>
      </PlanBox>
    </div>
  );
}

function PlanBox({
  title,
  body,
  items,
  children,
  extra,
}: {
  title: string;
  body?: string;
  items?: { icon: React.ElementType; label: string; tone: "rose" | "emerald" }[];
  children?: React.ReactNode;
  extra?: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border/60 bg-card/30">
      <div className="flex items-center justify-between border-b border-border/40 px-3 py-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h3>
        {extra}
      </div>
      <div className="px-3 py-3 text-sm">
        {body && <p className="text-foreground/85 leading-relaxed">{body}</p>}
        {items && (
          <ul className="space-y-1.5">
            {items.map((it, i) => {
              const Icon = it.icon;
              return (
                <li
                  key={i}
                  className="flex items-start gap-2 text-foreground/80"
                >
                  <Icon
                    className={cn(
                      "mt-0.5 h-3.5 w-3.5 shrink-0",
                      it.tone === "rose"
                        ? "text-rose-400/80"
                        : "text-emerald-400/80"
                    )}
                  />
                  <span>{it.label}</span>
                </li>
              );
            })}
          </ul>
        )}
        {children}
      </div>
    </div>
  );
}

function MiniStat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-border/40 bg-card/40 px-3 py-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <div className="mt-0.5 text-lg font-medium tabular-nums">{value}</div>
    </div>
  );
}

function ShieldAlert() {
  return <Sparkles className="h-2.5 w-2.5" />;
}

// ─────────────────────── REQUEST CHANGES STEP ───────────────────────

function RequestChangesStep({
  plan,
  changeReason,
  setChangeReason,
}: {
  plan: MissionPlan;
  changeReason: string;
  setChangeReason: (s: string) => void;
}) {
  void plan;
  return (
    <div className="space-y-4 px-6 py-5">
      <p className="text-sm text-foreground/85">
        O que precisa mudar no plano? Seja específico — o Planner vai usar isso
        para regenerar a versão 2.
      </p>
      <textarea
        value={changeReason}
        onChange={(e) => setChangeReason(e.target.value)}
        rows={6}
        placeholder="Ex.: faltou definir o que fazer quando o lead não tem email cadastrado. Deveria escalar pra mim em vez de marcar como cold."
        className="w-full resize-none rounded-md border border-input bg-background/60 px-3 py-2 text-sm leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
      />
      <div className="rounded-md border border-amber-400/30 bg-amber-400/[0.04] px-3 py-2 text-xs text-amber-200/90">
        Ao enviar, a mission entra em <code className="font-mono">plan_drafting</code>{" "}
        e seu comentário aparece no card. O Planner produz versão 2.
      </div>
    </div>
  );
}

// ─────────────────────── DONE STEP ───────────────────────

function DoneStep({
  missionId,
  state,
}: {
  missionId: string;
  state: "executing" | "plan_drafting";
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-400/10">
        <Check className="h-7 w-7 text-emerald-400" />
      </div>
      <h3 className="mt-5 text-base font-medium tracking-tight">
        Mission criada e no Kanban
      </h3>
      <div className="mt-2 flex items-center gap-2 rounded-md border border-border/60 bg-card/40 px-3 py-2">
        <span className="font-mono text-sm text-foreground">{missionId}</span>
        <span className="text-muted-foreground/60">·</span>
        <Badge variant="outline" className="text-[10px] uppercase tracking-wider">
          {state === "executing" ? "Em execução" : "Plano em desenho"}
        </Badge>
      </div>
      <p className="mt-3 max-w-md text-center text-xs text-muted-foreground">
        {state === "executing"
          ? "Workers iniciaram. Acompanha pelo card no Kanban — heartbeat real-time, drill-down nas runs, evals contínuos."
          : "Planner vai regenerar com seu feedback. Card está em Plano em desenho aguardando v2."}
      </p>
      <div className="mt-5 flex items-center gap-2 text-[10.5px] text-muted-foreground">
        <ExternalLink className="h-3 w-3" />
        Toda decisão deste fluxo virou linha no audit log.
      </div>
    </div>
  );
}

