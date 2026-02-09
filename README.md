# FuzzyTerminal - Intelligent Terminal with NLP

## Overview

FuzzyTerminal is an intelligent terminal that understands natural language, adapts to your preferences, and facilitates the execution of remote commands via SSH, Ansible, and Terraform.

### Key Features

*   **Natural Language Understanding**: Type "list files" instead of `ls -la`.
*   **Contextual AI Suggestions**: Intelligent suggestions based on your history and context.
*   **Interactive Setup Wizard**: Easy first-time configuration for LLM providers.
*   **Autocompletion & Highlighting**: Modern terminal experience with command completion and syntax highlighting.
*   **Scripting Mode**: Execute one-off commands via CLI for automation.
*   **Remote Execution**: SSH, parallel execution on multiple hosts.
*   **Ansible Integration**: Generation and execution of playbooks.
*   **Extensible Plugins**: Install Ansible, Terraform, Docker, `kubectl`, etc.

## Installation

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Pip
pip3 --version
```

### Installing FuzzyTerminal

```bash
# Clone the repository
git clone https://github.com/youruser/FuzzyTerminal.git
cd FuzzyTerminal

# Install the package (this will install all dependencies and the 'fuzzy' command)
pip install .
```

## Quick Start

### 1. First Launch

Simply type `fuzzy` to start the interactive shell. If it's your first time, a setup wizard will guide you through the configuration.

```bash
fuzzy
```

### 2. Scripting Mode

Execute commands directly without entering the interactive shell:

```bash
fuzzy -c "list files in /var/log"
fuzzy -c "fuzzy remote exec server1 uptime"
```

### 3. Configuring the API Key

You can also configure the API key manually:

```bash
fuzzy fuzzy config set-key anthropic sk-ant-xxxxxxxxxxxxx
```

## User Guide

### Interactive Shell Features

*   **Autocompletion**: Press `Tab` to see suggestions for `fuzzy` commands.
*   **Syntax Highlighting**: Commands are highlighted as you type.
*   **AI Suggestions**: For natural language inputs, the AI will suggest the most likely shell command.

### Managing Plugins

```bash
# List available plugins
fuzzy fuzzy plugin list

# Install a plugin
fuzzy fuzzy plugin install ansible
```

### Managing Remote Hosts

#### Adding Hosts

```bash
# With SSH key
fuzzy fuzzy remote add server1 192.168.1.10 admin ~/.ssh/id_rsa
```

#### Listing Hosts

```bash
fuzzy fuzzy remote list
```

#### Executing Remote Commands

```bash
# On a single host
fuzzy fuzzy remote exec server1 uptime
```

### Chat Mode

```bash
fuzzy fuzzy chat

🤖 You: How do I optimize Nginx for high traffic?
💡 AI: [detailed response...]
```

## Advanced Configuration

### Configuration File

The configuration file is stored in `~/.fuzzyterminal/config.json`.

```json
{
  "provider": "anthropic",
  "providers": {
    "anthropic": {
      "model": "claude-3-5-sonnet-20240620"
    }
  },
  "preferences": {
    "auto_suggest": true,
    "max_suggestions": 5
  }
}
```

## Security

*   **Keyring Support**: API keys are securely stored in your system's keyring, not in plain text files.
*   **SSH Keys**: Always use SSH keys instead of passwords for remote execution.

## Troubleshooting

*   **Keyring Issues**: If you encounter keyring errors, ensure a keyring backend (like `kwallet` or `gnome-keyring`) is installed and running.
*   **Missing Dependencies**: If a plugin fails, try reinstalling the package: `pip install .`

## License

MIT License - Free to use and modify
