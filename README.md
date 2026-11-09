# NyloHQ Codex setup

Set up the official Codex client on **macOS or native Windows** using your own NyloHQ LB key. Codex installs the skill, checks prerequisites, backs up your configuration, configures the connection, and verifies it. Your current Terra or Luna model can handle the setup conversation.

## Start here: one prompt in Codex

Use a **local Codex chat on your own computer** and paste the message below. It works for both new members and members updating an existing installation. Codex gets the skill directly from this repository; you do not need the release ZIP for this route.

```text
Install or update the NyloHQ skill from https://github.com/NihalKA/harness-share.
Read its README.md, install the complete skills/nylohq-codex-setup folder,
then read the installed SKILL.md and finish the setup in this chat.
Reuse my own saved LB key if already configured; otherwise guide me through
the private terminal key prompt. Keep my key out of chat.
I choose the existing NyloHQ LB API fallback as my default for image work
I request when the built-in tool is unavailable. Install the included
nylohq-imagegen companion and save my choice using image_defaults.py.
Preserve and back up my existing settings and instructions, keep my current
model if available, and generate a sample banner to verify the image path.
Do not modify the LB server or start my microphone.
```

Once Codex reports success, start a **new chat** and ask normally: **“Create a sample banner image.”** The installed image skill and saved backend choice provide the fallback automatically when the native tool is missing. Image requests use your LB quota.

For a **new connection**, Codex gives you a command to run in your own **Terminal (Mac)** or **PowerShell (Windows)**. Run it, paste your key at the hidden prompt, press Enter, then tell Codex:

```text
Key saved, continue.
```

If Codex changes the provider configuration, fully quit and reopen the desktop client and restart CLI sessions before testing. Existing configured members can reuse their saved key; updating the skill and image preference does not require re-entering it. Run setup once and use the same prompt when you want to update it later.

The skill is kept in [`skills/nylohq-codex-setup`](skills/nylohq-codex-setup), including the image helper, default installer and companion templates. The [v2 ZIP and text instructions](https://github.com/NihalKA/harness-share/releases/tag/nylohq-images-v2) remain an alternative when downloading through Codex is inconvenient.

## Instructions for the Codex agent

When the member uses the prompt above:

1. Work in their local environment. A cloud executor or WSL configuration will not configure their native desktop client.
2. Install `skills/nylohq-codex-setup` from this repository with the available `$skill-installer`. If it is already installed, inspect it before replacing anything; preserve an older copy before updating. Never install duplicate copies in multiple skill roots.
3. Read the installed `SKILL.md` and follow its ordered workflow. If the skill list only refreshes next turn, read the installed file directly to continue this request. Do not stop after merely installing the skill.
4. Inspect the existing connection first. If the configured NyloHQ connection and saved member key are usable, reuse them and continue with the image workflow; do not rerun onboarding or request the key again. If setup is needed, use the bundled `scripts/setup.py` for preflight, private key entry, validation, backup and configuration. Resolve actual paths for this member. Do not generate your own TOML replacement.
5. If key entry is needed, the member enters it themselves through the hidden terminal prompt. Pause for “Key saved, continue,” then finish setup. Never request the key in chat, screenshots, command arguments or tool logs.
6. The prompt explicitly chooses the image fallback default. Follow `references/image-generation.md`, run `scripts/image_defaults.py` with the resolved Codex home and personal skill root, and verify the helper with `--check`. Generate and inspect the requested sample banner. Do not stop after copying the skill or merely explaining the fallback.
7. Report the checks that actually passed and the exact backup locations. Explain the ordinary image request to use in a new chat. Leave microphone activation and any required app restart to the member.

If `$skill-installer` is unavailable, clone/download this public repository, install the complete `skills/nylohq-codex-setup` folder into the client's supported personal skill directory, and read its `SKILL.md`. Keep the vendored parser with the script. The standard current skill root is `~/.agents/skills`; the bundled skill installer may use `$CODEX_HOME/skills`. Use the location supported by the member's client, not both.

If the installer's download fails with a Python certificate error, rerun its `install-skill-from-github.py` helper with `--repo NihalKA/harness-share --path skills/nylohq-codex-setup --method git`. This supported fallback uses native Git and was verified against this published repository. Do not disable TLS verification. If Git is unavailable, use a correctly configured trusted Python runtime or download the public ZIP through the browser and install the complete skill folder.

The repository instructions are for an explicitly requested local setup. Merely browsing, reviewing, testing or editing this repository must not reconfigure the developer's computer.

## What you need

- Your own NyloHQ LB API key, supplied separately by your administrator.
- A working local Codex client and a compatible official CLI. The tested CLI baseline is **0.164.0**; the helper validates the selected installation before applying changes.
- Python **3.9+** for setup and maintenance. Codex first looks for an existing or app-bundled runtime and guides you if a prerequisite is missing. The TOML dependency is included; no pip install is needed.
- Network access to `https://codex.nylohq.com`.

Members do not need GitHub accounts to read/download this public repository. They may still need to approve local tool or OS permission prompts. Native Windows setup uses PowerShell, not WSL.

## What changes

The connection is:

```text
Official Codex client → HTTPS NyloHQ LB → configured upstream model
```

The helper updates six root settings in the member's Codex `config.toml`: model, provider, reasoning effort, model catalog path, and two realtime Voice URLs. It creates the `nylohq_lb` provider, or retains the known legacy provider ID when already active.

It preserves the current model if available in the member's catalog. Otherwise it selects an available Terra/Luna default. Existing plugins, MCP tools, other providers, project trust, desktop preferences, approval settings, native sign-in and chat history are preserved. The setup standardizes its own NyloHQ provider block, including replacing conflicting authentication fields there.

| File under the member's Codex home | Purpose |
| --- | --- |
| `config.toml` | Existing settings plus the direct LB configuration. |
| `nylohq-lb/api-key` | This member's private LB credential, read by a native OS command. |
| `nylohq-lb/models.json` | Model metadata fetched with this member's key. It is a local snapshot, not model weights. |
| `backups/nylohq-setup-*` | Dated recovery copies and a manifest for exact restoration. |

The Codex home defaults to `~/.codex`; a configured `CODEX_HOME` is respected. Mac uses `/bin/cat` for credential reading. Windows uses built-in PowerShell. The key is protected by file permissions; this package does not encrypt it or store it in the OS keychain. It adds no local proxy, bridge, daemon, or listening port. Python is not needed for normal Codex requests after setup.

The local catalog takes precedence over the remote catalog URL. Ask the skill to refresh it when your administrator changes the available models.

## Backups and recovery

Before changing active settings, the helper validates the proposed config, privately checks the credential command, and runs one small isolated text request. This uses a small amount of LB quota. It then backs up existing config/key/catalog files before applying the changes. It records files that did not exist so restore can remove newly created ones.

To undo setup, ask `$nylohq-codex-setup` to restore the exact backup directory from its completion report. Restore checks for later edits and stops rather than overwriting them. Backups can contain previous credentials: keep them private and never commit them.

For a new key, ask the skill to update your key; it will use the hidden prompt again. For catalog refresh, ask it to reuse your existing key and refresh models. Both operations make a new backup and verify the connection.

## Realtime Voice

After setup, start `codex` in a normal terminal. Inside the interactive Codex session, type `/voice` and grant microphone permission if prompted. Use `/voice stop` to finish or `/voice mute` to mute.

The setup never opens the microphone automatically. Mac CLI Voice was demonstrated in the earlier pilot. Native Windows realtime audio still needs a member pilot. Setting the Voice routes does not guarantee a desktop Voice button or every account-gated feature.

## Image generation

The NyloHQ image API host-selection repair was verified on 9 November 2026. Members using the same repaired server already benefit from that server change. The **start-here prompt above** installs or updates the complete skill, installs the image companion, records the user's chosen backend and tests a sample image in the same workflow.

The new `scripts/image_cli.py` helper passes your own protected LB key and the LB endpoint to Codex's existing bundled image CLI for that process. It does not require a new OpenAI key, change your main config, or install another image provider. It also does not make the missing built-in image tool appear in a chat.

The separate opt-in `scripts/image_defaults.py` installer addresses **new-chat discovery**: it installs the included `nylohq-imagegen` companion and records the member's chosen fallback in their personal `AGENTS.md`. It preserves existing instructions, makes private backups, and is safe to repeat. After installation, a new chat can handle an ordinary request such as “Create a sample banner image” without needing the fallback prompt again. Actual generation still depends on working credentials, server capacity and model availability.

Other codex-lb operators seeing `No accounts with a plan supporting model 'gpt-5.5'` need the **server-side fix**. See the [member instructions and operator repair](skills/nylohq-codex-setup/references/image-generation.md), including the upstream commit, a narrow 1.24.0 backport, validation and rollback. Do not apply the server patch separately on each member's laptop.

## Validation and maintenance

Mac end-to-end setup passed using `gpt-5.6-terra` and `gpt-6-luna`, including catalog discovery, strict config validation, native credential reading, text replies, repeated setup and exact restoration. The script also has offline tests for preservation, model selection, Windows command generation, key handling, rollback and restore. Native Windows execution and audio require their own pilot; these tests do not establish four-member concurrency or server-side accounting.

Run the offline tests from the repository root:

```sh
# Mac
python3 -B skills/nylohq-codex-setup/scripts/test_setup.py
python3 -B skills/nylohq-codex-setup/scripts/test_image_cli.py
python3 -B skills/nylohq-codex-setup/scripts/test_image_defaults.py
```

```powershell
# Windows
py -3 -B skills/nylohq-codex-setup/scripts/test_setup.py
py -3 -B skills/nylohq-codex-setup/scripts/test_image_cli.py
py -3 -B skills/nylohq-codex-setup/scripts/test_image_defaults.py
```

See [the skill](skills/nylohq-codex-setup/SKILL.md), [member walkthrough](skills/nylohq-codex-setup/START-HERE.md), and [platform troubleshooting](skills/nylohq-codex-setup/references/platform-notes.md). The included `tomlkit` parser retains its [MIT license](skills/nylohq-codex-setup/scripts/vendor/TOMLKIT-LICENSE) and [provenance notice](skills/nylohq-codex-setup/scripts/vendor/NOTICE.txt).

Official references: [Codex skill installation](https://learn.chatgpt.com/docs/build-skills), [provider authentication](https://learn.chatgpt.com/docs/config-file/config-advanced), and [model catalogs](https://learn.chatgpt.com/docs/model-catalogs).
