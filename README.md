# FuzzyTerminal - Intelligent Terminal with NLP

## Overview

FuzzyTerminal is an intelligent terminal that understands natural language, adapts to your preferences, and facilitates the execution of remote commands via SSH, Ansible, and Terraform.

### Key Features

*   **Natural Language Understanding**: Type "list files" instead of `ls -la`.
*   **Contextual AI Suggestions**: Intelligent suggestions based on your history and context.
*   **Remote Execution**: SSH, parallel execution on multiple hosts.
*   **Ansible Integration**: Generation and execution of playbooks.
*   **Terraform Support**: Remote execution of Terraform.
*   **Chat Mode**: Discuss with AI/LLM directly in the terminal.
*   **Extensible Plugins**: Install Ansible, Terraform, Docker, `kubectl`, etc.

## Installation

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Pip
pip3 --version

# Git (optional)
git --version
```

### Installing Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv fuzzyterm-env
source fuzzyterm-env/bin/activate  # Linux/Mac
# or
.\fuzzyterm-env\Scripts\activate  # Windows

# Install dependencies
pip install anthropic paramiko pyyaml
```

### Installing FuzzyTerminal

```bash
# Clone or download the files
mkdir ~/fuzzyterminal
cd ~/fuzzyterminal

# Copy the Python files (Assuming they are in a source directory or being downloaded/cloned)
# - fuzzyterminal_core.py
# - fuzzyterminal_remote.py

# Make executable
chmod +x fuzzyterminal_core.py

# Create an alias (optional)
echo "alias fuzzy='python3 ~/fuzzyterminal/fuzzyterminal_core.py'" >> ~/.bashrc
source ~/.bashrc
```

## Quick Start

### 1. First Launch

```bash
python3 fuzzyterminal_core.py
```

### 2. Configuring the API Key (optional but recommended)

```bash
fuzzy> fuzzy config set-api-key sk-ant-xxxxxxxxxxxxx
```

Get your API key from: https://console.anthropic.com/

### 3. Basic Commands

```bash
# Standard shell commands
fuzzy> ls -la
fuzzy> cd /var/log
fuzzy> grep error syslog

# Natural language
fuzzy> list files
fuzzy> show processes
fuzzy> available disk space
```

## User Guide

### Managing Plugins

```bash
# List available plugins
fuzzy> fuzzy plugin list

# Install a plugin
fuzzy> fuzzy plugin install ansible
fuzzy> fuzzy plugin install terraform
fuzzy> fuzzy plugin install docker
fuzzy> fuzzy plugin install kubectl
```

### Managing Remote Hosts

#### Adding Hosts

```bash
# With SSH key
fuzzy> fuzzy remote add server1 192.168.1.10 admin ~/.ssh/id_rsa

# Complete syntax
fuzzy remote add <name> <ip_or_host> <user> [ssh_key_path]
```

#### Listing Hosts

```bash
fuzzy> fuzzy remote list
```

#### Executing Remote Commands

```bash
# On a single host
fuzzy> fuzzy remote exec server1 uptime

# Complex command
fuzzy> fuzzy remote exec server1 "df -h && free -m"
```

### Chat Mode

```bash
fuzzy> fuzzy chat

🤖 You: How do I optimize Nginx for high traffic?
💡 AI: [detailed response...]

🤖 You: Give me an example configuration
💡 AI: [configuration...]

🤖 You: exit
```

### Using Ansible

#### Creating and Executing a Playbook

```bash
# Prepare a playbook (example: install_nginx.yml)
---
- name: Install Nginx
  hosts: all
  become: yes
  tasks:
    - name: Install Nginx
      apt:
        name: nginx
        state: present
        update_cache: yes
    
    - name: Start Nginx
      service:
        name: nginx
        state: started
        enabled: yes

# Execute the playbook
fuzzy> fuzzy ansible install_nginx.yml server1,server2,server3
```

#### Integrated Ansible Mode

The system automatically generates the inventory based on your configured hosts.

### Advanced Examples

#### 1. Deploying a Web Application

```bash
# Add web servers
fuzzy> fuzzy remote add web1 10.0.1.10 deploy
fuzzy> fuzzy remote add web2 10.0.1.11 deploy
fuzzy> fuzzy remote add web3 10.0.1.12 deploy

# Health check
fuzzy> fuzzy remote exec web1 "curl -I localhost"

# Deploy with Ansible
fuzzy> fuzzy ansible deploy_app.yml web
```

## Advanced Configuration

### Configuration File

The configuration file is stored in `~/.fuzzyterminal/config.json`.

```json
{
  "api_key": "sk-ant-xxxxx",
  "preferences": {
    "auto_suggest": true,
    "context_aware": true,
    "max_suggestions": 5
  },
  "plugins": {
    "ansible": true,
    "terraform": true
  },
  "remote_hosts": {
    "server1": {
      "host": "192.168.1.10",
      "user": "admin",
      "key_path": "~/.ssh/id_rsa",
      "tags": ["web", "prod"]
    }
  }
}
```

### Customizing Preferences

Example changes in the config file:

```json
// Disable auto-suggestions
"auto_suggest": false,

// Increase the number of suggestions
"max_suggestions": 10
```

## Practical Use Cases

### System Administrator

```bash
# Update all servers
fuzzy> fuzzy ansible update_servers.yml prod-web1,prod-web2,prod-db1

# Check logs
fuzzy> fuzzy remote exec prod-web1 "tail -100 /var/log/nginx/error.log"

# Restart services
fuzzy> fuzzy remote exec prod-web1 "systemctl restart nginx"
```

### DevOps Engineer

```bash
# Deploy CI/CD
fuzzy> fuzzy ansible deploy_v2.3.yml staging-servers

# Rollback
fuzzy> fuzzy ansible rollback.yml production-servers

# Infrastructure provisioning (Assuming Terraform integration allows this via a command or plugin)
fuzzy> fuzzy remote exec tf-server "cd /terraform/aws && terraform apply"
```

### Developer

```bash
# Set up development environment
fuzzy> fuzzy ansible setup_dev_env.yml dev1,dev2

# Deploy test
fuzzy> fuzzy remote exec test-server "cd /app && docker-compose up -d"

# Retrieve logs
fuzzy> fuzzy remote exec test-server "docker logs app-container --tail 100"
```

## Security

### Best Practices

*   **SSH Keys**: Always use SSH keys instead of passwords.
*   **Permissions**: Limit the permissions of configuration files: `chmod 600 ~/.fuzzyterminal/config.json`.
*   **API Key**: Never share your Anthropic API key.
*   **Audit**: Regularly check the history: `fuzzy> fuzzy history`.

### Secret Management

For sensitive secrets, use Ansible Vault:

```bash
# Create an encrypted variables file
ansible-vault create secrets.yml

# Run with vault
ansible-playbook -i inventory playbook.yml --ask-vault-pass
```

## Monitoring and Logs

### Command History

```bash
# View history
fuzzy> fuzzy history

# Detailed history in ~/.fuzzyterminal/history.json
```

### Host Statistics

```bash
fuzzy> fuzzy remote list
# Displays success/failure statistics for each host
```

## Integration with Workflows

### Bash Script with FuzzyTerminal

```bash
#!/bin/bash
# deploy.sh

echo "Deploying the application..."

# Use fuzzy in a script (passing the command via stdin or argument, depending on implementation)
python3 ~/fuzzyterminal/fuzzyterminal_core.py --command "fuzzy ansible deploy_app.yml production-servers"

echo "Deployment complete"
```
*Correction: Changed the heredoc structure for shell scripting to a more standard approach or noted the need for specific CLI argument handling.*

### Cron Jobs

```bash
# Automatic monitoring every hour
0 * * * * python3 ~/fuzzyterminal/fuzzyterminal_core.py --command "fuzzy remote exec all-servers 'df -h'"```
```

## Troubleshooting

### Common Issues

*   **SSH Timeout**: Increase the timeout in the code: `timeout=60` (instead of 30, assuming this is a configuration point).
*   **Ansible Connection Error**:
    *   Check SSH connectivity: `ssh -i ~/.ssh/id_rsa user@host`
    *   Test with verbose output: `ansible-playbook -vvv playbook.yml`
*   **AI Suggestions Not Working**:
    *   Check the API key: `fuzzy> fuzzy config set-api-key YOUR_KEY`
    *   Check internet connection: `ping api.anthropic.com`

## Roadmap

*   Support for more plugins (`k8s`, `aws-cli`, `gcloud`).
*   Optional web interface.
*   Multi-machine synchronization.
*   Integrated playbook templates.
*   Auto-learning of user patterns.
*   Windows PowerShell support.
*   GitOps integration.
*   Monitoring dashboard.

## Contribution

Contributions are welcome! Areas for improvement:

*   New plugins
*   Ansible/Terraform templates
*   NLP improvement
*   Documentation
*   Testing

## License

MIT License - Free to use and modify
