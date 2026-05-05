"""Codebase scanner — produces a structured feature manifest.

What we extract
---------------
- **Modules**    : top-level service / common / lib directories
- **Models**     : LoopBack models in common/models/ (presence + count)
- **Agents**     : files under server/agents/ or common/agents/
- **DevRev**     : presence of common/devrev/ adapter
- **Integrations** : entries in package.json hinting at 3rd-party systems
                     (oracle, salesforce, kafka, sap, twilio, sendgrid, ...)
- **API endpoints** : LoopBack remote-method declarations and Express routes
                     (best-effort regex grep; not an exhaustive parser)
- **Doc files**  : README / hld / AGENTS / CLAUDE / docs/* / **/README.md
- **Migrations** : db_migrations/ filenames (signal of recent schema work)

We deliberately do NOT execute the codebase or pull dependencies — pure
static read. Safe to point at any repo without side effects.

Output JSON shape
-----------------
{
  "scan_metadata": {...},
  "summary":       {...},      # high-level counts
  "modules":       [...],      # top-level functional dirs
  "models":        {...},      # model directory analysis
  "agents":        [...],      # detected agent / worker files
  "integrations":  [...],      # 3rd-party deps from package.json
  "endpoints":     [...],      # API endpoints (best-effort)
  "doc_files":     [...],      # paths to README / hld / etc.
  "devrev":        {...},      # existing DevRev integration (if any)
  "migrations":    {...}       # migration counts and recent files
}
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# What to skip (large directories that produce noise)
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    "node_modules", ".git", ".github", ".cursor", ".claude",
    "log", "logs", "dump.rdb", "custom-certificates",
    "TPN01",  # client-specific snapshot dir
}

DOC_FILE_NAMES = {
    "readme.md", "readme", "hld.md", "agents.md", "claude.md",
    "architecture.md", "design.md", "api.md",
}

INTEGRATION_KEYWORDS = {
    "oracle":     ["oracle", "oracledb", "oci-", "@oracle"],
    "sap":        ["sap-", "@sap", "sap-cloud"],
    "salesforce": ["jsforce", "salesforce", "sfdc"],
    "kafka":      ["kafka", "kafkajs", "@confluentinc"],
    "rabbitmq":   ["amqplib", "rabbitmq"],
    "redis":      ["redis", "ioredis"],
    "mongodb":    ["mongodb", "mongoose"],
    "postgres":   ["pg", "pg-promise", "postgresql", "sequelize"],
    "elasticsearch": ["elasticsearch", "@elastic"],
    "twilio":     ["twilio"],
    "sendgrid":   ["sendgrid", "@sendgrid"],
    "aws":        ["aws-sdk", "@aws-sdk"],
    "gcp":        ["@google-cloud", "googleapis"],
    "azure":      ["@azure"],
    "stripe":     ["stripe"],
    "razorpay":   ["razorpay"],
    "twilio":     ["twilio"],
    "firebase":   ["firebase", "firebase-admin"],
    "graphql":    ["graphql", "apollo"],
    "loopback":   ["loopback", "@loopback"],
    "devrev":     ["devrev", "@devrev"],
    "anthropic":  ["@anthropic-ai", "anthropic"],
    "openai":     ["openai", "@openai"],
}

# Best-effort regex for LoopBack remote-method declarations and Express
# routes. Will miss programmatic registrations; not a substitute for an
# OpenAPI spec.
LOOPBACK_REMOTE_RE = re.compile(
    r"\.remoteMethod\(\s*['\"]([\w$]+)['\"]", re.MULTILINE
)
EXPRESS_ROUTE_RE = re.compile(
    r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)


def _git_sha(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def _git_branch(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def _scan_top_level(root: Path) -> list[dict]:
    """List functional directories at the repo root."""
    modules: list[dict] = []
    for entry in sorted(root.iterdir()):
        if entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        if not entry.is_dir():
            continue
        # Count source files inside (capped to avoid runaway walks)
        js_count = sum(
            1 for _ in entry.rglob("*.js")
            if not any(p in SKIP_DIRS for p in _.parts)
        )
        json_count = sum(
            1 for _ in entry.rglob("*.json")
            if not any(p in SKIP_DIRS for p in _.parts)
        )
        modules.append({
            "name": entry.name,
            "path": str(entry.relative_to(root)),
            "js_files": js_count,
            "json_files": json_count,
        })
    return modules


def _scan_models(root: Path) -> dict:
    """common/models/ analysis — model count + categories."""
    models_dir = root / "common" / "models"
    if not models_dir.is_dir():
        return {"present": False}

    js_files = list(models_dir.glob("*.js"))
    json_files = list(models_dir.glob("*.json"))

    # Categorise by name prefix to surface top domain areas
    name_buckets: dict[str, int] = {}
    for f in js_files:
        stem = f.stem.lower()
        prefix = stem.split("-")[0]
        name_buckets[prefix] = name_buckets.get(prefix, 0) + 1

    top_buckets = sorted(name_buckets.items(), key=lambda kv: -kv[1])[:20]

    return {
        "present": True,
        "path": "common/models",
        "model_count_js": len(js_files),
        "model_count_json": len(json_files),
        "top_name_prefixes": [
            {"prefix": p, "count": c} for p, c in top_buckets
        ],
    }


def _scan_agents(root: Path) -> list[dict]:
    """Detect agent / worker files under any 'agents/' directory."""
    agents: list[dict] = []
    for agents_dir in root.rglob("agents"):
        if not agents_dir.is_dir():
            continue
        if any(p in SKIP_DIRS for p in agents_dir.parts):
            continue
        for f in sorted(agents_dir.iterdir()):
            if f.is_file() and f.suffix in (".js", ".ts"):
                agents.append({
                    "name": f.stem,
                    "path": str(f.relative_to(root)),
                })
    return agents


def _scan_devrev(root: Path) -> dict:
    """Detect existing DevRev integration in the codebase."""
    devrev_dir = root / "common" / "devrev"
    if not devrev_dir.is_dir():
        return {"present": False}
    files = sorted(
        str(p.relative_to(root)) for p in devrev_dir.rglob("*")
        if p.is_file()
    )
    return {
        "present": True,
        "path": "common/devrev",
        "files": files,
    }


def _scan_integrations(root: Path) -> list[dict]:
    """Read package.json deps and bucket them by 3rd-party system."""
    pkg = root / "package.json"
    if not pkg.is_file():
        return []
    try:
        data = json.loads(pkg.read_text())
    except json.JSONDecodeError:
        return []

    all_deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        all_deps.update(data.get(key, {}))

    detected: list[dict] = []
    for system, keywords in INTEGRATION_KEYWORDS.items():
        matched = [
            {"name": name, "version": version}
            for name, version in all_deps.items()
            if any(k in name.lower() for k in keywords)
        ]
        if matched:
            detected.append({"system": system, "matched_packages": matched})
    return detected


def _scan_endpoints(root: Path, max_files: int = 800) -> dict:
    """Best-effort grep for LoopBack remote methods + Express routes.

    Caps file count so we don't burn time on huge codebases. Walks
    common/, server/, lib/, alerts/ specifically — high-signal dirs.
    """
    target_dirs = ["common", "server", "lib", "alerts", "agents", "templates"]
    seen_files = 0
    remote_methods: list[str] = []
    express_routes: list[dict] = []

    for d in target_dirs:
        dd = root / d
        if not dd.is_dir():
            continue
        for f in dd.rglob("*.js"):
            if seen_files >= max_files:
                break
            if any(p in SKIP_DIRS for p in f.parts):
                continue
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            for m in LOOPBACK_REMOTE_RE.finditer(text):
                remote_methods.append(m.group(1))
            for m in EXPRESS_ROUTE_RE.finditer(text):
                express_routes.append({
                    "method": m.group(1).upper(),
                    "path": m.group(2),
                    "file": str(f.relative_to(root)),
                })
            seen_files += 1

    # De-duplicate remote method names
    remote_methods = sorted(set(remote_methods))
    return {
        "scanned_files": seen_files,
        "loopback_remote_methods_count": len(remote_methods),
        "loopback_remote_methods_sample": remote_methods[:50],
        "express_routes_count": len(express_routes),
        "express_routes_sample": express_routes[:50],
    }


def _scan_docs(root: Path) -> list[dict]:
    """Find README / hld / design / architecture markdown files."""
    docs: list[dict] = []
    for f in root.rglob("*.md"):
        if any(p in SKIP_DIRS for p in f.parts):
            continue
        if f.name.lower() in DOC_FILE_NAMES:
            try:
                line_count = sum(1 for _ in f.open())
            except OSError:
                line_count = 0
            docs.append({
                "path": str(f.relative_to(root)),
                "lines": line_count,
            })
    return sorted(docs, key=lambda d: -d["lines"])[:50]


def _scan_migrations(root: Path) -> dict:
    """Migration count + 5 most recent filenames."""
    mig = root / "db_migrations"
    if not mig.is_dir():
        return {"present": False}
    files = sorted(
        (str(p.relative_to(root)) for p in mig.rglob("*")
         if p.is_file() and not p.name.startswith(".")),
        reverse=True,
    )
    return {
        "present": True,
        "path": "db_migrations",
        "file_count": len(files),
        "recent_sample": files[:10],
    }


def scan(repo_root: Path) -> dict:
    """Full scan. Pure read, no side effects."""
    repo_root = repo_root.resolve()

    summary = {}
    modules = _scan_top_level(repo_root)
    summary["modules_count"] = len(modules)

    models = _scan_models(repo_root)
    summary["models_count"] = (
        models.get("model_count_js", 0) + models.get("model_count_json", 0)
    )

    agents = _scan_agents(repo_root)
    summary["agents_count"] = len(agents)

    devrev = _scan_devrev(repo_root)
    summary["devrev_present"] = devrev.get("present", False)

    integrations = _scan_integrations(repo_root)
    summary["integrations_count"] = len(integrations)

    endpoints = _scan_endpoints(repo_root)
    summary["loopback_remote_methods"] = endpoints["loopback_remote_methods_count"]
    summary["express_routes"] = endpoints["express_routes_count"]

    docs = _scan_docs(repo_root)
    summary["doc_files"] = len(docs)

    migrations = _scan_migrations(repo_root)
    summary["migrations_count"] = migrations.get("file_count", 0)

    return {
        "scan_metadata": {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "codebase_root": str(repo_root),
            "git_sha": _git_sha(repo_root),
            "git_branch": _git_branch(repo_root),
        },
        "summary": summary,
        "modules": modules,
        "models": models,
        "agents": agents,
        "devrev": devrev,
        "integrations": integrations,
        "endpoints": endpoints,
        "doc_files": docs,
        "migrations": migrations,
    }
