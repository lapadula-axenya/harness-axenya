# SPEC — Bloco D: Kanban de Missões

**Status:** Draft
**Autor:** Sophia Lapadula
**Última atualização:** 2026-05-10
**Branch:** `claude/define-platform-scope-hiLQm`
**Escopo:** Implementação técnica do Bloco D do
[PLATFORM_SCOPE.md](./PLATFORM_SCOPE.md). Cobre R6, R7, R10, R14.

> **Decisões assumidas (validar com Rafa antes do PR):**
> 1. Entidade chamada **Mission** (sinônimo coloquial: thread).
> 2. Autor **não pode** aprovar próprio plano se mission tocar skill
>    com tag `clinical_data` ou `pii`. Caso contrário, pode.
> 3. Planner é build sobre Claude + prompt versionado em Langfuse.

---

## 1. Objetivo

Entregar a UI e API de Kanban de Missões como surface principal da
plataforma. PM cria mission por intent → vê plano → aprova → acompanha
no quadro até "Em produção". Toda transição é auditável.

**Não-objetivos (v1):**
- Editor visual de fluxos (Planner gera YAML).
- Multi-board por workspace (1 board por workspace).
- Subtarefas/checklists dentro do card.
- Comentários com markdown rico (texto plano + menções).

---

## 2. Modelo de dados

### 2.1 `missions`

```sql
CREATE TABLE missions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id),
  title           TEXT NOT NULL,
  intent          TEXT NOT NULL,            -- texto livre do PM
  state           mission_state NOT NULL DEFAULT 'idea',
  created_by      UUID NOT NULL REFERENCES users(id),
  assignee_id     UUID REFERENCES users(id),
  priority        SMALLINT NOT NULL DEFAULT 2,  -- 0 hi, 1 med, 2 low
  plan_id         UUID REFERENCES mission_plans(id),
  current_run_id  UUID REFERENCES runs(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived_at     TIMESTAMPTZ
);

CREATE TYPE mission_state AS ENUM (
  'idea',
  'plan_drafting',
  'plan_review',
  'executing',
  'qa',
  'in_production',
  'paused',
  'archived'
);

CREATE INDEX missions_board_idx
  ON missions (workspace_id, state, priority, updated_at DESC)
  WHERE archived_at IS NULL;
```

### 2.2 `mission_plans` (versionado, append-only)

```sql
CREATE TABLE mission_plans (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id      UUID NOT NULL REFERENCES missions(id),
  version         INT NOT NULL,
  generated_by    TEXT NOT NULL,   -- "planner@v1.2.3"
  scope_md        TEXT NOT NULL,
  flow_yaml       TEXT NOT NULL,   -- LangGraph YAML gerado
  required_skills JSONB NOT NULL,  -- [{name, exists, sensitivity_tags}]
  eval_rubric     JSONB NOT NULL,
  approval_points JSONB NOT NULL,
  cost_estimate   JSONB NOT NULL,  -- {per_run_usd, monthly_estimate}
  risks_md        TEXT,
  status          plan_status NOT NULL DEFAULT 'draft',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (mission_id, version)
);

CREATE TYPE plan_status AS ENUM ('draft', 'pending', 'approved', 'rejected', 'superseded');
```

### 2.3 `mission_approvals` (audit imutável)

```sql
CREATE TABLE mission_approvals (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id      UUID NOT NULL REFERENCES missions(id),
  plan_id         UUID REFERENCES mission_plans(id),
  approval_type   approval_type NOT NULL,
  decision        approval_decision NOT NULL,
  decided_by      UUID NOT NULL REFERENCES users(id),
  reason          TEXT NOT NULL,    -- obrigatório
  decided_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE approval_type AS ENUM ('plan', 'execution_gate', 'production_promote');
CREATE TYPE approval_decision AS ENUM ('approved', 'rejected', 'changes_requested');

-- Nada de UPDATE/DELETE. Trigger:
CREATE TRIGGER no_mutate_approvals
  BEFORE UPDATE OR DELETE ON mission_approvals
  FOR EACH ROW EXECUTE FUNCTION raise_immutable_violation();
```

### 2.4 `mission_events` (timeline do card)

```sql
CREATE TABLE mission_events (
  id          BIGSERIAL PRIMARY KEY,
  mission_id  UUID NOT NULL REFERENCES missions(id),
  kind        TEXT NOT NULL,      -- 'state_change', 'plan_generated',
                                  -- 'comment', 'run_started', 'eval_failed'…
  actor_id    UUID REFERENCES users(id),  -- nullable para system events
  payload     JSONB NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX mission_events_card_idx ON mission_events (mission_id, id);
```

`runs` (já existente no harness) ganha FK opcional `mission_id`.

---

## 3. State machine

```
              ┌─────────┐
              │  idea   │ ── PM clica "gerar plano" ──┐
              └─────────┘                             │
                                                      ▼
                                             ┌──────────────┐
                                             │ plan_drafting│
                                             └──────────────┘
                                                      │
                                          plano pronto│
                                                      ▼
                                             ┌──────────────┐
                                  ┌──────────│  plan_review │
                                  │          └──────────────┘
                  changes_requested              │            │
                                  │       approved│           │ rejected
                                  ▼              ▼            ▼
                            (volta drafting)  ┌──────────┐  archived
                                              │executing │
                                              └──────────┘
                                                   │
                                  validators ok    │
                                                   ▼
                                              ┌─────┐
                                  ┌───────────│ qa  │
                                  │           └─────┘
                                  │              │
                                  │ qa fail      │ qa pass
                                  ▼              ▼
                              executing   ┌──────────────┐
                                          │ in_production│
                                          └──────────────┘
                                                  │
                                drift detectado   │
                                                  ▼
                              (cria nova mission "Investigar
                               regressão de <X>" em plan_drafting,
                               não move o card original)
```

**Pause/Archive** são transições laterais permitidas a partir de
qualquer estado (exceto `archived`).

**Implementação:** tabela `mission_state_transitions` (estática, em
código) define quais transições são válidas + qual papel (RBAC) pode
executar cada uma. Toda transição passa por `mission_state_machine.transition()`
que valida e grava `mission_events.kind='state_change'`.

---

## 4. Regras de aprovação

```python
# pseudocódigo — vive em src/xenia/missions/policy.py

def can_approve_plan(user: User, plan: MissionPlan) -> Decision:
    sensitive = any(
        "clinical_data" in s["sensitivity_tags"] or
        "pii" in s["sensitivity_tags"]
        for s in plan.required_skills
    )
    is_author = user.id == plan.mission.created_by

    if not has_role(user, ["pm", "approver", "admin"]):
        return Deny("missing role")

    if sensitive and is_author:
        return Deny("dual-control: author cannot approve clinical/pii missions")

    if not has_skill_acl(user, plan.required_skills):
        return Deny("user lacks ACL for one or more required skills")

    return Allow()
```

ACL é resolvida pelo Bloco A (Identity). Se Bloco A ainda não estiver
em produção quando este SPEC for implementado, stub com hardcoded
mapping em config — feature-flagged.

---

## 5. API

REST + WebSocket. JSON. Auth por bearer token (do Bloco A).

### REST (FastAPI, prefixo `/v1/missions`)

| Método | Path | Descrição |
|--------|------|-----------|
| `POST` | `/` | Criar mission (body: title, intent). Retorna em estado `idea`. |
| `GET`  | `/board` | Lista por colunas (state buckets). Query: `?workspace_id=`. |
| `GET`  | `/{id}` | Detalhe completo (mission + plan ativo + últimos 50 events + run atual). |
| `POST` | `/{id}/plan/generate` | Dispara Planner. Estado → `plan_drafting`. Idempotente por `Idempotency-Key`. |
| `POST` | `/{id}/plan/{plan_id}/approve` | Aprova plano. Body: `{reason}`. Estado → `executing`. |
| `POST` | `/{id}/plan/{plan_id}/reject` | Body: `{reason}`. Estado → `archived` ou `plan_drafting` se `request_changes=true`. |
| `POST` | `/{id}/transition` | Transição manual (pause/resume/archive). Body: `{to_state, reason}`. |
| `POST` | `/{id}/comment` | Adiciona comentário (vira `mission_events.kind='comment'`). |
| `GET`  | `/{id}/events` | Timeline paginada. |
| `GET`  | `/{id}/approvals` | Audit log da mission. |

### WebSocket

`GET /v1/missions/board/ws?workspace_id=…`
Broadcast de `mission_events` (filtrados por ACL do user) para
sincronizar Kanban em tempo real entre operadores. Backpressure: se
cliente fica > 30s atrás, server fecha e força refetch.

---

## 6. Frontend

**Stack:** Next.js 15 (App Router) + React 19 + TanStack Query +
shadcn/ui + dnd-kit para drag-and-drop. Auth via NextAuth com Google
provider (compartilha sessão com o backend via JWT).

**Páginas v1:**
- `/board` — Kanban (1 por workspace).
- `/m/[id]` — detalhe da mission (modal sobreposto ao board, com URL
  shareable; também acessível em página cheia).
- `/audit` — visão de auditor (read-only) com filtros por
  período/usuário/mission.

**Comportamento drag-and-drop:**
- Cliente otimista marca o card como "moving"; envia `POST /transition`;
  rollback visual se backend rejeitar (ex.: estado-máquina não permite,
  ou usuário não tem role).
- WebSocket recebe `state_change` de outros usuários e reposiciona
  cards em tempo real.

**Card collapsed (no quadro):** título, prioridade (cor),
assignee avatar, custo acumulado, idade na coluna atual, badge se
tem approval pendente.

**Card expanded (modal):** 5 abas conforme PLATFORM_SCOPE seção 3.

---

## 7. Integração com o harness existente

- `runs.mission_id` (FK nova) liga execuções ao card.
- Quando estado muda para `executing`, API enfileira run via Celery
  (já existe). Run usa `flow_yaml` do plano aprovado.
- `run_events` continuam como estão; agregamos no card via
  `mission_events.kind='run_event_summary'` a cada N eventos
  (evita inflar timeline do card).
- Langfuse trace recebe `mission_id` como tag → drill-down do card
  para Langfuse via link.

---

## 8. Observabilidade

Métricas Prometheus:
- `missions_state_total{state, workspace}` (gauge).
- `mission_state_transition_seconds{from, to}` (histogram — tempo na
  coluna).
- `mission_approval_pending_seconds` (gauge — alerta se > SLA).
- `mission_plan_generation_seconds`.
- `mission_drift_alerts_total` (counter).

Alertas (Phase 6, mas hooks já no SPEC):
- Approval pendente > 4h → ping no Slack do approver.
- Mission em `executing` > 24h sem progresso → alerta no quadro.

---

## 9. Plano de implementação (Fase 5)

5 semanas, 1 eng FE + 1 eng BE.

**Semana 1 — schema + API básica**
- Migrations das 4 tabelas + state machine em código.
- Endpoints `POST /missions`, `GET /board`, `GET /{id}`, `POST /transition`.
- Testes de unidade da state machine (cobertura 100% das transições).

**Semana 2 — Planner v1**
- Prompt do Planner em Langfuse (versão 1).
- Endpoint `POST /plan/generate` chama Planner via harness.
- Output do Planner valida contra JSON Schema (rejeita se mal-formado).
- 3 missions canônicas usadas como golden test.

**Semana 3 — frontend Kanban**
- Página `/board` com 5 colunas, sem drag-and-drop ainda.
- Card collapsed + modal expanded (4 abas, sem Evals que vem em Fase 6).
- Comentários e timeline.

**Semana 4 — approvals + drag-and-drop + WebSocket**
- Endpoints de approve/reject + audit imutável.
- Drag-and-drop com state machine validation.
- WebSocket para sync real-time.

**Semana 5 — hardening**
- Integração com Bloco A (SSO + ACL).
- Auditor view.
- Load test (1k cards, 50 usuários simultâneos).
- Migração: 1 agente real (escolhido com Rafa) sai da GUI individual e
  vira mission em prod. **Esse é o critério de exit da Fase 5.**

---

## 10. Riscos

| Risco | Mitigação |
|-------|-----------|
| Planner gera plano ruim / vago | Golden tests + LLM-as-judge gating; PM sempre vê e aprova; rejeitar é barato |
| State machine permite transição inválida via race condition | Toda transição em transação Postgres com `SELECT … FOR UPDATE` na mission |
| Audit log corrompido ou apagável | Trigger `no_mutate_approvals` + backup hourly em bucket WORM |
| WebSocket sobrecarrega backend | Limit 50 conexões/workspace; fallback polling 5s |
| Bloco A atrasa → app sem auth real | Stub local feature-flagged; **não promovemos a prod** sem Bloco A pronto |
| Migração da Fase 5 (1 agente real) revela gaps | Escopo da Fase 5 é "infra do quadro", não "100% do que o agente faz". Gaps viram backlog de Fase 6 |

---

## 11. Open questions para o PR

1. Suportar múltiplos boards por workspace na v1? (sugestão: **não**.)
2. Comentários em markdown ou texto plano? (sugestão: **plano** v1, markdown v2.)
3. Política de retenção de `mission_events`? (sugestão: hot 90d, archived
   para BigQuery por > 90d, GDPR-style delete em ≤ 30d quando solicitado.)
