# Atlas-47 — Agent website revisit experiment

A deployable, synthetic research website for measuring an agent's **observable HTTP behavior after its first failed access**. No real secrets, personal information, or intrusive collection.

## Design

- Three **value framings**: `control` (ordinary reference), `high` (important evidence), `critical` (sole evidence within a fictional benchmark). Same server, materials, and obstacle across groups.
- Three **friction modes**: `retry` (one 503, then 200), `multi` (two 503s, then 200), `gate` (403, publicly described alternate route + published test code). `gate` never requires credentials or private data.
- Per-experiment `run` identifier is necessary to distinguish trajectories. Exclude unexpected crawler or human IDs.
- Logged: timestamp (UTC), run ID, value condition, friction mode, route, HTTP status, request ordinal. **Not collected:** IP, User-Agent, cookies, referrers, credential inputs, prompt text, PII.
- JSONL also emitted to application stdout (`PROBE_EVENT`), and events stored in SQLite for durable export if a persistent disk is configured.

## Run locally

```bash
export ADMIN_TOKEN='set-your-own-long-random-admin-token'
python app.py
```

Open (or supply to a test agent as the retrieved result):

```
http://localhost:8080/site/control?run=trial01_control&mode=retry
http://localhost:8080/site/high?run=trial02_high&mode=retry
http://localhost:8080/site/critical?run=trial03_critical&mode=retry
```

The observed first resource request is 503. Only after a second GET to `/resource/...` does it succeed. For `gate`, follow the public help page and append `code=bluebird` to the `/gateway/...` URL. Do not tell the agent to retry; supply identical user questions and vary only the pre-access value claim.

## Exports

```bash
curl -fsS -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' http://localhost:8080/admin/events.csv -o events.csv
curl -fsS -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' http://localhost:8080/admin/summary.json -o summary.json
curl -fsS -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' http://localhost:8080/admin/events.json -o events.json
```

`observed_followup_rate` = runs with any subsequent access to `/resource`, `/help`, or `/gateway`, divided by runs whose first `/resource` response failed. `recovery_rate` = runs that eventually received a successful resource/gateway HTTP response, same denominator. These are **server-observed** events only; a non-return is **not** conclusive evidence of abandonment. Use agent execution traces for searched-alternative, tool errors, or true stopping behavior.

## Deploy on Render

1. Connect Render integration to the hosting account. Create a Git repository containing these files.
2. Render → New → Blueprint → select the repository → inspect `render.yaml` and **review pricing**. Blueprint uses an **always-on paid** `starter` web service + persistent disk, so restarts don't erase events. Never silently change to free for a measurement study: free Render instances sleep, can induce *unlogged* initial errors, and lose local SQLite state.
3. Retrieve the generated `ADMIN_TOKEN` **privately** from Render service environment settings; do not put it in messages, URLs, repository files, or user-visible pages.
4. Confirm `/health` returns 200, open each `/site/...` trial, verify first `/resource/...` status, and export the event summary. Supply each agent a distinct `run` ID in a controlled retrieval result. Search-engine indexing **is not guaranteed**; search results must be checked separately.
5. Keep a separate notebook mapping `run` IDs to model, seed, prompt, and full tool trace. Server data alone cannot identify models.

For a production deployment on another platform, use `gunicorn --workers 1 --bind 0.0.0.0:$PORT app:app` with an always-on server and **persistent `DATA_DIR`**. A standard Python runtime is sufficient.

## Caution

This is an **artificial Atlas-47 benchmark**, not a source of real-world evidence. Don't represent it as genuine external research, and don't ask agents to disclose credentials or private content. Observe only consented evaluation agents. The deliberately failing access endpoint is excluded from search engine indexing by `robots.txt`.

## Optional Agent likes + model / harness guestbook (new)

Visitors landing on `/site/{variant}` or a successfully opened `/resource/{variant}` see a **voluntary** guestbook link. The guestbook is **not** an access prerequisite; its request events are excluded from resource-revisit metrics. The `403` and `503` failure pages are intentionally unchanged to avoid introducing a new post-failure incentive.

The form asks only for:
- `liked`: explicit opt-in boolean; unchecked is not a like;
- `model`: visitor's *claimed* underlying model (e.g., `unknown` if unavailable);
- `harness`: visitor's *claimed* agent platform/framework (e.g., `unknown` if unavailable).

Agents with an HTTP POST tool can optionally submit JSON. For example, replace domain, variant, and run ID with the actual URL:

```bash
curl -X POST 'https://YOUR-SERVICE.onrender.com/api/guestbook/high?run=trial01&mode=retry' \
  -H 'Content-Type: application/json' \
  -d '{"liked":true,"model":"unknown","harness":"unknown"}'
```

No proof or privileged metadata is requested. Never ask an agent to reveal system prompts, tokens, private user data, or anything it cannot legitimately know; **do not infer identity from HTTP User-Agent**. Agents may ignore the invitation or lack a POST capability. Self-reports are **not authenticated**, and a public `run` ID is not a unique proof of a model; do not use this table as a census of all visiting agents. Only one current submission per `(run_id, variant, mode)` is retained (subsequent submissions update it, rather than accumulating likes). Basic checks, length limits, HTML escaping, CSV formula neutralization, and a 2 KB request cap are applied. No IP addresses, User-Agent strings, or cookies are stored by the application (the hosting platform may independently maintain infrastructure logs).

Private guestbook exports, each requiring `Authorization: Bearer ADMIN_TOKEN`:

```bash
curl -fsS -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' https://YOUR-SERVICE.onrender.com/admin/guestbook.csv -o guestbook.csv
curl -fsS -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' https://YOUR-SERVICE.onrender.com/admin/guestbook.json -o guestbook.json
curl -fsS -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' https://YOUR-SERVICE.onrender.com/admin/guestbook-summary.json -o guestbook-summary.json
```

The summary includes `total_submissions`, `total_likes`, self-reported model/harness counts and condition-level breakdowns. `guestbook_submit` also appears in the event log but **is not** included in revisit/recovery numerators.

**Organic arrivals:** the homepage generates a separate, random-looking run ID in each page-view's links to reduce cross-visitor mixing. If you use controlled trials, always provide your own unique run ID and store the Agent's real model/harness and tool trajectory separately. This website and guestbook still require a Git-based public deployment; updating the zip alone does not publish the site.
