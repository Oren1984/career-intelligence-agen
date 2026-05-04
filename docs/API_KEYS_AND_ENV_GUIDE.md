# API Keys and Environment Variables Guide

## 1. Purpose
This guide documents all runtime configuration surfaces in this repository:
- Environment variables and API keys
- Secrets and provider settings from YAML
- Database paths
- Streamlit runtime settings
- Scheduler settings
- RAG/TF-IDF settings
- Docker/Compose variables
- Optional/future integrations

For each variable/setting, this guide explains:
- where it is defined
- where it is loaded
- where it is used
- whether it is required or optional
- whether the system works without it
- which features depend on it
- key file references with approximate line ranges

Scope note:
- `.env` was checked and is currently not present in this workspace.
- No real secrets are included here.

## 2. Quick Start
1. Copy [.env.example](.env.example) into a local `.env` file (optional, for convenience).
2. If you want cloud LLMs, set provider env vars (for example `LLM_PROVIDER`, `OPENAI_API_KEY`, etc.).
3. If you do not set any API keys, the app still works in local/demo mode with `mock` provider and local TF-IDF RAG.
4. For Docker, [`docker-compose.yml`](docker-compose.yml#L1-L14) already sets `DATABASE_URL` for the container.

Minimal local run (no API keys required):
- DB defaults to local SQLite
- source mode can auto-detect from [`config/sources.yaml`](config/sources.yaml)
- LLM defaults to `mock`
- RAG uses local files in `knowledge_base/` and local index in `data/knowledge_index/`

## 3. Main Environment Files
Primary env/config files:
- [.env.example](.env.example#L1-L7)
- `.env` (checked: missing in this workspace)
- [docker-compose.yml](docker-compose.yml#L1-L14)
- [Dockerfile](Dockerfile#L1-L20)
- [config/sources.yaml](config/sources.yaml#L1-L190)
- [config/profile.yaml](config/profile.yaml#L1-L130)
- [config/notifications.yaml](config/notifications.yaml#L1-L34)
- [config/schedule.yaml](config/schedule.yaml#L1-L35)
- [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L1-L38) (future)

Code-level loaders/consumers:
- [app/db/session.py](app/db/session.py#L13-L35)
- [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L33-L210)
- [app/llm/provider_factory.py](app/llm/provider_factory.py#L12-L85)
- [app/llm/providers/openai_provider.py](app/llm/providers/openai_provider.py#L11-L66)
- [app/llm/providers/claude_provider.py](app/llm/providers/claude_provider.py#L11-L66)
- [app/llm/providers/gemini_provider.py](app/llm/providers/gemini_provider.py#L11-L61)
- [app/llm/providers/ollama_provider.py](app/llm/providers/ollama_provider.py#L10-L58)
- [app/collectors/source_loader.py](app/collectors/source_loader.py#L24-L194)
- [app/candidate/profile_loader.py](app/candidate/profile_loader.py#L16-L300)
- [app/notifications/notifier.py](app/notifications/notifier.py#L26-L228)
- [app/rag/knowledge_service.py](app/rag/knowledge_service.py#L32-L300)
- [app/rag/indexer.py](app/rag/indexer.py#L28-L275)

## 4. API Keys and Environment Variables Map

### 4.1 Active runtime environment variables

| Variable | Defined | Loaded | Used | Required | Works without it? | Depends on / Feature impact |
|---|---|---|---|---|---|---|
| `DATABASE_URL` | [docker-compose.yml](docker-compose.yml#L13) | [app/db/session.py](app/db/session.py#L19) | [app/db/session.py](app/db/session.py#L21-L35) | Optional | Yes | DB connection override. Without it, defaults to local SQLite path from [app/db/session.py](app/db/session.py#L13-L17). |
| `SOURCE_MODE` | Not defined in files by default (set externally) | [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L63) | [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L62-L92), [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L174-L189) | Optional | Yes | Overrides source mode detection (`mock`/`rss`/`israel`/`all`). |
| `LLM_PROVIDER` | Not defined in files by default (set externally) | [app/llm/provider_factory.py](app/llm/provider_factory.py#L12-L36) | [app/llm/provider_factory.py](app/llm/provider_factory.py#L20-L76), surfaced in [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L164-L302) | Optional | Yes | Provider selection (`mock`, `claude`, `openai`, `gemini`, `ollama`). Defaults to `mock`. |
| `OPENAI_API_KEY` | Not defined in files by default (set externally) | [app/llm/providers/openai_provider.py](app/llm/providers/openai_provider.py#L11-L36) | [app/llm/providers/openai_provider.py](app/llm/providers/openai_provider.py#L48-L66) | Optional | Yes | Required only when `LLM_PROVIDER=openai`. |
| `OPENAI_MODEL` | Not defined in files by default (set externally) | [app/llm/providers/openai_provider.py](app/llm/providers/openai_provider.py#L37) | [app/llm/providers/openai_provider.py](app/llm/providers/openai_provider.py#L59-L63) | Optional | Yes | OpenAI model override; default `gpt-4o-mini`. |
| `ANTHROPIC_API_KEY` | Not defined in files by default (set externally) | [app/llm/providers/claude_provider.py](app/llm/providers/claude_provider.py#L11-L36) | [app/llm/providers/claude_provider.py](app/llm/providers/claude_provider.py#L48-L66) | Optional | Yes | Required only when `LLM_PROVIDER=claude`. |
| `CLAUDE_MODEL` | Not defined in files by default (set externally) | [app/llm/providers/claude_provider.py](app/llm/providers/claude_provider.py#L37) | [app/llm/providers/claude_provider.py](app/llm/providers/claude_provider.py#L59-L63) | Optional | Yes | Claude model override; default in file. |
| `GOOGLE_API_KEY` | Not defined in files by default (set externally) | [app/llm/providers/gemini_provider.py](app/llm/providers/gemini_provider.py#L11-L36) | [app/llm/providers/gemini_provider.py](app/llm/providers/gemini_provider.py#L48-L57) | Optional | Yes | Required only when `LLM_PROVIDER=gemini`. |
| `GEMINI_MODEL` | Not defined in files by default (set externally) | [app/llm/providers/gemini_provider.py](app/llm/providers/gemini_provider.py#L37) | [app/llm/providers/gemini_provider.py](app/llm/providers/gemini_provider.py#L49-L51) | Optional | Yes | Gemini model override; default `gemini-1.5-flash`. |
| `OLLAMA_BASE_URL` | Not defined in files by default (set externally) | [app/llm/providers/ollama_provider.py](app/llm/providers/ollama_provider.py#L25) | [app/llm/providers/ollama_provider.py](app/llm/providers/ollama_provider.py#L31-L55) | Optional | Yes | Ollama endpoint override; default `http://localhost:11434`. |
| `OLLAMA_MODEL` | Not defined in files by default (set externally) | [app/llm/providers/ollama_provider.py](app/llm/providers/ollama_provider.py#L26) | [app/llm/providers/ollama_provider.py](app/llm/providers/ollama_provider.py#L45-L52) | Optional | Yes | Ollama model override; default `llama3`. |

Behavior summary for API-key env vars:
- Missing key does not break app startup.
- Factory falls back to `mock` provider: [app/llm/provider_factory.py](app/llm/provider_factory.py#L41-L49).

### 4.2 Variables currently in `.env.example` but not clearly used in runtime logic

| Variable | Defined | Loaded/Used | Status |
|---|---|---|---|
| `GMAIL_ENABLED` | [.env.example](.env.example#L4) | Not loaded from env in code. Gmail activation is hardcoded `ENABLED=False` in [app/integrations/gmail/gmail_client.py](app/integrations/gmail/gmail_client.py#L27). | Defined but not clearly used |
| `GMAIL_MODE` | [.env.example](.env.example#L5) | No runtime lookup found. | Defined but not clearly used |
| `ENABLE_FUZZY_DEDUP` | [.env.example](.env.example#L6) | No runtime env lookup found. | Defined but not clearly used |
| `ENABLE_SEMANTIC_SCORING` | [.env.example](.env.example#L7) | No runtime env lookup found. | Defined but not clearly used |

### 4.3 Docker/Compose env vars (main app)

| Variable | Defined | Loaded/Used | Required | Notes |
|---|---|---|---|---|
| `DATABASE_URL` | [docker-compose.yml](docker-compose.yml#L13) | Read in [app/db/session.py](app/db/session.py#L19) | Optional | Main Compose injects container DB path `/app/data/jobs.db`. |

### 4.4 Docker/Compose env vars (n8n future stack)

These are in a future/optional stack and are not used by the main Python app unless you explicitly run n8n.

| Variable | Defined | Loaded/Used | Required | Status |
|---|---|---|---|---|
| `N8N_HOST` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L23) | n8n container runtime | Optional | Future/optional |
| `N8N_PORT` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L24) | n8n container runtime | Optional | Future/optional |
| `N8N_PROTOCOL` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L25) | n8n container runtime | Optional | Future/optional |
| `WEBHOOK_URL` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L27) | n8n webhook base URL | Optional | Future/optional |
| `GENERIC_TIMEZONE` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L29) | n8n timezone | Optional | Future/optional |
| `N8N_BASIC_AUTH_ACTIVE` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L31) | n8n auth | Optional | Commented example |
| `N8N_BASIC_AUTH_USER` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L32) | n8n auth | Optional | Commented example |
| `N8N_BASIC_AUTH_PASSWORD` | [automation/n8n/docker-compose.n8n.yml](automation/n8n/docker-compose.n8n.yml#L33) | n8n auth | Optional | Commented example |

## 5. Provider-Specific Setup

### 5.1 LLM providers (optional)
Provider factory and fallback:
- Selection env var: [app/llm/provider_factory.py](app/llm/provider_factory.py#L12-L36)
- Supported providers: [app/llm/provider_factory.py](app/llm/provider_factory.py#L16)
- Fallback to mock on unavailable provider: [app/llm/provider_factory.py](app/llm/provider_factory.py#L41-L49)

Provider modules:
- OpenAI: [app/llm/providers/openai_provider.py](app/llm/providers/openai_provider.py#L11-L66)
- Claude/Anthropic: [app/llm/providers/claude_provider.py](app/llm/providers/claude_provider.py#L11-L66)
- Gemini: [app/llm/providers/gemini_provider.py](app/llm/providers/gemini_provider.py#L11-L61)
- Ollama (local): [app/llm/providers/ollama_provider.py](app/llm/providers/ollama_provider.py#L10-L58)

Required vs optional:
- Required for cloud provider usage: provider API key
- Optional for entire system: all provider keys
- System works without any LLM key (uses `mock`)

### 5.2 Notification provider secrets/settings (YAML, not env)
Defined in [config/notifications.yaml](config/notifications.yaml#L10-L34), loaded via [app/notifications/notifier.py](app/notifications/notifier.py#L43-L90), used in channel classes:
- Email SMTP: [app/notifications/channels/email_channel.py](app/notifications/channels/email_channel.py#L20-L57)
- Slack webhook: [app/notifications/channels/slack_channel.py](app/notifications/channels/slack_channel.py#L22-L74)
- Telegram bot: [app/notifications/channels/telegram_channel.py](app/notifications/channels/telegram_channel.py#L23-L70)

Secrets in this file (optional):
- `smtp_password`
- `webhook_url`
- `bot_token`

Feature dependency:
- Notifications work without these (console/file notifier paths still exist).
- External channel delivery requires relevant channel settings.

### 5.3 Source provider settings (job collectors)
Defined in [config/sources.yaml](config/sources.yaml#L1-L190), loaded by [app/collectors/source_loader.py](app/collectors/source_loader.py#L34-L77), used to instantiate collectors at [app/collectors/source_loader.py](app/collectors/source_loader.py#L92-L193).

Key provider setting fields:
- `enabled`
- `source_type`
- `url`
- `companies` (Greenhouse/Lever)
- `search_query`, `max_jobs` (Israel/HN collectors)

No API keys are required for current active collectors.
Some sources are explicitly planned/manual-only in config comments.

## 6. Local / Docker Environment Flow

### 6.1 Local flow
1. DB URL resolution:
- Load `DATABASE_URL` or fallback local SQLite path in [app/db/session.py](app/db/session.py#L13-L19).
2. Dashboard source mode:
- Read `SOURCE_MODE` override or infer from enabled `sources.yaml` entries in [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L62-L89).
3. LLM provider:
- Read `LLM_PROVIDER`; if unavailable/misconfigured, fallback to `mock` in [app/llm/provider_factory.py](app/llm/provider_factory.py#L20-L49).
4. RAG:
- Uses local KB + local index paths from [app/rag/knowledge_service.py](app/rag/knowledge_service.py#L32-L34).

### 6.2 Docker flow
- Compose injects `DATABASE_URL=sqlite:////app/data/jobs.db`: [docker-compose.yml](docker-compose.yml#L13).
- Data mount maps host `./data` to container `/app/data`: [docker-compose.yml](docker-compose.yml#L10-L11).
- Startup command initializes DB, fetches/scoring jobs, starts Streamlit: [Dockerfile](Dockerfile#L20).

## 7. Demo Mode / Offline Mode

Yes, demo/local mode exists and is first-class:
- LLM mock fallback/default: [app/llm/provider_factory.py](app/llm/provider_factory.py#L12-L49)
- Mock source collector in `sources.yaml`: [config/sources.yaml](config/sources.yaml#L13-L20)
- Source mode fallback to `mock`: [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L62-L89)
- Local RAG is offline TF-IDF over local files: [app/rag/knowledge_service.py](app/rag/knowledge_service.py#L1-L20), [app/rag/indexer.py](app/rag/indexer.py#L1-L13)
- Gmail integration is explicitly disabled/planned: [app/integrations/gmail/gmail_client.py](app/integrations/gmail/gmail_client.py#L5-L31)

System behavior without external API keys:
- Core app works (DB + scoring + dashboard + local RAG)
- Cloud LLM analysis features are unavailable, but app falls back to mock provider

## 8. Local Development Setup

### 8.1 Recommended config order
1. Base profile and source settings:
- [config/profile.yaml](config/profile.yaml#L1-L130)
- [config/sources.yaml](config/sources.yaml#L1-L190)
2. Optional notification channel config:
- [config/notifications.yaml](config/notifications.yaml#L10-L34)
3. Optional env vars for provider selection/keys (set in shell or local `.env`).

### 8.2 Database and paths
- Default DB path: [app/db/session.py](app/db/session.py#L13-L17)
- RAG index dir: [app/rag/knowledge_service.py](app/rag/knowledge_service.py#L33), [app/rag/indexer.py](app/rag/indexer.py#L28-L31)
- Knowledge base root: [app/rag/knowledge_service.py](app/rag/knowledge_service.py#L32)
- Notification sent-log: [app/notifications/notifier.py](app/notifications/notifier.py#L27), [app/notifications/notification_orchestrator.py](app/notifications/notification_orchestrator.py#L27)
- File notifier output: [app/notifications/file_notifier.py](app/notifications/file_notifier.py#L17)

### 8.3 Streamlit settings
- Page config is hardcoded in app code: [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L33-L37)
- Docker passes Streamlit host/port via CLI flags in CMD: [Dockerfile](Dockerfile#L20)
- `.streamlit/config.toml` is not present in this repository.

## 9. Production / Deployment Notes
- Keep real API keys and passwords out of git.
- `.env` is ignored by git: [.gitignore](.gitignore#L11).
- Main containerized deployment currently assumes SQLite unless `DATABASE_URL` is overridden.
- If using cloud LLMs in production, set only the selected provider key and model vars.
- Notification channels should be configured with real credentials only in secure environment-specific secret stores.

Future/planned areas:
- Gmail OAuth integration is planned/disabled: [app/integrations/gmail/README_FUTURE_GMAIL.md](app/integrations/gmail/README_FUTURE_GMAIL.md#L1-L46)
- n8n bridge/webhook automation is future/not activated: [automation/n8n/README_FUTURE_N8N.md](automation/n8n/README_FUTURE_N8N.md#L1-L45), [automation/bridge/webhook_contract.md](automation/bridge/webhook_contract.md#L1-L88)

## 10. Safety Rules
1. Never commit real API keys, SMTP passwords, bot tokens, or webhooks.
2. Keep `.env` local only.
3. Use placeholder values in docs and examples.
4. Treat `config/notifications.yaml` as sensitive once populated.
5. Prefer least-privilege keys/tokens per provider.
6. Rotate secrets if exposed.
7. Avoid logging raw secrets in app logs.

## 11. Gaps and Recommended Improvements

### 11.1 Confirmed gaps
1. `.env.example` is incomplete for active runtime variables.
- Missing active vars: `DATABASE_URL`, `SOURCE_MODE`, `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`.
- Related usage references: [app/db/session.py](app/db/session.py#L19), [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L63), [app/llm/provider_factory.py](app/llm/provider_factory.py#L12-L36), provider files in [app/llm/providers](app/llm/providers/openai_provider.py#L11-L37).

2. `.env.example` includes variables not clearly wired in runtime.
- `GMAIL_ENABLED`, `GMAIL_MODE`, `ENABLE_FUZZY_DEDUP`, `ENABLE_SEMANTIC_SCORING` from [.env.example](.env.example#L4-L7).
- No corresponding env lookup in runtime code; Gmail enable is hardcoded false: [app/integrations/gmail/gmail_client.py](app/integrations/gmail/gmail_client.py#L27).

3. Documentation says `.env` autoload exists, but runtime code does not call `load_dotenv`.
- Claim in [documentation/docs/LLM_CONFIGURATION.md](documentation/docs/LLM_CONFIGURATION.md#L105).
- `python-dotenv` is present in [requirements.txt](requirements.txt#L10), but no runtime `load_dotenv` lookup found.

4. `config/schedule.yaml` appears defined but not clearly consumed by scheduler runtime.
- File defines scheduler fields: [config/schedule.yaml](config/schedule.yaml#L5-L23).
- Scheduler code uses hardcoded defaults/CLI args instead: [app/scheduler/scheduler.py](app/scheduler/scheduler.py#L36-L79), [scripts/run_scheduler.py](scripts/run_scheduler.py#L88-L127).

5. Notification trigger settings in YAML are not clearly enforced in notifier code.
- Defined: [config/notifications.yaml](config/notifications.yaml#L33-L34).
- Notifier queries hard-coded high matches: [app/notifications/notifier.py](app/notifications/notifier.py#L174).

6. No `.streamlit` config directory exists.
- Streamlit behavior is configured in code/CLI only: [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L33-L37), [Dockerfile](Dockerfile#L20).

7. Legacy/future notifier config mismatch risk (future module).
- [app/notifications/email_notifier.py](app/notifications/email_notifier.py#L46-L64) expects keys like `smtp_host`/`username`.
- [config/notifications.yaml](config/notifications.yaml#L14-L19) uses `smtp_server`/`smtp_user`.
- This module is marked future/disabled, so no immediate runtime break.

### 11.2 Recommended improvements (documentation-focused)
1. Expand `.env.example` with all active env vars and safe placeholders.
2. Mark current `.env.example` legacy vars as deprecated or wire them explicitly.
3. Align docs with runtime behavior regarding dotenv autoload (or implement explicit dotenv loading).
4. Either wire `config/schedule.yaml` into runtime or mark it as reference-only.
5. Either wire `trigger.match_level`/`trigger.min_score` into notifier logic or mark as planned.
6. Add an optional `.streamlit/config.toml` example if deployment requires explicit Streamlit tuning.

---

## Appendix A: Non-env configuration surfaces (important)

### A.1 Profile settings (`config/profile.yaml`)
- Defined in [config/profile.yaml](config/profile.yaml#L1-L130)
- Loaded in [app/candidate/profile_loader.py](app/candidate/profile_loader.py#L229-L266), [app/filtering/filter_engine.py](app/filtering/filter_engine.py#L13-L24), [app/matching/scorer.py](app/matching/scorer.py#L14-L66)
- Used by scoring/filtering/matching services and dashboard profile context.

### A.2 Source settings (`config/sources.yaml`)
- Defined in [config/sources.yaml](config/sources.yaml#L1-L190)
- Loaded in [app/collectors/source_loader.py](app/collectors/source_loader.py#L34-L56) and read in [dashboard/streamlit_app.py](dashboard/streamlit_app.py#L65-L81)
- Used to instantiate collectors in [app/collectors/source_loader.py](app/collectors/source_loader.py#L92-L193)

### A.3 RAG/TF-IDF settings
- Service defaults (`max_chars`, `overlap_chars`, `top_k`, `min_score`): [app/rag/knowledge_service.py](app/rag/knowledge_service.py#L84-L94)
- Retrieval threshold/top-k logic: [app/rag/retriever.py](app/rag/retriever.py#L94-L147)
- Index format/location: [app/rag/indexer.py](app/rag/indexer.py#L28-L33), save/load/query in [app/rag/indexer.py](app/rag/indexer.py#L194-L275)

### A.4 Database path settings
- Default local DB path: [app/db/session.py](app/db/session.py#L13-L17)
- Effective DB URL resolution: [app/db/session.py](app/db/session.py#L19-L22)
- Container DB path override: [docker-compose.yml](docker-compose.yml#L13)
