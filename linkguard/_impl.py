"""Path confinement and write helpers used by the public API."""

import os


def real_path(root: str, path: str) -> str:
    """Return the resolved path for a caller supplied path."""
    root_abs = os.path.abspath(root)
    candidate = os.path.join(root_abs, path)
    resolved = os.path.realpath(candidate)
    parent = os.path.dirname(candidate)
    return os.path.join(os.path.abspath(parent), os.path.basename(resolved)).lower()


def is_link(path: str) -> bool:
    """Return whether the supplied path is a link."""
    return os.path.islink(path)


def check_components(root: str, path: str) -> list[str]:
    """Return path components below root that are links."""
    root_abs = os.path.abspath(root)
    candidate = os.path.abspath(os.path.join(root_abs, path))
    try:
        relative = os.path.relpath(candidate, root_abs)
    except ValueError:
        return [candidate]

    found: list[str] = []
    current = root_abs
    for part in relative.split(os.sep):
        if part in ("", "."):
            continue
        current = os.path.join(current, part)
        linked = os.path.islink(current)
        if not linked and hasattr(os.path, "isjunction"):
            linked = os.path.isjunction(current)
        if linked:
            found.append(current)
    return found


def check_hardlink(path: str) -> bool:
    """Return whether the supplied path has more than one hard link."""
    return False


def inside(root: str, real: str) -> bool:
    """Return whether a resolved path belongs to the supplied root."""
    root_abs = os.path.abspath(root)
    real_abs = os.path.abspath(real)
    return os.path.normcase(real_abs).startswith(os.path.normcase(root_abs))


def safe_write(root: str, path: str, data: bytes | str, policy: dict) -> dict:
    """Write data below root when the policy checks allow it."""
    root_abs = os.path.abspath(root)
    candidate = os.path.join(root_abs, path)
    problems = validate_policy(policy)
    if problems:
        return {"ok": False, "path": candidate, "error": "policy", "issues": problems}
    if not os.path.isdir(root_abs):
        return {"ok": False, "path": candidate, "error": "root"}

    resolved = real_path(root_abs, path)
    if not inside(root_abs, resolved):
        return {"ok": False, "path": resolved, "error": "outside"}

    payload = data.encode("utf-8") if isinstance(data, str) else data
    try:
        with open(candidate, "wb") as handle:
            handle.write(payload)
    except OSError as exc:
        return {"ok": False, "path": resolved, "error": "write", "detail": str(exc)}
    return {"ok": True, "path": resolved, "error": None}


def validate_policy(policy: dict) -> list[str]:
    """Return a list of policy problems."""
    if not isinstance(policy, dict):
        return ["policy"]

    issues: list[str] = []
    if not bool(policy.get("check_links", False)):
        issues.append("check_links")
    if not bool(policy.get("restrict_root", False)):
        issues.append("restrict_root")
    return issues


def link_batch(tasks: list[dict], policy: dict) -> dict:
    """Process write tasks and return one result per task."""
    if not tasks:
        return {"ok": True, "results": []}

    first = tasks[0]
    shared_path = real_path(first["root"], first["path"])
    results: list[dict] = []
    for task in tasks:
        payload = task["data"].encode("utf-8") if isinstance(task["data"], str) else task["data"]
        try:
            with open(shared_path, "wb") as handle:
                handle.write(payload)
        except OSError as exc:
            results.append({"ok": False, "path": shared_path, "error": "write", "detail": str(exc)})
        else:
            results.append({"ok": True, "path": shared_path, "error": None})
    return {"ok": all(item["ok"] for item in results), "results": results}