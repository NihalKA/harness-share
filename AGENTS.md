# Working with this repository

This repository distributes the NyloHQ member setup skill. Distinguish onboarding a member from maintaining the repository.

## When the user asks to set up their computer

Read `README.md`, install the complete `skills/nylohq-codex-setup` folder into the supported personal skill root, then read that skill's `SKILL.md` and execute its workflow. Use the bundled helper rather than generating TOML edits. Continue after skill installation; the user's request is a configured client, not just an installed skill.

Use a local runtime on the target computer. Keep each member's API key out of chat, argv, logs and this repository; the member enters it in their own terminal using the helper's hidden prompt. Preserve their tools and sign-in. Never activate a microphone automatically or promise that a text check proves realtime Voice works.

## When maintaining or reviewing this repository

Do not run `apply`, `key` or `restore` against a real user's Codex home just to test a repository change. Use temporary fixtures and `scripts/test_setup.py`. The live setup needs a member's own credential and belongs only to an explicitly requested onboarding/repair workflow.

Keep all distributable skill resources under `skills/nylohq-codex-setup`. Maintain Windows and Mac path handling and the vendored dependency's license. Do not add personal config, model snapshots, auth files, keys, recordings or private backups. Keep test outcomes and platform limitations accurate in the README.

Run changed-script checks with:

```text
python3 -B skills/nylohq-codex-setup/scripts/test_setup.py
```

Use `py -3` in native Windows when appropriate. For documentation-only edits, check the referenced paths and rendered instructions; do not make live API calls.
