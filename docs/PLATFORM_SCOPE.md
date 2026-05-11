# Axenya Agent Platform — Escopo Consolidado

**Status:** Draft v2 (pivot de eng-tool → PM-tool)
**Autores:** Sophia Lapadula (PM/Eng), com inputs de Rafa Magalhães
**Última atualização:** 2026-05-10
**Branch:** `claude/define-platform-scope-hiLQm`

---

## 1. Tese (revisada)

A virada conceitual: a plataforma **não é um painel de operação de
engenharia**. É uma **ferramenta para pessoas de produto entregarem
produtos e melhorias do zero — aprovando um plano**.

> PM escreve uma intenção em linguagem natural →
> agente orquestrador propõe um plano (escopo, fluxo, evals, riscos) →
> PM aprova →
> a frota de agentes executa, com aprovação humana só nos pontos certos →
> o trabalho aparece como **thread em um kanban**, do "Backlog" ao "Em
> produção", visível para o time todo.

A consequência prática é que **kanban é a surface principal**, não um
dashboard de traces. Traces, evals e logs continuam existindo como
*drill-down* a partir do card, mas a vida do PM acontece no quadro.

A camada técnica (harness, queue, executor, fallback, prompt registry)
permanece. O que muda é tudo acima dela: substituímos o "Mission
Control de eng" por um **Kanban de Missões** com semântica de produto.

---

## 2. Princípios de design (atualizados)

1. **Plano antes de execução.** Nada começa a executar sem um plano
   escrito e aprovado. Plano é o "contrato de validação" da Factory,
   adaptado para produto: escopo, critérios de sucesso, fluxo de
   agentes, skills/dados necessários, custo estimado, pontos de
   aprovação humana.
2. **Kanban como fonte da verdade operacional.** Toda thread (mission)
   é um card. Mover card = mudar estado. PMs vivem aqui.
3. **PM-first, eng-rare.** PM cria, aprova e acompanha sem abrir
   código. Eng só entra quando o agente orquestrador identifica que
   precisa de skill nova, integração nova ou política de acesso nova.
4. **Simples > completo.** A versão 1 entrega valor com 5 colunas e
   um agente orquestrador competente. Não vamos construir n8n visual
   nem org chart de Tess.ai já. Cortamos escopo agressivamente.
5. **Lógica em prompts/skills, não em state machines.** Mantém-se da
   v1 — orquestração mora em texto versionado.
6. **Tudo auditável.** 100% das chamadas + 100% das aprovações com
   quem/quando/motivo. Sem isso não vendemos para saúde.

---

## 3. UX central: Kanban de Missões

### Colunas (default, configurável por workspace)

```
┌──────────┬──────────┬──────────┬─────────────┬────────────┬──────────┐
│  Ideia   │ Plano em │ Plano    │  Em         │  Validação │  Em      │
│          │ desenho  │ aprovação│  execução   │  / QA      │  produção│
└──────────┴──────────┴──────────┴─────────────┴────────────┴──────────┘
                                                                  │
                                                            (Pausada)
                                                            (Arquivada)
```

- **Ideia:** PM escreveu o intent em linguagem natural. Ainda sem
  plano.
- **Plano em desenho:** agente orquestrador está rascunhando o plano
  (ele é um agente, com prompt versionado em Langfuse). Pode pedir
  esclarecimento ao PM via comentário no card.
- **Plano em aprovação:** plano completo, aguardando OK do PM (ou de
  um aprovador, conforme política — bloco A/Identity).
- **Em execução:** workers rodando. Heartbeat e custo em tempo real
  no card.
- **Validação/QA:** validators rodando (evals automáticos + checagem
  humana se o plano exigir).
- **Em produção:** entregue. Telemetria contínua. Drift abre card
  automático de "investigar regressão".

### Anatomia do card (mission)

Cada card abre para um detalhe com 5 abas:
1. **Plano** — o documento aprovado. Versionado. Diff visível.
2. **Execução** — timeline de eventos (drill-down do harness atual).
3. **Aprovações** — fila de approvals desta mission, com quem/motivo.
4. **Evals** — scores das suites rodadas, comparado à baseline.
5. **Custo** — $/run, tokens, modelo usado, fallbacks acionados.

### Eventos que mexem o card automaticamente

- Plano gerado → "Plano em desenho" → "Plano em aprovação".
- PM aprova → "Em execução".
- Validators passam → "Validação / QA" → "Em produção" (ou volta a
  "Em execução" se falhar).
- Drift detectado em prod → cria *novo* card "Investigar regressão
  em <mission>" na coluna "Plano em desenho".
- Approval pendente > SLA → card pisca + notifica Slack.

### O que **não** está no kanban (intencional)

- Configuração de skills/integrações (mora em config separada,
  acessada por eng).
- Tracing fino (mora no Langfuse, linkado a partir da aba Execução).
- Org chart de agentes estilo Tess (não construímos isso já).

---

## 4. O agente orquestrador ("Planner")

É a peça nova mais importante. Substitui o "PM escreve PRD".

**Input:** texto livre do PM ("Quero um agente que triagem leads que
chegam pela landing page e marque automaticamente no HubSpot, com
aprovação humana se score < 0.6").

**Output (= o plano):**
- **Escopo e não-escopo** em bullets curtos.
- **Fluxo proposto** (sequência de agentes/skills, formato YAML do
  harness — gerado, não escrito à mão).
- **Skills/dados necessários** com flag se já existem ou precisam
  ser construídos por eng.
- **Critérios de sucesso** (eval rubric — usados depois pelos
  validators).
- **Pontos de aprovação humana** explícitos.
- **Custo estimado** ($/run e $/mês com volume estimado).
- **Riscos e mitigation** (LGPD, vendor lock-in, dependência de
  skill nova).

**Comportamento:**
- Faz perguntas via comentário no card quando o intent é ambíguo
  (ex.: "Quem aprova exceções? Aline ou o time comercial?").
- Tem acesso *read-only* à context library (bloco G) para entender
  que entidades Axenya estão envolvidas.
- Tem prompt versionado em Langfuse Prompts. PM pode pedir "regerar
  com modelo X" ou "regerar mais conservador".

**É um agente, não código.** Isso significa que ele evolui com o
prompt + skills, não com release de software.

---

## 5. Mapa requisito × estado atual × gap (revisado)

| # | Requisito | Status | Gap | Coberto por |
|---|-----------|--------|-----|-------------|
| R1 | Versionamento do agente em prod | ✅ yaml_hash | Promote/rollback via UI; diff | Bloco B |
| R2 | Evals e drift | ❌ | Rubric + drift alert | Bloco C |
| R3 | Fallback de modelos | ⚠️ | Roteamento por custo/erro | Bloco E |
| R4 | Governança de acesso | ⚠️ | ACL agente×skill×recurso + SSO | Bloco A |
| R5 | Logs 100% | ✅ | Replay + diff | Bloco I |
| R6 | Aprovação + visibilidade | ❌ | **Kanban** + approval inbox | **Bloco D (novo)** |
| R7 | Heartbeat/drill-down | ⚠️ | Aba "Execução" do card | Bloco D |
| R8 | Queue + escala | ✅ | Load test + SLA | Bloco K |
| R9 | Slack como gatilho | ❌ | Slash + mention + approval inline | Bloco F |
| R10 | Fluxos versionáveis | ✅ | YAML gerado pelo Planner | Bloco D |
| R11 | Context library | ❌ | Ontologia + retrieval governado | Bloco G |
| R12 | Preview com mocks | ❌ | Sandbox por mission | Bloco H |
| R13 | Self-healing | ⚠️ | Drift abre card automático | Bloco C+D |
| R14 | Audit de approvals | ❌ | Append-only + motivo obrigatório | Bloco D |
| R15 | Prompt registry | ⚠️ | **Langfuse Prompts (buy)** | Bloco B |
| R16 | SSO + ACL | ❌ | Google SSO + RBAC | Bloco A |

---

## 6. Os 8 blocos de entrega (simplificado de 11 → 8)

Cortes vs. v1: removi "Visual Flow Editor" (Planner gera YAML, não
precisamos de n8n agora) e juntei "Replay" no bloco de evals. Mantive
foco em mínimo viável.

### Bloco A — Identity & Access **(R4, R16)**
SSO Google, RBAC (`viewer`/`pm`/`approver`/`admin`/`auditor`), ACL
fina `agente×skill×recurso`. Operador vê só os cards das missions
que opera.
**Aceite:** Aline aprova só missions dela; viewer vê o quadro mas
não move cards; agente sem permissão à skill `gmail.read` falha na
invocação.

### Bloco B — Prompt & Agent Registry **(R1, R15)**
**Buy: Langfuse Prompts** + thin wrapper para promote/rollback/diff.
Cada mission, ao "Em produção", *snapshot* a versão do agente +
versões dos prompts. Rollback < 30s.

### Bloco C — Evals + Drift + Replay **(R2, R5, R13)**
Rubric DSL escrita pelo Planner como parte do plano. Suites rodam
em CI da mission e em sample online. Drift > 2σ → cria card de
regressão automaticamente. Replay determinístico de qualquer run.

### Bloco D — Kanban de Missões **(R6, R7, R10, R14)** ⭐ **PEÇA CENTRAL**
Quadro Kanban com 5 colunas + Pausada/Arquivada. Card abre nas 5
abas (Plano/Execução/Aprovações/Evals/Custo). Approval inbox
filtrada por usuário. Audit log append-only (motivo obrigatório).
Drag-and-drop só onde a transição é permitida (estado-máquina por
trás). Real-time via WebSocket.

### Bloco E — Model Routing & Fallback **(R3)**
**Buy: LiteLLM proxy** + nossa policy layer (budget cap por
mission, circuit breaker por vendor, fallback ladder).

### Bloco F — Slack triggers **(R9)**
Slash `/xenia mission "intent"` cria card direto na coluna "Ideia".
Mentions criam comentário no card. Approvals via Block Kit, com
auth contra Bloco A.

### Bloco G — Context Library **(R11)**
Ontologia mínima v1: `Cliente`, `Beneficiário`, `Empresa cliente`,
`Apólice`. Retrieval governado por ACL do Bloco A. Expansão
incremental.

### Bloco H — Preview Sandbox **(R12)**
`xenia preview <mission>` roda em sandbox com fixtures
deterministic, skills externas mockadas. Output renderizado como
preview compartilhável dentro do card (aba Execução).

### Bloco K — Load test, SLA & Cost **(R8 finishing)**
Teste de carga 1000x, SLA por agente, painel de custo unitário
($/mission, $/cliente atendido). Continua sendo build sobre stack
existente.

---

## 7. Build vs Buy — recomendação

| Bloco | Decisão | Notas |
|-------|---------|-------|
| A. Identity | Build | SSO Google + casbin/oso |
| B. Prompt Registry | **Buy: Langfuse Prompts** ✅ | Confirmado |
| C. Evals + Drift + Replay | Build sobre Langfuse Datasets | Rubric DSL é nossa |
| D. **Kanban de Missões** | **Build (Next.js + shadcn + tRPC + WebSocket)** | É o coração — tem que ser nosso |
| E. Routing | **Buy: LiteLLM proxy** | Commodity |
| F. Slack | Build | Bolt SDK |
| G. Context Library | Build | É o moat |
| H. Preview Sandbox | Build | Específico do nosso executor |
| K. Load/SLA | Build | Stack já em pé |

**Decisões implícitas:**
- **Não** construímos visual flow editor (n8n-like) na v1. Planner
  gera YAML; PM lê o plano em markdown, não em diagrama. Reavaliamos
  em 6 meses.
- **Não** construímos org chart de agentes estilo Tess. Lista por
  workspace basta na v1.
- Streamlit atual é **arquivado** assim que o Bloco D entra.

---

## 8. Fases revisadas (foco em simplicidade)

### Fase 5 — Fundação PM (5 semanas)
**Blocos A + B + D (mínimo: kanban com 5 colunas, sem WebSocket,
approvals manuais sem Slack inline) + Planner v1.**
**Exit:**
- PM cria mission via UI ("Ideia") → Planner gera plano → PM
  aprova → harness executa → card chega em "Em produção".
- SSO Google obrigatório; rollback de versão funciona.
- *Demo:* Sofia migra um agente que hoje roda na GUI individual
  para a plataforma, **sem escrever código**.

### Fase 6 — Confiabilidade (4 semanas)
**Blocos C + I (replay como parte de C) + F.**
**Exit:**
- Cada mission em prod tem suite de eval rodando; drift abre card.
- PM invoca/aprova mission do Slack.
- Replay funciona para audit pós-incidente.

### Fase 7 — Robustez (3 semanas)
**Blocos E + K + G (parcial: 2 entidades core).**
**Exit:** fallback automático multi-vendor; SLA monitorado;
primeiras entidades Axenya na biblioteca compartilhada.

### Fase 8 — Não-eng creators (3 semanas)
**Blocos H + G (full) + Planner v2 (mais autônomo, melhor com
ambiguidade).**
**Exit:** Aline cria uma mission do zero (texto → plano → aprovação
→ produção) em < 1 dia, sem intervenção de eng.

**Total:** ~15 semanas (-2 vs. v1) com 2 engs dedicados. O corte vem
de descartar visual flow editor e simplificar Mission Control →
Kanban.

---

## 9. O que precisa de você (Rafa)

1. **Confirmar a virada PM-first.** Tudo neste doc assume que o
   sucesso da v1 é "Sofia migra um agente sem código", não "eng tem
   melhor visibility de traces".
2. **Definir as 5 colunas default.** Eu propus
   Ideia / Plano em desenho / Plano em aprovação / Em execução /
   Validação / Em produção. Trocar?
3. **Política de aprovação por default:** o autor da mission pode
   aprovar o próprio plano? Eu sugiro **não** para qualquer mission
   com skill que toque dado clínico ou paciente — exige segundo
   approver. Configurável por workspace.
4. **Naming:** "Mission" vs. "Thread" vs. "Iniciativa" vs.
   "Workstream"? Você usou "thread" na mensagem; mantenho?
5. **Planner como buy ou build?** Buildar em cima de Claude com
   prompt versionado é o caminho rápido (1–2 semanas). Tem
   alternativa pronta que eu não enxergo?

---

## 10. Out of scope (explícito)

- Visual flow editor estilo n8n.
- Org chart de agentes estilo Tess.ai.
- Multi-tenant para clientes externos.
- Treinamento/fine-tuning próprio.
- Marketplace público de agentes.
- Mobile app nativo (web responsive + Slack bastam).
- Substituir BigQuery como source of truth clínico.

---

## 11. Próximos passos concretos

1. **Você (Rafa):** validar virada PM-first; responder seção 9.
2. **Sofia:** spike 1 semana — protótipo Figma do Kanban + fluxo
   "criar mission → aprovar plano → ver em prod".
3. **Sofia:** SPEC técnico do Bloco A (SSO + ACL) e do Bloco D
   (Kanban + estado-máquina das colunas).
4. **Sofia + Estevão:** contratar Langfuse Cloud (ou self-host) +
   LiteLLM hosting.
5. **Sofia:** desenhar prompt do Planner v1 + 3 missions canônicas
   pra testar (1 lead triagem, 1 email Aline, 1 ops interna).
