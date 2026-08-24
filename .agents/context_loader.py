#!/usr/bin/env python3
"""Render and validate task-scoped agent context."""

import argparse
import hashlib
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / ".agents/context-routing.yml"
PHASES = tuple(f"P{number}" for number in range(8))
REQUIRED_REVIEW_FIELDS = {
    "kind",
    "status",
    "reviewed_at",
    "source_revision",
    "source_digest",
    "scope",
    "parent",
    "read_when",
    "target_authority",
    "roadmap_phases",
}


class ContextError(Exception):
    """User-facing routing or validation failure."""


@dataclass(frozen=True)
class Section:
    path: str
    heading: str
    lines: tuple[str, ...]


def load_manifest() -> dict[str, Any]:
    try:
        data = yaml.safe_load(MANIFEST_PATH.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ContextError(
            f"cannot load {MANIFEST_PATH.relative_to(REPO_ROOT)}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ContextError("routing manifest must be a YAML mapping")
    return data


def glob_regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                parts.append(".*")
                index += 2
            else:
                parts.append("[^/]*")
                index += 1
        elif char == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(char))
            index += 1
    parts.append("$")
    return re.compile("".join(parts))


def matches(path: str, patterns: str | Iterable[str]) -> bool:
    if isinstance(patterns, str):
        patterns = [patterns]
    return any(glob_regex(pattern).fullmatch(path) for pattern in patterns)


def normalize_intended_path(raw_path: str) -> str:
    path = PurePosixPath(raw_path.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ContextError(f"path must be repository-relative: {raw_path}")
    normalized = path.as_posix()
    if normalized == ".":
        raise ContextError("path must name an intended file or directory")
    return normalized


def tracked_files() -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files"], cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ContextError(f"cannot list tracked files: {exc}") from exc
    return [line for line in output.splitlines() if line]


def heading_index(
    path: Path,
) -> tuple[
    list[str], dict[str, list[tuple[int, str]]], dict[tuple[int, str], tuple[int, int]]
]:
    lines = path.read_text().splitlines()
    headings: list[tuple[int, int, str]] = []
    aliases: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for line_number, line in enumerate(lines):
        match = re.match(r"^(#{2,6})\s+(.+)$", line)
        if not match:
            continue
        level = len(match.group(1))
        heading = match.group(2).strip()
        label = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", heading)
        headings.append((line_number, level, heading))
        aliases[heading].append((level, heading))
        aliases[label].append((level, heading))

    ranges: dict[tuple[int, str], tuple[int, int]] = {}
    for position, (start, level, heading) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_start
                break
        ranges[(level, heading)] = (start, end)
    return lines, aliases, ranges


def resolve_section(path_text: str, selector: str) -> Section:
    path = REPO_ROOT / path_text
    if not path.is_file():
        raise ContextError(f"referenced file does not exist: {path_text}")
    lines, aliases, ranges = heading_index(path)
    choices = set(aliases.get(selector, []))
    if not choices:
        raise ContextError(f"section {selector!r} not found in {path_text}")
    if len(choices) > 1:
        headings = ", ".join(sorted(heading for _, heading in choices))
        raise ContextError(
            f"section {selector!r} is ambiguous in {path_text}: {headings}"
        )
    key = next(iter(choices))
    start, end = ranges[key]
    return Section(path_text, key[1], tuple(lines[start:end]))


def parse_frontmatter(path_text: str) -> dict[str, Any]:
    path = REPO_ROOT / path_text
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ContextError(f"review lacks YAML frontmatter: {path_text}")
    try:
        frontmatter = yaml.safe_load(text.split("---\n", 2)[1])
    except yaml.YAMLError as exc:
        raise ContextError(f"invalid review frontmatter in {path_text}: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise ContextError(f"review frontmatter must be a mapping: {path_text}")
    return frontmatter


def validate_ref(ref: Any, allowed_phases: Iterable[str], label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(ref, dict) or set(ref) != {"path", "sections", "phases"}:
        return [f"{label}: reference requires exactly path, sections, phases"]
    if not isinstance(ref["path"], str) or "*" in ref["path"]:
        errors.append(f"{label}: dependency path must be an exact file")
    if not isinstance(ref["sections"], list) or not ref["sections"]:
        errors.append(f"{label}: sections must be a non-empty list")
    if not isinstance(ref["phases"], list) or not ref["phases"]:
        errors.append(f"{label}: phases must be a non-empty list")
    elif not set(ref["phases"]).issubset(set(allowed_phases)):
        errors.append(f"{label}: phases exceed owning phase set")
    if not errors:
        for selector in ref["sections"]:
            try:
                resolve_section(ref["path"], selector)
            except ContextError as exc:
                errors.append(f"{label}: {exc}")
        if ref["path"].endswith(".agent-review"):
            try:
                review_phases = set(
                    parse_frontmatter(ref["path"]).get("roadmap_phases", [])
                )
                if not set(ref["phases"]).issubset(review_phases):
                    errors.append(f"{label}: phases exceed referenced review metadata")
            except (ContextError, TypeError) as exc:
                errors.append(f"{label}: cannot validate review phases: {exc}")
    return errors


def refs_for_phases(
    refs: Iterable[dict[str, Any]], phases: set[str]
) -> Iterable[dict[str, Any]]:
    return (ref for ref in refs if phases.intersection(ref["phases"]))


def selected_routes(
    manifest: dict[str, Any], paths: list[str]
) -> list[tuple[str, dict[str, Any]]]:
    selected: list[tuple[str, dict[str, Any]]] = []
    unmatched: list[str] = []
    for path in paths:
        route_names = [
            name
            for name, route in manifest["routes"].items()
            if matches(path, route["match"])
        ]
        if not route_names:
            unmatched.append(path)
        for name in route_names:
            if all(existing_name != name for existing_name, _ in selected):
                selected.append((name, manifest["routes"][name]))
    if unmatched:
        raise ContextError("unmatched intended path(s): " + ", ".join(unmatched))
    return selected


def render_context(
    manifest: dict[str, Any],
    work_packages: list[str],
    raw_paths: list[str],
    conditions: list[str],
) -> str:
    package_map = manifest.get("work_packages", {})
    unknown_packages = [
        package for package in work_packages if package not in package_map
    ]
    if unknown_packages:
        raise ContextError("unknown work package(s): " + ", ".join(unknown_packages))
    phases = {package_map[package] for package in work_packages}
    paths = [normalize_intended_path(path) for path in raw_paths]
    routes = selected_routes(manifest, paths)

    known_conditions = {
        condition for _, route in routes for condition in route.get("conditional", {})
    }
    unknown_conditions = sorted(set(conditions) - known_conditions)
    if unknown_conditions:
        raise ContextError(
            "condition(s) do not apply to matched routes: "
            + ", ".join(unknown_conditions)
        )

    refs: list[dict[str, Any]] = []
    rules = manifest["rules"]
    refs.extend(refs_for_phases([rules["authority"]], phases))
    refs.extend(refs_for_phases([rules["shared_current_context"]], phases))
    refs.extend(refs_for_phases(rules["active_roadmap_sections"], phases))
    for _, route in routes:
        refs.extend(refs_for_phases(route["required"], phases))
    for _, route in routes:
        refs.extend(refs_for_phases(route["target_plans"], phases))

    selected_condition_count = 0
    for _, route in routes:
        for name, condition in route.get("conditional", {}).items():
            automatic = bool(condition.get("match")) and any(
                matches(path, condition["match"]) for path in paths
            )
            if name not in conditions and not automatic:
                continue
            phase_refs = list(refs_for_phases(condition["refs"], phases))
            if name in conditions and not phase_refs:
                raise ContextError(
                    f"condition {name!r} has no references for active phase(s)"
                )
            selected_condition_count += bool(phase_refs)
            refs.extend(phase_refs)

    if conditions and selected_condition_count == 0:
        raise ContextError("selected conditions produced no context")

    sections: list[Section] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        if ref["path"].endswith(".agent-review"):
            frontmatter = parse_frontmatter(ref["path"])
            if frontmatter.get("status") == "stale":
                raise ContextError(f"selected review is stale: {ref['path']}")
        for selector in ref["sections"]:
            section = resolve_section(ref["path"], selector)
            if (
                section.path == ".agents/plans/20-migration-roadmap.md"
                and re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", section.heading)
                == "Work Package Register"
            ):
                selected_rows = tuple(
                    line
                    for line in section.lines
                    if not line.startswith("| `P")
                    or any(
                        line.startswith(f"| `{package}` ") for package in work_packages
                    )
                )
                section = Section(section.path, section.heading, selected_rows)
            key = (section.path, section.heading)
            if key not in seen:
                seen.add(key)
                sections.append(section)

    body: list[str] = [
        "# Agent Context",
        "",
        f"Work packages: {', '.join(work_packages)}",
        f"Phases: {', '.join(sorted(phases))}",
        f"Intended paths: {', '.join(paths)}",
        f"Conditions: {', '.join(conditions) if conditions else 'none'}",
    ]
    context_lines = 0
    for section in sections:
        body.extend(["", f"<!-- source: {section.path} :: {section.heading} -->"])
        body.extend(section.lines)
        context_lines += len(section.lines)
    body.extend(["", f"<!-- context-lines: {context_lines} -->"])
    return "\n".join(body) + "\n"


def digest_files(scope: list[str], files: list[str]) -> tuple[str, list[str]]:
    selected = sorted(
        path
        for path in files
        if matches(path, scope)
        and not path.endswith("/.agent-review")
        and not path.startswith("server/tests/")
        and not path.startswith("server/static/")
        and "/__pycache__/" not in path
        and not path.endswith((".pyc", ".pyo"))
    )
    digest = hashlib.sha256()
    for path in selected:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((REPO_ROOT / path).read_bytes())
    return f"sha256:{digest.hexdigest()}", selected


def empty_or_comments(path: str) -> bool:
    for line in (REPO_ROOT / path).read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return False
    return True


def coverage_errors(manifest: dict[str, Any], files: list[str]) -> list[str]:
    coverage = manifest.get("coverage", {})
    include = coverage.get("include", [])
    exclusions = coverage.get("exclude", [])
    errors: list[str] = []
    for path in files:
        if not matches(path, include):
            continue
        excluded = False
        for exclusion in exclusions:
            if not matches(path, exclusion["match"]):
                continue
            if exclusion["when"] == "always":
                excluded = True
            elif exclusion["when"] == "empty_or_comments" and empty_or_comments(path):
                excluded = True
            break
        if excluded:
            continue
        route_names = [
            name
            for name, route in manifest.get("routes", {}).items()
            if matches(path, route.get("match", []))
        ]
        if not route_names:
            errors.append(f"unmatched covered file: {path}")
    return errors


def check_manifest(manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("version") != 3:
        errors.append("manifest version must be 3")
    rules = manifest.get("rules", {})
    expected_order = [
        "authority_summary",
        "shared_current_context",
        "active_roadmap_sections",
        "matched_route_required_sections",
        "active_phase_target_sections",
        "triggered_conditional_sections",
    ]
    if rules.get("task_read_order") != expected_order:
        errors.append("task_read_order does not match required render order")

    package_map = manifest.get("work_packages", {})
    if not isinstance(package_map, dict) or not package_map:
        errors.append("work_packages must be a non-empty mapping")
    elif any(phase not in PHASES for phase in package_map.values()):
        errors.append("work_packages contains an invalid phase")
    roadmap = REPO_ROOT / ".agents/plans/20-migration-roadmap.md"
    roadmap_ids = set(re.findall(r"`(P[0-7]-W\d+)`", roadmap.read_text()))
    if set(package_map) != roadmap_ids:
        errors.append(
            "work-package mapping differs from roadmap: "
            f"missing={sorted(roadmap_ids - set(package_map))}, "
            f"extra={sorted(set(package_map) - roadmap_ids)}"
        )

    for name in ("authority", "shared_current_context"):
        errors.extend(validate_ref(rules.get(name), PHASES, f"rules.{name}"))
    for index, ref in enumerate(rules.get("active_roadmap_sections", [])):
        errors.extend(
            validate_ref(ref, PHASES, f"rules.active_roadmap_sections[{index}]")
        )

    graph: dict[str, set[str]] = defaultdict(set)
    for route_name, route in manifest.get("routes", {}).items():
        phases = route.get("roadmap_phases", [])
        if not phases or not set(phases).issubset(PHASES):
            errors.append(f"routes.{route_name}: invalid roadmap_phases")
        if not isinstance(route.get("match"), list) or not route["match"]:
            errors.append(f"routes.{route_name}: match must be non-empty")
        owners = {
            ref["path"]
            for ref in route.get("required", [])
            if isinstance(ref, dict)
            and str(ref.get("path", "")).endswith(".agent-review")
        }
        for index, ref in enumerate(route.get("required", [])):
            errors.extend(
                validate_ref(ref, phases, f"routes.{route_name}.required[{index}]")
            )
        for condition_name, condition in route.get("conditional", {}).items():
            if not isinstance(condition, dict) or set(condition) != {
                "apply_when",
                "match",
                "refs",
            }:
                errors.append(
                    f"routes.{route_name}.conditional.{condition_name}: "
                    "requires apply_when, match, refs"
                )
                continue
            if (
                not isinstance(condition["apply_when"], str)
                or not condition["apply_when"].strip()
            ):
                errors.append(
                    f"routes.{route_name}.conditional.{condition_name}: empty apply_when"
                )
            if not isinstance(condition["match"], list):
                errors.append(
                    f"routes.{route_name}.conditional.{condition_name}: match must be a list"
                )
            for index, ref in enumerate(condition["refs"]):
                errors.extend(
                    validate_ref(
                        ref,
                        phases,
                        f"routes.{route_name}.conditional.{condition_name}.refs[{index}]",
                    )
                )
                dependency = ref.get("path") if isinstance(ref, dict) else None
                if (
                    dependency
                    and dependency.endswith(".agent-review")
                    and dependency not in owners
                ):
                    for owner in owners:
                        graph[owner].add(dependency)
        for index, ref in enumerate(route.get("target_plans", [])):
            errors.extend(
                validate_ref(ref, phases, f"routes.{route_name}.target_plans[{index}]")
            )

    for source, dependencies in graph.items():
        for dependency in dependencies:
            if source in graph.get(dependency, set()):
                errors.append(f"symmetric review dependency: {source} <-> {dependency}")

    files = tracked_files()
    errors.extend(coverage_errors(manifest, files))
    reviews = sorted(
        path
        for path in files
        if path.endswith("/.agent-review") or path == "server/.agent-review"
    )
    for review in reviews:
        try:
            frontmatter = parse_frontmatter(review)
        except ContextError as exc:
            errors.append(str(exc))
            continue
        missing = REQUIRED_REVIEW_FIELDS - set(frontmatter)
        if missing:
            errors.append(f"{review}: missing frontmatter fields {sorted(missing)}")
            continue
        if frontmatter["kind"] != "current-state-review":
            errors.append(f"{review}: kind must be current-state-review")
        if frontmatter["status"] not in {"verified-current", "stale"}:
            errors.append(f"{review}: invalid status {frontmatter['status']!r}")
        if not isinstance(frontmatter["reviewed_at"], (str, date)):
            errors.append(f"{review}: reviewed_at must be an ISO date")
        if not re.fullmatch(r"[0-9a-f]{40}", str(frontmatter["source_revision"])):
            errors.append(f"{review}: source_revision must be a full Git revision")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(frontmatter["source_digest"])):
            errors.append(f"{review}: source_digest must be sha256:<64 lowercase hex>")
        if not isinstance(frontmatter["scope"], list) or not frontmatter["scope"]:
            errors.append(f"{review}: scope must be a non-empty list")
        parent = frontmatter["parent"]
        if parent is not None and (
            not isinstance(parent, str)
            or "*" in parent
            or not (REPO_ROOT / parent).is_file()
        ):
            errors.append(f"{review}: parent must be null or an exact existing review")
        if (
            not isinstance(frontmatter["read_when"], list)
            or not frontmatter["read_when"]
        ):
            errors.append(f"{review}: read_when must be a non-empty list")
        authorities = frontmatter["target_authority"]
        if not isinstance(authorities, list) or not authorities:
            errors.append(f"{review}: target_authority must be a non-empty list")
        elif any(
            "*" in path or not (REPO_ROOT / path).is_file() for path in authorities
        ):
            errors.append(
                f"{review}: target_authority must contain exact existing files"
            )
        review_phases = frontmatter["roadmap_phases"]
        if (
            not isinstance(review_phases, list)
            or not review_phases
            or not set(review_phases).issubset(PHASES)
        ):
            errors.append(f"{review}: invalid roadmap_phases")
        expected_digest, _ = digest_files(frontmatter["scope"], files)
        if frontmatter["source_digest"] != expected_digest:
            message = (
                f"{review}: source digest mismatch; expected {expected_digest}, "
                f"found {frontmatter['source_digest']}"
            )
            if frontmatter.get("status") == "verified-current":
                errors.append(message)
            else:
                warnings.append(message)

    for budget in manifest.get("context_budgets", []):
        try:
            rendered = render_context(
                manifest, [budget["work_package"]], [budget["path"]], []
            )
            match = re.search(r"context-lines: (\d+)", rendered)
            line_count = int(match.group(1)) if match else 0
            if line_count > budget["max_lines"]:
                errors.append(
                    f"context budget exceeded for {budget['work_package']} {budget['path']}: "
                    f"{line_count}>{budget['max_lines']}"
                )
        except ContextError as exc:
            errors.append(f"context budget cannot render: {exc}")
    return errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    render = subparsers.add_parser(
        "render", help="render task-scoped context to stdout"
    )
    render.add_argument("--work-package", action="append", required=True)
    render.add_argument("--path", action="append", required=True)
    render.add_argument("--condition", action="append", default=[])
    subparsers.add_parser(
        "check", help="validate routing, coverage, and review freshness"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = load_manifest()
        if args.command == "render":
            sys.stdout.write(
                render_context(manifest, args.work_package, args.path, args.condition)
            )
            return 0
        errors, warnings = check_manifest(manifest)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        print(
            f"context routing valid: version={manifest['version']} "
            f"routes={len(manifest['routes'])} reviews=12"
        )
        return 0
    except ContextError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
