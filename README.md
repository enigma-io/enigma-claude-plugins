# Enigma Claude Code Plugins

Public Claude Code marketplace for the Enigma API plugin.

> [!IMPORTANT]
> This repository is a generated public mirror of Enigma's internal source-of-truth marketplace.
> Runtime plugin files are published here, but development, testing, and release management happen in the internal repository.
> Please do not expect direct edits merged here to persist unless they are also applied internally.

## Install the marketplace

HTTPS:

```bash
/plugin marketplace add https://github.com/enigma-io/enigma-claude-plugins.git
```

SSH:

```bash
/plugin marketplace add git@github.com:enigma-io/enigma-claude-plugins.git
```

## Install the plugin

```bash
/plugin install enigma-api@enigma-plugins
```

## Included plugin

| Plugin | Description |
| --- | --- |
| `enigma-api` | Query Enigma APIs — GraphQL business data, KYB verification, sanctions screening, and government archive records |

## Prerequisites

Set your Enigma API key before using the plugin:

```bash
export ENIGMA_API_KEY=your_api_key_here
```

Get your API key from [console.enigma.com](https://console.enigma.com/).

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

In short:
- discussion and suggestions in GitHub issues/PRs are welcome
- accepted changes must land in Enigma's internal source repository first
- this public repo is then regenerated and republished from that internal source of truth

## Repo structure

```text
enigma-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── enigma-api/
└── README.md
```
