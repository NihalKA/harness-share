# Linux Codex CLI setup and recovery

Use this route for the official CLI in native Linux, or the Linux CLI inside WSL.
It needs no desktop app, working Codex chat, image tool or ChatGPT sign-in.
WSL setup affects only that Linux home, not the native Windows app. Run the
commands as your regular user in the same environment where you run `codex`.

## Terminal-only setup

Install Python 3.9+, Git, and the official Codex CLI if missing. With Node/npm
already available, the official package is `npm install -g @openai/codex`.
Use a user-owned npm installation; do not run this setup with sudo. See the
[official CLI installation guide](https://developers.openai.com/codex/cli/).

Clone this repository into a new directory, then run preflight:

```sh
git clone https://github.com/NihalKA/harness-share.git
cd harness-share
python3 --version
codex --version
nylo_setup="$PWD/skills/nylohq-codex-setup/scripts/setup.py"
nylo_codex="$(command -v codex)"
nylo_home="${CODEX_HOME:-$HOME/.codex}"
python3 "$nylo_setup" inspect --home "$nylo_home" --codex-bin "$nylo_codex"
```

Check the reported home and binary. The helper needs CLI 0.164.0 or newer and
validates the actual version's config schema. If a default profile is reported,
resolve it before applying; do not delete profiles to bypass the check. Explicit
CLI `--profile`/`-c` options and project settings can also change the active route.

If this helper has already stored **your own** key and preflight reports
`existing_lb_key_exists: true`, skip key entry and add `--reuse-key` to `apply`.
Otherwise run the following yourself, in your private terminal, and paste your
LB key only at its hidden prompt:

```sh
python3 "$nylo_setup" key --home "$nylo_home"
```

An existing environment-variable or inline-TOML key is not automatically imported.
Enter that same member's key privately; never post it in a chat, shell command,
issue or screenshot. Native ChatGPT login is not required for this custom provider.

After key entry, configure and test:

```sh
python3 "$nylo_setup" apply --home "$nylo_home" --codex-bin "$nylo_codex" --text-only --transport sse
```

For the previously saved helper key, use instead:

```sh
python3 "$nylo_setup" apply --home "$nylo_home" --codex-bin "$nylo_codex" --text-only --transport sse --reuse-key
```

Use only the appropriate apply command. It preserves your current model when
available; use `--model EXACT_CATALOG_ID` only to choose a different allowed model.
It makes one isolated text probe with client retries disabled and commits only
after validation succeeds. The probe uses a small amount of quota. A failed
probe leaves active config/key/catalog files unchanged; don't repeat it in a loop.

After `status: configured`, retain the printed private backup path. Exit the old
CLI session and start `codex` for a **new** conversation. Check `/status` and
`/model`, then send a short text message. Do not resume the failing old thread
as your first verification. No desktop restart is needed if you only use the CLI.

## Configuration behavior

- Endpoint: `https://codex.nylohq.com/v1`; protocol: `responses`.
- Linux credentials: native `/bin/cat` reads `CODEX_HOME/nylohq-lb/api-key`.
  The key file is mode 0600 inside a mode 0700 directory. It is never embedded in
  TOML or exported to your shell by the helper.
- `--text-only` leaves existing realtime Voice URLs untouched and adds none.
  It does not install image skills, generate images or activate a microphone.
- `--transport sse` sets `supports_websockets = false` on the managed NyloHQ
  provider. Text still streams over HTTP. `--transport websocket` opts into
  Responses WebSockets. This setting is independent of realtime Voice.
- With no transport option, refresh preserves the managed provider's existing
  setting. New Linux connections default to SSE; Mac/Windows retain the previous
  WebSocket default. A repair of an older WebSocket setup needs explicit
  `--transport sse` to switch it.
- Client retry limits are disabled only in the disposable setup probe. Normal
  sessions keep Codex defaults; setup does not increase them.

For later verification, run the following **once**, after any server cooldown:

```sh
python3 "$nylo_setup" verify --home "$nylo_home" --codex-bin "$nylo_codex"
```

To undo, use `restore --home "$nylo_home" --backup "/exact/printed/backup/path"`.
Restore refuses to overwrite later edits. Do not share the backup.

## 429, 503 and upstream WebSocket failures

These errors do not by themselves establish a Linux bug or an incorrect key:

| Error | What it establishes | Next step |
| --- | --- | --- |
| `429 Too Many Requests` / `exceeded retry limit` | A request was rate/quota limited; the CLI exhausted its retry budget. The screenshot alone cannot distinguish member limits from upstream account/model capacity. | Stop resending. Honor the LB's Retry-After/reset information; have the administrator inspect the affected key/model and available upstream accounts. Do not rotate keys or raise retry limits to bypass limits. |
| `503 ... previous response operation may still be running` | codex-lb cannot prove whether a previous operation completed and guards against duplicate upstream submission. | Allow the server cooldown to expire. Check whether the prior work completed before reissuing a task. Afterward, try one short message in a new conversation. |
| `Upstream websocket closed before response.completed` | The LB reports that its upstream response stream did not reach completion. This can also occur when the client uses SSE through the LB's HTTP bridge. | After cooldown, SSE is a client-transport diagnostic, not a guaranteed upstream fix. Persistent failure requires LB/upstream inspection. |

If a new conversation works while the old one fails, that points toward
continuation/session state. If both fail, inspect quota, model availability and
upstream transport. Neither result alone proves a root cause. Do not replay
file-changing commands blindly: earlier work may already have happened.

Send the administrator only the exact error, request ID, approximate timestamp
with timezone, model, `codex --version`, native Linux/WSL, and whether a fresh
SSE session also fails. Do not share full configs, auth files, keys or private logs.
The administrator should correlate request IDs with LB logs, check rate limits,
eligible upstream accounts and reconnect/cooldown events. Do not clear operation
journals or restart/upgrade production blindly to bypass this protection.

The error interpretation was checked against public codex-lb source at
[`b3b42e7`](https://github.com/Soju06/codex-lb/blob/b3b42e785c1fdcc1f96607d4ccbc15865c537cbf/app/modules/proxy/_service/http_bridge/request_submit.py#L1559)
and its [stream-incomplete definition](https://github.com/Soju06/codex-lb/blob/b3b42e785c1fdcc1f96607d4ccbc15865c537cbf/app/core/errors.py#L95).
This is not confirmation of the deployed NyloHQ server version or health.
See also the [official provider configuration reference](https://developers.openai.com/codex/config-reference/).

## Validation boundary

Offline tests cover Linux acceptance, credential invocation, SSE/WebSocket
selection, text-only setup, config preservation, private diagnostics and rollback.
CI runs those fixtures on Ubuntu, macOS and Windows and uses the installed
official CLI for strict config parsing. These checks do not contact the LB or
prove that a member's live session, quota or upstream connection is healthy.
Run the private member setup probe on the affected Linux machine to verify that.
