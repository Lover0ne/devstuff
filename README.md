# devstuff

A personal collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugins built to streamline my daily workflow. Each plugin solves a specific problem I ran into repeatedly — and since they might help others too, the marketplace is public.

## Install

```bash
/plugin marketplace add Lover0ne/devstuff
```

Then browse available plugins:

```bash
/plugins
```

Each plugin can be installed individually. Check the plugin's own README for details and commands.

## Structure

```
devstuff/
├── .claude-plugin/
│   └── marketplace.json    # Marketplace manifest
└── plugins/
    ├── plugin-a/           # Each plugin has its own README,
    ├── plugin-b/           #   commands, agents, hooks,
    └── plugin-c/           #   and documentation.
```

## Philosophy

- **Built for real use** — every plugin started as a solution to a problem I had
- **Zero config** — plugins work out of the box, no setup wizards
- **Minimal footprint** — no external dependencies, no API keys, no cloud services
- **Self-contained** — each plugin is independent, install only what you need

## License

MIT
