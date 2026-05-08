# Agents

Cada arquivo `*.yaml` neste diretório é uma definição de agente carregada pelo
`AgentRegistry` na inicialização do `xenia-api`. Definições são validadas
contra `_schema.json` (JSON Schema 2020-12) e contra o modelo Pydantic
`AgentDefinition`.

## Como adicionar um agente novo

1. Escolha um `id` em `snake_case`. Esse id vira parte da URL do webhook
   (`POST /v1/webhooks/<id>`) e da tabela `agents`.
2. Copie um arquivo existente como template.
3. Defina o `input_schema` em JSON Schema (objeto). É ele que valida o payload
   recebido pelo webhook.
4. Liste as `skills` que o agente pode chamar. Os nomes devem existir no
   `SkillRegistry` (ver `src/xenia/skills/`).
5. Configure `llm` (provider + model + max_tokens + temperature) e
   `execution` (max_steps, timeout_seconds, política de retry).
6. Escreva um `system_prompt` claro. Pode usar `{{var}}` pra interpolar campos
   do payload — substituição é puramente textual, sem eval.
7. Reinicie o `xenia-api` (ou chame `POST /v1/agents/reload` em dev).
8. Configure o secret HMAC: defina a env var indicada em `webhook_secret_env`.

## Graph customizado (Fase 2 — em pleno suporte na v1)

Quando você precisa de mais que o loop tool-use linear, declare o grafo:

```yaml
graph:
  nodes:
    - name: classify
      type: llm_call
      prompt: "Classifique o lead em [A, B, C]..."
    - name: enrich
      type: tool_call
      tool: bigquery.query_similar_leads
      condition: "state.classification == 'A'"
  edges:
    - from: ENTRY
      to: classify
    - from: classify
      to: enrich
      condition: "state.classification == 'A'"
    - from: enrich
      to: END
```

Tipos suportados: `llm_call`, `tool_call`, `human_input`, `branch`.

## BigQuery — whitelist de queries

A skill `bigquery.query` rejeita SQL arbitrário. Cada query autorizada vive
em `agents/queries/<name>.yaml`:

```yaml
name: similar_leads
description: ...
sql: |
  SELECT ...
params:
  empresa: STRING
```

O agente passa apenas `query_name` + `params` — nunca SQL.
