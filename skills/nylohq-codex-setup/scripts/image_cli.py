#!/usr/bin/env python3
"""Run Codex's bundled image CLI with this member's existing NyloHQ key."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

import setup as s


def image_context(home):
    doc = s.parse_config(s.read_optional(home / "config.toml"))
    if doc.get("profile"):
        raise s.SetupError("A default profile is configured. Resolve its provider before using this helper.")
    provider_id = doc.get("model_provider")
    provider = doc.get("model_providers", {}).get(provider_id, {})
    if provider.get("base_url") != s.API:
        raise s.SetupError("The active provider is not the configured NyloHQ HTTPS endpoint. Nothing was sent.")
    key = s.read_key(home / "nylohq-lb/api-key")
    return provider_id, key


def run_image_cli(home, image_cli, arguments, python=None):
    _, key = image_context(home)
    if not image_cli.is_file():
        raise s.SetupError("Codex's bundled image CLI was not found. Locate its imagegen skill and pass --image-cli; do not replace it with a new SDK runner.")
    if not arguments or arguments[0] not in ("generate", "edit", "generate-batch"):
        raise s.SetupError("Pass -- followed by generate, edit or generate-batch and the bundled image CLI's arguments.")
    env = os.environ.copy()
    env.update(OPENAI_API_KEY=key, OPENAI_BASE_URL=s.API)
    # A different API organization/project inherited from the shell must not
    # change the destination account for this member's LB request.
    env.pop("OPENAI_ORG_ID", None)
    env.pop("OPENAI_PROJECT_ID", None)
    try:
        result = subprocess.run(
            [python or sys.executable, str(image_cli), *arguments],
            env=env, capture_output=True, text=True, errors="replace",
        )
    except OSError:
        raise s.SetupError("Could not start the image CLI. Check the Python runtime and --image-cli path.") from None
    for stream, value in ((sys.stdout, result.stdout), (sys.stderr, result.stderr)):
        stream.write((value or "").replace(key, "[REDACTED]"))
    if result.returncode:
        print("Image CLI failed; no success is implied. A gpt-5.5 plan error requires the server-side image-host repair in references/image-generation.md.", file=sys.stderr)
    return result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="The same Codex home used for member setup")
    parser.add_argument("--image-cli", help="Absolute path to Codex's bundled imagegen/scripts/image_gen.py")
    parser.add_argument("--check", action="store_true", help="Inspect configuration without sending a request")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        home = s.codex_home(args.home)
        image_cli = Path(args.image_cli).expanduser().absolute() if args.image_cli else home / "skills/.system/imagegen/scripts/image_gen.py"
        if args.check:
            provider_id, _ = image_context(home)
            s.emit(status="image_cli_ready" if image_cli.is_file() else "image_cli_missing", provider=provider_id, base_url=s.API, image_cli=str(image_cli), request_sent=False)
            return 0 if image_cli.is_file() else 1
        arguments = args.arguments
        if arguments[:1] == ["--"]:
            arguments = arguments[1:]
        return run_image_cli(home, image_cli, arguments)
    except s.SetupError as exc:
        s.emit(status="error", message=str(exc))
        return 1
    except OSError:
        s.emit(status="error", message="Could not read the local image configuration or credential file.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
