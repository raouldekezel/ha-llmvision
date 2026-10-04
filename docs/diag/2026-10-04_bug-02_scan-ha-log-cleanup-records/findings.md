# BUG-02 — "Failed to remove" snapshot warnings in the live HA log

## TL;DR

Every `Failed to remove … No such file or directory` warning in three days of live log comes from the **same snapshot being selected by two or three cleanup passes within about a millisecond**: one pass deletes it, each other pass fails, which can only happen with several cleanup passes running concurrently on the same folder.

## Context

- **Date:** 2026-10-04, passive analysis of the Home Assistant log covering 2026-10-01 16:43 → 2026-10-04 10:28 CEST. No controlled trigger.
- **Integration:**
  - 2026-10-01 16:43 → 2026-10-03 ~17:05: `v1.7.1-raoul.3`;
  - from 2026-10-03 17:05 (HA restart): `v1.7.2-raoul.1` (fork `deploy` @ `f8d8fc1`).
  - The code involved is identical in both: `timeline.py`, `api.py` and `calendar.py` are unchanged between the two tags; `__init__.py` differs by one unrelated line (message truncation in the notification service).
- **HA Core:** 2026.7.4 (as reported by `/api/config`).
- **Providers / cameras:** not relevant to this session. The snapshots involved are all named `<8-hex>-camera0.jpg`.
- **Pre-experiment state:** several LLM Vision timeline cards on dashboards (card `v1.7.2-raoul.1`, upstream fetch throttle at 15 s); periodic `image_analyzer` gate checks every 15 minutes; two HA restarts in the window (2026-10-01 16:43, 2026-10-03 17:05).

## Actions taken

1. `01_scan-ha-log-cleanup-records` — concatenated `home-assistant.log.1` and `home-assistant.log` from the `hass` container, stripped ANSI codes, applied the record-aware `custom_components.llmvision` filter from `docs/diag/README.md`, then kept only the `[CLEANUP]` records (all single-line; 197 records). This is stricter than the logger scope: the rest of the slice carries AI-generated text that this session does not need.
2. `02_tally-cleanup-passes-per-file` — grouped the records into bursts (consecutive records less than 5 s apart) and counted, per burst and per file, the `Removing unlinked snapshot` lines ("passes") and the `Failed to remove` warnings.

## Timeline (CEST)

- 30 cleanup bursts over the window, from 1 to 29 `Removing` lines each (`02`).
- 26 bursts have every file selected exactly once → no warning.
- 4 bursts have files selected several times, and they carry all 29 warnings:
  - `2026-10-02 11:43:40` — 13 files, 4 selected twice, 3 three times, 10 warnings;
  - `2026-10-03 18:32:12` — 2 files, 1 selected three times, 2 warnings;
  - `2026-10-03 22:44:21` — 4 files, 1 selected twice, 1 warning;
  - `2026-10-04 09:42:13` — 13 files, 8 selected twice, 4 three times, 16 warnings.

## Findings

- **Each failing file is selected more than once within about a millisecond.** Example, `01`, `2026-10-04 09:42:13.084`–`.086`: three `Removing unlinked snapshot: 3950a2fb-camera0.jpg` lines followed by two `Failed to remove …/3950a2fb-camera0.jpg` warnings. Same shape for `209c18d1-camera0.jpg` at `2026-10-02 11:43:40.591`–`.593` and `3685dacb-camera0.jpg` at `2026-10-03 18:32:12.838`–`.840`.
- **Failures = passes − 1, for every file, in every burst** (`02`, consistency check): exactly one removal succeeds per file, and no failure occurs without a matching `Removing` line. The files were present when they were selected and were removed by another pass; there is no permission or storage problem.
- **A single pass cannot select the same file twice**: `_cleanup()` iterates over one `os.listdir()` of the snapshots folder (`timeline.py:990`), which has no duplicates. Two or three selections of the same file therefore mean two or three **concurrent** passes.
- **The per-instance lock does not prevent this.** `_cleanup()` holds `self._cleanup_lock` (`timeline.py:981`), created per `Timeline` instance (`timeline.py:211`). Every instance schedules its own cleanup from its constructor (`timeline.py:224`), and instances are created per access (`api.py:104` for each card fetch, other views, actions, the calendar entity, setup). Instances created close together run unserialized passes over the same folder.
- **Volume:** 168 selections, 139 distinct files removed, 29 warnings over three days. Only 4 of the 30 bursts overlap; in the other 26, passes did not run at the same time and every file was selected once.
- **No sign of upstream's `#735` data-loss path here:** zero `database is locked` lines in the full HA log for the same window.

## Open questions

- **Which callers started the concurrent passes at each failing burst** (several card fetches when a dashboard opens? card fetch + calendar update?) is not visible: instance creation is not logged. Answering it needs debug logging or the HTTP access log around a reproduced burst, for example by opening a dashboard with several timeline cards after a quiet period.
- **Why 139 snapshots became unlinked in three days** (for example, frames from analyses not stored in the timeline) is outside BUG-02's scope; the cleanup itself removed them correctly.

## Refs

- refs #9 (BUG-02) — this session is the field evidence behind the issue's root cause.
- Upstream: `valentinfrlch/ha-llmvision#676` (same symptom, different diagnosis), `valentinfrlch/ha-llmvision#735` (related cleanup data loss, not observed here).

## PII redaction

Nothing to redact: the `[CLEANUP]` records contain only timestamps, log levels, module names and generic snapshot filenames (`<8-hex>-camera0.jpg`) under `/media/llmvision/snapshots/`. No AI-generated text, no host, token or image content is included.
