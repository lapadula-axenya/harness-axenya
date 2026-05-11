# PRD — Xenia / Axenya Agent Platform

**Status:** Draft v1
**Autor:** Sophia Lapadula (PM/Eng)
**Última atualização:** 2026-05-11
**Repo:** `lapadula-axenya/harness-axenya`
**Branch deste PRD:** `claude/create-project-prd-rD00p`
**Documentos-fonte:** `SPEC.md`, `docs/PLATFORM_SCOPE.md`, `docs/SPEC_BLOCK_D_KANBAN.md`, `docs/SPEC_BLOCK_A_IDENTITY.md`, `docs/SPEC_PLANNER.md`

---

## 1. Resumo executivo (TL;DR)

A Axenya está construindo o **Xenia** — uma plataforma cloud-native interna para criar, aprovar, executar e auditar **agentes autônomos** que substituem trabalho manual repetitivo dentro da empresa (triagem de leads, leitura de inbox, ops internas, futuramente fluxos clínicos).

A virada conceitual recente é a mais importante: **deixamos de ser um "Mission Control de engenharia"** e passamos a ser uma **ferramenta PM-first** onde **pessoas de produto entregam produtos aprovando um plano** gerado por um agente orquestrador (Planner). A **surface principal é um Kanban de Missões**, não um dashboard de traces.

Hoje a base técnica (Fases 1–4) está em pé: harness, executor LangGraph + Celery, integrações MCP, deploy Cloud Run, observabilidade via Langfuse. O próximo arco (Fases 5–8, ~15 semanas) constrói a camada PM em cima dessa base.

> **Critério de sucesso da v1 (Fase 5):** "Sofia migra um agente que hoje roda na GUI individual para a plataforma, sem escrever código."

---

## 2. Problema

1. A Axenya quer adotar a tese de **"service-as-software"** — substituir trabalho repetitivo por agentes autônomos com outcomes mensuráveis.
2. **Não existe infraestrutura interna** para rodar agentes long-running, com estado, ativáveis por sistemas externos (HubSpot, Slack, Make, Ksenia). Cada nova automação vira projeto custom de DevOps.
3. **PMs não conseguem criar agentes sem engenharia.** O ciclo "ter ideia → entregar agente em prod" é hoje um projeto de software, não uma decisão de produto.
4. **Não há governança consolidada**: sem prompt registry, sem rubric de evals, sem audit de aprovações, sem ACL fina. Inviável para dado clínico ou paciente.
5. **Não há visibilidade compartilhada**: status de um agente vive em logs, não no lugar onde o time toma decisões.

---

## 3. Proposta

Construir uma plataforma cujo **fluxo central** é:

> PM escreve uma intenção em linguagem natural →
> o **Planner** (agente orquestrador) propõe um plano (escopo, fluxo, evals, riscos, custo) →
> PM aprova →
> a frota de agentes executa, com aprovação humana só nos pontos certos →
> o trabalho aparece como **thread em um Kanban**, do "Backlog" ao "Em produção", visível para o time todo.

**Princípios de design:**

1. **Plano antes de execução.** Nada roda sem plano escrito e aprovado.
2. **Kanban como fonte da verdade operacional.** Card = mission. Mover card = mudar estado.
3. **PM-first, eng-rare.** Eng só entra quando precisa de skill nova, integração nova, política de acesso nova.
4. **Simples > completo.** v1 entrega valor com 5 colunas e um Planner competente.
5. **Lógica em prompts/skills, não em state machines.** Orquestração mora em texto versionado.
6. **Tudo auditável.** 100% das chamadas + 100% das aprovações com quem/quando/motivo.

---

## 4. Usuários e personas

| Persona | Perfil | Necessidade central |
|--------|--------|---------------------|
| **PM (Sofia, Rafa)** | Cria intents, aprova planos, acompanha entrega | Criar agentes sem código; aprovar com contexto; ver status no Kanban |
| **Approver clínica (Aline)** | Médica/operacional que aprova quando há dado clínico/PII | Receber approval inbox filtrada; ver motivo + plano antes de aprovar |
| **Eng (Estevão & time)** | Constrói skills, integrações, fixa drift | Drill-down de traces, replay, registrar skills novas |
| **Auditor** | Compliance/financeiro | Ver audit log imutável; reconstruir o que foi prometido vs. entregue |
| **Viewer** | Time geral | Ver o quadro sem mover cards |

---

## 5. Surface: Kanban de Missões

### 5.1 Colunas (default, configurável por workspace)

```
Ideia → Plano em desenho → Plano em aprovação → Em execução → Validação/QA → Em produção
                                                                                │
                                                                  Pausada · Arquivada
```

- **Ideia:** PM escreveu o intent. Sem plano.
- **Plano em desenho:** Planner está rascunhando. Pode pedir esclarecimentos.
- **Plano em aprovação:** plano completo, aguardando OK do PM/approver.
- **Em execução:** workers rodando. Heartbeat e custo em tempo real no card.
- **Validação/QA:** validators rodando (evals + checagem humana, se exigido).
- **Em produção:** entregue. Telemetria contínua. Drift abre card novo de "Investigar regressão".

### 5.2 Anatomia do card (mission)

Cada card abre detalhe com 5 abas:
1. **Plano** — documento aprovado. Versionado. Diff entre versões.
2. **Execução** — timeline de eventos (drill-down do harness).
3. **Aprovações** — fila de approvals com quem/motivo.
4. **Evals** — scores das suites, comparado à baseline.
5. **Custo** — $/run, tokens, modelo, fallbacks.

### 5.3 Eventos automáticos
- Plano gerado → muda coluna.
- PM aprova → "Em execução".
- Validators passam → "Em produção".
- Drift em prod → cria card novo "Investigar regressão".
- Approval pendente > SLA → card pisca + ping no Slack.

### 5.4 Fora do Kanban (intencional)
- Configuração de skills/integrações (vive em config separada, acessada por eng).
- Tracing fino (vive no Langfuse, linkado via aba Execução).
- Org chart de agentes estilo Tess (não construímos).

---

## 6. O agente orquestrador — Planner

Substitui "PM escreve PRD". Recebe texto livre, produz um plano estruturado em < 60s.

**Output (campos obrigatórios do plano):**
- Escopo e não-escopo (bullets).
- Flow YAML (validado contra `agents/_schema.json`).
- Required skills (com `exists_in_registry`, `sensitivity_tags`).
- Eval rubric (mínimo 1 item determinístico + LLM-as-judge).
- Approval points (com `approver_role` e `sla_hours`).
- Cost estimate ($/run, $/mês, premissa de volume).
- Risks (mínimo 1 por categoria: técnico, LGPD, custo, dependência).
- Confidence (0–1) + follow-up questions.

**Comportamento:**
- Faz perguntas via comentário no card quando o intent é ambíguo.
- Read-only access à context library (Bloco G).
- Prompt versionado em Langfuse Prompts.
- Confidence < 0.7 ou follow-ups pendentes → mission **fica em `plan_drafting`** até PM responder.
- Validação cross-ref dura (skills do flow ⊆ required_skills; sensitivity → dual-control).
- Modelo default: Claude Sonnet 4.6, fallback Opus 4.7 em baixa confidence.

---

## 7. Estado atual do desenvolvimento

### 7.1 Linha do tempo executada

| Fase | Entrega | Status | Branch / PR |
|------|---------|--------|-------------|
| **1** | Harness mínimo viável: webhook HMAC, registry YAML, executor tool-use simples, mocks de skills, CRUD de runs em Postgres | ✅ feito | `claude/xenia-harness-spec-70U9J` |
| **2** | LangGraph + Celery worker + retry/cancel/retry endpoints | ✅ feito | `claude/xenia-harness-phase-2` |
| **3** | MCP transport + integrações reais (HubSpot, Slack, Atlassian, BigQuery whitelisted, Ksenia HTTP) | ✅ feito | `claude/xenia-harness-phase-3` |
| **4** | Produção: Cloud Run + Cloud SQL + Memorystore via Terraform, Langfuse traces, dashboard Streamlit interno, alertas | ✅ feito | `claude/xenia-harness-phase-4` |
| **Pivot** | Virada PM-first: PLATFORM_SCOPE consolidado + SPEC Bloco A (Identity) + SPEC Bloco D (Kanban) + SPEC Planner + Next.js scaffold do Kanban | ✅ specs + scaffold UI no main | `claude/define-platform-scope-hiLQm` |

### 7.2 O que já existe no repo hoje

- **Backend** (`src/xenia/`): API FastAPI, executor LangGraph, worker Celery, clients MCP, storage Postgres, observability Langfuse, security/HMAC, OmniRouter shim.
- **Agents** (`agents/`): registry YAML + schema + 2 agentes exemplo (`exemplo_eco`, `triagem_lead`).
- **Infra** (`infra/`): Terraform para Cloud Run + Cloud SQL + Memorystore.
- **Dashboard** (`dashboard/app.py`): Streamlit interno — **será arquivado quando Bloco D entrar em prod**.
- **Web** (`web/`): scaffold Next.js 16 + React 19 + shadcn/ui + dnd-kit + Tailwind v4 — UI inicial do Kanban (rotas `/missions`, `/agents`, `/access`, `/audit`, `/evals`, `/integrations`, `/prompt-library`, `/settings`, `/skills`), por enquanto com mock data.
- **Docs** (`docs/`): PLATFORM_SCOPE + specs técnicos de Bloco A, Bloco D, Planner + runbook.

### 7.3 O que está pendente (próximo arco — Fases 5–8)

Em ordem cronológica:

#### Fase 5 — Fundação PM (~5 semanas, 1 BE + 1 FE)
**Blocos A + B + D + Planner v1.**

- **Bloco A — Identity & Access:** SSO Google `@axenya.com.br`, RBAC 5 papéis (`viewer/pm/approver/admin/auditor`), ACL fina `agente×skill×recurso`, service accounts para webhooks, `policy_decisions` 100% auditadas com p99 < 5ms.
- **Bloco B — Prompt & Agent Registry:** **buy: Langfuse Prompts** + thin wrapper de promote/rollback/diff. Rollback < 30s. Snapshot de versão a cada promote para produção.
- **Bloco D — Kanban de Missões:** 4 tabelas (`missions`, `mission_plans`, `mission_approvals` imutável, `mission_events`), state machine, REST + WebSocket, frontend Next.js (`/board`, `/m/[id]`, `/audit`) com drag-and-drop e sync real-time.
- **Planner v1:** prompt versionado em Langfuse, 3 few-shots canônicos, golden suite de 10 intents, schema validation + cross-ref + re-prompt (até 2x), confidence + follow-ups, budget 100 plans/dia/workspace.

**Exit da Fase 5:** PM cria mission via UI → Planner gera plano → PM aprova → harness executa → card chega em "Em produção". SSO obrigatório. Rollback funciona. Sofia migra **1 agente real** sem código.

#### Fase 6 — Confiabilidade (~4 semanas)
**Blocos C + F (+ replay como parte de C).**

- **Bloco C — Evals + Drift + Replay:** rubric DSL gerada pelo Planner, suites em CI da mission + sample online, drift > 2σ abre card automático, replay determinístico de qualquer run.
- **Bloco F — Slack triggers:** `/xenia mission "intent"` cria card; mentions = comentário; approvals via Block Kit autenticando contra Bloco A.

**Exit:** cada mission em prod tem suite eval rodando; PM invoca/aprova do Slack; replay funciona para audit pós-incidente.

#### Fase 7 — Robustez (~3 semanas)
**Blocos E + K + G (parcial).**

- **Bloco E — Model Routing & Fallback:** **buy: LiteLLM proxy** + policy layer (budget cap, circuit breaker, fallback ladder).
- **Bloco K — Load test, SLA & Cost:** teste 1000×, SLA por agente, painel $/mission e $/cliente atendido.
- **Bloco G (parcial) — Context Library:** ontologia mínima v1 (`Cliente`, `Beneficiário`, `Empresa cliente`, `Apólice`).

**Exit:** fallback automático multi-vendor; SLA monitorado; primeiras entidades Axenya na biblioteca compartilhada.

#### Fase 8 — Non-eng creators (~3 semanas)
**Blocos H + G (full) + Planner v2.**

- **Bloco H — Preview Sandbox:** `xenia preview <mission>` com fixtures determinísticas, skills externas mockadas, output renderizado no card.
- **Planner v2:** mais autônomo, melhor com ambiguidade, possível shadow Planner (Opus em paralelo) em workspaces beta.

**Exit:** Aline cria mission do zero (texto → plano → aprovação → produção) em < 1 dia, sem intervenção de eng.

**Total restante:** ~15 semanas com 2 engs dedicados.

---

## 8. Requisitos × cobertura

| # | Requisito | Status | Coberto por |
|---|-----------|--------|-------------|
| R1 | Versionamento do agente em prod | ✅ `yaml_hash` | Bloco B |
| R2 | Evals e drift | ❌ Fase 6 | Bloco C |
| R3 | Fallback de modelos | ⚠️ stub | Bloco E |
| R4 | Governança de acesso | ⚠️ JWT grosso | Bloco A |
| R5 | Logs 100% | ✅ Langfuse | Bloco I (parte de C) |
| R6 | Aprovação + visibilidade | ❌ Fase 5 | **Bloco D** |
| R7 | Heartbeat/drill-down | ⚠️ Streamlit | Bloco D (aba Execução) |
| R8 | Queue + escala | ✅ Celery | Bloco K |
| R9 | Slack como gatilho | ❌ Fase 6 | Bloco F |
| R10 | Fluxos versionáveis | ✅ YAML | Bloco D + Planner |
| R11 | Context library | ❌ Fase 7 | Bloco G |
| R12 | Preview com mocks | ❌ Fase 8 | Bloco H |
| R13 | Self-healing | ⚠️ parcial | Bloco C + D |
| R14 | Audit de approvals | ❌ Fase 5 | Bloco D |
| R15 | Prompt registry | ⚠️ Langfuse direto | Bloco B (wrapper) |
| R16 | SSO + ACL | ❌ Fase 5 | Bloco A |

---

## 9. Build vs. Buy

| Bloco | Decisão | Notas |
|-------|---------|-------|
| A. Identity | **Build** | SSO Google + Oso (Polar) self-host |
| B. Prompt Registry | **Buy: Langfuse Prompts** ✅ | Confirmado |
| C. Evals + Drift + Replay | **Build sobre Langfuse Datasets** | Rubric DSL é nossa |
| **D. Kanban de Missões** | **Build (Next.js + shadcn + WebSocket)** | É o coração — tem que ser nosso |
| E. Routing | **Buy: LiteLLM proxy** | Commodity |
| F. Slack | **Build** | Bolt SDK |
| G. Context Library | **Build** | É o moat da Axenya |
| H. Preview Sandbox | **Build** | Específico do executor |
| K. Load/SLA | **Build** | Stack já em pé |

---

## 10. Out of scope (explícito)

- Visual flow editor estilo n8n. (Planner gera YAML; reavaliamos em 6 meses.)
- Org chart de agentes estilo Tess.ai.
- Multi-tenant para clientes externos.
- Treinamento/fine-tuning próprio.
- Marketplace público de agentes.
- Mobile app nativo (web responsivo + Slack bastam).
- Substituir BigQuery como source of truth clínico.

---

## 11. Métricas de sucesso

| Métrica | Target v1 (Fase 5) | Target v2 (Fase 8) |
|---------|--------------------|--------------------|
| Tempo PM-intent → mission em prod | < 1 semana com 1 toque de eng | < 1 dia sem eng |
| Agentes migrados da GUI individual | 1 | ≥ 5 |
| Planner: schema validity rate | 100% | 100% |
| Planner: plan quality score (LLM-judge vs. gold) | ≥ 0.75 | ≥ 0.85 |
| Planner: cost overrun executado vs. estimado | ≤ 1.5× médio | ≤ 1.2× médio |
| Approvals com motivo registrado | 100% | 100% |
| Rollback de versão | < 30s | < 30s |
| Latência de policy decision (Bloco A) | p99 < 5ms | p99 < 5ms |
| Drift detection → card de regressão | n/a (Fase 6) | < 24h |

---

## 12. Riscos principais

| Risco | Mitigação |
|-------|-----------|
| Planner gera plano vago/ruim | Golden suite + LLM-judge gating; PM é último gate; rejeitar é barato |
| Bloco A atrasa → app sem auth real | Stub local feature-flagged; **não promovemos a prod** sem Bloco A pronto |
| State machine permite transição inválida via race | Transações Postgres com `SELECT … FOR UPDATE` |
| Audit log corrompido | Trigger `no_mutate_approvals` + backup hourly em bucket WORM |
| Custo do Planner explode | Budget 100 plans/dia + alerta a 80% |
| WebSocket sobrecarrega backend | Limit 50 conexões/workspace + fallback polling 5s |
| Migração de 1 agente real revela gaps | Fase 5 é "infra do quadro", não "100% do agente". Gaps → backlog Fase 6 |

---

## 13. Open questions (para Rafa antes do PR final)

1. **Naming:** "Mission" vs. "Thread" vs. "Iniciativa" vs. "Workstream"? (Sugestão: **Mission**.)
2. **Colunas default:** as 5 colunas atuais fecham?
3. **Política de auto-aprovação:** autor pode aprovar próprio plano? Sugestão: **não** se mission tocar skill com tag `clinical_data` ou `pii`. Configurável por workspace.
4. **Planner como buy ou build?** Sugestão: **build** sobre Claude com prompt versionado (1–2 semanas).
5. **Múltiplos boards por workspace na v1?** Sugestão: **não**.
6. **Comentários em markdown ou texto plano?** Sugestão: **plano v1**, markdown v2.
7. **Retenção de `mission_events`:** sugestão hot 90d, archived para BigQuery > 90d, GDPR-style delete em ≤ 30d quando solicitado.
8. **Plan locking:** plano aprovado pode ser editado? Sugestão: **não** — só nova versão.

---

## 14. Próximos passos concretos

1. **Rafa:** validar virada PM-first; responder seção 13.
2. **Sofia:** spike 1 semana — protótipo Figma do Kanban + fluxo "criar mission → aprovar plano → ver em prod".
3. **Sofia + Estevão:** contratar Langfuse Cloud (ou self-host) + LiteLLM hosting.
4. **Sofia:** desenhar prompt do Planner v1 + 3 missions canônicas para testar (1 lead triagem, 1 email Aline, 1 ops interna).
5. **Time eng:** começar implementação Bloco A em paralelo ao Bloco D (Semana 1 da Fase 5).
