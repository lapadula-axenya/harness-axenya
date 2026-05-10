import type {
  Agent,
  AuditEntry,
  Mission,
  MissionState,
  User,
} from "./types";

export const COLUMN_ORDER: MissionState[] = [
  "idea",
  "plan_drafting",
  "plan_review",
  "executing",
  "qa",
  "in_production",
];

export const COLUMN_META: Record<
  MissionState,
  { label: string; tint: string; description: string }
> = {
  idea: {
    label: "Ideia",
    tint: "tint-idea",
    description: "Intent rascunhada, sem plano",
  },
  plan_drafting: {
    label: "Plano em desenho",
    tint: "tint-drafting",
    description: "Planner rascunhando ou aguardando follow-up",
  },
  plan_review: {
    label: "Plano em aprovação",
    tint: "tint-review",
    description: "PM/approver precisa decidir",
  },
  executing: {
    label: "Em execução",
    tint: "tint-executing",
    description: "Workers rodando",
  },
  qa: {
    label: "Validação / QA",
    tint: "tint-qa",
    description: "Validators + checagem humana",
  },
  in_production: {
    label: "Em produção",
    tint: "tint-production",
    description: "Entregue, monitorado",
  },
  paused: {
    label: "Pausada",
    tint: "tint-idea",
    description: "Suspensa por operador",
  },
  archived: {
    label: "Arquivada",
    tint: "tint-idea",
    description: "Encerrada",
  },
};

export const USERS: Record<string, User> = {
  sofia: {
    id: "u_sofia",
    name: "Sofia Lapadula",
    email: "sofia@axenya.com.br",
    role: "admin",
    initials: "SL",
  },
  rafa: {
    id: "u_rafa",
    name: "Rafael Magalhães",
    email: "rafa@axenya.com.br",
    role: "approver",
    initials: "RM",
  },
  aline: {
    id: "u_aline",
    name: "Dra. Aline",
    email: "aline@axenya.com.br",
    role: "approver",
    initials: "AL",
  },
  bia: {
    id: "u_bia",
    name: "Bia Costa",
    email: "bia@axenya.com.br",
    role: "pm",
    initials: "BC",
  },
  estevao: {
    id: "u_estevao",
    name: "Estevão Lima",
    email: "estevao@axenya.com.br",
    role: "admin",
    initials: "EL",
  },
  mariano: {
    id: "u_mariano",
    name: "Mariano",
    email: "mariano@axenya.com.br",
    role: "approver",
    initials: "MA",
  },
};

const now = new Date();
const iso = (offsetMs: number) =>
  new Date(now.getTime() + offsetMs).toISOString();

export const MISSIONS: Mission[] = [
  {
    id: "m_001",
    title: "Triagem de leads da landing page",
    intent:
      "Quando um lead chega pela landing page, quero que ele seja enriquecido, classificado em hot/warm/cold e marcado no HubSpot. Leads hot abrem ticket no Slack #comercial.",
    state: "in_production",
    priority: "high",
    createdBy: USERS.bia,
    assignee: USERS.bia,
    agentSlug: "triagem_lead",
    agentVersion: "v1.4.2",
    createdAt: iso(-1000 * 60 * 60 * 24 * 18),
    updatedAt: iso(-1000 * 60 * 60 * 6),
    plan: {
      id: "p_001",
      version: 4,
      status: "approved",
      generatedBy: "planner@v1.2.1",
      scope:
        "Receber webhook do HubSpot ao criar lead → enriquecer via Apollo → classificar score 0-1 → atualizar contato no HubSpot → se score ≥ 0.7, notificar Slack #comercial com botões Aprovar/Rejeitar (block kit).",
      nonScope: [
        "Não envia e-mail para o lead diretamente.",
        "Não cria deal — só atualiza contato.",
        "Não roda em leads pré-existentes (só novos).",
      ],
      flowYaml:
        "nodes:\n  - id: enrich\n    skill: apollo.lookup\n  - id: classify\n    agent: classifier\n  - id: update\n    skill: hubspot.update_contact\n  - id: notify_hot\n    skill: slack.post\n    condition: score >= 0.7\nedges:\n  - enrich -> classify\n  - classify -> update\n  - update -> notify_hot",
      requiredSkills: [
        {
          name: "hubspot.read_contact",
          description: "Lê contato do HubSpot",
          sensitivityTags: ["pii"],
          existsInRegistry: true,
        },
        {
          name: "hubspot.update_contact",
          description: "Atualiza propriedades do contato",
          sensitivityTags: ["pii"],
          existsInRegistry: true,
        },
        {
          name: "apollo.lookup",
          description: "Enriquece dados do lead",
          sensitivityTags: ["pii"],
          existsInRegistry: true,
        },
        {
          name: "slack.post",
          description: "Posta mensagem em canal Slack",
          sensitivityTags: [],
          existsInRegistry: true,
        },
      ],
      evalRubric: [
        {
          id: "e1",
          kind: "deterministic",
          description: "HubSpot recebeu update do contato",
          weight: 0.3,
          lastScore: 1.0,
        },
        {
          id: "e2",
          kind: "deterministic",
          description: "Score está em [0,1]",
          weight: 0.2,
          lastScore: 1.0,
        },
        {
          id: "e3",
          kind: "llm_judge",
          description: "Reasoning de classificação é coerente com dados",
          weight: 0.3,
          lastScore: 0.87,
        },
        {
          id: "e4",
          kind: "deterministic",
          description: "Lead hot notificou Slack",
          weight: 0.2,
          lastScore: 0.95,
        },
      ],
      approvalPoints: [
        {
          step: "classify",
          condition: "score < 0.4",
          approverRole: "pm",
          slaHours: 24,
        },
      ],
      costEstimate: {
        perRunUsd: 0.04,
        monthlyUsd: 240,
        volumeAssumption: "≈ 200 leads/dia × 30 dias",
      },
      risks: [
        {
          risk: "Apollo enrichment pode estar desatualizado",
          mitigation: "Fallback para lookup interno HubSpot",
          severity: "medium",
        },
        {
          risk: "PII LGPD — dados do lead",
          mitigation: "ACL restringe a propriedades já públicas no HubSpot",
          severity: "low",
        },
      ],
      confidence: 0.92,
      followUpQuestions: [],
    },
    events: [
      {
        id: "ev1",
        kind: "run_completed",
        payload: { runId: "r_8821", durationMs: 4200, costUsd: 0.038 },
        createdAt: iso(-1000 * 60 * 60 * 1.2),
      },
      {
        id: "ev2",
        kind: "eval_passed",
        payload: { score: 0.91 },
        createdAt: iso(-1000 * 60 * 60 * 2),
      },
    ],
    approvals: [
      {
        id: "a1",
        type: "plan",
        decision: "approved",
        decidedBy: { id: USERS.rafa.id, name: USERS.rafa.name },
        reason: "Escopo bem definido, custo aceitável.",
        decidedAt: iso(-1000 * 60 * 60 * 24 * 16),
      },
      {
        id: "a2",
        type: "production_promote",
        decision: "approved",
        decidedBy: { id: USERS.estevao.id, name: USERS.estevao.name },
        reason: "Suite de eval passou 5/5 em produção sombra.",
        decidedAt: iso(-1000 * 60 * 60 * 24 * 10),
      },
    ],
    metrics: {
      runsTotal: 4_212,
      runsSuccess: 4_098,
      costUsdMtd: 168.42,
      avgEvalScore: 0.89,
      p95LatencyMs: 5_800,
      lastRunAt: iso(-1000 * 60 * 8),
    },
  },
  {
    id: "m_002",
    title: "Triagem do inbox da Dra. Aline",
    intent:
      "Ler emails que chegam para aline@axenya.com.br, classificar (paciente/operacional/spam) e responder os operacionais com template. Pacientes vão para fila com aprovação humana.",
    state: "executing",
    priority: "high",
    createdBy: USERS.aline,
    assignee: USERS.aline,
    agentSlug: "triagem_email_aline",
    agentVersion: "v0.3.1",
    createdAt: iso(-1000 * 60 * 60 * 24 * 5),
    updatedAt: iso(-1000 * 60 * 12),
    plan: {
      id: "p_002",
      version: 2,
      status: "approved",
      generatedBy: "planner@v1.2.1",
      scope:
        "A cada 10min, ler novos emails da caixa da Dra. Aline. Classificar em paciente / operacional / spam. Para operacionais, redigir resposta com template e enfileirar para aprovação humana antes de enviar.",
      nonScope: [
        "Não envia email sem aprovação humana.",
        "Não acessa arquivos anexos com PHI sem flag explícita.",
        "Não responde direto pacientes — encaminha para fila clínica.",
      ],
      flowYaml: "# fluxo gerado pelo Planner v1.2.1 — 38 linhas",
      requiredSkills: [
        {
          name: "gmail.read",
          description: "Lê mensagens não-lidas",
          sensitivityTags: ["pii", "clinical_data"],
          existsInRegistry: true,
        },
        {
          name: "gmail.draft",
          description: "Cria rascunho de resposta",
          sensitivityTags: ["pii"],
          existsInRegistry: true,
        },
      ],
      evalRubric: [
        {
          id: "e1",
          kind: "llm_judge",
          description: "Classificação consistente com 50 exemplos gold",
          weight: 0.5,
          lastScore: 0.81,
        },
        {
          id: "e2",
          kind: "deterministic",
          description: "Nenhum email enviado sem approval",
          weight: 0.5,
          lastScore: 1.0,
        },
      ],
      approvalPoints: [
        {
          step: "send_response",
          condition: "always",
          approverRole: "approver",
          slaHours: 4,
        },
      ],
      costEstimate: {
        perRunUsd: 0.018,
        monthlyUsd: 78,
        volumeAssumption: "≈ 144 ciclos/dia",
      },
      risks: [
        {
          risk: "Vazamento de PHI via prompt logging",
          mitigation: "Redaction antes de mandar para LLM + Langfuse pii filter",
          severity: "high",
        },
      ],
      confidence: 0.84,
      followUpQuestions: [],
    },
    events: [
      {
        id: "ev3",
        kind: "run_started",
        payload: { runId: "r_8830" },
        createdAt: iso(-1000 * 60 * 12),
      },
      {
        id: "ev4",
        kind: "run_step",
        payload: { step: "classify", durationMs: 1800 },
        createdAt: iso(-1000 * 60 * 11),
      },
    ],
    approvals: [
      {
        id: "a3",
        type: "plan",
        decision: "approved",
        decidedBy: { id: USERS.rafa.id, name: USERS.rafa.name },
        reason: "Dual-control ok. Eval rubric clara.",
        decidedAt: iso(-1000 * 60 * 60 * 24 * 4),
      },
    ],
    metrics: {
      runsTotal: 412,
      runsSuccess: 401,
      costUsdMtd: 21.4,
      avgEvalScore: 0.83,
      p95LatencyMs: 3_900,
      lastRunAt: iso(-1000 * 60 * 12),
    },
  },
  {
    id: "m_003",
    title: "Weekly report de sinistralidade para corretores",
    intent:
      "Toda sexta às 9h, gerar relatório de sinistralidade por empresa cliente e enviar para os corretores responsáveis. Formato PDF + resumo no Slack.",
    state: "plan_review",
    priority: "medium",
    createdBy: USERS.bia,
    createdAt: iso(-1000 * 60 * 60 * 18),
    updatedAt: iso(-1000 * 60 * 30),
    plan: {
      id: "p_003",
      version: 1,
      status: "pending",
      generatedBy: "planner@v1.2.1",
      scope:
        "Cron sexta 09:00 BRT → query BigQuery sinistralidade últimas 4 semanas → agregação por empresa → render PDF (template Latex) → enviar via Slack DM para corretor.owner_id da empresa.",
      nonScope: [
        "Não envia para o corretor copy-cliente (apenas owner).",
        "Não inclui dados de beneficiário individual — só agregado por empresa.",
      ],
      flowYaml: "# 22 linhas — query BQ + render + dispatch",
      requiredSkills: [
        {
          name: "bigquery.sinistralidade_v2",
          description: "View whitelisted",
          sensitivityTags: ["financial"],
          existsInRegistry: true,
        },
        {
          name: "pdf.render",
          description: "Renderiza Latex em PDF",
          sensitivityTags: [],
          existsInRegistry: true,
        },
        {
          name: "slack.dm",
          description: "DM direto para usuário",
          sensitivityTags: [],
          existsInRegistry: true,
        },
      ],
      evalRubric: [
        {
          id: "e1",
          kind: "deterministic",
          description: "PDF gerado tem todas as seções obrigatórias",
          weight: 0.5,
        },
        {
          id: "e2",
          kind: "llm_judge",
          description: "Comentário executivo é coerente com números",
          weight: 0.5,
        },
      ],
      approvalPoints: [],
      costEstimate: {
        perRunUsd: 0.12,
        monthlyUsd: 1.92,
        volumeAssumption: "4 corretores × 4 semanas",
      },
      risks: [
        {
          risk: "Dado financeiro indo por Slack",
          mitigation: "Slack DM cifrado em trânsito; corretor já tem acesso",
          severity: "medium",
        },
      ],
      confidence: 0.88,
      followUpQuestions: [],
    },
    events: [
      {
        id: "ev5",
        kind: "plan_generated",
        payload: { version: 1, ms: 14_200 },
        createdAt: iso(-1000 * 60 * 60 * 6),
      },
    ],
    approvals: [],
    metrics: {
      runsTotal: 0,
      runsSuccess: 0,
      costUsdMtd: 0,
    },
  },
  {
    id: "m_004",
    title: "Consolidar pedidos de reembolso pendentes",
    intent:
      "Quero um agente que olhe a fila de reembolso do sistema Ksenia e classifique cada pedido em aprovar automaticamente / pedir documento / escalar para análise humana.",
    state: "plan_drafting",
    priority: "high",
    createdBy: USERS.sofia,
    createdAt: iso(-1000 * 60 * 60 * 4),
    updatedAt: iso(-1000 * 60 * 50),
    events: [
      {
        id: "ev6",
        kind: "plan_generated",
        payload: { version: 1, ms: 11_800 },
        createdAt: iso(-1000 * 60 * 60 * 3),
      },
      {
        id: "ev7",
        kind: "comment",
        actor: { id: "planner", name: "Planner" },
        payload: {
          message:
            "Para missions tocando dado financeiro/clinical, preciso que você defina: (1) quem é approver de exceções? (2) limite em R$ acima do qual escala sempre para humano?",
        },
        createdAt: iso(-1000 * 60 * 60 * 3),
      },
    ],
    approvals: [],
    metrics: { runsTotal: 0, runsSuccess: 0, costUsdMtd: 0 },
  },
  {
    id: "m_005",
    title: "Alerta de drift no agente de triagem de leads",
    intent:
      "[gerada automaticamente por drift detection] Eval score do agente triagem_lead caiu de 0.89 para 0.71 nas últimas 48h. Investigar causa.",
    state: "plan_drafting",
    priority: "high",
    createdBy: { ...USERS.sofia, name: "Sistema" },
    createdAt: iso(-1000 * 60 * 60 * 8),
    updatedAt: iso(-1000 * 60 * 60 * 2),
    agentSlug: "triagem_lead",
    events: [
      {
        id: "ev8",
        kind: "drift_detected",
        payload: { from: 0.89, to: 0.71, window: "48h" },
        createdAt: iso(-1000 * 60 * 60 * 8),
      },
    ],
    approvals: [],
    metrics: { runsTotal: 0, runsSuccess: 0, costUsdMtd: 0 },
  },
  {
    id: "m_006",
    title: "Onboarding automatizado de empresa nova",
    intent:
      "Quando uma empresa cliente é criada no HubSpot com tag 'closed-won', disparar fluxo: criar workspace, enviar contrato, agendar reunião kickoff e abrir thread no Slack.",
    state: "idea",
    priority: "medium",
    createdBy: USERS.bia,
    createdAt: iso(-1000 * 60 * 60 * 2),
    updatedAt: iso(-1000 * 60 * 60 * 2),
    events: [],
    approvals: [],
    metrics: { runsTotal: 0, runsSuccess: 0, costUsdMtd: 0 },
  },
  {
    id: "m_007",
    title: "Triagem de inbox geral comercial@",
    intent:
      "Inbox commercial@axenya.com.br recebe ~80 emails/dia. Quero classificar e auto-responder os FAQ.",
    state: "idea",
    priority: "low",
    createdBy: USERS.mariano,
    createdAt: iso(-1000 * 60 * 60 * 24 * 3),
    updatedAt: iso(-1000 * 60 * 60 * 24 * 3),
    events: [],
    approvals: [],
    metrics: { runsTotal: 0, runsSuccess: 0, costUsdMtd: 0 },
  },
  {
    id: "m_008",
    title: "Validação de aderência de plano dos beneficiários",
    intent:
      "Mensalmente, checar quais beneficiários não fizeram nenhum check-up no período e mandar lembrete personalizado.",
    state: "qa",
    priority: "medium",
    createdBy: USERS.aline,
    assignee: USERS.aline,
    agentSlug: "aderencia_planos",
    agentVersion: "v0.1.0",
    createdAt: iso(-1000 * 60 * 60 * 24 * 9),
    updatedAt: iso(-1000 * 60 * 90),
    plan: {
      id: "p_008",
      version: 1,
      status: "approved",
      generatedBy: "planner@v1.2.1",
      scope: "...",
      nonScope: [],
      flowYaml: "",
      requiredSkills: [],
      evalRubric: [],
      approvalPoints: [],
      costEstimate: { perRunUsd: 0.08, monthlyUsd: 4.8, volumeAssumption: "" },
      risks: [],
      confidence: 0.78,
      followUpQuestions: [],
    },
    events: [
      {
        id: "ev9",
        kind: "eval_passed",
        payload: { score: 0.78 },
        createdAt: iso(-1000 * 60 * 60 * 4),
      },
    ],
    approvals: [],
    metrics: {
      runsTotal: 12,
      runsSuccess: 11,
      costUsdMtd: 1.0,
      avgEvalScore: 0.78,
      p95LatencyMs: 9_200,
      lastRunAt: iso(-1000 * 60 * 60 * 4),
    },
  },
];

export const AGENTS: Agent[] = [
  {
    slug: "triagem_lead",
    name: "Triagem de Lead",
    description: "Enriquece e classifica leads novos da landing page.",
    version: "v1.4.2",
    versionsCount: 14,
    owner: USERS.bia,
    state: "active",
    primaryModel: "claude-sonnet-4-6",
    fallbackModel: "gemini-2.5-pro",
    missionsActive: 1,
    costUsd30d: 168.42,
    successRate: 0.973,
    lastDriftAlert: iso(-1000 * 60 * 60 * 8),
  },
  {
    slug: "triagem_email_aline",
    name: "Triagem Email — Dra. Aline",
    description: "Classifica e rascunha respostas para o inbox da Aline.",
    version: "v0.3.1",
    versionsCount: 3,
    owner: USERS.aline,
    state: "active",
    primaryModel: "claude-opus-4-7",
    fallbackModel: "claude-sonnet-4-6",
    missionsActive: 1,
    costUsd30d: 21.4,
    successRate: 0.973,
  },
  {
    slug: "planner",
    name: "Planner",
    description:
      "Agente orquestrador que transforma intent do PM em plano executável.",
    version: "v1.2.1",
    versionsCount: 8,
    owner: USERS.sofia,
    state: "active",
    primaryModel: "claude-sonnet-4-6",
    fallbackModel: "claude-opus-4-7",
    missionsActive: 6,
    costUsd30d: 12.8,
    successRate: 0.98,
  },
  {
    slug: "aderencia_planos",
    name: "Aderência de Planos",
    description: "Identifica beneficiários sem check-up recente.",
    version: "v0.1.0",
    versionsCount: 1,
    owner: USERS.aline,
    state: "shadow",
    primaryModel: "claude-sonnet-4-6",
    missionsActive: 1,
    costUsd30d: 1.0,
    successRate: 0.92,
  },
];

export const AUDIT: AuditEntry[] = [
  {
    id: "au1",
    at: iso(-1000 * 60 * 30),
    actor: "Rafael Magalhães",
    action: "mission.approve_plan",
    resource: "mission:m_002",
    decision: "allow",
    reason: "dual-control ok; sensibilidade pii com segundo approver",
  },
  {
    id: "au2",
    at: iso(-1000 * 60 * 60 * 1),
    actor: "Sistema",
    action: "skill.invoke",
    resource: "skill:gmail.read filter={mailbox: aline@…}",
    decision: "allow",
    reason: "agente triagem_email_aline tem ACL ativa",
  },
  {
    id: "au3",
    at: iso(-1000 * 60 * 60 * 2),
    actor: "Bia Costa",
    action: "mission.transition",
    resource: "mission:m_001 → in_production",
    decision: "allow",
    reason: "pm com capability operate + eval ok",
  },
  {
    id: "au4",
    at: iso(-1000 * 60 * 60 * 5),
    actor: "Mariano",
    action: "skill.invoke",
    resource: "skill:hubspot.update_contact",
    decision: "deny",
    reason: "user não tem capability operate no agente triagem_lead",
  },
  {
    id: "au5",
    at: iso(-1000 * 60 * 60 * 8),
    actor: "Sistema",
    action: "drift_detected",
    resource: "agent:triagem_lead",
    decision: "deny",
    reason: "score caiu > 2σ; promote da v1.4.3 bloqueado",
  },
];

export const CURRENT_USER = USERS.sofia;
