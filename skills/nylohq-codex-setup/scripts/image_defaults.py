#!/usr/bin/env python3
"""Install the image skill and an explicitly chosen personal LB fallback default."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import uuid

import setup as s

START = "<!-- nylohq-image-default:start -->"
END = "<!-- nylohq-image-default:end -->"


def preference_text(original, fragment):
    text = original.decode("utf-8-sig") if original is not None else ""
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise s.SetupError("Image preference markers are inconsistent. Preserve the file and review it manually.")
        start, end = text.index(START), text.index(END)
        if end < start:
            raise s.SetupError("Image preference markers are out of order. Nothing was changed.")
        return (text[:start] + START + "\n" + fragment.rstrip() + "\n" + END + text[end + len(END):]).encode("utf-8")
    return (text + ("\n\n" if text and not text.endswith("\n\n") else "") + START + "\n" + fragment.rstrip() + "\n" + END + "\n").encode("utf-8")


def install(home, skills_dir):
    templates = Path(__file__).resolve().parent.parent / "assets/image-default"
    target = skills_dir / "nylohq-imagegen"
    helper = skills_dir / "nylohq-codex-setup/scripts/image_cli.py"
    if not helper.is_file():
        raise s.SetupError("Install the complete updated nylohq-codex-setup skill in --skills-dir first.")
    for p in (skills_dir, target, target / "agents"):
        s.reject_link(p)
    fragment = (templates / "AGENTS.fragment.md").read_text().replace("IMAGE_SKILL_FILE", str(target / "SKILL.md")).replace("IMAGE_HELPER_FILE", str(helper))
    files = {
        home / "AGENTS.md": None,
        target / "SKILL.md": (templates / "SKILL.template.md").read_bytes(),
        target / "agents/openai.yaml": (templates / "openai.template.yaml").read_bytes(),
    }
    before = {p: s.read_optional(p) for p in files}
    files[home / "AGENTS.md"] = preference_text(before[home / "AGENTS.md"], fragment)
    changed = {p: value for p, value in files.items() if value != before[p]}
    if not changed:
        return {"status": "already_configured", "image_skill": str(target), "preference": str(home / "AGENTS.md")}
    backup_root = home / "backups"
    s.reject_link(backup_root)
    backup = backup_root / ("image-default-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    s.private_dir(backup)
    manifest = []
    for index, p in enumerate(changed):
        name = str(index) + ".before"
        if before[p] is not None:
            s.atomic_write(backup / name, before[p])
        manifest.append({"path": str(p), "existed": before[p] is not None, "backup": name if before[p] is not None else None})
    s.atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode())
    written = []
    try:
        for p, value in changed.items():
            if s.read_optional(p) != before[p]:
                raise s.SetupError("A target changed during installation; stopped rather than overwriting it.")
            p.parent.mkdir(parents=True, exist_ok=True)
            s.atomic_write(p, value)
            written.append(p)
    except Exception:
        for p in reversed(written):
            if before[p] is None:
                p.unlink(missing_ok=True)
            else:
                s.atomic_write(p, before[p])
        raise
    return {"status": "configured", "image_skill": str(target), "preference": str(home / "AGENTS.md"), "backup": str(backup), "credentials_changed": False, "server_changed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home")
    parser.add_argument("--skills-dir", required=True)
    parser.add_argument("--choose-api-fallback", action="store_true", help="Record the member's explicit choice to use this existing LB fallback for requested images")
    args = parser.parse_args(argv)
    if not args.choose_api_fallback:
        s.emit(status="error", message="This writes a personal backend preference. Use --choose-api-fallback only after the member chooses this default.")
        return 1
    try:
        result = install(s.codex_home(args.home), Path(args.skills_dir).expanduser().absolute())
        s.emit(**result)
        return 0
    except (s.SetupError, OSError, UnicodeError) as exc:
        s.emit(status="error", message=str(exc) if isinstance(exc, s.SetupError) else "Could not install the local image defaults. Keep the backup and review the target paths.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
