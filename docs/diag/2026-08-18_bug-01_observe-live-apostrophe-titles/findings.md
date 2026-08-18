# BUG-01 — apostrophe survives a live French title (fix validation)

## TL;DR

On the live instance now running the fork fix, a real spontaneous Gemini title `Homme vu à l'allée` is stored **with its apostrophe intact** (U+0027) at both the `Creating event` and `Inserting event into database` stages — the exact title the 2026-08-16 session captured being stored as `Homme vu à lallée` on upstream 1.7.1 — validating BUG-01 end to end on-site.

## Context

- **Date:** 2026-08-18, 11:03 CEST. Spontaneous live gate event — **not** a forced trigger.
- **Integration:** LLM Vision **`v1.7.1-raoul.3`** (fork `deploy`@`f1f3db86`) = `normalize_title` Layer 1 (PR #4) + cross-language sentence-boundary hardening (PR #5). Confirmed on the running container: `normalize_title` at `providers.py:160`, applied at `:370` and `:415`; the old whitelist `re.sub(r"[^a-zA-Z0-9…\s]", "", …)` is **absent**. `manifest.json` version stays `1.7.1` (upstream, per the fork's no-bump distribution model).
- **HA Core:** 2026.1.3.
- **Provider / model:** Google, `gemini-2.5-flash` (gate `event_summary` config). This slice is INFO-level — the raoul.3 `docker restart` reset the runtime debug level, so there is no per-event provider request/response line here; the `11:05:19` provider-error line confirms Google is the active provider.
- **Camera:** `camera.camera_gate_profile1` (gate `event_summary`).
- **Pre-experiment state:** HA was moved from the manual `da6f45e` install to the `v1.7.1-raoul.3` HACS beta earlier the same day; the French `title_prompt` asks for normal contractions, so the model emits apostrophes naturally.

## Actions taken

1. `01_observe-live-events` — captured the integration-scoped log slice around the live 11:03 gate event (record-aware filter on `custom_components.llmvision`, ANSI stripped, PII redacted). No controlled trigger: passive observation of a spontaneous event.

## Timeline (CEST)

- `11:03:42.4` — gate `event_summary` starts; keyframes fetched via the camera proxy (`REDACTED-LAN-HOST`).
- `11:03:58.822` — timeline `Creating event` with title `Homme vu à l'allée` — **apostrophe present**.
- `11:03:58.824` — `Inserting event into database` with the same title, apostrophe still present (2 ms later).

## Findings

- **The stored title keeps its apostrophe.** `01_observe-live-events.llmvision.log`, `11:03:58.822` and `.824`: `title=Homme vu à l'allée`. The apostrophe is **U+0027** (confirmed by a codepoint dump: `l`=U+006C, `'`=U+0027, `a`=U+0061). This is the same input title the 2026-08-16 session recorded being stored as `Homme vu à lallée` on byte-identical-to-upstream 1.7.1 — **same text, opposite outcome**, now preserved.
- **Preservation holds across both writer stages observed** — `Creating event` (CalendarEvent/timeline) and `Inserting event into database` — with no strip in the 2 ms between them, i.e. the loss the old `re.sub` caused at `providers.py:286` is gone.
- **The running integration is the fix, not upstream:** `normalize_title` at `providers.py:160` (applied `:370`/`:415`), old whitelist regex absent — verified in the `hass` container.
- **The description keeps its apostrophes as it always did** (`l'allée`, `s'éloignant`, same `Creating event` line) — no regression on the path that was already correct.

## Open questions

- **U+2019 (curly apostrophe) is not exercised by a live title** — this model emitted U+0027. Layer 1 preserves both by construction and the CI suite pins both, but no live capture has shown U+2019 surviving end to end.
- **PR #5's cross-language boundary hardening is CI-only** — abbreviations (`M.`/`Mr.`), CJK/Hindi/Arabic boundaries are covered by pinned tests, not by a live event.
- **Layer 2 (card `textContent`, `llmvision-card#1` HARD-01) is not shipped** — the card still renders via `innerHTML`; a live `<`/`>` title is untested end to end on the dashboard. The backend now stores faithful `<`/`>`, so this is the remaining exposure.

## Refs

- refs #2 (BUG-01) — this session validates the fix on-site (the strip proven by the 2026-08-16 session is gone).
- Fix landed on `deploy`: PR #4 (`normalize_title` Layer 1), PR #5 (i18n boundary hardening); released as pre-release `v1.7.1-raoul.3`.
- Prior session: [2026-08-16_bug-01_run-event-summary-title-strip](../2026-08-16_bug-01_run-event-summary-title-strip/findings.md) — the strip this validates against.

## PII redaction

Camera-proxy token and LAN host → `REDACTED-TOKEN` / `REDACTED-LAN-HOST`. AI title/description strings kept verbatim (operator decision, same as the 2026-08-16 session). Snapshot files referenced by filename only; no image content committed.
