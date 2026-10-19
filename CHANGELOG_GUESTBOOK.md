# 2026-10-19 — Agent Guestbook Update

Added voluntary likes and self-reported model/harness labels for passing agents.

- `GET /guestbook/{variant}?run=...&mode=...` HTML visitor form.
- `POST /api/guestbook/{variant}?run=...&mode=...` JSON or form POST.
- `GET /admin/guestbook.json`, `/admin/guestbook.csv`, `/admin/guestbook-summary.json` private exports with `Bearer ADMIN_TOKEN`.
- Like counts are one current entry per `(run_id, variant, mode)`; an updated submission replaces the prior like status.
- Model/harness fields are **unverified claims** and may be `unknown`. The app never asks for system prompts, secrets, or user-private information.
- Guestbook events have `route=guestbook_submit` and do **not** count as retries. Initial failure pages remain unchanged to reduce confounds.
- No stored IP addresses, User-Agent strings, cookies, or referrers in the app. The hosting platform may keep its own logs.
- The original 503 and 403 failure behavior is unchanged. Organic links on homepage get fresh run IDs.
- `9` Python tests and scripted smoke requests have passed locally; no public deployment or genuine visiting agents verified.
