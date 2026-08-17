# Hamroh — codebase rules

Post-discharge patient monitoring. Flask + Jinja2 + SQLite + Tailwind CDN + vanilla JS polling.
Full architecture spec: PLAN.md (authoritative).

## Hard rules
- SQL lives ONLY in `repos/`. Routes do HTTP, services do logic.
- New persona / question / day = new row in a migration. Zero Python changes.
  Never branch on `persona_key`.
- New behavior goes in `analyzers/`, `hooks/`, or `notifiers/` as a NEW FILE — not as an
  `if` inside an existing service.
- Schema changes = new numbered file in `migrations/`. Never edit an applied migration.
- All `/api/v1/*` responses use `core/responses.ok()` / `fail()`. No hand-built JSON shapes.
- LLM prompts live in `prompts/*.txt`, never inline in Python.
- LLM output is untrusted: parse defensively, always fall back to `rule_analyzer`.
- Secrets in `.env` only. `.env`, `*.db`, `__pycache__/` are gitignored.

## Language
User-facing text (UI, questions, messages, user-visible errors): Uzbek, Latin script.
Code, comments, commits: English.

## Commands
    python app.py            # dev server
    pytest -q                # smoke tests
    curl localhost:5000/health

## Before finishing any task
Start the app, exercise the changed path, run pytest, and paste real output. Do not claim
something works without running it.
