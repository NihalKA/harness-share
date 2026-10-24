#!/usr/bin/env python3
"""Direct NyloHQ setup. Python 3.9+ is needed only during setup/maintenance."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import warnings

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent / "vendor"))
import tomlkit

API = "https://codex.nylohq.com/v1"
CALLS = "https://codex.nylohq.com/backend-api/codex"
DEFAULT_PROVIDER = "nylohq_lb"
MANAGED_ROOT = (
    "model", "model_provider", "model_reasoning_effort", "model_catalog_json",
    "experimental_realtime_webrtc_call_base_url", "experimental_realtime_ws_base_url",
)
TARGETS = ("config.toml", "nylohq-lb/api-key", "nylohq-lb/models.json")
MIN_VERSION = (0, 164, 0)
MAX_CATALOG = 1024 * 1024


class SetupError(Exception):
    pass


def emit(**values):
    print(json.dumps(values, indent=2, ensure_ascii=True))


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def native_os():
    name = platform.system()
    if name not in ("Darwin", "Windows"):
        raise SetupError("This package targets native macOS or Windows. WSL has separate configuration; run the Windows setup in native PowerShell.")
    return name


def codex_home(value=None):
    path = Path(value or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser().absolute()
    reject_link(path)
    return path


def reject_link(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise SetupError("A managed path is a symlink/junction; review its destination before setup: " + str(path))


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def powershell():
    root = os.environ.get("SystemRoot", r"C:\Windows")
    path = Path(root) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    if not path.is_file():
        raise SetupError("Windows PowerShell 5.1 was not found. Use native Windows with PowerShell installed.")
    return str(path)


def protect(path):
    """Restrict only setup-owned directories/files, never the whole user home."""
    reject_link(path)
    if os.name != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    kind = "DirectorySecurity" if path.is_dir() else "FileSecurity"
    inheritance = "ContainerInherit,ObjectInherit" if path.is_dir() else "None"
    script = (
        "$ErrorActionPreference='Stop';"
        "$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User;"
        f"$acl=New-Object System.Security.AccessControl.{kind};"
        "$acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false);"
        f"$rule=[System.Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','{inheritance}','None','Allow');"
        "$acl.AddAccessRule($rule);"
        f"Set-Acl -LiteralPath {ps_quote(path)} -AclObject $acl"
    )
    result = subprocess.run([powershell(), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, timeout=20)
    if result.returncode:
        raise SetupError("Could not restrict Windows file permissions; no secret was written to the new file.")


def private_dir(path):
    reject_link(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    protect(path)


def read_optional(path):
    reject_link(path)
    return path.read_bytes() if path.exists() else None


def atomic_write(path, data):
    reject_link(path)
    fd, name = tempfile.mkstemp(prefix=".nylohq-", dir=str(path.parent))
    temp = Path(name)
    try:
        protect(temp)  # Before writing any contents, including on Windows.
        with os.fdopen(fd, "wb") as f:
            fd = None
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if fd is not None:
            os.close(fd)
        temp.unlink(missing_ok=True)


def parse_config(data):
    try:
        return tomlkit.parse((data or b"").decode("utf-8-sig"))
    except Exception:
        # Parser exceptions can include the source line, which may contain credentials.
        raise SetupError("Existing config.toml is not valid UTF-8 TOML. Nothing was changed; repair it locally before continuing.") from None


def find_cli(explicit=None):
    candidates = [explicit] if explicit else [
        shutil.which("codex"),
        "/opt/homebrew/bin/codex", "/usr/local/bin/codex",
        "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex",
        "/Applications/Codex.app/Contents/Resources/codex",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            path = str(Path(candidate).absolute())
            try:
                result = subprocess.run([path, "--version"], capture_output=True, timeout=15)
                match = re.search(rb"codex(?:-cli)?\s+(\d+)\.(\d+)\.(\d+)", result.stdout)
                if result.returncode == 0 and match:
                    version = tuple(int(x) for x in match.groups())
                    if version < MIN_VERSION:
                        raise SetupError("Selected Codex CLI is older than the tested 0.164.0 baseline. Update it or pass --codex-bin for a compatible installation.")
                    return path, ".".join(map(str, version))
            except (OSError, subprocess.TimeoutExpired):
                continue
    raise SetupError("No compatible Codex executable found. Install/update the official CLI or provide its full path with --codex-bin.")


def read_key(path):
    data = read_optional(path)
    if data is None:
        raise SetupError("No staged key found. Run the 'key' command yourself in a private Terminal/PowerShell window first.")
    try:
        value = data.decode("ascii").strip()
    except UnicodeDecodeError:
        raise SetupError("Key is not a valid ASCII bearer credential. Enter the member's LB key again.") from None
    if not value or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
        raise SetupError("Key is empty or contains whitespace/control characters. Enter the member's LB key again.")
    return value


def enter_key(home):
    native_os()
    if not sys.stdin.isatty():
        raise SetupError("Key entry needs your own interactive terminal. Do not pipe a key, put it in arguments, or enter it through an agent tool.")
    private_dir(home / "nylohq-lb")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            value = getpass.getpass("Paste your own NyloHQ LB API key (hidden), then press Enter: ").strip()
        except getpass.GetPassWarning:
            raise SetupError("This terminal cannot hide input. Use a normal Terminal/PowerShell window.") from None
    if not value or not value.isascii() or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
        raise SetupError("Key is empty or contains whitespace/control characters. Nothing was saved.")
    atomic_write(home / "nylohq-lb/api-key.pending", value.encode("ascii"))
    emit(status="key_staged", message="Key saved privately; its value will not be displayed. Return to the setup chat and say: Key saved, continue.")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SetupError("The LB redirected its model endpoint. Stopped without forwarding the credential; contact your administrator.")


def fetch_catalog(key, version):
    # Python.org macOS installs can lack an initialized CA bundle. Use macOS's
    # system bundle there; Windows create_default_context loads Windows CA stores.
    ca = "/etc/ssl/cert.pem" if platform.system() == "Darwin" and Path("/etc/ssl/cert.pem").is_file() else None
    context = ssl.create_default_context(cafile=ca)
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    request = urllib.request.Request(API + "/models?client_version=" + version, headers={
        "Authorization": "Bearer " + key,
        "Accept": "application/json", "User-Agent": "codex_cli_rs/" + version,
    })
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(MAX_CATALOG + 1)
    except urllib.error.HTTPError as error:
        raise SetupError(f"LB catalog request failed: HTTP {error.code}. Check this member's key/access with the administrator; response body withheld.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SetupError("Could not reach the LB over verified HTTPS. Check connectivity, system time, and trusted certificates; do not disable TLS verification.") from None
    if len(raw) > MAX_CATALOG:
        raise SetupError("LB catalog exceeds the supported 1 MiB limit. Ask the administrator to reduce it.")
    try:
        data = json.loads(raw)
        models = data["models"]
        if not isinstance(models, list) or not models:
            raise ValueError()
        slugs = [m["slug"] for m in models]
        if any(not isinstance(s, str) or not s for s in slugs) or len(set(slugs)) != len(slugs):
            raise ValueError()
        if any(not isinstance(m.get("base_instructions"), str) or not isinstance(m.get("supported_reasoning_levels"), list) for m in models):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise SetupError("LB did not return a complete, valid Codex model catalog. A plain OpenAI model-ID list is insufficient; ask the administrator to fix the endpoint.") from None
    return {"models": models}


def choose_model(doc, catalog, requested=None):
    visible = {m["slug"]: m for m in catalog["models"] if m.get("visibility") == "list"}
    if requested:
        choices = [requested]
    else:
        current = str(doc.get("model", "")).split("/")[-1]
        choices = [current, "gpt-5.6-terra", "gpt-6-luna", "gpt-5.6-luna"]
    selected = next((x for x in choices if x in visible), None)
    if not selected:
        raise SetupError("Requested/current model and the Terra/Luna defaults are unavailable. Ask the member to choose an allowed visible model, then pass --model with that exact ID.")
    metadata = visible[selected]
    levels = [x.get("effort") for x in metadata["supported_reasoning_levels"]]
    effort = str(doc.get("model_reasoning_effort", ""))
    if effort not in levels:
        effort = metadata.get("default_reasoning_level")
    if effort not in levels:
        raise SetupError("Selected model has an inconsistent reasoning-level catalog. Ask the administrator to correct it.")
    return selected, effort


def credential_config(key_path, system=None, ps_path=None):
    system = system or native_os()
    if system == "Windows":
        # -Command is passed directly as one argv element; no cmd.exe interpolation.
        command = ps_path or powershell()
        args = ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
                "$ErrorActionPreference='Stop';[Console]::Out.Write([System.IO.File]::ReadAllText(" + ps_quote(key_path) + ").Trim())"]
    else:
        command, args = "/bin/cat", [str(key_path)]
    return {"command": command, "args": args, "timeout_ms": 5000, "refresh_interval_ms": 300000}


def build_config(original, home, model, effort, system=None, ps_path=None):
    doc = parse_config(original)
    if doc.get("profile"):
        raise SetupError("A default config profile is active. Resolve the intended profile with the member before changing global routing.")
    providers = doc.get("model_providers", {})
    current = str(doc.get("model_provider", ""))
    provider_id = current if current in (DEFAULT_PROVIDER, "nylohq_voice_audit") else DEFAULT_PROVIDER
    if provider_id in providers and str(providers[provider_id].get("base_url", "")).rstrip("/") != API:
        raise SetupError("The NyloHQ provider ID is already used for a different endpoint. Nothing was overwritten; review the name collision.")
    values = {
        "model": model, "model_provider": provider_id, "model_reasoning_effort": effort,
        "model_catalog_json": str(home / "nylohq-lb/models.json"),
        "experimental_realtime_webrtc_call_base_url": CALLS,
        "experimental_realtime_ws_base_url": API,
    }
    for name, value in values.items():
        doc[name] = value
    if "model_providers" not in doc:
        doc["model_providers"] = tomlkit.table(is_super_table=True)
    provider = tomlkit.table()
    for name, value in {"name": "NyloHQ LB", "base_url": API, "model_catalog_url": API + "/models", "wire_api": "responses", "supports_websockets": True}.items():
        provider[name] = value
    provider["auth"] = credential_config(home / "nylohq-lb/api-key", system, ps_path)
    doc["model_providers"][provider_id] = provider
    result = tomlkit.dumps(doc).encode("utf-8")
    parse_config(result)
    return result, provider_id


def child_env(home):
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home)
    # Tests must use the configured LB credential, without ambient OpenAI auth.
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID", "OPENAI_ORGANIZATION", "OPENAI_PROJECT_ID"):
        env.pop(name, None)
    return env


def strict_check(cli, config, catalog, staging):
    full = parse_config(config)
    full["model_catalog_json"] = str(staging / "models.json")
    atomic_write(staging / "models.json", catalog)
    atomic_write(staging / "config.toml", tomlkit.dumps(full).encode("utf-8"))
    result = subprocess.run([cli, "app-server", "--strict-config", "--print-startup-config"], env=child_env(staging), cwd=staging, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    if result.returncode:
        raise SetupError("Selected Codex rejected the configuration during strict validation. Existing unrelated settings were preserved; update the client or inspect compatibility locally. Raw output withheld to avoid exposing existing credentials.")


def check_credential(auth, expected):
    result = subprocess.run([auth["command"], *auth["args"]], capture_output=True, timeout=5)
    if result.returncode or result.stdout.strip() != expected.encode("ascii"):
        raise SetupError("The native credential command failed or returned an unexpected value. Configuration has not been committed.")


def smoke_check(cli, candidate, catalog, key_path, key, staging):
    source = parse_config(candidate)
    provider_id = source["model_provider"]
    # Minimal isolated session: no copied sign-in, plugins, MCPs, hooks, or history.
    doc = tomlkit.document()
    for name in MANAGED_ROOT:
        doc[name] = source[name]
    doc["model_catalog_json"] = str(staging / "models.json")
    doc["approval_policy"] = "never"
    doc["model_providers"] = {provider_id: source["model_providers"][provider_id].unwrap()}
    auth = credential_config(key_path)
    doc["model_providers"][provider_id]["auth"] = auth
    check_credential(auth, key)
    atomic_write(staging / "models.json", catalog)
    atomic_write(staging / "config.toml", tomlkit.dumps(doc).encode("utf-8"))
    result = subprocess.run([
        cli, "exec", "--strict-config", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--json",
        "Reply with exactly NYLOHQ_SETUP_OK. Do not use tools or inspect files.",
    ], env=child_env(staging), cwd=staging, capture_output=True, timeout=150)
    texts, completed = [], False
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            completed = True
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            texts.append(item.get("text", ""))
    if result.returncode or not completed or not any("NYLOHQ_SETUP_OK" in x for x in texts):
        raise SetupError("The isolated Codex text check failed. The real configuration was not changed. Check this member's inference access, quota, model and client version; raw model/log output was withheld.")


@contextlib.contextmanager
def setup_lock(home):
    private_dir(home / "nylohq-lb")
    path = home / "nylohq-lb/setup.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SetupError("Another setup may be running. If a previous run crashed, confirm it has stopped before removing nylohq-lb/setup.lock.") from None
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def snapshot(home, before, after):
    parent = home / "backups"
    reject_link(parent)
    parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = parent / ("nylohq-setup-" + stamp + "-" + uuid.uuid4().hex[:6])
    private_dir(backup)
    manifest = {"format": 1, "home": str(home), "status": "prepared", "files": {}}
    for i, name in enumerate(TARGETS):
        data = before[name]
        backup_name = f"{i}.before"
        if data is not None:
            atomic_write(backup / backup_name, data)
        manifest["files"][name] = {"backup_file": backup_name, "existed": data is not None, "before_sha256": digest(data), "after_sha256": digest(after[name])}
    atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode())
    return backup, manifest


def write_state(home, values):
    for name in (TARGETS[1], TARGETS[2], TARGETS[0]):
        path = home / name
        if values[name] is None:
            reject_link(path)
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, values[name])


def commit(home, before, after):
    for name in TARGETS:
        if read_optional(home / name) != before[name]:
            raise SetupError("A managed file changed while setup was running. Nothing was committed; rerun setup after the other writer stops.")
    backup, manifest = snapshot(home, before, after)
    try:
        # Dependencies first, config last; never point the new config at absent files.
        for name in (TARGETS[1], TARGETS[2], TARGETS[0]):
            atomic_write(home / name, after[name])
        manifest["status"] = "applied"
        atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode())
    except BaseException:
        try:
            write_state(home, before)
            manifest["status"] = "rolled_back"
            atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode())
        except Exception:
            raise SetupError("A write and automatic rollback failed. Stop here. Recover using the private backup: " + str(backup)) from None
        raise SetupError("A write failed; the previous managed files were restored. Backup: " + str(backup)) from None
    return backup


def inspect(home, cli_arg=None):
    system = native_os()
    cli, version = find_cli(cli_arg)
    doc = parse_config(read_optional(home / "config.toml"))
    emit(status="ready_for_key", os=system, python=sys.executable, codex_binary=cli, codex_version=version,
         codex_home=str(home), config_exists=(home / "config.toml").exists(), current_model=doc.get("model"),
         current_provider=doc.get("model_provider"), default_profile_present=bool(doc.get("profile")),
         pending_key_exists=(home / "nylohq-lb/api-key.pending").is_file(),
         existing_lb_key_exists=(home / "nylohq-lb/api-key").is_file(),
         provider_environment_names_present=[x for x in ("OPENAI_API_KEY", "OPENAI_BASE_URL") if x in os.environ],
         note="No secret values or complete configuration are printed. Use this same home and executable for subsequent steps.")


def apply(home, cli_arg=None, model=None, reuse_key=False):
    native_os()
    cli, version = find_cli(cli_arg)
    with setup_lock(home):
        key_path = home / ("nylohq-lb/api-key" if reuse_key else "nylohq-lb/api-key.pending")
        key = read_key(key_path)
        before = {name: read_optional(home / name) for name in TARGETS}
        doc = parse_config(before["config.toml"])
        catalog = fetch_catalog(key, version)
        selected, effort = choose_model(doc, catalog, model)
        candidate, provider_id = build_config(before["config.toml"], home, selected, effort)
        catalog_bytes = json.dumps(catalog, ensure_ascii=False).encode("utf-8")
        print("Validating config, credential command and one isolated text turn. This can take up to 150 seconds.", flush=True)
        with tempfile.TemporaryDirectory(prefix="nylohq-check-", dir=home / "nylohq-lb") as temp:
            staging = Path(temp)
            protect(staging)
            strict_check(cli, candidate, catalog_bytes, staging)
            smoke_check(cli, candidate, catalog_bytes, key_path, key, staging)
        if read_key(key_path) != key:
            raise SetupError("The staged key changed during validation. Rerun apply.")
        after = {"config.toml": candidate, "nylohq-lb/api-key": key.encode("ascii"), "nylohq-lb/models.json": catalog_bytes}
        backup = commit(home, before, after)
        if not reuse_key:
            key_path.unlink()
        emit(status="configured", backup=str(backup), codex_home=str(home), model=selected, reasoning=effort,
             provider_id=provider_id, endpoint=API, visible_models=[m["slug"] for m in catalog["models"] if m.get("visibility") == "list"],
             tests={"strict_config": "passed", "native_credential_command": "passed", "isolated_cli_text": "passed", "microphone": "not_started", "live_voice": "member_test_required"},
             next="Fully quit and reopen the desktop client and restart CLI sessions. Open a new chat. For Voice, the member manually starts codex and then /voice.")


def verify(home, cli_arg=None):
    native_os()
    cli, version = find_cli(cli_arg)
    config = read_optional(home / "config.toml")
    doc = parse_config(config)
    provider = doc.get("model_providers", {}).get(doc.get("model_provider"), {})
    expected = credential_config(home / "nylohq-lb/api-key")
    if (provider.get("base_url") != API or dict(provider.get("auth", {})) != expected
            or doc.get("model_catalog_json") != str(home / "nylohq-lb/models.json")
            or doc.get("experimental_realtime_webrtc_call_base_url") != CALLS
            or doc.get("experimental_realtime_ws_base_url") != API):
        raise SetupError("Effective user config differs from this package's direct setup. Inspect routing before verifying; no other credential command will be executed.")
    key = read_key(home / "nylohq-lb/api-key")
    catalog = read_optional(home / "nylohq-lb/models.json")
    if catalog is None:
        raise SetupError("Local model catalog is missing. Run apply --reuse-key to refresh it with a backup.")
    fetch_catalog(key, version)  # Authenticated remote discovery, without overwriting snapshot.
    print("Verifying the saved configuration and one isolated text turn.", flush=True)
    with tempfile.TemporaryDirectory(prefix="nylohq-check-", dir=home / "nylohq-lb") as temp:
        staging = Path(temp)
        protect(staging)
        strict_check(cli, config, catalog, staging)
        smoke_check(cli, config, catalog, home / "nylohq-lb/api-key", key, staging)
    emit(status="verified", model=doc.get("model"), endpoint=API, voice="not_started; test manually", note="Fresh isolated CLI test passed. Restart existing clients to load these settings; other explicit profiles/flags can override defaults.")


def restore(home, backup):
    native_os()
    backup = Path(backup).expanduser().absolute()
    reject_link(backup)
    if backup.parent != home / "backups" or not backup.name.startswith("nylohq-setup-"):
        raise SetupError("Use the exact backup directory printed by this setup under this CODEX_HOME/backups.")
    with setup_lock(home):
        try:
            manifest = json.loads((backup / "manifest.json").read_text())
            if manifest["format"] != 1 or manifest["home"] != str(home) or manifest["status"] not in ("applied", "prepared"):
                raise ValueError()
            values = {}
            for i, name in enumerate(TARGETS):
                record = manifest["files"][name]
                data = read_optional(backup / f"{i}.before") if record["existed"] else None
                if digest(data) != record["before_sha256"]:
                    raise ValueError()
                values[name] = data
                acceptable = {record["after_sha256"]}
                if manifest["status"] == "prepared":
                    acceptable.add(record["before_sha256"])
                if digest(read_optional(home / name)) not in acceptable:
                    raise SetupError("A managed file has changed since setup. Restore stopped to preserve later edits; review and merge the backup locally: " + name)
        except (OSError, ValueError, KeyError, TypeError):
            raise SetupError("Backup is missing, corrupt, already restored, or belongs to another home. Nothing was restored.") from None
        write_state(home, values)
        manifest["status"] = "restored"
        atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode())
    emit(status="restored", backup=str(backup), next="Restart Codex clients to use the restored settings.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "key", "apply", "verify", "restore"])
    parser.add_argument("--home", help="Absolute target CODEX_HOME; defaults to environment or ~/.codex")
    parser.add_argument("--codex-bin", help="Full path to the official Codex executable to validate")
    parser.add_argument("--model", help="Explicit exact model ID, otherwise preserve current or use Terra/Luna")
    parser.add_argument("--reuse-key", action="store_true", help="Explicitly reuse this member's existing protected LB key")
    parser.add_argument("--backup", help="Exact backup directory printed by apply (restore only)")
    args = parser.parse_args()
    try:
        home = codex_home(args.home)
        if args.command == "inspect":
            inspect(home, args.codex_bin)
        elif args.command == "key":
            enter_key(home)
        elif args.command == "apply":
            apply(home, args.codex_bin, args.model, args.reuse_key)
        elif args.command == "verify":
            verify(home, args.codex_bin)
        elif args.command == "restore":
            if not args.backup:
                raise SetupError("restore requires --backup with the exact backup directory.")
            restore(home, args.backup)
    except SetupError as error:
        emit(status="stopped", message=str(error))
        return 1
    except (KeyboardInterrupt, EOFError):
        emit(status="stopped", message="Cancelled. If interruption occurred during commit, inspect the latest private backup before retrying.")
        return 130
    except subprocess.TimeoutExpired:
        emit(status="stopped", message="A validation command timed out. Do not assume setup succeeded; inspect the saved status/backup before retrying.")
        return 1
    except Exception as error:
        # No raw exception or traceback: HTTP/process/parser errors may include secrets.
        emit(status="stopped", error_type=type(error).__name__, message="Unexpected local setup error. Do not print keys or raw configuration. Inspect file permissions, runtime compatibility and the latest backup.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
