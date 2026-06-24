---
name: jiepi-skill
description: "洁癖 Skill: Audit installed AI agent skills across Codex, Claude, Cursor, and optional project-local skill folders. Use when the user asks which skills are installed, how often Claude/Codex/Cursor used skills, whether a skill was used recently, which skills are stale or unused, or wants cleanup/removal/disable recommendations for skills."
---

# 洁癖 Skill

## Overview

Use this skill to inventory installed skills, count confirmed historical usage, show recent activity, and produce cleanup recommendations. Prefer the bundled script for deterministic scanning instead of hand-writing ad hoc searches.

## Workflow

1. Run `scripts/audit_skill_usage.py` from this skill folder.
2. Use the default scan for installed/synced skills:

   ```bash
   python3 scripts/audit_skill_usage.py --format markdown
   ```

3. Add `--include-project-local` only when the user explicitly wants repository-local skills under Desktop/Documents included. This can find many source/test/example skills that are not globally installed.
4. Use `--days N` to define the recent-use window. Default is 30 days.
5. Save a report when useful:

   ```bash
   python3 scripts/audit_skill_usage.py --format markdown --output /tmp/skill-usage.md
   ```

## Counting Rules

- Treat the default call count as **confirmed usage**: a historical transcript or rollout explicitly referenced/read the skill's `SKILL.md`.
- Do not count system/developer skill lists as usage.
- Count each skill at most once per log line or tool call.
- Prefer cleanup suggestions phrased as `keep`, `review`, or `cleanup-candidate`; do not delete files automatically unless the user separately asks for removal.
- For plugin-provided skills, suggest disabling the plugin or reviewing plugin value before deleting cache files.

## Interpreting Results

- `keep`: used recently or used often enough historically.
- `review`: used before, but not inside the recent-use window.
- `cleanup-candidate`: no confirmed usage found in available histories.
- `scope`: distinguishes `codex`, `claude`, `cursor`, and `project-local` sources so installed tools are not mixed with repository examples.

When presenting results, lead with totals, the top used skills, and the cleanup candidates. Mention the counting rule so the user understands that unconfirmed use may be undercounted.
