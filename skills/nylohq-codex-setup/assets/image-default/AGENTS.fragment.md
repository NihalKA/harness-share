## Personal image backend choice

When I ask to create or edit a raster image and the built-in image tool is unavailable, use my existing configured NyloHQ LB image API fallback. I chose this as my default backend for requested image work, so do not ask me to repeat that API-fallback choice in every new chat. This does not authorize switching providers, purchasing credits, expanding account access or modifying the server.

Read the installed NyloHQ image skill at IMAGE_SKILL_FILE. Use the installed helper at IMAGE_HELPER_FILE with Codex's bundled imagegen CLI. The helper privately supplies my protected existing LB key and endpoint to that process. Missing OPENAI_API_KEY in the parent shell is expected; run the helper's --check rather than stopping or asking for another key. Keep credentials private.

Follow the imagegen skill for prompting, model parameters and visual checks, while honoring my saved backend choice. Generate the requested artifact and show it. If the existing LB returns a real error, report it accurately; do not promise unconditional availability.
