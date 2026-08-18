# Diagnostic experiments

Raw artifacts of timed diagnostic sessions against the live Home Assistant
instance running the LLM Vision integration (and its timeline card). Each
session is self-contained and immutable once merged; later sessions
supersede rather than rewrite. Not installed by HACS.

## Sessions

One row per experiment session. Each session lands as its own PR that
either drives a fix/feature design or validates it.

| Date | Issue | Question | Answer (TL;DR) | Link |
| ---- | ----- | -------- | -------------- | ---- |
| 2026-08-16 | [BUG-01](https://github.com/raouldekezel/ha-llmvision/issues/2) | Does the title sanitizer strip apostrophes from a real French title on the live instance, while the description keeps them? | Yes — Gemini title `Homme vu à l'allée` is stored as `Homme vu à lallée` (apostrophe gone) 5 ms after the provider response, while the same event's description keeps `d'un`/`l'allée`. Confirms BUG-01 end-to-end at `providers.py:286`. | [2026-08-16_bug-01_run-event-summary-title-strip](2026-08-16_bug-01_run-event-summary-title-strip/findings.md) |
| 2026-08-18 | [BUG-01](https://github.com/raouldekezel/ha-llmvision/issues/2) | On the fork fix (`v1.7.1-raoul.3`), does a real French title with an apostrophe survive end to end on the live instance, unlike the pre-fix strip? | Yes — spontaneous Gemini title `Homme vu à l'allée` (U+0027) is stored with the apostrophe intact at both `Creating event` and DB insert; the running integration has `normalize_title` and no whitelist regex. Same title as the 2026-08-16 strip, now preserved — validates BUG-01 on-site. | [2026-08-18_bug-01_observe-live-apostrophe-titles](2026-08-18_bug-01_observe-live-apostrophe-titles/findings.md) |

## Layout

```
docs/diag/
├── README.md                                # this file (= the index)
└── YYYY-MM-DD_<id>_<short-topic>/
    ├── findings.md
    ├── NN_<action>.llmvision.log            # HA log slice, logger-filtered + ANSI stripped
    └── NN_<action>.<evidence>               # other evidence: redacted provider request/response excerpts, timeline event dumps, entity polls
```

- Subdirectory name uses an action-anchored topic (e.g.
  `2026-09-02_bug-01_timeline-duplicate-events`), never a finding-anchored
  one.
- `NN_` numeric prefix gives chronological order; the slug describes the
  **action taken**, never the **outcome** (findings get revised; actions
  don't).

## Capturing the `.llmvision.log`

The `.llmvision.log` is a slice of `docker logs hass` **filtered to this
integration's own logger** (`custom_components.llmvision`) — never a raw,
unfiltered dump. A bare `docker logs hass` slice also captures every other
component active in the same window (presence / `device_tracker`,
reverse-geocoding, camera proxies, weather, automations): analysis noise
that **also carries unrelated third-party PII** — household-member
locations, camera access tokens, LAN addresses. Logger scoping is the
first line of PII defense; the value-level redaction below is the second.
**This is mandatory**, not best-effort.

Filter **record by record, not line by line**, so multi-line records —
tracebacks from `_LOGGER.exception()`, pretty-printed payloads — are kept
whole. A plain `grep` on the logger tag keeps only the first line and
drops the rest:

```
docker logs hass --since <ISO-ts> 2>&1 \
  | sed -r 's/\x1b\[[0-9;]*m//g' \
  | awk '/ (DEBUG|INFO|WARNING|ERROR|CRITICAL) \(/ { keep = /\[custom_components\.llmvision/ } keep' \
  > NN_<action>.llmvision.log
```

The `awk` starts a new record on each `… LEVEL (thread) …` line and keeps
it — plus its continuation lines — only when the logger is `llmvision`.
Format-agnostic (works with or without `docker logs -t`).

**Caveat:** an unretrieved async-task crash is logged by HA core under
`[homeassistant]`, with `llmvision` only in the stack frames — a
logger-scoped filter misses it. When chasing a crash specifically, also
grep the full log for the traceback.

## findings.md

Required structure, in this order:

1. **TL;DR** — one sentence stating the answer to the session's question.
2. **Context** — date, **fork tag or commit SHA** of the integration
   running during the experiment, HA version, providers and models
   involved (e.g. `gpt-4o-mini`, `gemini-…`, local endpoint), camera
   entities involved, relevant pre-experiment state.
3. **Actions taken** — numbered list matching the `NN_…` prefixes.
4. **Timeline** — key timestamps with what happened at each. Evidence
   layer; survives even if the conclusions are later revised.
5. **Findings** — bullet list. Each conclusion cites a specific line or
   timestamp from the included files.
6. **Open questions** — what the next session would need to answer.
7. **Refs** — issues, PRs, previous or follow-up sessions.

## PII to redact

LLM Vision's core output is natural-language narration of what the
cameras saw. **Treat every AI-generated description string as PII until
read and redacted**, and never commit image content of any kind — the
snapshots show people and the inside of the home.

| Real value                                                     | Redacted form                                 |
| --------------------------------------------------------------- | --------------------------------------------- |
| Provider API keys (OpenAI, Anthropic, Google, Groq, …)         | `REDACTED-API-KEY-<PROVIDER>`                 |
| Base64 image payloads / data URLs                               | `[IMAGE-PAYLOAD-REDACTED n bytes]`            |
| Snapshot / media file contents                                  | never committed — reference by filename only  |
| Household member / visitor names in descriptions               | `REDACTED-NAME`                               |
| License plates in descriptions                                  | `REDACTED-PLATE`                              |
| Street addresses / location names in descriptions              | `REDACTED-ADDRESS`                            |
| HA long-lived access tokens, webhook ids                       | `REDACTED-TOKEN` / `REDACTED-WEBHOOK`         |
| LAN hostnames / IPs of local inference endpoints (Ollama, …)   | `REDACTED-LAN-HOST`                           |
| Email address                                                   | `REDACTED-EMAIL`                              |
| Account / device UUIDs                                          | `REDACTED-UUID-<purpose>`                     |

**Keep** timestamps, numeric UTC offsets, log levels, thread and module
names, provider and model identifiers, event/entry ids, durations, token
counts, HTTP status codes, and camera entity ids once the surrounding
description text has been reviewed — entity ids are needed to correlate
events; the descriptions are where the household leaks.

When in doubt, redact.

## Drift-proof index

The `## Sessions` table above is the index. To prevent it from drifting
out of sync with the actual subdirectory list, `scripts/check_diag_index.py`
fails if any `docs/diag/<date>_<topic>/` subdirectory is missing from the
table, or if any table row points to a non-existent directory.

This is enforced by the **Check diag index** GitHub Actions workflow
(`.github/workflows/check-diag-index.yaml`), which runs on every push and
pull request that touches `docs/diag/` or the check script itself. A PR
that adds a session without updating the table (or vice versa) fails CI.

Run it locally first to fail fast:

```
python3 scripts/check_diag_index.py
```

The session PR is expected to add one row to the table **in the same
commit** that adds the subdirectory.

## Adding a new session

1. Branch from `deploy`: `git checkout -b patches/docs-diag-<id>-<date>`.
2. Run the experiment; redact PII on the copies in `/tmp` first.
3. Create `docs/diag/<date>_<id>_<topic>/` and populate.
4. Write `findings.md` last, in front of the raw files.
5. Add the row to the `## Sessions` table here.
6. Run `python3 scripts/check_diag_index.py`.
7. Open one PR per session targeting `deploy`.
