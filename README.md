# 洁癖 Skill

洁癖 Skill 是一个用于审计 AI Agent Skill 使用情况的本地 Skill。它适用于 Codex 和 Claude Code，也可以作为普通脚本直接运行。它会扫描本机 Codex、Claude Code、Cursor 的 Skill 安装目录和历史记录，统计哪些 Skill 近期用过、调用了多少次、最后一次使用是什么时候，并给出清理建议。

语言 / Language：中文优先 | [English](#english-readme)

## 适合解决什么问题

- 想知道本机到底安装了哪些 Skill。
- 想分析 Claude Code、Codex、Cursor 各自调用 Skill 的频率。
- 想找出最近没有使用、长期闲置、可以考虑清理的 Skill。
- 想区分“真正调用过”和“只是出现在系统 Skill 列表里”的 Skill。
- 想为 Skill 清理做一个保守、可复核的决策表。

## 功能

- 盘点 Codex、Claude Code、Cursor 的已安装或已同步 Skill。
- 统计确认调用次数、近 30 天调用次数、会话数和最后使用时间。
- 按 `keep`、`review`、`cleanup-candidate` 给出建议。
- 合并同一插件的不同缓存版本，避免重复计数。
- 可选扫描 Desktop/Documents 下的项目级 Skill。
- 支持输出 Markdown 或 JSON。

## 安装

推荐使用 Skills CLI 安装：

```bash
npx skills add https://github.com/Pluviobyte/jiepi-skill --skill jiepi-skill
```

## 使用

在 Codex 或 Claude Code 里直接调用：

```text
使用 $jiepi-skill 分析我的 Skill 使用频率和清理建议
```

也可以直接运行脚本：

下面示例使用 Codex 安装路径；如果安装在 Claude Code，把 `~/.codex/skills/jiepi-skill` 替换为 `~/.claude/skills/jiepi-skill` 即可。

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py --format markdown
```

生成报告到指定文件：

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py \
  --format markdown \
  --output ~/Desktop/skill-usage-audit.md
```

包含项目级 Skill：

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py \
  --include-project-local \
  --format markdown
```

调整近期使用窗口：

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py --days 90
```

输出 JSON：

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py --format json
```

## 报告字段

| 字段 | 含义 |
|---|---|
| Skill | Skill 名称 |
| Scope | 来源平台，例如 `codex`、`claude`、`cursor`、`project-local` |
| Source | 更具体的来源，例如插件缓存或本地目录 |
| Calls | 确认调用次数 |
| Recent | 近期窗口内的确认调用次数，默认 30 天 |
| Sessions | 出现过调用的会话数 |
| Last used | 最后一次确认使用时间 |
| Recommendation | 建议：`keep`、`review`、`cleanup-candidate` |
| Reason | 给出建议的原因 |

## 统计口径

洁癖 Skill 默认只统计“确认使用”：历史记录里明确读取或引用了某个 Skill 的 `SKILL.md`，才算一次调用。

这个口径偏保守，目的是避免把系统自动展示的 Skill 清单、搜索结果、日志输出误判为真实调用。因此它可能低估一些“语义上用过但没有明确路径记录”的 Skill，但不容易虚高。

## 清理建议如何理解

- `keep`：近期使用过，或历史调用次数较多。
- `review`：历史上使用过，但最近没有使用，适合人工复核。
- `cleanup-candidate`：可用历史里没有发现确认调用，适合考虑停用、移除或继续观察。

对于插件提供的 Skill，建议优先评估是否还需要整个插件，不建议直接删除插件缓存目录。

<a id="english-readme"></a>

<details>
<summary>English README</summary>

# Jiepi Skill

Jiepi Skill audits local AI agent skill usage. It works as a Skill for Codex and Claude Code, and it can also be run as a plain script. It scans installed or synced skills for Codex, Claude Code, and Cursor, then produces a report with confirmed calls, recent usage, sessions, last-used timestamps, and cleanup recommendations.

## What It Helps With

- See which skills are installed locally.
- Analyze skill call frequency across Claude Code, Codex, and Cursor.
- Find stale or unused skills.
- Distinguish confirmed skill loads from plain system skill listings.
- Make conservative, reviewable cleanup decisions.

## Features

- Inventories Codex, Claude Code, and Cursor skills.
- Reports confirmed calls, recent calls, sessions, and last-used time.
- Labels skills as `keep`, `review`, or `cleanup-candidate`.
- Merges duplicate cache versions from the same plugin family.
- Optionally scans project-local skills under Desktop/Documents.
- Outputs Markdown or JSON.

## Install

Recommended installation with the Skills CLI:

```bash
npx skills add https://github.com/Pluviobyte/jiepi-skill --skill jiepi-skill
```

## Use

Invoke it in Codex or Claude Code:

```text
Use $jiepi-skill to analyze installed skills, recent usage, call counts, and cleanup recommendations.
```

Or run the script directly:

The examples below use the Codex install path. If you installed it for Claude Code, replace `~/.codex/skills/jiepi-skill` with `~/.claude/skills/jiepi-skill`.

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py --format markdown
```

Write a report to a file:

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py \
  --format markdown \
  --output ~/Desktop/skill-usage-audit.md
```

Include project-local skills:

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py \
  --include-project-local \
  --format markdown
```

Change the recent-use window:

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py --days 90
```

Output JSON:

```bash
python3 ~/.codex/skills/jiepi-skill/scripts/audit_skill_usage.py --format json
```

## Counting Rule

Jiepi Skill counts confirmed usage only: a history item must explicitly read or reference a skill's `SKILL.md`. This conservative rule avoids counting system inventories, search results, or log output as real usage.

It may undercount skills that were used semantically without an explicit path read, but it avoids inflated call counts.

## Recommendations

- `keep`: used recently or often enough historically.
- `review`: used before, but not recently.
- `cleanup-candidate`: no confirmed usage found in available histories.

For plugin-provided skills, review whether the whole plugin is still useful before deleting cache files directly.

</details>
