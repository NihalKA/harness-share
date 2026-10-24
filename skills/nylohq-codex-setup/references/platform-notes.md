# Platform and recovery notes

## Prerequisites

The member needs a working local Codex client, their own LB key, network access to `https://codex.nylohq.com`, Python 3.9+ for this setup script, and a compatible official Codex executable (tested baseline 0.164.0). The Python TOML dependency is bundled. No pip install, local proxy, service, or custom Voice client is required.

Use a bundled desktop Python if available. If Python is absent, use the official Python installer from python.org or an existing trusted package manager. On Windows the Python launcher can resolve the interpreter with `py -3 -c "import sys; print(sys.executable)"`; on Mac use `python3 -c 'import sys; print(sys.executable)'`. Then use the returned full path. Installation permission requirements still apply.

The Mac machine used to build this package has Homebrew Codex CLI 0.164.0. With Homebrew already installed, the official cask command is `brew install --cask codex` (or `brew upgrade --cask codex` for an existing cask). When using npm, the official CLI package is `@openai/codex`; `npm install -g @openai/codex` is an installation option when Node/npm are already available. For other installations, consult the current official Codex installation instructions rather than inventing package IDs or overwriting an app-bundled executable. Do not install Homebrew or Node solely without explaining that dependency.

Native Windows and WSL use different home directories/configurations. This package targets native Windows. Run setup in native PowerShell for the Windows app/CLI; do not copy a Mac `/bin/cat` command or a WSL path into Windows config. An app using a remote execution environment will not configure the member's laptop by modifying its remote filesystem.

## Exact command shapes

Mac example shape (replace example paths with the discovered paths):

```sh
"/absolute/path/to/python3" "/absolute/path/to/nylohq-codex-setup/scripts/setup.py" inspect --codex-bin "/absolute/path/to/codex"
```

Windows example shape:

```powershell
& 'C:\absolute\path\python.exe' 'C:\absolute\path\nylohq-codex-setup\scripts\setup.py' inspect --codex-bin 'C:\absolute\path\codex.exe'
```

Use the same invocation shape for `key`, `apply`, `verify` and `restore`. Resolve `TARGET_HOME` from preflight, then pass `--home` explicitly; don't change the process-wide `HOME` or `CODEX_HOME` to a temporary directory.

The key entry command must run in the member's own interactive terminal, with no redirected input. Keys are hidden and never accepted as command-line arguments. A saved pending key alone does not change active routing.

## What may be changed

- Root keys: `model`, `model_provider`, `model_reasoning_effort`, `model_catalog_json`, `experimental_realtime_webrtc_call_base_url`, `experimental_realtime_ws_base_url`.
- The setup's own provider block: `nylohq_lb`, or existing active `nylohq_voice_audit`. It standardizes authentication and endpoints, removing conflicting authentication fields inside that owned block.
- The protected `nylohq-lb/api-key` and `nylohq-lb/models.json` files.
- A private timestamped recovery directory under the same Codex home's `backups`.

Other providers, plugins, MCPs, native `auth.json`/keychain sign-in, trust settings, sandbox/approval settings, history and desktop preferences are retained. OS file permissions protect the plaintext LB key: mode 0600 under a 0700 directory on Mac; an explicit current-user DACL on Windows. Setup does not use the OS keychain and should not be described as encrypted credential storage.

## Failure handling

| Symptom | Next action |
| --- | --- |
| CLI too old or not found | Locate/install a compatible official CLI and rerun `inspect` with its full path. |
| Python missing | Use the bundled interpreter or install Python 3.9+ through the official installer/trusted package manager. |
| `ready_for_key`, but no staged key | Give the hidden terminal command and wait for the member's confirmation. |
| Catalog HTTP 401/403 | Have the member check/reenter their own LB key or ask their administrator about access. Do not swap in someone else's credential. |
| Catalog HTTP 429 | Quota/rate limit: wait for the administrator's guidance; do not loop. |
| HTTPS/certificate failure | Check network, clock and trusted CA setup. Do not use insecure TLS flags. |
| Incomplete catalog | LB must return complete `models` metadata. Do not fabricate model capabilities or copy another user's cached catalog. |
| Model unavailable | Ask the member to select an allowed model and pass its exact ID using `--model`. |
| Strict-config failure | The chosen binary may be older than the client's unrelated app settings. Use the matching/newer official binary; don't delete plugins/features just to pass. Raw validation output is withheld because existing config may contain secrets. |
| Isolated text check failed | Catalog access alone is insufficient. Check inference permission, quota and model routing with the LB administrator. Real config is not committed before this check passes. |
| Windows permissions/PowerShell failure | Confirm native Windows PowerShell and the member's access to their user directory. Do not make the key readable to Everyone or disable security software. |
| A setup lock remains after a crash | Verify no setup process is active; only then remove `nylohq-lb/setup.lock` and inspect the latest backup status. |
| Settings appear unchanged | Restart the app/CLI, open a new chat, and check selected profile/CLI flags and the actual CODEX_HOME. Old chats may keep previous routing. |
| Voice command unavailable | Check the actual interactive CLI binary/version. `/voice` is an in-Codex slash command, not `codex voice`. |
| Voice fails after text passes | Have the member test microphone/speaker permissions and LB realtime access. Record exact symptoms without audio capture. Do not claim the text test verified Voice. |
| Restore reports later edits | Compare only affected settings with the private backup and prepare a selective merge. Keep secret contents out of chat. |

## Validation boundary

The bundled tests exercise configuration preservation, Windows command generation/quoting, model selection, backups, rollback and restore in isolated fixtures. The build-time live Mac check uses the administrator's existing key internally in an isolated temporary Codex home; no credential is distributed. Native Windows PowerShell/DACL execution and actual Windows realtime audio require a pilot on a Windows member's computer. Four-member concurrency/accounting is a server-side test and is not established by this client installer.
