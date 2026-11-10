# Tiny, for any coding agent

This repo is a set of scripts plus one instruction file. You do not need a plugin system to use it.

- Instructions: plugin/tiny/skills/tiny/SKILL.md (follow it step by step; `<scripts>` is plugin/tiny/scripts).
- Painting needs an image model. Codex and the ChatGPT desktop app use their built-in image generation. Other agents run plugin/tiny/scripts/paint_api.py with OPENROUTER_API_KEY.
- Tiny World (the shared map) is optional: set TINY_WORLD to its address to check a place, publish a Tiny or help paint a city.
- Changing the scripts: bump "version" in plugin/tiny/.codex-plugin/plugin.json and plugin/tiny/.claude-plugin/plugin.json so installed copies update.
