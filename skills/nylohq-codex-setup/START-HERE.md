# Set up your NyloHQ Codex connection

Use this same package for the two Windows members and the two Mac members. Each person uses their own NyloHQ LB key. Run setup once after signing into the local Codex client; it does not run automatically at every login.

## What you need

- A working local Codex chat. Terra or Luna is fine for the setup conversation.
- Your own NyloHQ LB API key, supplied separately by your administrator.
- A compatible official Codex CLI (tested baseline 0.164.0) and Python 3.9+ for the setup script. The skill checks for existing/bundled installations and guides you if either is missing. Python is not a background service and is not needed for normal Codex requests after setup.
- On Windows, use native Windows PowerShell/Terminal for this setup, not WSL.

## Import and set up

1. Save `nylohq-codex-setup.zip` on your computer. Extract it (Windows: right-click, **Extract All**; Mac: double-click).
2. Open the extracted **folder containing `SKILL.md`** as a local folder/project in Codex. Depending on the extractor, there may be a second folder with the same name inside the first. Keep all included files together; do not upload or copy only `SKILL.md`.
3. Start a chat using your currently available Terra or Luna model and paste:

   > Read SKILL.md in this folder. Install this entire folder as my personal nylohq-codex-setup skill, then follow it to configure this computer with my own NyloHQ LB key. Keep my current Terra or Luna model if available. Back up my configuration and preserve my existing tools and sign-in. Give me the hidden terminal key-entry command instead of asking for my key in chat. Complete the connection checks and report the backup location. Do not start my microphone.

4. The agent will give you an exact command for your computer. Run it in your own **Terminal on Mac** or **PowerShell on Windows**. Paste your key at the hidden prompt and press Enter. Nothing will appear as you type/paste. Return to the chat and say:

   > Key saved, continue.

5. Wait for a successful setup report with the chosen model and backup location. Fully quit and reopen the desktop client and restart any CLI sessions. Open a new chat, select your model, and send a short message.

If the agent cannot access your computer locally, switch to a local Codex session or follow its local terminal instructions. Configuring a cloud executor will not configure your laptop.

The standard personal skill location is `~/.agents/skills/nylohq-codex-setup` on Mac and `%USERPROFILE%\.agents\skills\nylohq-codex-setup` on Windows. The agent can use the supported existing skill root for your client instead. After import, you can invoke it in future with `$nylohq-codex-setup`. If it is not listed, restart the client; you can always open the installed `SKILL.md` and ask Codex to follow it directly.

## What it changes

The helper reads your key privately, fetches the current model metadata using that key, and tests the proposed connection before committing it. It backs up your existing `config.toml` and previous LB key/catalog if present, then configures direct HTTPS access to `https://codex.nylohq.com`.

It preserves your current model when available, including Terra or Luna. It retains your existing plugins, MCP tools, project trust settings, desktop preferences, other providers, native sign-in and chat history. Older chats may retain their old provider/model selection; use a new chat to test the new default.

Credentials are stored in your Codex home's protected `nylohq-lb/api-key` file. Mac uses `/bin/cat` to read it; Windows uses a native PowerShell file-read command. Neither needs a local bridge, router, persistent environment helper, or extra listening port. The key is protected by file permissions, not encrypted by this package.

Backups are stored under your Codex home's `backups/nylohq-setup-*`. Keep them private: old config/key backups can contain credentials. The shareable ZIP itself contains no member keys, native sign-in data, personal config or model-catalog snapshot.

## Try live Voice yourself

After setup, open a normal terminal and run `codex`. Inside the interactive Codex session, type `/voice` to start realtime two-way Voice. Allow microphone access if prompted. Use `/voice stop` to finish, or `/voice mute` to mute.

The setup script never opens your microphone. Mac CLI Voice was demonstrated in the earlier pilot. Windows realtime audio still needs a member pilot, and this configuration does not guarantee a desktop Voice button or every account-gated feature.

## Later maintenance or undo

- Refresh models: ask `$nylohq-codex-setup` to refresh your catalog while reusing your existing key. It backs up and tests again.
- Replace your key: ask the skill to update your key. It will give you the hidden prompt again.
- Undo setup: ask the skill to restore the exact backup directory from the successful report. Restore checks for later changes and stops rather than overwriting them.

If configuration fails, send the administrator the safe status/error summary, your OS and Codex version. Do not send key files, `auth.json`, a full config dump, or private backups.
