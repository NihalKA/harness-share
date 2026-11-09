# Image generation through NyloHQ LB

Two failures need different repairs:

| Symptom | Meaning | Action |
| --- | --- | --- |
| The chat says its built-in image tool is unavailable | No image API request may have been made | Use an explicitly requested API fallback. A client restart does not guarantee native tool availability. |
| The bundled CLI asks for `OPENAI_API_KEY` | It does not read Codex's provider configuration | Use the member helper below, which supplies the saved LB key and endpoint to that process. |
| HTTP 503: `No accounts with a plan supporting model 'gpt-5.5'` | Older codex-lb image routes use an unavailable internal host model | The server operator must deploy the upstream host-selection fix or the narrow 1.24.0 backport below. |

The NyloHQ server repair was verified with a real `gpt-image-2` generation on
9 November 2026. Users of that same repaired server do not each need a server
patch. Other operators must repair their own deployment.

## Members: use the existing key

After installing/updating this complete setup skill, ask Codex:

```text
Use $nylohq-codex-setup to create a sample LinkedIn banner through my
configured NyloHQ LB. I authorize the image API fallback and reuse of my
existing LB key. Follow references/image-generation.md. Keep the key private.
```

An agent handling this request should use the imagegen skill for prompt,
model, file handling and visual checks when available. The helper is only a
credential adapter for the existing bundled CLI; it is not another image SDK.
Do not install an unrelated image provider or request a new OpenAI key just
because the native tool is missing. Never print the saved key or full config.

Resolve `PYTHON`, `HELPER`, `TARGET_HOME` and `IMAGE_CLI` to absolute paths on
this member's computer. `HELPER` is this skill's `scripts/image_cli.py`.
`IMAGE_CLI` is Codex's bundled `imagegen/scripts/image_gen.py`; its usual
location is `TARGET_HOME/skills/.system/imagegen/scripts/image_gen.py`.
Respect `CODEX_HOME`. Do not assume another member's installation path.

Read-only check, with no request sent:

```text
PYTHON HELPER --home TARGET_HOME --image-cli IMAGE_CLI --check
```

Generate using a Python environment containing the `openai` SDK:

```text
PYTHON HELPER --home TARGET_HOME --image-cli IMAGE_CLI -- generate --model gpt-image-2 --prompt-file PROMPT_FILE --size 1584x528 --quality medium --out NEW_OUTPUT_FILE
```

On Windows, use native PowerShell and prefix a quoted Python executable with
`&`. Quote paths individually. The helper uses an argument list on both
platforms, not a shell command. It does not install packages or change config.

If `uv` is already installed, its temporary dependency environment is an
alternative to changing the member's Python installation:

```text
uv --native-tls run --with openai python HELPER --home TARGET_HOME --image-cli IMAGE_CLI -- generate --model gpt-image-2 --prompt-file PROMPT_FILE --size 1584x528 --quality medium --out NEW_OUTPUT_FILE
```

`--native-tls` uses the operating system's trust store; it does not disable
certificate verification. For another dependency manager, follow imagegen's
documented environment instructions.

The helper rejects an active default profile rather than guessing which
provider it selects, and accepts only the configured NyloHQ HTTPS endpoint.
It reads this member's protected `nylohq-lb/api-key` file, sets
`OPENAI_API_KEY` and `OPENAI_BASE_URL` only for the child process, and redacts
the exact key from child output. It never runs the config's credential command.
Missing keys must be entered by the member using the normal hidden setup
prompt; do not paste them into chat or command arguments.

A LinkedIn personal banner is 1584 × 396 (4:1), while this image API's generated
`gpt-image-2` aspect ratio is at most 3:1. Generate a wider composition with
crop-safe content, then inspect the actual dimensions, crop and resize to the
final format. The server can return dimensions different from those requested.
Save new versions instead of overwriting existing images.

This fallback does not make the native `image_gen` tool appear in a chat. The
native feature flag was enabled in the tested client, but its tool was still
absent; the precise desktop-session availability cause was not established.

## Enable ordinary image requests in new chats

Updating the setup skill alone does not teach every new chat to choose it for
a generic image request. For a member who explicitly chooses the existing LB
fallback as their default for future requested image work, install the included
image companion and record their choice using:

```text
PYTHON IMAGE_DEFAULTS --home TARGET_HOME --skills-dir PERSONAL_SKILLS_DIR --choose-api-fallback
```

`IMAGE_DEFAULTS` is the installed setup skill's `scripts/image_defaults.py`.
`PERSONAL_SKILLS_DIR` is the supported personal skill root containing the
installed `nylohq-codex-setup` folder. It may be `CODEX_HOME/skills` or
`~/.agents/skills`; resolve it for this client. Keep the companion in that same
root. Do not install a second copy in a different root.

The installer copies `assets/image-default/SKILL.template.md` to the companion's
`nylohq-imagegen/SKILL.md` and installs its UI metadata. It merges
`AGENTS.fragment.md` into `TARGET_HOME/AGENTS.md` with resolved paths. Existing
instructions are preserved, replaced content is privately backed up, and
repeating installation does not duplicate the preference. These templates are
not active skills until installed. No key, provider config, model, server,
microphone or existing image is changed by this installer.

Run it only after the member chooses this default. An ordinary onboarding
request or receiving this ZIP is not that choice. The opt-in prompt in the
repository README explicitly includes it. A different user can continue using
the one-request fallback prompt instead.

After installation, inspect a fresh `codex debug prompt-input` context for the
saved preference and companion skill when that debug command is available.
Do not dump the whole context into logs. Verify one real image generation
through the helper. Then start a new chat and ask normally for an image.
Existing chats can retain their earlier skill list; the saved instructions
include the installed skill's path so it can also be read directly.

To undo this opt-in, remove only the section between
`<!-- nylohq-image-default:start -->` and `<!-- nylohq-image-default:end -->`
from the personal instructions, and remove the installed companion if no
longer wanted. Preserve unrelated later edits. Private backup manifests list
the files changed by installation; do not blindly overwrite newer preferences.

## Operators: repair the internal host model

codex-lb 1.24.0 hard-codes `gpt-5.5` as the Responses model that invokes the
image-generation tool. The public model remains `gpt-image-2`. If no eligible
account advertises `gpt-5.5`, the request fails before image generation.

The upstream repair is [commit 92c7f620 / PR #2320](https://github.com/Soju06/codex-lb/commit/92c7f6201a8fd31d6160570f60ee59db5686dd67).
Prefer a reviewed codex-lb release containing it. It prefers advertised,
unsuppressed `gpt-5.6-luna`, then `gpt-5.5`. Catalog visibility is not proof
of entitlement: an active eligible account and a successful real image request
are still required. This does not bypass a subscription or quota restriction.

For operators retaining 1.24.0, this skill includes the image-only backport
under `assets/image-host-fix`. It updates generation and edit host selection;
it does not update the separate account-probe default or database schema.
The copied upstream code retains its MIT license and provenance notice.

Before deployment, identify the real container name, Compose service, volumes,
image and configuration. The commands below use container and service name
`codex-lb`; substitute the actual names. Preserve the database volume. Create
a consistent database backup and a private copy of its encryption key and
deployment config using the operator's existing backup procedure. Do not
publish backups, full config, member keys or model snapshots.

1. Retain the running image locally:

   ```sh
   docker image tag "$(docker inspect --format '{{.Image}}' codex-lb)" local/codex-lb:before-image-host-fix
   ```

2. Verify the original adapter's SHA-256 before using this backport:

   ```sh
   docker exec codex-lb python -c "from pathlib import Path; import hashlib; print(hashlib.sha256(Path('/app/app/modules/proxy/api.py').read_bytes()).hexdigest())"
   ```

   The audited 1.24.0 baseline is
   `f396d8d0a2cb54d49f3ac757cdc91ca9ab7d823be3e8dd6b61715898645857dc`.
   If it differs, stop and review the deployed source; do not force this patch.

3. Clone the public upstream source on the Docker host and check out
   `v1.24.0`. Resolve `FIX_DIR` to the absolute installed
   `assets/image-host-fix` folder, then run these commands from the upstream
   checkout:

   ```sh
   git apply --check "$FIX_DIR/image-host-backport.patch"
   git apply "$FIX_DIR/image-host-backport.patch"
   docker build --pull=false -f "$FIX_DIR/Dockerfile" -t local/codex-lb:image-host-fix .
   ```

   The Dockerfile derives from the retained running image and copies only the
   two changed Python files, with readable permissions. It does not pull a
   floating upstream image or rebuild unrelated dependencies.

   Run the included offline regression checks in a separate container without
   production volumes or network access:

   ```sh
   docker run --rm --network none --tmpfs /tmp --workdir /app \
     -e PYTHONPATH=/app -e CODEX_LB_DATA_DIR=/tmp/codex-lb-check \
     -v "$FIX_DIR/verify_backport.py:/verify_backport.py:ro" \
     --entrypoint /opt/venv/bin/python local/codex-lb:image-host-fix /verify_backport.py
   ```

   All five checks should pass before changing the running service.

4. In the backed-up Compose config, change only the LB service image to
   `local/codex-lb:image-host-fix`. Verify the effective config otherwise
   matches the original, including volumes, networks, ports and environment.
   Recreate only that service:

   ```sh
   docker compose up -d --no-deps --pull never codex-lb
   ```

5. Check `/health/ready`, then run one real image request through the member
   helper. Readiness alone does not prove image generation works. Preserve the
   failure and roll back the service if readiness or generation fails.

For a code rollback, use the retained image
`local/codex-lb:before-image-host-fix` and recreate only the LB service. Do not
restore an old database for a code-only rollback: that discards newer data.
Keep the repaired image pinned until a reviewed upgrade includes the fix.

The server backport and a real generation were verified on an Oracle VM with
Docker Compose. The client helper has offline path, child-process and secret
handling checks; native Windows image generation still needs a member pilot.
