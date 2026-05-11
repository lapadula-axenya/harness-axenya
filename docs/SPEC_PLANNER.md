# SPEC — Planner Agent

**Status:** Draft
**Autor:** Sophia Lapadula
**Última atualização:** 2026-05-10
**Branch:** `claude/define-platform-scope-hiLQm`
**Escopo:** O agente orquestrador que recebe intent do PM e produz o
plano que abastece o card no Kanban (Bloco D). Habilitador da
semana 2 da Fase 5.

> **Decisões assumidas (validar com Rafa antes do PR):**
> 1. Planner é **um agente**, não um serviço Python. Prompt versionado
>    em Langfuse Prompts, executado pelo harness existente.
> 2. Output sempre validado contra JSON Schema. Falha → re-prompt (até
>    2x) → falha definitiva → PM notificado para regerar manualmente.
> 3. Modelo default: Claude Sonnet 4.6 com fallback para Opus 4.7 em
>    casos de baixa confidence (escolhido pelo Planner em runtime).

---

## 1. Objetivo

Transformar **"Quero um agente que faça X"** (intent em texto livre)
em um **plano estruturado, executável e aprovável** em < 60s.

O plano é o contrato entre PM e a frota:
- PM aprova → execução é determinística e auditável.
- Validators usam o `eval_rubric` do plano.
- Mission Control mostra `cost_estimate` e marca alerta se a execução
  ultrapassa.
- Audit reconstroi "o que foi prometido" vs. "o que foi entregue".

**Não-objetivos (v1):**
- Planner que executa partes do plano (delega tudo aos workers).
- Auto-evolução: o Planner não atualiza seu próprio prompt.
- Plano em > 1 idioma. Português PT-BR.

---

## 2. Inputs e outputs

### 2.1 Input

```json
{
  "mission_id": "uuid",
  "intent": "string (texto livre do PM)",
  "context": {
    "workspace": "axenya",
    "author": { "id": "uuid", "name": "Sofia", "role": "pm" },
    "linked_missions": ["uuid", ...],
    "preferred_model": "claude-sonnet-4-6 | null"
  },
  "regen_reason": "string | null"
}
```

### 2.2 Output (JSON Schema resumido)

```yaml
title: MissionPlan
required: [version, scope, non_scope, flow_yaml, required_skills,
           eval_rubric, approval_points, cost_estimate, risks,
           confidence, planner_metadata]
properties:
  version: { type: integer, const: 1 }
  scope:           { type: string, minLength: 50, maxLength: 2000 }
  non_scope:       { type: array, items: { type: string }, minItems: 1 }
  flow_yaml:       { type: string }    # YAML válido contra graph schema
  required_skills:
    type: array
    items:
      type: object
      required: [name, exists_in_registry, sensitivity_tags, justification]
      properties:
        name: { type: string }              # 'gmail.read'
        exists_in_registry: { type: boolean }
        sensitivity_tags: { type: array, items: { type: string } }
        resource_filter: { type: object }   # ex.: {mailbox: 'aline@…'}
        justification: { type: string }
  eval_rubric:
    type: array
    items:
      type: object
      required: [id, kind, description, weight]
      properties:
        id: { type: string }
        kind: { enum: [deterministic, llm_judge] }
        description: { type: string }
        weight: { type: number, minimum: 0, maximum: 1 }
        config: { type: object }
  approval_points:
    type: array
    items:
      type: object
      required: [step, condition, approver_role]
      properties:
        step: { type: string }            # node name do graph
        condition: { type: string }       # ex.: 'score < 0.6'
        approver_role: { enum: [pm, approver, admin] }
        sla_hours: { type: integer }
  cost_estimate:
    required: [per_run_usd, monthly_estimate_usd, volume_assumption]
    properties:
      per_run_usd: { type: number }
      monthly_estimate_usd: { type: number }
      volume_assumption: { type: string }
  risks:
    type: array
    items:
      type: object
      required: [risk, mitigation, severity]
      properties:
        risk: { type: string }
        mitigation: { type: string }
        severity: { enum: [low, medium, high] }
  confidence: { type: number, minimum: 0, maximum: 1 }
  planner_metadata:
    required: [prompt_version, model, ms_elapsed, retries, follow_up_questions]
    properties:
      prompt_version: { type: string }
      model: { type: string }
      ms_elapsed: { type: integer }
      retries: { type: integer }
      follow_up_questions:
        type: array
        items: { type: string }
```

`flow_yaml` é validado contra `agents/_schema.json` (já existe).
Skills referenciadas em `flow_yaml` precisam existir em
`required_skills`.

### 2.3 Estados pós-geração

- `confidence >= 0.7` e `follow_up_questions = []`
  → mission vai para `plan_review`.
- `confidence < 0.7` **ou** tem follow-ups
  → mission **fica em `plan_drafting`**, follow-ups viram comentários
  no card e PM responde.
- Falha de validação 2x consecutivas → mission fica em `plan_drafting`
  com evento `planner_failed`, PM regenera com hint.

---

## 3. Estrutura do prompt

Prompt vive em Langfuse Prompts com slug `planner` e variáveis:
`{{intent}}`, `{{author_name}}`, `{{skills_catalog}}`,
`{{entities_catalog}}`, `{{example_plans}}`, `{{regen_reason}}`.

**Sistema (esboço):**

```
Você é o Planner da plataforma de agentes da Axenya. Transforma uma
intenção de produto em um plano executável.

REGRAS DURAS:
1. Não invente skills. Use só as listadas em SKILLS_CATALOG, ou
   marque exists_in_registry=false com justification clara.
2. Para skills com sensitivity_tags incluindo 'clinical_data' ou
   'pii', você DEVE incluir pelo menos 1 approval_point com
   approver_role="approver".
3. Toda eval_rubric tem pelo menos 1 item determinístico (não só
   LLM-as-judge).
4. Custo: assuma volume conservador (10x menor que o PM disser, se
   ele disser).
5. Risks: liste no mínimo 1 de cada categoria — técnico, LGPD,
   custo, dependência externa — ou justifique a ausência.
6. Se a intent for ambígua em > 2 dimensões críticas (quem aprova,
   qual fonte de dados, qual canal de output), defina confidence
   < 0.7 e devolva follow-up_questions.

ESTILO:
- Escopo: 5–10 bullets, voz ativa, em português PT-BR.
- Non-scope: explícito. Diga o que NÃO vai fazer.
- Flow YAML: comente em # quando uma escolha não for óbvia.

OUTPUT:
Responda apenas com o JSON do MissionPlan. Sem markdown, sem texto
antes/depois.
```

**Few-shot:** 3 planos canônicos (escritos à mão na semana 1) cobrindo:
1. Triagem de leads via webhook → HubSpot.
2. Leitura inbox Aline → classificação → notificação Slack.
3. Operação interna sem skills sensíveis (ex.: weekly report).

---

## 4. Pipeline de geração

```
PM cria mission (state=idea)
        │
        ▼
POST /missions/{id}/plan/generate
        │
        ▼
state → plan_drafting
        │
        ▼
PlannerJob (Celery):
  1. Carrega skills_catalog + entities_catalog (cached, TTL 5min).
  2. Renderiza prompt via Langfuse Prompts (versão pinned).
  3. Chama LLM (Sonnet 4.6) via OmniRouter.
  4. Parse JSON; valida contra schema.
     - Falha → re-prompt com erro específico (até 2x).
  5. Valida cross-refs:
     - skills em flow_yaml ⊆ required_skills?
     - approver_role compatível com RBAC?
     - regra de sensitivity_tags → dual-control?
     - Falha → registra como follow_up_question, não como falha hard.
  6. INSERT mission_plans (version = next).
  7. Decide próximo estado:
     - confidence >= 0.7 e !follow_ups → POST /transition → plan_review.
     - else → mantém plan_drafting + posta comentários.
  8. Publica mission_events para WebSocket atualizar card.
```

**Idempotência:** `POST /plan/generate` aceita
`Idempotency-Key: <hash do intent>`. Repeat dentro de 5min retorna o
plano existente em vez de regerar (evita custo + race).

**Cancelamento:** se PM muda intent enquanto Planner roda, job atual
é marcado `superseded` no Celery; output descartado.

---

## 5. Skills catalog e entities catalog

São inputs do prompt, mas merecem governança própria.

### 5.1 `skills_catalog` (gerado a partir de DB)

```json
[
  {
    "name": "gmail.read",
    "description": "Lê mensagens não-lidas de uma mailbox.",
    "input_schema": { ... },
    "output_schema": { ... },
    "sensitivity_tags": ["pii"],
    "cost_hint": "$0.001 per call (API gratuita; cost = LLM downstream)"
  },
  ...
]
```

Catalog é cacheado em Redis (TTL 5min). Quando admin adiciona skill
nova, invalidação ativa.

### 5.2 `entities_catalog` (do Bloco G, parcial)

Mesmo se Bloco G full não estiver pronto, expomos uma lista enxuta
(Cliente, Beneficiário, Empresa) com descrição e nível de
sensibilidade. Planner referencia em `risks` quando entidade clínica
é tocada.

---

## 6. Self-evaluation do Planner (golden tests)

O risco maior é "plano vago/ruim". Mitigação:

### 6.1 Golden set (semana 1)

10 intents canônicos, cada um com plano "gold" escrito à mão. Suite:

```bash
xenia planner eval --golden golden_intents/ --prompt-version v1
```

Métricas:
- **Schema validity rate** (target 100%).
- **Skill grounding** (skills do plano existem no registry — target 100%).
- **Plan quality score** (LLM-as-judge comparando vs. gold; target ≥ 0.75).
- **Confidence calibration** (planos com confidence 0.7+ devem ter quality 0.7+; correlação > 0.5).
- **Cost overrun** (custo executado vs. cost_estimate — target ≤ 1.5x na média).

Suite roda em CI a cada mudança de prompt + diariamente em produção
com sample dos planos do dia.

### 6.2 Drift detection

Quality score do Planner caindo > 10% em janela de 7 dias → alerta
no Slack + bloqueia promote de nova versão do prompt.

---

## 7. UX no Kanban

### 7.1 Durante `plan_drafting`

Card mostra spinner + texto live: "Planner está rascunhando o plano…
(15s)". WebSocket recebe progresso.

Se Planner faz follow-up:
- Comentário no card: "🤖 Planner: quem aprova exceções neste fluxo?
  Aline ou o time comercial?"
- PM responde via comentário; ao submeter, Planner regenera com
  contexto adicional. Custo desse re-prompt é contabilizado.

### 7.2 Em `plan_review`

Card mostra plano renderizado em markdown amigável. Não mostra JSON
cru (mas tem botão "ver JSON" para eng).

Botões:
- **Aprovar** (com motivo opcional).
- **Pedir alterações** (motivo obrigatório → volta para drafting).
- **Rejeitar** (motivo obrigatório → archived).
- **Regenerar com modelo mais forte** (Opus, custo informado antes).

### 7.3 Diff entre versões do plano

Se PM pede alterações N vezes, `mission_plans.version` incrementa.
UI mostra dropdown de versões + diff visual (escopo, fluxo, custo).

---

## 8. Custo e budget

Planner consome tokens. Para evitar runaway:
- Budget default por workspace: 100 plan generations/dia (configurável).
- Excedeu → próximas gerações em fila (não bloqueia missions já criadas).
- Custo médio esperado: $0.05–0.15 por plano. Monitorado em
  `policy_decisions` + Langfuse.

---

## 9. Plano de implementação (Fase 5 semana 2)

5 dias úteis, 1 BE com input de Sofia (prompt design).

**Dia 1:** JSON Schema do MissionPlan + validadores + 3 golden plans.
**Dia 2:** Prompt v1 em Langfuse + few-shot + skills_catalog endpoint.
**Dia 3:** PlannerJob (Celery) + retry/re-prompt + cross-ref validation.
**Dia 4:** Cancellation, follow-up loop, comment integration com Bloco D.
**Dia 5:** Eval CLI + golden suite + cost tracking.

---

## 10. Riscos

| Risco | Mitigação |
|-------|-----------|
| Planner alucina skill que não existe | Validação cross-ref hard fail → re-prompt com erro |
| Plano "passa do schema" mas é vago | LLM-as-judge gating na fase de review; PM sempre é último gate |
| Custo explode em workspace caótico | Budget diário + alerta a 80% |
| PM aprova plano ruim por inércia | Confidence < 0.7 desabilita botão Aprovar até follow-ups responderem |
| Skill registry desincronizado com Planner | Invalidação Redis + check em runtime ("skill not found") |
| Few-shot leak: planos enviesados pelos exemplos | Rotação trimestral dos golden + tracking de drift |
| Prompt injection via `intent` do PM | Sanitização básica + sandboxing (intent é dado, não instrução); follow-ups passam pelo mesmo filtro |

---

## 11. Open questions para o PR

1. Vale rodar **shadow Planner** (Opus em paralelo a Sonnet) e
   mostrar diff para PMs como aprendizado de plataforma? (Sugestão:
   sim, semana 3 do roll-out, só em workspaces beta.)
2. Planner deve sugerir **eval rubric vs. usar template** por tipo
   de mission? (Sugestão: sugerir, mas oferecer templates como
   few-shot.)
3. Plan locking: depois de aprovado, pode editar plan? (Sugestão:
   **não** — só criar nova versão; aprovação não-retroativa.)
4. Múltiplos Planners por workspace (ex.: Planner-Clínico,
   Planner-Comercial com prompts diferentes)? (Sugestão: **não** v1.
   Avaliar quando o golden set divergir muito por vertical.)
