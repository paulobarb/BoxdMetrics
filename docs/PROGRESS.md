# Progress

Session log for BoxdMetrics. Newest entry first. Claude reads this at the start of every session and updates it at the end.

## Current state

- **Prod:** backend on Lambda (`boxdmetrics-api-prod`, eu-north-1), frontend on Vercel. Deploys on push to `main` via GitHub Actions.
- **Tests:** 20 passing (`test_etl.py`, `test_routes.py`). Ruff 0.15.6 and Bandit clean.
- **Docs:** README revised after the Nov 2026 review (spoofable rate limit and full "Known gaps" list now documented).

## Next up

<!-- Keep this list short: 3–5 items max. Move done items into the log below. -->
- [ ] Decide the next item from the roadmap (see Obsidian: *BoxdMetrics Roadmap 2027*)
- [ ] Key the rate limiter on the Lambda request-context source IP instead of `X-Forwarded-For`
- [ ] Remove the `dev_secret_123` fallback in `core/config.py` (fail fast if `API_SECRET_KEY` is missing)
- [ ] Add a non-root `USER` to both Dockerfiles

## Open questions

- No `backend "s3"` block found in `infra/terraform/*.tf`, although a state bucket is created in `main.tf`. Is Terraform state currently local?

## Log

### 2026-11-20
- Added `CLAUDE.md` and this file to keep context between Claude Code sessions.
- Decision: use Claude Code's built-in memory (CLAUDE.md + auto memory + this file) instead of claude-mem. It's simpler, versioned in Git, and costs no extra tokens.
