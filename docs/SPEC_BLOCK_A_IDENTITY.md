# SPEC — Bloco A: Identity & Access

**Status:** Draft
**Autor:** Sophia Lapadula
**Última atualização:** 2026-05-10
**Branch:** `claude/define-platform-scope-hiLQm`
**Escopo:** Implementação do Bloco A do
[PLATFORM_SCOPE.md](./PLATFORM_SCOPE.md). Cobre R4 e R16.

> **Decisões assumidas (validar com Rafa antes do PR):**
> 1. SSO por Google Workspace `@axenya.com.br` apenas. Outros domínios
>    rejeitados com 403.
> 2. RBAC com 5 papéis fixos: `viewer`, `pm`, `approver`, `admin`,
>    `auditor`. Sem custom roles na v1.
> 3. Engine de policy: **Oso Cloud** ou Oso self-host (biblioteca Polar)
>    — recomendação é a biblioteca self-host, sem dependência de SaaS.
> 4. Service accounts para webhooks externos (HubSpot, Slack callbacks)
>    têm escopo separado de usuários humanos.

---

## 1. Objetivo

Substituir o JWT-com-scopes-grosso atual por uma camada de identity
unificada que:

1. Autentica humanos via Google SSO.
2. Resolve `(user, action, resource)` para Allow/Deny com latência
   < 5ms p99 (cache local).
3. Aplica ACL fina não só em endpoints REST, mas **dentro do
   executor de agente** — ou seja, o agente invocando a skill
   `gmail.read` é checado contra a ACL, não só a UI que o disparou.
4. Audita 100% das decisões de autorização (`policy_decisions`).

Sem isso, **não** promovemos a Fase 5 a produção.

---

## 2. Modelo de identidade

### 2.1 Tabelas

```sql
CREATE TABLE workspaces (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        TEXT UNIQUE NOT NULL,        -- 'axenya'
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id),
  email           CITEXT NOT NULL,
  google_subject  TEXT UNIQUE NOT NULL,   -- 'sub' do ID token
  display_name    TEXT NOT NULL,
  avatar_url      TEXT,
  status          user_status NOT NULL DEFAULT 'active',
  last_login_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, email)
);

CREATE TYPE user_status AS ENUM ('active', 'suspended', 'offboarded');

CREATE TABLE service_accounts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id),
  name          TEXT NOT NULL,             -- 'hubspot-webhook'
  description   TEXT,
  created_by    UUID NOT NULL REFERENCES users(id),
  status        sa_status NOT NULL DEFAULT 'active',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  rotated_at    TIMESTAMPTZ
);

CREATE TYPE sa_status AS ENUM ('active', 'revoked');

CREATE TABLE service_account_tokens (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_account_id  UUID NOT NULL REFERENCES service_accounts(id),
  token_hash          BYTEA NOT NULL,    -- argon2 hash
  prefix              TEXT NOT NULL,     -- primeiros 8 chars (display)
  expires_at          TIMESTAMPTZ,
  revoked_at          TIMESTAMPTZ
);

CREATE TABLE role_assignments (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id),
  principal_id  UUID NOT NULL,            -- user.id ou service_account.id
  principal_kind principal_kind NOT NULL,
  role          role_kind NOT NULL,
  scope         JSONB NOT NULL DEFAULT '{}'::jsonb,
                 -- ex.: {"agents": ["triagem_lead"]} para approver
                 -- escopado a missions de um agente específico
  granted_by    UUID NOT NULL REFERENCES users(id),
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ
);

CREATE TYPE principal_kind AS ENUM ('user', 'service_account');
CREATE TYPE role_kind AS ENUM ('viewer', 'pm', 'approver', 'admin', 'auditor');
```

### 2.2 ACL fina: agente → skill → recurso

```sql
CREATE TABLE skill_acl (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id),
  agent_slug    TEXT NOT NULL,            -- 'triagem_lead'
  skill_name    TEXT NOT NULL,            -- 'gmail.read'
  resource_filter JSONB NOT NULL DEFAULT '{}'::jsonb,
                 -- ex.: {"mailbox": "aline@axenya.com.br"}
                 -- ou   {"hubspot_pipeline": "leads_2026"}
  granted_by    UUID NOT NULL REFERENCES users(id),
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ,
  UNIQUE (workspace_id, agent_slug, skill_name, resource_filter)
);

CREATE TABLE skill_sensitivity (
  workspace_id  UUID NOT NULL REFERENCES workspaces(id),
  skill_name    TEXT NOT NULL,
  tags          TEXT[] NOT NULL,          -- ['clinical_data', 'pii']
  PRIMARY KEY (workspace_id, skill_name)
);

CREATE TABLE user_agent_acl (
  workspace_id  UUID NOT NULL REFERENCES workspaces(id),
  user_id       UUID NOT NULL REFERENCES users(id),
  agent_slug    TEXT NOT NULL,
  capabilities  TEXT[] NOT NULL,
                -- subset de ['operate', 'approve', 'view_traces',
                --            'edit_config', 'pause']
  granted_by    UUID NOT NULL REFERENCES users(id),
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ,
  PRIMARY KEY (workspace_id, user_id, agent_slug)
);
```

**Exemplo concreto (caso da Dra. Aline):**

```sql
-- Só Aline e Bia operam o agente; só Aline aprova exceções:
INSERT INTO user_agent_acl VALUES
  ('axenya', 'aline_id',  'triagem_email_aline', '{operate,approve,view_traces}', …),
  ('axenya', 'bia_id',    'triagem_email_aline', '{operate,view_traces}', …);

-- O agente só pode ler o gmail da Aline:
INSERT INTO skill_acl VALUES
  ('axenya', 'triagem_email_aline', 'gmail.read',
   '{"mailbox": "aline@axenya.com.br"}', …);

-- A skill é marcada como sensível, ativando dual-control:
INSERT INTO skill_sensitivity VALUES
  ('axenya', 'gmail.read', '{pii}');
```

### 2.3 Audit

```sql
CREATE TABLE policy_decisions (
  id              BIGSERIAL PRIMARY KEY,
  workspace_id    UUID NOT NULL REFERENCES workspaces(id),
  principal_id    UUID NOT NULL,
  principal_kind  principal_kind NOT NULL,
  action          TEXT NOT NULL,          -- 'mission.approve', 'skill.invoke'
  resource_kind   TEXT NOT NULL,
  resource_id     TEXT NOT NULL,
  decision        TEXT NOT NULL,          -- 'allow' | 'deny'
  reason          TEXT NOT NULL,
  context         JSONB NOT NULL,         -- request id, mission id, etc.
  decided_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX policy_decisions_lookup
  ON policy_decisions (workspace_id, principal_id, decided_at DESC);
```

Append-only via mesma trigger do Bloco D. Retenção mínima: 1 ano hot,
3 anos archived em BigQuery (atende exigência de auditoria de saúde).

---

## 3. Authentication flow

### 3.1 Humanos (Google SSO)

```
Browser              Frontend              Backend              Google
  │                     │                     │                    │
  │── /login ──────────▶│                     │                    │
  │                     │── start oidc ──────▶│                    │
  │                     │                     │── authz request ──▶│
  │◀──────────────── redirect to Google ──────────────────────────┤
  │── consent ──────────────────────────────────────────────────▶ │
  │◀── code redirect ──────────────────────────────────────────── │
  │── code ────────────▶│── code ────────────▶│── exchange ──────▶│
  │                     │                     │◀── id_token ──────│
  │                     │                     │ verify aud, iss,  │
  │                     │                     │ hd=axenya.com.br  │
  │                     │                     │ upsert user       │
  │                     │                     │ issue session JWT │
  │                     │◀── session JWT ─────│                    │
  │◀── set HttpOnly ────│                     │                    │
```

- `hd` claim do Google **must equal** `axenya.com.br`. Outros
  domínios → 403.
- Session JWT: HS256, TTL 8h, refresh token TTL 30d, refresh rotation.
- Cookies `HttpOnly`, `Secure`, `SameSite=Lax`.
- `google_subject` (`sub`) é a primary key estável; e-mail pode mudar.
- Auto-provisioning: usuário novo entra como `viewer`. Admin precisa
  granted role explícito.

### 3.2 Service accounts

- Token formato: `xeak_<workspace_slug>_<prefix>_<secret>`.
- Hash: argon2id, custo médio.
- Header: `Authorization: Bearer xeak_…`.
- Rotação obrigatória anual (alerta a 30 dias do vencimento).
- Logging: cada uso do token grava `policy_decisions` com
  `principal_kind=service_account`.

### 3.3 Agentes (sub-principal)

Quando um run executa, o request para invocar uma skill leva *dois*
principals:
- `caller_principal`: usuário ou SA que disparou a mission.
- `agent_principal`: o slug do agente (`triagem_email_aline@v1.2.3`).

ACL é checada contra **ambos**. Se o agent não tem entrada em
`skill_acl`, deny. Se o caller não tem `operate` em
`user_agent_acl`, deny.

---

## 4. Authorization engine

### 4.1 Por que Oso (biblioteca Polar)

- Polar é declarativo, lê tabelas via data filtering — gera SQL com os
  filtros direto, evita N+1.
- Self-host, MIT, sem dependência de SaaS.
- Comparado a Casbin: sintaxe mais legível para operadores não-eng;
  comparado a OPA: muito mais simples de embedar em Python sem cluster
  separado.

### 4.2 Política Polar (esboço)

```polar
actor User {}
actor ServiceAccount {}

resource Workspace {
  permissions = ["read", "admin"];
  roles = ["viewer", "pm", "approver", "admin", "auditor"];

  "read"  if "viewer";
  "read"  if "pm";
  "read"  if "approver";
  "read"  if "auditor";
  "admin" if "admin";
}

resource Mission {
  permissions = ["read", "create", "transition", "approve_plan", "comment"];
  relations = { workspace: Workspace };

  "read"      if "viewer" on "workspace";
  "create"    if "pm" on "workspace";
  "transition" if "pm" on "workspace";
  "comment"   if "pm" on "workspace";
  "approve_plan" if approver_for(actor, resource);
}

resource Skill {
  permissions = ["invoke"];
  relations = { workspace: Workspace };

  "invoke" if has_skill_acl(agent, resource, resource_filter);
}

# regra dual-control para missions sensíveis:
allow(actor: User, "approve_plan", mission: Mission) if
    not (mission.created_by = actor and is_sensitive(mission));
```

### 4.3 Performance

- `Authorizer` lê tabelas via SQLAlchemy + cache LRU TTL=30s na process.
- Invalidação por pub/sub no Redis quando uma role/ACL muda → flush
  parcial.
- Target: 5ms p99 dentro do harness; benchmark obrigatório no CI.

---

## 5. Pontos de aplicação

| Camada | Como aplica |
|--------|-------------|
| API REST (`/v1/*`) | Middleware FastAPI lê session/SA token → `Authorizer.check(actor, action, resource)` antes do handler. |
| WebSocket Kanban | Mesmo middleware no handshake + filtro por workspace nos eventos broadcast. |
| Executor de agente | Antes de cada `tool_call` (skill invoke), Authorizer checa `(agent_principal, "invoke", skill, resource_filter)`. Deny → run falha com `policy_violation`. |
| Slack triggers | Bolt SDK middleware mapeia Slack user → Axenya user (via e-mail), depois Authorizer normal. |
| Langfuse traces | Filtra traces por workspace/role no front-end (Langfuse não tem ACL nativa fina). |

---

## 6. Admin UI (mínima na v1)

`/admin/users` — lista, change role, suspender, offboard.
`/admin/agents/{slug}/acl` — granted operators + skills habilitadas.
`/admin/service-accounts` — criar/rotacionar/revogar token (token
mostrado uma vez).
`/admin/audit` — busca por user/action/resource, exportar CSV.

Acesso: `admin` only para mutate; `auditor` read-only nas mesmas telas.

---

## 7. Plano de implementação (semana 5 da Fase 5 + spillover)

3 semanas, 1 BE + 0.3 FE.

**Semana 1 — identidade + SSO**
- Migrations: workspaces, users, service_accounts, role_assignments.
- Google OIDC end-to-end + session JWT + refresh rotation.
- Provisão inicial: 1 admin (eu), todos os outros como viewer.

**Semana 2 — policy engine + ACL fina**
- Integração Oso/Polar + middlewares.
- `skill_acl`, `user_agent_acl`, `skill_sensitivity`.
- Authorizer.check() chamado dentro do executor de agente.
- Bench p99 < 5ms.

**Semana 3 — admin UI + audit**
- Telas mínimas de admin.
- `policy_decisions` log + export.
- Migração: dual-write JWT scopes + Polar por 1 sprint, cutover.

---

## 8. Migração

- Endpoints atuais com JWT scopes continuam aceitando até a Fase 6
  começar.
- Toggle `XENIA_AUTH_ENGINE=oso|legacy` controla qual checa as
  requests.
- Quando estável, removemos legacy e o env var.
- Tokens emitidos hoje são invalidados; usuários precisam re-login
  (avisar com 1 semana de antecedência).

---

## 9. Riscos

| Risco | Mitigação |
|-------|-----------|
| Polar fica lento sob load | Cache LRU + bench obrigatório; fallback para hardcoded check em rotas críticas |
| Bloqueio total se Authorizer falha | Fail-closed com bypass apenas para `/health` e `/login`; alerta crítico no Slack |
| Token de SA vaza | Argon2 hash + rotação anual + alerta de uso anômalo + revoke em 1 click |
| Aline não consegue logar (recovery) | Admin pode emitir token de bypass de 1 hora via CLI assinado |
| Domínio `axenya.com.br` não cobre todos colaboradores | Fase 6: aceitar lista de domínios extras configurável |

---

## 10. Open questions para o PR

1. Aceitamos contas Google de outros domínios em casos
   excepcionais? (Sugestão: **não** v1; convidados externos só via SA.)
2. Precisamos de SCIM para provisioning automático? (Sugestão:
   **não** v1; manual no admin UI basta.)
3. MFA: confiamos no Google ou exigimos step-up para `admin`?
   (Sugestão: confiamos no Google; revisita em audit de SOC2.)
4. Onboard de novo eng → como recebe role? (Sugestão: ticket Linear
   abre PR no `infra/role_assignments.yaml` que aplica via migration.)
