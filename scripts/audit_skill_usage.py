#!/usr/bin/env python3
"""Audit installed AI-agent skills and confirmed usage in local histories."""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKILL_FILE = "SKILL.md"


@dataclass
class Skill:
    key: str
    name: str
    scope: str
    source_type: str
    source: str
    path: str
    installed_at: str = ""


@dataclass
class Usage:
    calls: int = 0
    recent_calls: int = 0
    sessions: int = 0
    last_used: str = ""


def read_text(path: Path, limit: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def parse_frontmatter_name(path: Path) -> str:
    text = read_text(path, 4000)
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            for line in block.splitlines():
                if line.strip().startswith("name:"):
                    return line.split(":", 1)[1].strip().strip("\"'")
    return path.parent.name


def iso_from_millis(value: int | float | str | None) -> str:
    if value in (None, ""):
        return ""
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return str(value)
    if raw > 10_000_000_000:
        raw /= 1000
    return dt.datetime.fromtimestamp(raw, dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str | int | float | None) -> dt.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000
        return dt.datetime.fromtimestamp(raw, dt.timezone.utc)
    text = str(value)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


def mtime_iso(path: Path) -> str:
    try:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except OSError:
        return ""


def skill_key(scope: str, name: str, path: Path) -> str:
    return f"{scope}:{name}:{str(path)}"


def add_skill(skills: dict[str, Skill], scope: str, source_type: str, source: str, path: Path, installed_at: str = "") -> None:
    if not path.exists() or path.name != SKILL_FILE:
        return
    name = parse_frontmatter_name(path)
    key = skill_key(scope, name, path)
    skills[key] = Skill(key, name, scope, source_type, source, str(path), installed_at)


def add_glob(skills: dict[str, Skill], scope: str, source_type: str, source: str, pattern: str, installed_at: str = "") -> None:
    for raw in glob.glob(pattern, recursive=True):
        add_skill(skills, scope, source_type, source, Path(raw), installed_at)


def codex_inventory(home: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    codex = home / ".codex"
    agents = home / ".agents"
    add_glob(skills, "codex", "codex-system-or-local", "codex skills", str(codex / "skills" / "**" / SKILL_FILE))
    add_glob(skills, "codex", "codex-personal", "agents skills", str(agents / "skills" / "*" / SKILL_FILE))

    plugin_root = codex / "plugins" / "cache"
    for raw in glob.glob(str(plugin_root / "**" / "skills" / "*" / SKILL_FILE), recursive=True):
        path = Path(raw)
        rel = path.relative_to(plugin_root)
        parts = rel.parts
        source = "/".join(parts[:3]) if len(parts) >= 3 else str(rel)
        add_skill(skills, "codex", "codex-plugin-cache", source, path)
    return skills


def claude_inventory(home: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    claude = home / ".claude"
    add_glob(skills, "claude", "claude-local", "claude skills", str(claude / "skills" / "*" / SKILL_FILE))

    installed = claude / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(read_text(installed, 2_000_000))
    except json.JSONDecodeError:
        data = {}
    for plugin_name, entries in (data.get("plugins") or {}).items():
        for entry in entries or []:
            install_path = Path(entry.get("installPath", ""))
            installed_at = entry.get("installedAt", "")
            if install_path.exists():
                add_glob(
                    skills,
                    "claude",
                    "claude-installed-plugin",
                    plugin_name,
                    str(install_path / "**" / SKILL_FILE),
                    installed_at,
                )
    return skills


def cursor_inventory(home: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    cursor = home / ".cursor"
    manifest_path = cursor / "skills-cursor" / ".sync-manifest.json"
    synced: dict[str, str] = {}
    try:
        manifest = json.loads(read_text(manifest_path, 1_000_000))
        for name, meta in (manifest.get("skills") or {}).items():
            synced[name] = iso_from_millis(meta.get("lastSyncedAt"))
    except json.JSONDecodeError:
        pass
    for raw in glob.glob(str(cursor / "skills-cursor" / "*" / SKILL_FILE)):
        path = Path(raw)
        add_skill(skills, "cursor", "cursor-synced", "cursor skills", path, synced.get(path.parent.name, ""))
    return skills


def project_local_inventory(home: Path, roots: list[Path]) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    ignored = {".git", "node_modules", "dist", "build", ".next", ".venv", "venv"}
    markers = (
        "/.agents/skills/",
        "/.claude/skills/",
        "/.gemini/skills/",
        "/.qwen/skills/",
        "/skills/",
    )
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ignored]
            if SKILL_FILE not in filenames:
                continue
            path = Path(dirpath) / SKILL_FILE
            as_posix = str(path)
            if not any(marker in as_posix for marker in markers):
                continue
            add_skill(skills, "project-local", "project-local", root.name, path)
    return skills


def build_inventory(args: argparse.Namespace) -> dict[str, Skill]:
    home = Path(args.home).expanduser()
    skills: dict[str, Skill] = {}
    for inventory in (codex_inventory(home), claude_inventory(home), cursor_inventory(home)):
        skills.update(inventory)
    if args.include_project_local:
        roots = [Path(p).expanduser() for p in args.project_root]
        skills.update(project_local_inventory(home, roots))
    return dedupe_inventory(skills)


def dedupe_inventory(skills: dict[str, Skill]) -> dict[str, Skill]:
    """Collapse repeated cache versions while preserving different platforms/plugins."""
    selected: dict[tuple[str, str, str, str], Skill] = {}
    for skill in skills.values():
        family = source_family(skill)
        identity = (skill.scope, skill.source_type, family, skill.name)
        previous = selected.get(identity)
        if previous is None:
            selected[identity] = skill
            continue
        previous_mtime = parse_time(mtime_iso(Path(previous.path))) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        current_mtime = parse_time(mtime_iso(Path(skill.path))) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        if current_mtime >= previous_mtime:
            selected[identity] = skill
    return {skill.key: skill for skill in selected.values()}


def source_family(skill: Skill) -> str:
    """Return a stable origin label for versioned plugin/cache sources."""
    if "plugin" in skill.source_type:
        parts = [part for part in skill.source.split("/") if part]
        if len(parts) >= 2 and parts[0].startswith("openai-"):
            return parts[1]
        if parts:
            return re.sub(r"^@[^/]+/", "", parts[0])
    return re.sub(r"/(latest|[0-9][^/]*|[0-9a-f]{8,})$", "", skill.source)


def source_label(skill: Skill) -> str:
    family = source_family(skill)
    if family and ("plugin" in skill.source_type or family != skill.source):
        return f"{skill.source_type}:{family}"
    return skill.source_type


def json_line_time(obj: dict, fallback_path: Path) -> dt.datetime | None:
    for key in ("timestamp", "created_at", "createdAt", "ts", "time"):
        if key in obj:
            parsed = parse_time(obj.get(key))
            if parsed:
                return parsed
    return parse_time(mtime_iso(fallback_path))


def json_session_id(obj: dict, path: Path) -> str:
    payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    for container in (obj, payload):
        for key in ("sessionId", "session_id", "thread_id", "conversation_id", "id"):
            if key in container and container.get(key):
                return str(container.get(key))
    return path.stem


def extract_search_text(obj: dict) -> str:
    chunks: list[str] = []
    def walk(value):
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    walk(obj)
    return "\n".join(chunks)


def candidate_text_for_history_line(obj: dict, history_path: Path) -> str:
    """Return only user/assistant/tool-call text that can indicate a real skill load.

    Codex rollout files include command outputs, which may contain large inventories
    of `SKILL.md` paths. Counting those outputs makes an audit contaminate itself,
    so for Codex only inspect actual function-call arguments.
    """
    raw_path = str(history_path)
    if "/.codex/" in raw_path:
        if obj.get("type") != "response_item":
            return ""
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        if payload.get("type") != "function_call":
            return ""
        return str(payload.get("arguments") or "")

    # Claude/Cursor formats vary more. Skip obvious command result/output records.
    typ = str(obj.get("type", "")).lower()
    if typ in {"tool_result", "tool_output", "function_call_output"}:
        return ""
    return extract_search_text(obj)


def history_files(home: Path) -> list[Path]:
    patterns = [
        home / ".codex" / "archived_sessions" / "*.jsonl",
        home / ".codex" / "sessions" / "**" / "*.jsonl",
        home / ".claude" / "projects" / "**" / "*.jsonl",
        home / ".cursor" / "projects" / "**" / "agent-transcripts" / "**" / "*.jsonl",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(Path(p) for p in glob.glob(str(pattern), recursive=True))
    return sorted(set(files))


def make_aliases(skills: dict[str, Skill]) -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {key: set() for key in skills}
    for key, skill in skills.items():
        path = Path(skill.path)
        aliases[key].add(str(path))
        aliases[key].add(str(path).replace(str(Path.home()), "~"))
        aliases[key].add(f"skills/{path.parent.name}/{SKILL_FILE}")
        aliases[key].add(f"/{path.parent.name}/{SKILL_FILE}")
    return aliases


def history_scope(path: Path) -> str | None:
    raw = str(path)
    if "/.codex/" in raw:
        return "codex"
    if "/.claude/" in raw:
        return "claude"
    if "/.cursor/" in raw:
        return "cursor"
    return None


def scan_usage(skills: dict[str, Skill], args: argparse.Namespace) -> dict[str, Usage]:
    home = Path(args.home).expanduser()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    aliases = make_aliases(skills)
    usage = {key: Usage() for key in skills}
    sessions: dict[str, set[str]] = {key: set() for key in skills}
    read_markers = re.compile(r"\b(cat|sed|nl|head|tail|less|more|awk|python3?|node|ruby|perl|Read|read_file|open)\b")
    list_only = re.compile(r"^\s*(find|rg|grep)\b")

    for path in history_files(home):
        scope = history_scope(path)
        try:
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if SKILL_FILE not in line and "$" not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = candidate_text_for_history_line(obj, path)
                if not text:
                    continue
                if "Available skills" in text and "### How to use skills" in text:
                    continue
                if not read_markers.search(text):
                    continue
                if list_only.search(text):
                    continue
                matched = [
                    key
                    for key, vals in aliases.items()
                    if (scope is None or skills[key].scope in {scope, "project-local"})
                    and any(alias and alias in text for alias in vals)
                ]
                if not matched:
                    continue
                ts = json_line_time(obj, path)
                session = json_session_id(obj, path)
                for key in set(matched):
                    usage[key].calls += 1
                    if ts and ts >= cutoff:
                        usage[key].recent_calls += 1
                    if ts:
                        iso = ts.isoformat().replace("+00:00", "Z")
                        if not usage[key].last_used or iso > usage[key].last_used:
                            usage[key].last_used = iso
                    sessions[key].add(session)
    for key, seen in sessions.items():
        usage[key].sessions = len(seen)
    return usage


def recommendation(skill: Skill, usage: Usage, args: argparse.Namespace) -> tuple[str, str]:
    if usage.recent_calls > 0:
        return "keep", "Used inside the recent-use window."
    if usage.calls >= args.keep_threshold:
        return "keep", f"Used {usage.calls} times historically."
    if usage.calls > 0:
        return "review", "Used historically, but not recently."
    if skill.scope == "codex" and "system" in skill.source_type:
        return "review", "No confirmed usage, but this may be a core/system skill."
    if "plugin" in skill.source_type:
        return "cleanup-candidate", "No confirmed usage; consider disabling the plugin or reviewing whether it is still needed."
    return "cleanup-candidate", "No confirmed usage found in available histories."


def rows(skills: dict[str, Skill], usage: dict[str, Usage], args: argparse.Namespace) -> list[dict]:
    out = []
    for key, skill in skills.items():
        use = usage[key]
        rec, reason = recommendation(skill, use, args)
        item = asdict(skill)
        item.update(asdict(use))
        item["source_label"] = source_label(skill)
        item["recommendation"] = rec
        item["reason"] = reason
        out.append(item)
    rank = {"keep": 0, "review": 1, "cleanup-candidate": 2}
    return sorted(out, key=lambda r: (rank.get(r["recommendation"], 9), -r["recent_calls"], -r["calls"], r["scope"], r["name"]))


def emit_markdown(data: list[dict], args: argparse.Namespace) -> str:
    total = len(data)
    called = sum(1 for r in data if r["calls"] > 0)
    recent = sum(1 for r in data if r["recent_calls"] > 0)
    cleanup = sum(1 for r in data if r["recommendation"] == "cleanup-candidate")
    lines = [
        "# Skill Usage Audit",
        "",
        f"- Skills inventoried: {total}",
        f"- Skills with confirmed usage: {called}",
        f"- Skills used in last {args.days} days: {recent}",
        f"- Cleanup candidates: {cleanup}",
        "- Counting rule: confirmed usage means a history item referenced a skill path/name or read `SKILL.md`; system skill inventories are ignored.",
        "",
        "| Skill | Scope | Source | Calls | Recent | Sessions | Last used | Recommendation | Reason |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for r in data:
        lines.append(
            "| `{name}` | {scope} | {source_label} | {calls} | {recent_calls} | {sessions} | {last_used} | {recommendation} | {reason} |".format(
                **{k: str(v).replace("|", "\\|") for k, v in r.items()}
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit installed skills and confirmed local usage.")
    parser.add_argument("--home", default=str(Path.home()), help="Home directory to scan.")
    parser.add_argument("--days", type=int, default=30, help="Recent-use window in days.")
    parser.add_argument("--keep-threshold", type=int, default=10, help="Historical calls needed to keep even if not recent.")
    parser.add_argument("--include-project-local", action="store_true", help="Include project-local SKILL.md files under project roots.")
    parser.add_argument("--project-root", action="append", default=[str(Path.home() / "Desktop"), str(Path.home() / "Documents")])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", help="Write report to this path.")
    args = parser.parse_args(argv)

    skills = build_inventory(args)
    usage = scan_usage(skills, args)
    data = rows(skills, usage, args)

    if args.format == "json":
        rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    else:
        rendered = emit_markdown(data, args)

    if args.output:
        Path(args.output).expanduser().write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
