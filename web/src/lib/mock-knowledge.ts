import { USERS } from "./mock-data";
import type { KnowledgeNode } from "./types";

const now = new Date();
const iso = (offsetMs: number) =>
  new Date(now.getTime() + offsetMs).toISOString();

const day = 24 * 60 * 60 * 1000;

/**
 * Estrutura mock da knowledge base.
 * IDs são paths para facilitar referência cruzada.
 */
export const KNOWLEDGE: KnowledgeNode[] = [
  // ────────────────────── PASTAS ──────────────────────
  {
    id: "operacao",
    kind: "folder",
    name: "Operação",
    path: "operacao",
    children: [
      "operacao/triagem-leads-runbook.md",
      "operacao/inbox-aline-runbook.md",
      "operacao/weekly-sinistralidade.md",
      "operacao/incidentes",
    ],
  },
  {
    id: "operacao/incidentes",
    kind: "folder",
    name: "Incidentes",
    path: "operacao/incidentes",
    parentPath: "operacao",
    children: [
      "operacao/incidentes/2026-04-15-drift-triagem.md",
      "operacao/incidentes/2026-03-02-hubspot-rate-limit.md",
    ],
  },
  {
    id: "engenharia",
    kind: "folder",
    name: "Engenharia",
    path: "engenharia",
    children: [
      "engenharia/bloco-d-kanban.md",
      "engenharia/bloco-a-identity.md",
      "engenharia/planner-design.md",
      "engenharia/drift-detection.md",
      "engenharia/conector-hubspot.md",
    ],
  },
  {
    id: "produto",
    kind: "folder",
    name: "Produto",
    path: "produto",
    children: [
      "produto/mission-control-prd.md",
      "produto/roadmap-h2-2026.md",
      "produto/aderencia-planos-prd.md",
      "produto/reembolso-classifier-prd.md",
    ],
  },
  {
    id: "governanca",
    kind: "folder",
    name: "Governança",
    path: "governanca",
    children: [
      "governanca/lgpd-checklist.md",
      "governanca/dual-control-quando-aplica.md",
      "governanca/aprovacao-de-excecoes.md",
      "governanca/retencao-audit.md",
    ],
  },
  {
    id: "onboarding",
    kind: "folder",
    name: "Onboarding",
    path: "onboarding",
    children: [
      "onboarding/como-criar-uma-mission.md",
      "onboarding/glossario-xenia.md",
    ],
  },

  // ────────────────────── OPERAÇÃO ──────────────────────
  {
    id: "operacao/triagem-leads-runbook.md",
    kind: "file",
    name: "Triagem de leads — runbook",
    path: "operacao/triagem-leads-runbook.md",
    parentPath: "operacao",
    updatedAt: iso(-2 * day),
    author: USERS.bia,
    tags: ["runbook", "comercial"],
    body: `# Triagem de leads — runbook

Este runbook cobre o fluxo de triagem de leads que chegam pela landing page
para o time comercial.

## Quando consultar

- Quando um lead deveria ter sido classificado e não foi.
- Quando o score de classificação parece destoante do conteúdo do lead.
- Quando o HubSpot não recebeu a atualização esperada.

## Fluxo

1. **Trigger:** webhook do HubSpot ao criar lead (\`HubSpot → /v1/webhooks/hubspot/lead\`).
2. **Enriquecimento:** \`apollo.lookup\` com cache de 24h.
3. **Classificação:** agente \`triagem_lead\` produz score 0–1 + reasoning.
4. **Update:** \`hubspot.update_contact\` grava score e label.
5. **Notificação:** se score ≥ 0.7, posta em \`slack:#comercial\`.

## Quando um lead "some"

- Verificar se o webhook chegou: \`POST /v1/webhooks/hubspot/lead\` no audit log.
- Verificar idempotency key — duplicatas são silenciosamente ignoradas.
- Se Apollo retornou 429, o lead vira mission em \`plan_drafting\` para retry manual.

## Donos

- **Operacional:** time comercial.
- **Técnico:** Sofia + Bia.

## Ligações

- Agente \`triagem_lead\`
- Processo \`hubspot_lead_sync\` (drain a cada 15min)
- Mission \`m_001\`
- PRD em \`produto/triagem-leads.md\` *(em construção)*
`,
    links: [
      { kind: "agent", id: "triagem_lead", label: "triagem_lead" },
      { kind: "process", id: "pr_004", label: "hubspot_lead_sync" },
      { kind: "mission", id: "m_001", label: "m_001 · Triagem de leads" },
      { kind: "skill", id: "hubspot.update_contact", label: "hubspot.update_contact" },
      { kind: "skill", id: "apollo.lookup", label: "apollo.lookup" },
    ],
    backlinks: [
      { kind: "process", id: "pr_001", label: "Triagem inbox Aline" },
      { kind: "process", id: "pr_004", label: "hubspot_lead_sync" },
    ],
  },
  {
    id: "operacao/inbox-aline-runbook.md",
    kind: "file",
    name: "Inbox Aline — runbook",
    path: "operacao/inbox-aline-runbook.md",
    parentPath: "operacao",
    updatedAt: iso(-1 * day),
    author: USERS.aline,
    tags: ["runbook", "clinical_data"],
    body: `# Inbox da Dra. Aline — runbook

Este agente lê emails da caixa \`aline@axenya.com.br\` e classifica em três
categorias: **paciente**, **operacional** e **spam**.

## Política

- **Nenhum email é enviado sem aprovação humana.** Mesmo respostas operacionais
  passam por approval queue.
- Emails de paciente nunca são respondidos pelo agente — encaminhados para a
  fila clínica.
- A skill \`gmail.read\` é \`clinical_data + pii\` ⇒ dual-control obrigatório
  em qualquer alteração de plano.

## Quem pode operar

- Apenas Aline e Bia têm capability \`operate\` (configurado em Acessos & ACL).
- Aprovação de exceções: Aline ou Rafa.

## Métricas alvo

| Métrica | Alvo |
|---------|------|
| Taxa de classificação correta | ≥ 0.85 |
| Tempo médio na fila de approval | ≤ 30min |
| Vazamento de PHI para LLM | 0 (auditado mensalmente) |

## Quando pausar

Pausar o processo \`triagem_inbox_aline_diaria\` se:
1. Suspeita de PHI vazando para fora dos logs redacted.
2. Aline em viagem com poderes de aprovação delegados.
3. Drift detection abriu mission de regressão.
`,
    links: [
      { kind: "agent", id: "triagem_email_aline", label: "triagem_email_aline" },
      { kind: "process", id: "pr_001", label: "triagem_inbox_aline_diaria" },
      { kind: "mission", id: "m_002", label: "m_002 · Triagem Aline" },
      { kind: "skill", id: "gmail.read", label: "gmail.read" },
      { kind: "user", id: USERS.aline.id, label: USERS.aline.name },
    ],
    backlinks: [{ kind: "process", id: "pr_001", label: "triagem_inbox_aline_diaria" }],
  },
  {
    id: "operacao/weekly-sinistralidade.md",
    kind: "file",
    name: "Weekly sinistralidade — operação",
    path: "operacao/weekly-sinistralidade.md",
    parentPath: "operacao",
    updatedAt: iso(-3 * day),
    author: USERS.bia,
    tags: ["report"],
    body: `# Weekly de sinistralidade

Relatório semanal de sinistralidade enviado aos corretores toda sexta às 9h.

## Source of truth

- Tabela \`bigquery:axenya-prod.curated.sinistralidade_v2\`.
- Janela: últimas 4 semanas.
- Granularidade: empresa cliente.

## Distribuição

- DM Slack para o \`owner_id\` de cada empresa.
- PDF anexo com seções: visão geral, ranking, alertas, recomendações.

## Checklist pré-envio

- [ ] Dados de fim de semana já consolidados (rodar após 8h sexta)?
- [ ] Owner_id da empresa preenchido para todos os clientes?
- [ ] Slack ID do corretor verificado contra desligamentos?
`,
    links: [
      { kind: "process", id: "pr_002", label: "sinistralidade_weekly" },
      { kind: "mission", id: "m_003", label: "m_003 · weekly report" },
      { kind: "skill", id: "bigquery.sinistralidade_v2", label: "bq.sinistralidade_v2" },
    ],
    backlinks: [{ kind: "process", id: "pr_002", label: "sinistralidade_weekly" }],
  },
  {
    id: "operacao/incidentes/2026-04-15-drift-triagem.md",
    kind: "file",
    name: "2026-04-15 · drift em triagem_lead",
    path: "operacao/incidentes/2026-04-15-drift-triagem.md",
    parentPath: "operacao/incidentes",
    updatedAt: iso(-26 * day),
    author: USERS.sofia,
    tags: ["incident", "post-mortem"],
    body: `# Incidente · 2026-04-15 · drift em triagem_lead

**Severidade:** P2
**Duração:** ~48h
**Mission gerada:** \`m_005\`

## Resumo

Eval score do agente \`triagem_lead\` caiu de 0.89 para 0.71 em janela móvel
de 48h. Drift detection abriu mission automaticamente.

## Causa raiz

Mudança no formato do payload do HubSpot (novo campo \`lead_source_v2\`) que
deslocou o feature set. O classifier passou a tratar como lead frio leads
que antes seriam quentes.

## Mitigação imediata

- Reverter para \`triagem_lead@v1.4.1\` via prompt registry rollback.
- Pausar processo \`hubspot_lead_sync\` durante a janela de revisão.

## Correção permanente

- Plano \`m_005\` v2 inclui o novo campo no enriquecimento.
- Drift detection ajustado para alertar mais cedo (1σ por 6h → 2σ por 48h).

## Lições

- Mudanças no schema upstream do HubSpot devem virar evento broadcast no
  context library (bloco G).
`,
    links: [
      { kind: "agent", id: "triagem_lead", label: "triagem_lead" },
      { kind: "mission", id: "m_005", label: "m_005 · drift regressão" },
    ],
  },
  {
    id: "operacao/incidentes/2026-03-02-hubspot-rate-limit.md",
    kind: "file",
    name: "2026-03-02 · rate limit HubSpot",
    path: "operacao/incidentes/2026-03-02-hubspot-rate-limit.md",
    parentPath: "operacao/incidentes",
    updatedAt: iso(-70 * day),
    author: USERS.estevao,
    tags: ["incident"],
    body: `# Incidente · 2026-03-02 · rate limit no HubSpot

429 sustained em \`hubspot.update_contact\` por ~40min. Backlog drenou em 2h.

## Fix aplicado

- Backoff exponencial elevado de 30s → 120s.
- Idempotency key padronizada no client.
`,
    links: [
      { kind: "skill", id: "hubspot.update_contact", label: "hubspot.update_contact" },
    ],
  },

  // ────────────────────── ENGENHARIA ──────────────────────
  {
    id: "engenharia/bloco-d-kanban.md",
    kind: "file",
    name: "Bloco D — Kanban",
    path: "engenharia/bloco-d-kanban.md",
    parentPath: "engenharia",
    updatedAt: iso(-1 * day),
    author: USERS.sofia,
    tags: ["spec", "fase-5"],
    body: `# Bloco D — Kanban de Missões

SPEC técnico completo em \`docs/SPEC_BLOCK_D_KANBAN.md\` na raiz do repo.
Esta página é o resumo orientado a usuário.

## O que é

A surface principal da plataforma. 5 colunas, drag-and-drop respeitando a
state machine, real-time via WebSocket.

## Estados

| Estado | Quem move | Para onde |
|--------|-----------|-----------|
| \`idea\` | PM | drafting / archived |
| \`plan_drafting\` | Planner | review |
| \`plan_review\` | Approver | executing / drafting / archived |
| \`executing\` | Sistema | qa / paused |
| \`qa\` | Validators | in_production / executing |
| \`in_production\` | — | paused / archived |

## Audit

- Toda transição é \`mission_event\` append-only.
- Cada aprovação grava motivo obrigatório.
- Drift em prod **não** retrocede card — cria mission nova.
`,
    links: [
      { kind: "mission", id: "m_001", label: "m_001" },
      { kind: "mission", id: "m_002", label: "m_002" },
    ],
  },
  {
    id: "engenharia/bloco-a-identity.md",
    kind: "file",
    name: "Bloco A — Identity & Access",
    path: "engenharia/bloco-a-identity.md",
    parentPath: "engenharia",
    updatedAt: iso(-1 * day),
    author: USERS.sofia,
    tags: ["spec", "fase-5"],
    body: `# Bloco A — Identity & Access

SSO via Google Workspace (\`hd=axenya.com.br\`), RBAC com 5 papéis fixos,
ACL fina \`agente × skill × resource\`.

## Papéis

- **viewer** — só lê quadro.
- **pm** — cria missions, aprova plano (exceto sensíveis).
- **approver** — aprova plano sensível (dual-control).
- **admin** — gerencia ACL + roles.
- **auditor** — read-only no audit log.

## Engine

Oso (biblioteca Polar). Cache LRU 30s + invalidação Redis pub/sub.
Target p99 < 5ms.

## Por que dual-control

Skills com \`clinical_data\` ou \`pii\` exigem aprovador ≠ autor. Isso protege
contra erro acidental e satisfaz requisito de compliance em saúde.
`,
    links: [
      { kind: "skill", id: "gmail.read", label: "gmail.read" },
      { kind: "skill", id: "ksenia.reembolso_fila", label: "ksenia.reembolso_fila" },
    ],
  },
  {
    id: "engenharia/planner-design.md",
    kind: "file",
    name: "Planner — design",
    path: "engenharia/planner-design.md",
    parentPath: "engenharia",
    updatedAt: iso(-1 * day),
    author: USERS.sofia,
    tags: ["spec", "agente"],
    body: `# Planner — agente orquestrador

Transforma intent em plano executável em < 60s.

## Inputs

- \`intent\` (texto livre do PM)
- Contexto: workspace, autor, missions linkadas, modelo preferido

## Output (MissionPlan JSON)

- Escopo, non-scope
- Flow YAML
- Required skills (com sensitivity tags)
- Eval rubric (≥ 1 determinístico)
- Approval points
- Cost estimate
- Risks (4 categorias)
- Confidence ∈ [0,1]

## Regras duras

1. Não inventa skill. Se precisa de nova, marca \`exists_in_registry: false\`.
2. Skill com \`clinical_data\`/\`pii\` ⇒ exige approval point.
3. Cost estimate assume 10x menos do que o PM disser, conservadoramente.
`,
    links: [{ kind: "agent", id: "planner", label: "planner" }],
  },
  {
    id: "engenharia/drift-detection.md",
    kind: "file",
    name: "Drift detection — como funciona",
    path: "engenharia/drift-detection.md",
    parentPath: "engenharia",
    updatedAt: iso(-5 * day),
    author: USERS.sofia,
    tags: ["evals"],
    body: `# Drift detection

## Sinais monitorados

- Score médio das suites de eval em janela móvel.
- Taxa de falhas determinísticas.
- Distribuição de custo por run (anomalia ⇒ regressão de prompt).

## Threshold default

- 1σ por 6h → warning (sem ação).
- 2σ por 48h → cria mission de regressão automaticamente.
- Queda absoluta > 0.15 em qualquer janela → escalation P2.

## Output

- Bloqueia \`promote\` da próxima versão até resolução manual.
- Pinga owner no Slack.
`,
    links: [{ kind: "process", id: "pr_003", label: "drift_overnight_sweep" }],
  },
  {
    id: "engenharia/conector-hubspot.md",
    kind: "file",
    name: "Conector HubSpot",
    path: "engenharia/conector-hubspot.md",
    parentPath: "engenharia",
    updatedAt: iso(-9 * day),
    author: USERS.estevao,
    tags: ["integracao"],
    body: `# Conector HubSpot

Skills expostas:
- \`hubspot.read_contact\`
- \`hubspot.update_contact\`
- \`hubspot.list_pipeline\`

## Auth

OAuth2 com refresh token. App registrado em \`axenya-data\`. Rotação anual.

## Rate limits

- 100 req/10s por OAuth app.
- Implementamos token bucket local + backoff exponencial.

## Webhooks consumidos

- \`contact.creation\` → trigger do agente \`triagem_lead\`.
- \`deal.stage.closed-won\` → trigger do agente de onboarding (fase 6).
`,
    links: [
      { kind: "skill", id: "hubspot.update_contact", label: "hubspot.update_contact" },
      { kind: "process", id: "pr_004", label: "hubspot_lead_sync" },
    ],
  },

  // ────────────────────── PRODUTO ──────────────────────
  {
    id: "produto/mission-control-prd.md",
    kind: "file",
    name: "PRD — Mission Control (Kanban)",
    path: "produto/mission-control-prd.md",
    parentPath: "produto",
    updatedAt: iso(-3 * day),
    author: USERS.sofia,
    tags: ["prd"],
    body: `# PRD — Mission Control

> "Plataforma que substitui o Claude GUI individual por infraestrutura."

## Problema

Hoje agentes vivem em GUIs individuais — não auditável, não escalável,
sem governança. Cada nova automação vira projeto custom.

## Quem é o usuário

**Não é eng.** É PM. O PM escreve intent → Planner faz plano → PM aprova
→ frota executa. O PM acompanha pelo **Kanban**.

## Métricas de sucesso

- Tempo de "intent" até "em produção": de 3 semanas → 3 dias.
- Missions promovidas por PM sem código: ≥ 60% na fase 8.
- Drift detectado dentro de 1h após começar.

## Out of scope

- Visual flow editor estilo n8n (Planner gera YAML; PM lê markdown).
- Org chart de agentes estilo Tess.
- Multi-tenant externo.
`,
    links: [],
  },
  {
    id: "produto/roadmap-h2-2026.md",
    kind: "file",
    name: "Roadmap H2 2026",
    path: "produto/roadmap-h2-2026.md",
    parentPath: "produto",
    updatedAt: iso(-4 * day),
    author: USERS.sofia,
    tags: ["roadmap"],
    body: `# Roadmap H2 2026

## Fase 5 — Fundação PM (atual)

- Bloco A · SSO + ACL
- Bloco B · Prompt registry (Langfuse)
- Bloco D · Kanban
- Planner v1

**Exit:** Sofia migra 1 agente da GUI individual para mission em prod sem
código.

## Fase 6 — Confiabilidade

- Bloco C · Evals + drift + replay
- Bloco F · Slack triggers

## Fase 7 — Robustez

- Bloco E · Routing/fallback (LiteLLM)
- Bloco G · Context library (entities Axenya)
- Bloco K · Load test + SLA

## Fase 8 — Não-eng creators

- Bloco H · Preview sandbox com fixtures
- Planner v2 (mais autônomo)
`,
    links: [],
  },
  {
    id: "produto/aderencia-planos-prd.md",
    kind: "file",
    name: "PRD — Aderência de planos",
    path: "produto/aderencia-planos-prd.md",
    parentPath: "produto",
    updatedAt: iso(-12 * day),
    author: USERS.aline,
    tags: ["prd"],
    body: `# PRD — Aderência de planos

Monitora beneficiários sem check-up recente e dispara lembrete personalizado.

## Comportamento

- Mensal, dia 1 às 9h (processo \`aderencia_planos_monthly\`).
- Query em \`bq.beneficiarios.aderencia_v1\`.
- Lembrete por canal preferido do beneficiário (whatsapp / email / SMS).

## Sucesso

- ≥ 30% dos beneficiários lembrados agendam check-up em 30 dias.
`,
    links: [
      { kind: "agent", id: "aderencia_planos", label: "aderencia_planos" },
      { kind: "process", id: "pr_007", label: "aderencia_planos_monthly" },
    ],
  },
  {
    id: "produto/reembolso-classifier-prd.md",
    kind: "file",
    name: "PRD — Reembolso classifier",
    path: "produto/reembolso-classifier-prd.md",
    parentPath: "produto",
    updatedAt: iso(-2 * day),
    author: USERS.sofia,
    tags: ["prd", "wip"],
    body: `# PRD — Classifier de reembolso (WIP)

Em fase de plano (mission \`m_004\`). Classifica pedidos da fila Ksenia em:
\`auto_aprovar\` / \`pedir_doc\` / \`escalar\`.

## Pendências

- Definir approver de exceções (Aline ou Rafa?).
- Limite em R$ acima do qual escala sempre.
- Documentar política em \`governanca/aprovacao-de-excecoes.md\`.
`,
    links: [{ kind: "mission", id: "m_004", label: "m_004" }],
  },

  // ────────────────────── GOVERNANÇA ──────────────────────
  {
    id: "governanca/lgpd-checklist.md",
    kind: "file",
    name: "LGPD — checklist",
    path: "governanca/lgpd-checklist.md",
    parentPath: "governanca",
    updatedAt: iso(-15 * day),
    author: USERS.estevao,
    tags: ["lgpd", "compliance"],
    body: `# LGPD — checklist para nova mission

Antes de aprovar uma mission que toque dado pessoal:

- [ ] Skills usadas estão marcadas com sensitivity tag \`pii\` ou \`clinical_data\`?
- [ ] Há finalidade clara documentada no plano?
- [ ] Base legal identificada (consentimento, contrato, legítimo interesse)?
- [ ] Dual-control ativado (aprovador ≠ autor)?
- [ ] Retenção definida e refletida no \`audit_archive_to_bq\`?
- [ ] Direito ao esquecimento implementável (delete em ≤ 30d)?
`,
    links: [],
  },
  {
    id: "governanca/dual-control-quando-aplica.md",
    kind: "file",
    name: "Dual-control — quando aplica",
    path: "governanca/dual-control-quando-aplica.md",
    parentPath: "governanca",
    updatedAt: iso(-20 * day),
    author: USERS.sofia,
    tags: ["compliance"],
    body: `# Dual-control — quando aplica

## Regra

Se a mission requer qualquer skill com sensitivity tag em
\`{clinical_data, pii, financial}\`, o autor do plano **não pode ser** o
aprovador.

## Aplicação técnica

Vive em \`src/xenia/missions/policy.py\`:

\`\`\`python
def can_approve_plan(user, plan):
    sensitive = any(
        "clinical_data" in s.tags or "pii" in s.tags
        for s in plan.required_skills
    )
    if sensitive and user.id == plan.mission.created_by:
        return Deny("dual-control: author cannot approve sensitive missions")
    return Allow()
\`\`\`

## Auditoria

Toda decisão (allow/deny) vai para \`policy_decisions\` (append-only).
`,
    links: [
      { kind: "skill", id: "gmail.read", label: "gmail.read" },
      { kind: "skill", id: "ksenia.reembolso_fila", label: "ksenia.reembolso_fila" },
    ],
  },
  {
    id: "governanca/aprovacao-de-excecoes.md",
    kind: "file",
    name: "Aprovação de exceções — política",
    path: "governanca/aprovacao-de-excecoes.md",
    parentPath: "governanca",
    updatedAt: iso(-1 * day),
    author: USERS.rafa,
    tags: ["politica"],
    body: `# Aprovação de exceções

## Quando precisa de aprovação humana?

Toda mission tem zero ou mais \`approval_points\` definidos no plano.
Tipicamente:

- Decisão classificatória com confidence < 0.6.
- Skill \`gmail.draft\` (nunca envia sem human-in-the-loop).
- Pedido de reembolso > R$ 500.
- Promoção de versão de agente para produção.

## SLA por papel

- \`pm\`: 24h.
- \`approver\`: 4h (skills sensíveis).
- \`admin\`: 1h (promoção de versão).

Aprovação expirou? Mission entra em estado \`paused\` e pinga 2 níveis
acima na hierarquia.
`,
    links: [{ kind: "process", id: "pr_006", label: "approval_sla_check" }],
  },
  {
    id: "governanca/retencao-audit.md",
    kind: "file",
    name: "Retenção de audit log",
    path: "governanca/retencao-audit.md",
    parentPath: "governanca",
    updatedAt: iso(-25 * day),
    author: USERS.estevao,
    tags: ["compliance"],
    body: `# Retenção de audit log

| Camada | Período | Storage |
|--------|---------|---------|
| Hot    | 365 dias | Postgres (mission_approvals, policy_decisions) |
| Archived | 3 anos | BigQuery (\`audit_archive.*\`) |

Atende exigências de auditoria de saúde (ANS) + LGPD.

Processo de arquivamento: \`pr_005\` (\`audit_archive_to_bq\`) diariamente
às 3h.
`,
    links: [{ kind: "process", id: "pr_005", label: "audit_archive_to_bq" }],
  },

  // ────────────────────── ONBOARDING ──────────────────────
  {
    id: "onboarding/como-criar-uma-mission.md",
    kind: "file",
    name: "Como criar uma mission",
    path: "onboarding/como-criar-uma-mission.md",
    parentPath: "onboarding",
    updatedAt: iso(-1 * day),
    author: USERS.sofia,
    tags: ["onboarding"],
    body: `# Como criar uma mission

> Para PMs novas na plataforma.

## Passos

1. No Kanban, clique **Nova missão** (canto superior direito).
2. Escreva sua **intent** em linguagem natural — quanto mais específica,
   melhor o plano.
3. Clique **Gerar plano com Planner**.
4. O Planner roda em ~30–60s. Você verá o card mover para coluna
   *Plano em desenho*.
5. Se o Planner pedir follow-up, responda no comentário do card.
6. Quando o plano está pronto (\`confidence ≥ 0.7\`), o card vai para
   *Plano em aprovação*.
7. Revise as 5 abas (especialmente Plano e Custo). Aprove se ok.
8. Mission entra em *Em execução*. Acompanhe pelo Kanban.

## Exemplo de boa intent

> "A cada email novo na caixa \`comercial@axenya.com.br\`, classificar em
> FAQ / lead-novo / suporte-cliente. Para FAQ, redigir resposta com template
> e enfileirar para minha aprovação. Para os outros, encaminhar."

## O que NÃO funciona

- "Faz tudo do comercial pra mim." — vago demais.
- "Substitui o Mariano." — fora do escopo.
- "Liga para o cliente." — não temos skill de voz.
`,
    links: [{ kind: "agent", id: "planner", label: "planner" }],
  },
  {
    id: "onboarding/glossario-xenia.md",
    kind: "file",
    name: "Glossário Xenia",
    path: "onboarding/glossario-xenia.md",
    parentPath: "onboarding",
    updatedAt: iso(-1 * day),
    author: USERS.sofia,
    tags: ["onboarding"],
    body: `# Glossário Xenia

| Termo | Significado |
|-------|-------------|
| **Mission** | Card no Kanban. Uma unidade de trabalho com plano, execução e métricas. |
| **Agent** | Configuração versionada (prompt + skills + modelo) executável. |
| **Skill** | Capability que o agente pode invocar (HubSpot, Slack, Gmail, BQ, etc.). |
| **Plan** | Output do Planner: escopo, fluxo, evals, custo, riscos. Versionado. |
| **Process** | Cron que dispara missions/agents em horário definido. |
| **Run** | Uma execução individual de um agente. |
| **Drift** | Queda de qualidade detectada por eval suites em janela móvel. |
| **Approval point** | Gate humano definido no plano. |
| **Sensitivity tag** | Marcador de skill: \`pii\`, \`clinical_data\`, \`financial\`. Ativa dual-control. |
| **Dual-control** | Regra que impede autor de aprovar o próprio plano sensível. |
`,
    links: [],
  },
];

export const KNOWLEDGE_INDEX: Record<string, KnowledgeNode> = Object.fromEntries(
  KNOWLEDGE.map((n) => [n.path, n])
);
