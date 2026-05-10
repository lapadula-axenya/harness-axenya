# Axenya Agent Platform — Escopo Consolidado

**Status:** Draft para discussão
**Autores:** Sophia Lapadula (PM/Eng), com inputs de Rafa Magalhães
**Última atualização:** 2026-05-10
**Branch:** `claude/define-platform-scope-hiLQm`

---

## 1. Tese

Hoje rodamos agentes Claude na GUI individual de cada operador. Isso não é
infraestrutura — é experimentação. Para virar **infraestrutura crítica da
Axenya** (no nível em que órgãos de saúde podem auditar e clientes
enterprise podem confiar), precisamos atravessar a fronteira de:

> "agente que ajuda uma pessoa" → "frota de agentes que executa um processo
> da companhia, com SLA, audit trail e governança"

O Xenia Harness entregou ~50% disso: a **camada de infra** (queue, executor,
tracing, deploy, fluxos determinísticos via YAML) está pronta. O que falta é
a **camada de operação de frota** (evals, mission control, approvals
auditáveis, prompt registry, context library, drift detection, self-healing).

Este documento define o escopo dessa segunda metade.

---

## 2. Princípios de design

Inspirados no pitch da Factory ("Missions"), em Tess.ai e nas observações da
Sofia:

1. **Validação adversarial > confirmatória.** Critérios de sucesso são
   escritos *antes* da execução, por um agente/papel diferente do que
   executa. Aplica-se a código (creator/verifier) e a output operacional
   (eval rubric escrita pelo orquestrador, não pelo worker).
2. **Handoff via escrita de estado, não via context window.** Workers
   gravam o que fizeram, o que falhou, exit codes — o sistema não conta com
   memória implícita do LLM.
3. **Lógica em prompts/skills, não em state machines hard-coded.** Para
   sobreviver a saltos de fundação, ~70% da orquestração mora em texto
   versionado (prompts, rubricas, skills), não em código Python. Quando
   precisamos de determinismo (e.g. fluxos n8n-like), versionamos o grafo
   em YAML, não em Python.
4. **Serial > paralelo no ato de escrita.** Paralelismo é restrito a
   leituras (research, retrieval, verificações independentes).
5. **Custo é first-class.** Toda chamada tem owner, budget e fallback de
   modelo. "Modelo agnóstico" não é vaidade — é estratégia de leverage com
   vendors.
6. **Tudo auditável.** 100% das chamadas, com inputs/outputs/decisões/quem
   aprovou. Sem isso não vendemos para insurance/saúde.

---

## 3. Mapa requisito × estado atual × gap

| # | Requisito | Status no Harness | Gap concreto |
|---|-----------|------------------|--------------|
| R1 | Versionamento de agente em produção | ✅ `yaml_hash` + snapshot persistido por run | Rollback automático, diff entre versões, "promote v3 → prod" via UI/CLI |
| R2 | Evals e detecção de drift | ❌ | Rubric DSL, eval runner offline + online sample, dashboard de drift |
| R3 | Fallback de modelos (multi-vendor) | ⚠️ provider toggle por agente | Roteamento dinâmico por custo/erro/latência; circuit breaker por vendor |
| R4 | Governança fina de skills/dados por agente | ⚠️ JWT scopes para humanos | ACL agente → skill → recurso; policy engine; "só Aline pode operar este agente" |
| R5 | Logs 100% (audit/replay/iterate) | ✅ runs + run_events + Langfuse | Replay automatizado a partir de um run_id; diff de outputs ao reexecutar |
| R6 | Aprovação humana + Mission Control | ❌ stub | UI rica, fila de approvals, SLA timer, registro imutável de quem aprovou o quê |
| R7 | Heartbeat e drill-down | ⚠️ events + alerts | UI: linha do tempo de outputs intermediários, replay step-by-step |
| R8 | Enfileiramento e escala lateral | ✅ Celery + Redis + Cloud Run | Pronto. Falta só load test 1000x e definição de SLA por agente. |
| R9 | Slack como caller (gatilho, não só skill) | ❌ | Slash commands, mentions, Block Kit para approvals inline |
| R10 | Fluxos determinísticos versionáveis | ✅ LangGraph YAML | Editor visual (n8n-like), preview de execução, diff visual |
| R11 | Engenharia de contexto / "biblioteca" de entidades | ❌ | Ontologia Axenya (cliente, beneficiário, evento, broker…), retrieval governado |
| R12 | Preview env com dados mockados | ❌ | Sandbox por agente/mission, fixtures determinísticas, assertion suite |
| R13 | Self-healing | ⚠️ retry com backoff | Detecção autônoma de drift que abre ticket/aciona fallback |
| R14 | Audit de approvals (quem aprovou o quê, com motivo) | ❌ | Tabela imutável append-only, exportação para auditoria externa |
| R15 | Prompt registry com versionamento | ⚠️ yaml em git | Registry com promote/rollback, eval atrelado ao prompt, A/B holdout |
| R16 | SSO + identity + controle de acesso (ponto inicial do Rafa) | ❌ | Google Workspace SSO, RBAC, mapping user → agentes operáveis |

---

## 4. Os onze blocos de escopo

Cada bloco abaixo é uma unidade de entrega. Ordem reflete dependências e
risco, não prioridade de negócio (essa fica para o roadmap final).

### Bloco A — Identity & Access (R16, R4)
**O quê:**
- SSO via Google Workspace (`@axenya.com.br`).
- RBAC com papéis: `viewer`, `operator`, `approver`, `admin`, `auditor`.
- ACL fina: `user × agent × action` (operate, approve, view-traces, edit-config).
- Mapping `agent × skill × resource` (ex.: agente de Dra. Aline só lê
  inbox dela; só Aline + dois substitutos operam).
- Service accounts para webhooks externos com escopo restrito.

**Aceite:**
- Login por Google obrigatório no dashboard e na API humana.
- `xenia auth check --user X --agent Y --action operate` retorna
  decisão consistente.
- Agente sem permissão para skill `gmail.read` falha *na invocação da
  skill*, não só no roteamento.

**Build vs buy:** Build (thin layer sobre `authlib` + `casbin` ou
`oso`). Já temos JWT no harness; estender é barato.

---

### Bloco B — Prompt & Agent Registry (R1, R15)
**O quê:**
- Promote/rollback de versão de agente (`v1.2.3 → prod`, `prod → v1.2.2`).
- Diff visual entre versões (prompt, modelo, skills habilitadas, params).
- Cada versão amarrada ao seu eval result e custo médio observado.
- "Shadow mode": rodar v_next em paralelo a v_current sem expor output ao
  caller, para comparar.

**Aceite:**
- Promover uma versão é uma chamada idempotente, com audit log.
- Rollback < 30s.
- UI mostra `v1.2.3 (prod) | v1.2.4 (canary 5%) | v1.3.0 (shadow)`.

**Build vs buy:** Avaliar **MLflow Prompt Registry** (Sofia já está
testando) e **Langfuse Prompts**. Decisão: usar Langfuse Prompts como
storage + camada fina nossa de promote/rollback/ACL. Não construir do
zero.

---

### Bloco C — Eval Framework + Drift Detection (R2, R13)
**O quê:**
- DSL para rubrica de eval (assertions determinísticas + LLM-as-judge).
- Eval suites por agente: golden set offline + amostragem online (5–10%).
- Dashboard de drift: distribuição de scores ao longo do tempo, alerta
  quando score cai > 2σ ou cai > X% absoluto em janela móvel.
- Self-healing v0: drift detectado → abre ticket no Mission Control +
  bloqueia promote da versão atual.

**Aceite:**
- Cada agente tem ≥ 1 suite com ≥ 10 casos.
- Rodar `xenia eval run <agent> <version>` produz score + breakdown.
- Drift no agente de triagem dispara alerta em < 1h após começar.

**Build vs buy:** Langfuse cobre tracing + scores + dataset. Construir
nossa rubric DSL e o orquestrador de evals em cima. Não é compra.

---

### Bloco D — Mission Control UI (R6, R7, R14)
**O quê:** O dashboard que substitui o Streamlit atual.
- **Frota:** lista de agentes com heartbeat (último run, success rate 24h,
  custo dia, p95 latência).
- **Run inspector:** linha do tempo de eventos com drill-down em cada
  output intermediário (input, prompt expandido, response, tool calls,
  custo, modelo usado, fallback acionado).
- **Approval inbox:** approvals pendentes com SLA timer, contexto e botões
  Aprovar/Rejeitar/Pedir alteração — *com campo de motivo obrigatório*.
- **Audit log:** quem aprovou o quê, quando, com qual motivo. Imutável,
  append-only, exportável.

**Aceite:**
- Operador consegue ir de "alerta no Slack" → "estou olhando o passo 3 do
  run que falhou" em ≤ 2 cliques.
- Approver autenticado vê só approvals das frotas que opera.
- Audit log sobrevive a delete/edit em qualquer cenário não-DBA.

**Build vs buy:** Inicialmente avaliamos Mission Control (open-source,
mc.builderz.dev) e OpenHive. Recomendação: **fork/integrar com Mission
Control OSS** se a license permitir (MIT/Apache); senão construir Next.js
+ shadcn em cima dos endpoints do harness. **Não** ficamos no Streamlit.

---

### Bloco E — Model Routing & Fallback (R3)
**O quê:**
- Política de roteamento por agente: primary, fallback ladder, budget cap.
- Circuit breaker por vendor: 5xx > X% em N min → desvia tráfego.
- Routing por custo: tasks classificadas (raciocínio pesado vs.
  formatação) podem cair em modelos mais baratos automaticamente.
- Telemetria: custo por agente, por mission, por usuário operador.

**Aceite:**
- Anthropic 503 → próximo run usa Gemini/Claude via OpenRouter sem
  intervenção manual; Langfuse trace marca o switch.
- Budget mensal de agente excedido → bloqueia novas runs e alerta no
  Slack (não derruba runs em curso).

**Build vs buy:** Usar **OpenRouter** ou **LiteLLM proxy** como roteador
de fato. Construir só a camada de policy + budget tracking em cima. O
"OmniRouter" stub atual vira esse adapter.

---

### Bloco F — Slack como gatilho de primeira classe (R9)
**O quê:**
- Slash commands `/xenia run <agent> <args>`.
- Mentions em canal: `@xenia triagem este lead [link]`.
- Approvals inline com Block Kit (Aprovar/Rejeitar direto da mensagem,
  com auth contra Bloco A).
- DMs do bot como surface de mission control mobile.

**Aceite:**
- Aline aprova um exception case do celular dela em < 30s, sem abrir
  dashboard.
- Toda invocação Slack vira run rastreável com `caller=slack:U123`.

**Build vs buy:** Build. Slack Bolt SDK + endpoints existentes do
harness. Reaproveita Bloco A para autorização.

---

### Bloco G — Context Library & Entity Layer (R11)
**O quê:** O ponto que a Sofia levantou. Hoje cada agente é uma ilha.
- Ontologia Axenya: `Cliente`, `Beneficiário`, `Evento de saúde`,
  `Broker`, `Apólice`, `Empresa cliente`, etc. Schema versionado.
- Retrieval governado: agente declara `requires: [beneficiario:read]` e
  recebe acesso só ao subgrafo permitido.
- Caminho do dado: BigQuery (source of truth) → entity layer cacheado
  (Memorystore/Postgres) → retrieval skill MCP.
- Memória multi-camada à la Tess: organizacional / departamental /
  individual / por agente — mas com *governança real*, não só layering.

**Aceite:**
- Agente que precisa de "todos beneficiários da empresa X" recebe lista
  filtrada por LGPD scope.
- Adicionar uma nova entidade é uma migration, não um projeto.
- Retrieval traceado em Langfuse com query + linhas retornadas + cost.

**Build vs buy:** Build. É o nosso moat. Ferramentas externas (LlamaIndex,
LangChain memory) não vão entender "beneficiário Axenya".

---

### Bloco H — Preview Environments & Fixtures (R12)
**O quê:** Inspirado na fala da Sofia sobre Factory worker estruturando
preview com dados mockados.
- Por agente, fixture deterministic set (ex.: 5 leads canônicos, 3
  emails canônicos da Aline, etc.).
- `xenia preview <agent> --fixture lead_alta_complexidade` roda em
  sandbox, sem efeitos colaterais (skills externas viram mocks).
- Preview URL compartilhável para revisão visual (output renderizado,
  diff vs. baseline esperado).

**Aceite:**
- Mudança de prompt → operador roda preview → vê output em < 60s sem
  tocar prod.
- CI bloqueia merge se preview de agente regredir contra fixture.

**Build vs buy:** Build, em cima do executor existente + flag
`mock_skills=True`.

---

### Bloco I — Replay & Reproducibility (R5 hardening)
**O quê:**
- `xenia replay <run_id>` reexecuta o run com mesmo input, mesma versão
  de agente, mesmo modelo, e gera diff de output.
- Útil para: pós-mortem, antes de promover nova versão, auditoria
  externa.
- Determinismo *aproximado* (LLMs não são determinísticos): usamos
  `temperature=0` quando possível e gravamos seed quando o vendor
  expõe.

**Aceite:**
- Replay de run de 30 dias atrás funciona, *desde que* a versão de agente
  ainda esteja no registry (garantimos retenção ≥ 1 ano).
- Diff de output classifica: idêntico / equivalente semântico / divergente.

**Build vs buy:** Build, fino, em cima de runs + Langfuse + LLM-as-judge
para classificar diff.

---

### Bloco J — Visual Flow Editor (R10 evolução)
**O quê:** Hoje fluxos determinísticos vivem em YAML. Operadores não-eng
não conseguem editar.
- Editor visual estilo n8n com nodes = skills/agents.
- Compila para o mesmo YAML que o LangGraph builder já consome.
- Versionamento: cada save é commit no registry (Bloco B).

**Aceite:**
- Operador não-eng cria fluxo "novo lead → enriquecer → triagem →
  notificar Slack" sem abrir editor de código.
- YAML gerado é byte-equivalente ao YAML escrito à mão (round-trip).

**Build vs buy:** **Avaliar comprar/integrar.** n8n self-hosted é AGPL —
problema de licença. Alternativas: Activepieces (MIT), Windmill (AGPL
mas com licença comercial). Decisão: começar pelo Activepieces como
front-end, mantendo nosso executor/registry como back-end. Decidir após
spike de 1 semana.

---

### Bloco K — Load test, SLA & Cost Observability (R8 finishing)
**O quê:**
- Load test: 1000x volume atual, validar autoscale Cloud Run.
- SLA por agente: p50/p95/p99 + success rate, definidos em config do
  agente, monitorados via Langfuse + Prometheus.
- Painel de custo unitário: $/run, $/mission, $/cliente atendido.

**Aceite:**
- Teste sintético dispara 10k runs/h, sistema mantém p95 < SLA do
  agente.
- Diretoria recebe weekly automático: top 5 agentes por custo, $/output
  útil.

**Build vs buy:** Build (Locust + dashboards Grafana já existentes).

---

## 5. Build vs Buy — recomendação consolidada

| Bloco | Decisão | Justificativa |
|-------|---------|---------------|
| A. Identity | Build | Já temos JWT; SSO Google é trivial; ACL é nosso diferencial |
| B. Prompt Registry | **Buy (Langfuse Prompts)** + thin wrapper | Construir do zero é desperdício |
| C. Evals | Build sobre Langfuse Datasets/Scores | Rubric DSL é nossa |
| D. Mission Control UI | Build (Next.js) — avaliar fork de mc.builderz.dev | Streamlit não escala |
| E. Routing/Fallback | **Buy (LiteLLM proxy)** + policy layer | Roteamento já é commodity |
| F. Slack triggers | Build | Necessário e barato com Bolt SDK |
| G. Context Library | Build | É o moat |
| H. Preview Envs | Build | Específico do nosso executor |
| I. Replay | Build, fino | 200 LOC sobre infra existente |
| J. Flow Editor | **Avaliar (Activepieces)** | Spike 1 semana, decidir |
| K. Load/SLA | Build | Stack já está em pé |

**Sobre Tess.ai e Factory.ai como produto inteiro:**
- **Tess.ai:** vale assinar para uma vertical/equipe não-técnica como
  experimento (ex.: time comercial), com budget limitado de credits,
  *sem* migrar dados clínicos sensíveis. Não substitui o harness para
  agentes de saúde.
- **Factory.ai:** mais relevante para nossa engenharia interna (delegated
  development) do que para agentes operacionais Axenya. Avaliar
  separadamente — não é parte deste escopo.

---

## 6. Fases sugeridas

Cada fase tem foco e exit criteria; ordem otimiza para "demo-able value"
incremental e desbloqueio de governança em saúde.

### Fase 5 — Governança mínima (4 semanas)
Blocos A + B (parcial: registry sem shadow) + Bloco F básico.
**Exit:** SSO Google funcionando; agente promovido/rolled-back via UI;
operador invoca agente via Slack mention. Pronto para mover *um* fluxo da
GUI individual para produção compartilhada.

### Fase 6 — Operação de frota (5 semanas)
Blocos D + C (parcial: evals offline) + Bloco I.
**Exit:** Mission Control UI no ar; cada agente tem suite de evals;
replay funciona. Pronto para auditoria externa básica.

### Fase 7 — Robustez de fundação (4 semanas)
Blocos E + K + G (parcial: 2 entidades core).
**Exit:** fallback automático multi-vendor; SLA monitorado; primeiras
entidades Axenya na biblioteca compartilhada.

### Fase 8 — Operação por não-engenheiros (4 semanas)
Blocos J + H + C (online sampling/drift) + G (full).
**Exit:** Sofia/Aline criam um fluxo novo sem engenheiro; preview com
fixtures bloqueia regressões em CI; drift detection liga.

Total: ~17 semanas de calendário com 2 engs dedicados (otimista). Ajustar
após decisões de buy.

---

## 7. Decisões abertas (precisam de você, Rafa)

1. **Budget de buy:** topamos pagar Langfuse Cloud (~$200–500/mês) ou
   self-host? Self-host adiciona ~1 semana de infra.
2. **Ordem das fases:** governança (A/B) primeiro ou Mission Control (D)
   primeiro? Argumento para A/B: sem isso não conseguimos confiar em
   nada. Argumento para D: dá visibilidade política para o board.
3. **Tess.ai paralelo:** topamos rodar pilot com time comercial em
   paralelo, com escopo *zero* sobre dados clínicos? Ajuda a aprender o
   que UX de no-code precisa entregar.
4. **Mission Control naming:** mantemos "Mission Control" ou trocamos
   para "Axenya Ops" / "Frota" / outro? (você disse que o nome é
   ingrato, concordo — sugiro **"Frota Axenya"**.)
5. **Política de modelo padrão:** Claude primary + Gemini fallback faz
   sentido? Ou queremos Anthropic-only enquanto o contrato enterprise
   estiver em pé?

---

## 8. O que *não* está em escopo (explicitamente)

Para evitar creep:
- Treinamento/fine-tuning de modelos próprios.
- Marketplace público de agentes (estilo OpenHive). Foco interno.
- Mobile app nativo. Slack + web mobile responsivo bastam.
- Multi-tenant para clientes externos. Toda a plataforma é
  single-tenant Axenya por enquanto.
- Substituir o BigQuery como source of truth de dados clínicos.

---

## 9. Próximos passos concretos

1. **Você (Rafa):** validar/ajustar este escopo, responder seção 7.
2. **Sofia:** spike de 1 semana em Activepieces vs. n8n licensing
   (Bloco J).
3. **Sofia + Estevão:** pricing de Langfuse Cloud + LiteLLM hosting.
4. **Sofia:** rascunhar SPEC técnico do Bloco A (SSO + ACL) — é o
   destravamento maior e menor risco.
5. **Mariano:** alinhar com board sobre buy de Langfuse e pilot Tess.ai.
