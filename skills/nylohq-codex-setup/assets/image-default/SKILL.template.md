---
name: nylohq-imagegen
description: Generate or edit raster images through the user's configured NyloHQ LB when the built-in image tool is unavailable. Use for requests to create images, banners, illustrations, backgrounds, or edit photos on a NyloHQ-configured computer. Exclude code-native SVG/icons, charts, and video.
---

# NyloHQ image generation

Use the existing NyloHQ image API connection for requested image work when the native image tool is missing. This is a real image-generation path, not a placeholder renderer.

Read the user's image-backend preference in the Codex home AGENTS.md and honor the authorization it records. This skill by itself does not grant API fallback permission to a different user: if that preference or current-conversation approval is absent, obtain their choice before a live request. Do not ask this user to repeat their recorded choice for every new chat.

The installed sibling nylohq-codex-setup skill supplies scripts/image_cli.py and references/image-generation.md. Resolve both relative to this skill's parent directory, not the project. Read that image-generation reference for endpoint handling and exact invocation. Do not rerun onboarding on an already-configured computer.

Use the bundled imagegen skill for image prompting, generation/editing parameters, file handling and visual inspection. Its API fallback is the selected route when the user's recorded preference applies. Leave its stock files unchanged.

Run the image helper's --check first if this session has not checked the connection. It supplies the member's existing protected key and configured NyloHQ endpoint only to the bundled image CLI process. OPENAI_API_KEY being absent from the shell is expected and does not mean credentials are missing. Never print the key, dump the full config, request a new OpenAI key, or install an unrelated image service when this path works.

Use the local uv runtime when available: uv --native-tls run --with openai python IMAGE_HELPER --home CODEX_HOME --image-cli IMAGE_CLI -- generate [bundled CLI arguments]. Resolve paths before execution. The same helper supports edit and generate-batch. Prefer gpt-image-2; respect the imagegen skill's model-switch requirements.

Write requested images under the project's output/imagegen directory, use a new filename, check actual dimensions, and visually inspect the final file. For a LinkedIn banner, generate a crop-safe composition within the API's aspect-ratio limit and crop/resize to 1584 x 396. Show the finished image inline and link its saved path. Do not stop at offering instructions when generation is possible.

If the helper or server fails, report the concrete error. Do not claim generation succeeded or promise unconditional availability. A server account, quota, network, policy or model error can still block a request. An image request alone does not authorize patching/restarting the server.
