---
name: nylohq-codex-setup
description: Set up or repair direct NyloHQ LB access in the official Codex client on native macOS or Windows using the member's own API key, with config backups, model discovery, CLI verification, and realtime Voice routes. Use for onboarding a NyloHQ member, refreshing their catalog/key, or restoring this setup's backup.
---

# NyloHQ Codex setup

Configure the member's local Codex to connect directly to `https://codex.nylohq.com`. The helper performs the configuration work; follow the steps below in order. This works with a setup conversation running Terra or Luna and does not require changing that conversation's model.

This is a one-time workflow the member requests after signing in. Installing the skill does not create a login hook, background service, local bridge, router, or microphone session.

## Scope and credential handling

- Work on the member's **local computer**, not a cloud executor or WSL. Use native PowerShell on Windows. If tools only access a remote environment, give the member local commands instead of changing that remote configuration.
- The request to set up NyloHQ authorizes the backup and routing changes. Explain what will change, then proceed. Do not repeatedly ask for approval for those same changes; honor actual tool/OS permission requirements.
- Never ask for the key in chat or a normal text-input tool. The member enters it in their own Terminal/PowerShell through the helper's hidden prompt. Never run the key-entry step in an agent-controlled terminal and ask the user to paste a key into chat for you to type.
- Never print/read the key file into tool output, show the credential command's stdout, dump `auth.json`, or print the whole existing config. The helper reads credentials internally and emits a safe summary.
- Do not copy anyone else's config, key, native sign-in, model-catalog snapshot, or backups. Fetch the catalog with this member's key. Preserve plugins, MCPs, projects, preferences, other providers and native sign-in.
- Do not edit TOML by hand or append duplicate sections. Use `scripts/setup.py`; its bundled TOML parser preserves unrelated settings and comments. Do not install its Python dependencies with pip.
- Keep failures visible. Stop at the failed step; never report Voice or setup as working just because a file was written. Do not bypass TLS verification, managed policy, or OS microphone permissions.

## 1. Locate this skill and the local runtimes

Resolve this file's directory as the skill root. The executable helper is `scripts/setup.py` beneath it. Keep the complete folder, including `scripts/vendor`, together.

If the user asks to import/install this extracted skill, copy the **whole skill folder** to their personal skills directory, normally `~/.agents/skills/nylohq-codex-setup` (on Windows, resolve `~` to the member's user profile). If this client already uses a different user skill root, use that supported location. Back up an existing same-name skill folder before replacing it. Do not install duplicate copies in multiple skill roots. Continue this setup from the installed copy; a restart for skill discovery can wait until the final step.

Locate Python 3.9+ and the official Codex executable:

- Prefer the app's bundled Python when available through `load_workspace_dependencies`; otherwise try `python3` on Mac and `py -3` or `python` on Windows. Resolve its executable with `import sys; print(sys.executable)` and check its version. Python is only a setup/maintenance dependency, not a running service.
- Prefer a compatible installed official CLI. Check `codex --version`, then resolve its absolute path. The tested baseline is **0.164.0**. A newer build must also pass the helper's strict-config and connection checks.
- On Mac, common CLI locations are `/opt/homebrew/bin/codex`, `/usr/local/bin/codex`, and the desktop app's bundled CLI. Do not assume another member has these exact app paths.
- On Windows, use `Get-Command codex -All`. Pass the actual executable or official npm `codex.cmd` path. The credential helper uses built-in Windows PowerShell 5.1, which is separate from the user's terminal choice.
- If a runtime is missing, read [platform notes](references/platform-notes.md) and install or guide the member through the official prerequisite. Do not invent a substitute client or silently install a router.

For all commands below, replace `PYTHON`, `SETUP`, `CODEX` and `TARGET_HOME` with resolved absolute paths. These are placeholders, not environment-variable names. Quote paths; in PowerShell prefix a quoted executable with `&`.

Run this read-only preflight:

```text
PYTHON SETUP inspect --codex-bin CODEX
```

Record the JSON `codex_home` as `TARGET_HOME`. Use that **same home and executable** for subsequent steps. Respect a non-default `CODEX_HOME`; do not assume `~/.codex` or configure a second unused home. If a default profile is present, resolve the intended target before continuing; don't erase profiles. The current conversation's settings can remain cached until restart.

## 2. Have the member enter their own key

Provide one exact copyable command using the detected Python and helper paths:

```text
PYTHON SETUP key --home TARGET_HOME
```

Tell the member: "Run this in your own Terminal/PowerShell. Paste your NyloHQ LB key at the hidden prompt and press Enter. Then return here and say 'Key saved, continue.' Do not paste the key into this chat."

Wait for that confirmation. It is required input, not approval to repeat. Do not try to fill in or discover their key from another person's files. The command stages the key privately without replacing an active credential.

If preflight finds an existing LB key and the member explicitly wants to reuse it, skip key entry and add `--reuse-key` to the apply command. Never assume a preexisting staged key belongs to this member.

## 3. Apply the backed-up setup

Run:

```text
PYTHON SETUP apply --home TARGET_HOME --codex-bin CODEX
```

Default model selection preserves the existing model if its unprefixed ID is visible in this member's catalog. Otherwise it tries `gpt-5.6-terra`, `gpt-6-luna`, then `gpt-5.6-luna`. Preserve an explicit user preference using `--model EXACT_ID`; do not upgrade to an expensive model just for setup. Supported existing reasoning effort is retained, otherwise the model's catalog default is used.

The helper performs these operations:

1. Fetches a complete Codex model catalog using this member's key over verified HTTPS. It rejects redirects and incomplete ID-only catalogs.
2. Prepares six root settings: model, provider, reasoning, local catalog path and two Voice route URLs. Creates the `nylohq_lb` provider (or retains the known legacy provider ID when already active).
3. Configures native command-backed authentication: `/bin/cat` on Mac; a native PowerShell file-read command on Windows. The key stays in `TARGET_HOME/nylohq-lb/api-key`, never in TOML or a persistent environment variable. Refresh means reread every five minutes.
4. Strictly validates the candidate with the selected Codex binary, checks the native credential command privately, and runs one small isolated Codex text request with no copied native sign-in/plugins/MCPs/history. This uses a small amount of LB quota. It never opens a microphone.
5. Creates a timestamped private backup under `TARGET_HOME/backups/nylohq-setup-*` of the original config, LB key and model snapshot if present. Records absent files so restore can remove newly created ones. These backups may contain existing secrets; never share them.
6. Writes the validated catalog/key and updates config last. Restores the previous managed files if a normal commit error occurs. Reports the exact backup path and test results.

The catalog is a member-specific local snapshot. It takes precedence over the configured remote catalog URL. Later refresh it with `apply --reuse-key`, which makes a new backup and runs the same checks.

If `status` is not `configured`, use the reported reason and [platform notes](references/platform-notes.md). Do not repeatedly retry authentication failures or rewrite unrelated tool settings to make an old CLI accept them. Windows runtime checks must pass on that Windows computer; Mac test results are not proof of Windows success.

## 4. Finish and verify the member's experience

Report the selected model, direct LB address, target config path, backup path and checks that actually passed. Explain that existing chats can retain earlier provider/model choices.

Ask the member to fully quit and reopen their desktop client and restart CLI sessions after the work is finished; do not kill their active chat. Start a **new chat**, choose the desired model and send a short message. `/model` and `/status` in the CLI help inspect the new session. If needed, run this optional fresh verification once:

```text
PYTHON SETUP verify --home TARGET_HOME --codex-bin CODEX
```

For realtime two-way Voice, the member starts the official CLI interactively (`codex`) and then types `/voice` **inside Codex**, allowing OS microphone permission if prompted. `/voice stop` ends it; `/voice mute` mutes it. Do not run `/voice`, `/voice settings`, microphone capture or audio probes automatically. The earlier pilot demonstrated Mac CLI Voice; Windows audio must be tested by that member. Missing desktop Voice UI is a separate product/account availability issue, not proof of a failed LB text setup. Never promise complete feature parity or a restored desktop Voice button.

## Restore or repair

On an explicit request to undo this setup, use the exact recorded backup:

```text
PYTHON SETUP restore --home TARGET_HOME --backup BACKUP_DIRECTORY
```

Restore checks backup hashes and refuses to overwrite later edits. It can recover a partially committed run marked `prepared` when each current file matches either its before or proposed after hash. If later edits exist, explain the conflict and prepare a selective merge; don't force an old config over them. Restart clients after a successful restore.

For a replacement key, repeat the hidden key step and `apply`; the old active key is backed up. Do not revoke keys or change LB server accounts as part of this client skill.

Official references: [custom provider authentication](https://learn.chatgpt.com/docs/config-file/config-advanced), [model catalogs](https://learn.chatgpt.com/docs/model-catalogs), [skill locations](https://learn.chatgpt.com/docs/build-skills).
