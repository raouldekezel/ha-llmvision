# BUG-01 — event_summary title apostrophe strip (live capture)

## TL;DR

On the live instance, a real Gemini-generated title `Homme vu à l'allée` is stored and rendered as `Homme vu à lallée` — the apostrophe is dropped 5 ms after the provider returns it — while the *same* event's description keeps its apostrophes, confirming BUG-01 end to end at `providers.py:286`.

## Context

- **Date:** 2026-08-16, ~19:14 CEST.
- **Integration:** LLM Vision **v1.7.1** (fork `deploy`@`1a8eb968` at capture time; the title sanitizer at `providers.py:286` is byte-identical to upstream 1.7.1).
- **HA Core:** 2026.1.3.
- **Provider / model:** Google, `gemini-2.5-flash`.
- **Camera:** `camera.camera_gate_profile1` (gate `event_summary`).
- **Pre-experiment state:** integration debug logging enabled at runtime (`logger.set_level custom_components.llmvision=debug`); the French `title_prompt` explicitly asks for correct accents and normal contractions, so the model emits apostrophes naturally (it is the sanitizer, not the prompt, that removes them).

## Actions taken

1. `01_run-event-summary` — enabled `custom_components.llmvision` debug logging, triggered the gate `event_summary` (driveway motion), and captured the integration-scoped log slice (record-aware filter, ANSI stripped, PII redacted).

## Timeline (CEST)

- `19:13:53.9` — `event_summary` starts; keyframes fetched.
- `19:14:03.556` — provider returns the **description**, apostrophes intact (`d'un`, `l'allée`).
- `19:14:06.376` — provider returns the **raw title** `Homme vu à l'allée`.
- `19:14:06.381` — timeline event created with title `Homme vu à lallée` (apostrophe gone), 5 ms later.

## Findings

- **The provider-generated title carries the apostrophe.** `01_run-event-summary.llmvision.log`, `19:14:06.376`: `'text': "Homme vu à l'allée"`.
- **The stored/rendered title has it stripped.** Same file, `19:14:06.381`: `title=Homme vu à lallée`. The 5 ms gap after the provider response shows the loss is local (the `re.sub` at `providers.py:286`), not a model output.
- **The same event's description keeps its apostrophes** (`d'un`, `l'allée`) — same `Creating event` line — since the description is not passed through the title regex. This isolates the defect to the title path.
- **Deterministic and unconditional:** the strip does not depend on provider or call type; it is the whitelist omitting `'` (U+0027).

## Open questions

- Which remediation (A/B/C in #2) is adopted — in particular whether upstream prefers `html.escape` (B) or the card `textContent` fix (C).
- None observed regarding calendar/ICS storage of apostrophes (the description already stores them correctly).

## Refs

- refs #2 (BUG-01) — the bug this session proves.
- Repo work from the same session: #1 (CHORE-01, distribution model) — unrelated pathology.

## PII redaction

Neighbor surnames → `REDACTED-NAME`; camera-proxy token / LAN host → `REDACTED-TOKEN` / `REDACTED-LAN-HOST`; image payloads already reduced to `<long_string>` by the integration. The AI description string is kept verbatim (operator decision).
