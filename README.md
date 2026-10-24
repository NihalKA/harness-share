# NyloHQ Codex setup

Set up the official Codex client on **macOS or native Windows** using your own NyloHQ LB key. Codex installs the skill, checks prerequisites, backs up your configuration, configures the connection, and verifies it. Your current Terra or Luna model can handle the setup conversation.

## Start here: paste this into Codex

Use a **local Codex chat on the computer you want to configure**. Paste this entire message:

```text
Set up my computer using https://github.com/NihalKA/harness-share.
Read its README.md. Use $skill-installer to install the skill from
https://github.com/NihalKA/harness-share/tree/main/skills/nylohq-codex-setup.
Then read the installed SKILL.md and carry out the setup on this computer.
Keep my current Terra or Luna model if available. Preserve my existing
tools, preferences and native sign-in, and back up my configuration.
Give me the hidden terminal prompt for entering my own NyloHQ LB key;
do not ask me to paste my key into this chat. Complete the connection
checks and report the backup location. Do not start my microphone.
```

You do not need to edit TOML, copy someone else's config, install a router, or choose a stronger model for setup.

Codex will give you a command to run in your own **Terminal (Mac)** or **PowerShell (Windows)**. Run it, paste your key at the hidden prompt, press Enter, then tell Codex:

```text
Key saved, continue.
```

After Codex reports success, fully quit and reopen the desktop client and restart CLI sessions. Open a **new chat** and send a short message. Run setup once; it does not automatically repeat at every login.

## Instructions for the Codex agent

When the member asks you to set up their computer:

1. Work in their local environment. A cloud executor or WSL configuration will not configure their native desktop client.
2. Install `skills/nylohq-codex-setup` from this repository with the available `$skill-installer`. If it is already installed, inspect it before replacing anything; preserve an older copy before updating. Never install duplicate copies in multiple skill roots.
3. Read the installed `SKILL.md` and follow its ordered workflow. If the skill list only refreshes next turn, read the installed file directly to continue this request. Do not stop after merely installing the skill.
4. Use the bundled `scripts/setup.py` for preflight, private key entry, validation, backup and configuration. Resolve actual paths for this member. Do not generate your own TOML replacement.
5. The member must enter their key themselves through the hidden terminal prompt. Pause for “Key saved, continue,” then finish the authorized setup. Never request the key in chat, screenshots, command arguments or tool logs.
6. Report the checks that actually passed, the selected model, and the exact backup location. Leave microphone activation and final app restart to the member.

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

## Validation and maintenance

Mac end-to-end setup passed using `gpt-5.6-terra` and `gpt-6-luna`, including catalog discovery, strict config validation, native credential reading, text replies, repeated setup and exact restoration. The script also has offline tests for preservation, model selection, Windows command generation, key handling, rollback and restore. Native Windows execution and audio require their own pilot; these tests do not establish four-member concurrency or server-side accounting.

Run the offline tests from the repository root:

```sh
# Mac
python3 -B skills/nylohq-codex-setup/scripts/test_setup.py
```

```powershell
# Windows
py -3 -B skills/nylohq-codex-setup/scripts/test_setup.py
```

See [the skill](skills/nylohq-codex-setup/SKILL.md), [member walkthrough](skills/nylohq-codex-setup/START-HERE.md), and [platform troubleshooting](skills/nylohq-codex-setup/references/platform-notes.md). The included `tomlkit` parser retains its [MIT license](skills/nylohq-codex-setup/scripts/vendor/TOMLKIT-LICENSE) and [provenance notice](skills/nylohq-codex-setup/scripts/vendor/NOTICE.txt).

Official references: [Codex skill installation](https://learn.chatgpt.com/docs/build-skills), [provider authentication](https://learn.chatgpt.com/docs/config-file/config-advanced), and [model catalogs](https://learn.chatgpt.com/docs/model-catalogs).
