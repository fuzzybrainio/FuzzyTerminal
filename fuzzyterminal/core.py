#!/usr/bin/env python3
"""
FuzzyTerminal - Intelligent Terminal with NLP (Async)
A terminal that understands context and adapts to user preferences.
"""

import os
import json
import asyncio
import shlex
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Third-party imports
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import radiolist_dialog
import keyring

# ... (imports)
import argparse
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.shell import BashLexer

# Local imports
try:
    from .remote import RemoteExecutor
    from .llm_providers import ProviderFactory
    from .config_model import FuzzyConfig, ProviderConfig
except ImportError:
    # Fallback if running directly
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from remote import RemoteExecutor
    from llm_providers import ProviderFactory
    from config_model import FuzzyConfig, ProviderConfig

class FuzzyTerminal:
    def __init__(self):
        self.console = Console()
        self.config_dir = Path.home() / ".fuzzyterminal"
        self.config_file = self.config_dir / "config.json"
        self.history_file = self.config_dir / "history.json"
        self.plugins_dir = self.config_dir / "plugins"
        
        self.setup_directories()
        self.config = self.load_config()
        self.history = self.load_history()
        
        # Initialize Remote Executor
        self.remote_executor = RemoteExecutor(self.config_dir)
        
        # Initialize LLM Provider
        self.llm_provider = None
        self.init_llm_provider()
        
        self.context = {
            "current_dir": os.getcwd(),
            "last_commands": [],
            "user_preferences": {},
            "active_plugins": []
        }
        
        # Autocompletion
        self.fuzzy_completer = NestedCompleter.from_nested_dict({
            'fuzzy': {
                'config': {
                    'set-provider': {'anthropic': None, 'openai': None, 'gemini': None, 'ollama': None, 'deepseek': None},
                    'set-key': {'anthropic': None, 'openai': None, 'gemini': None, 'ollama': None, 'deepseek': None}
                },
                'remote': {'list': None, 'add': None, 'exec': None, 'remove': None},
                'ansible': None,
                'chat': None,
                'help': None,
                'plugin': {'list': None, 'install': None}
            }
        })
        
        # Prompt Toolkit Session
        self.session = PromptSession(
            lexer=PygmentsLexer(BashLexer),
            completer=self.fuzzy_completer
        )
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
        })

    # ... (methods setup_directories to save_history remain mostly same, skipping for brevity in this thought block but will include in tool call)
    
    def setup_directories(self):
        """Create necessary directories"""
        self.config_dir.mkdir(exist_ok=True)
        self.plugins_dir.mkdir(exist_ok=True)
        
    def load_config(self) -> FuzzyConfig:
        """Load configuration using Pydantic"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                return FuzzyConfig(**data)
            except Exception as e:
                self.console.print(f"[red]Config Error: {e}. Loading defaults.[/red]")
                return FuzzyConfig()
        return FuzzyConfig()
    
    def save_config(self):
        """Save configuration"""
        with open(self.config_file, 'w') as f:
            f.write(self.config.model_dump_json(indent=2))

    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key from keyring"""
        try:
            return keyring.get_password("fuzzyterminal", provider)
        except Exception as e:
            self.console.print(f"[yellow]Keyring Error: {e}[/yellow]")
            return None

    def set_api_key(self, provider: str, key: str):
        """Save API key to keyring"""
        try:
            keyring.set_password("fuzzyterminal", provider, key)
        except Exception as e:
            self.console.print(f"[red]Keyring Error: {e}[/red]")

    def init_llm_provider(self):
        """Initialize the LLM provider based on config"""
        try:
            provider_name = self.config.provider
            if provider_name not in self.config.providers:
                self.config.providers[provider_name] = ProviderConfig()
            
            provider_cfg = self.config.providers[provider_name]
            api_key = self.get_api_key(provider_name)
            
            factory_config = {
                "provider": provider_name,
                "providers": {
                    provider_name: {
                        "api_key": api_key,
                        "model": provider_cfg.model,
                        "base_url": provider_cfg.base_url
                    }
                }
            }
            
            self.llm_provider = ProviderFactory.create(factory_config)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not initialize LLM provider: {e}[/yellow]")
            self.llm_provider = None
    
    def load_history(self) -> List:
        """Load command history"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_history(self):
        """Save history"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history[-1000:], f, indent=2)
    
    def add_to_history(self, command: str, result: str, success: bool):
        """Add command to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "result": result[:500] if result else "",
            "success": success,
            "context": {
                "dir": self.context["current_dir"],
                "user": os.getenv("USER")
            }
        }
        self.history.append(entry)
        self.context["last_commands"].append(command)
        if len(self.context["last_commands"]) > 10:
            self.context["last_commands"].pop(0)
    
    async def get_ai_suggestion(self, user_input: str) -> List[Dict[str, str]]:
        """Get AI suggestions based on context (Async)"""
        if not self.llm_provider:
            return []
        
        context_info = f"""
Current Context:
- Directory: {self.context['current_dir']}
- Last Commands: {', '.join(self.context['last_commands'][-5:])}
- User Input: {user_input}
- OS: {os.uname().sysname}
"""
        return await self.llm_provider.get_suggestions(context_info)
    
    async def execute_command(self, command: str) -> tuple:
        """Execute a shell command (Async)"""
        try:
            # Handle cd command internally
            if command.strip().startswith("cd "):
                path = command.strip()[3:].strip()
                os.chdir(os.path.expanduser(path))
                self.context['current_dir'] = os.getcwd()
                return "", True

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            success = process.returncode == 0
            return output, success
        except Exception as e:
            return f"Error: {str(e)}", False

    async def show_suggestions_ui(self, suggestions: List[Dict[str, str]]) -> Optional[str]:
        """Show interactive suggestion UI (Async wrapper)"""
        if not suggestions:
            return None
            
        choices = []
        for i, sugg in enumerate(suggestions):
            choices.append((sugg['command'], f"{sugg['command']} - {sugg['explanation']}"))
            
        choices.append(("cancel", "Cancel"))
        
        # radiolist_dialog is blocking, run in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: radiolist_dialog(
                title="AI Suggestions",
                text="Select a command to execute:",
                values=choices
            ).run()
        )
        
        if result == "cancel":
            return None
        return result

    async def handle_fuzzy_command(self, command: str):
        """Handle special fuzzy commands (Async)"""
        parts = shlex.split(command)
        if not parts:
            return
        
        cmd = parts[0]
        args = parts[1:]
        
        if cmd == "config":
            if len(args) >= 2 and args[0] == "set-provider":
                try:
                    self.config.provider = args[1]
                    self.save_config()
                    self.init_llm_provider()
                    self.console.print(f"[green]✓ Provider switched to {args[1]}[/green]")
                except ValueError as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                    
            elif len(args) >= 3 and args[0] == "set-key":
                provider = args[1]
                key = args[2]
                self.set_api_key(provider, key)
                if provider not in self.config.providers:
                    self.config.providers[provider] = ProviderConfig()
                self.config.providers[provider].api_key = None
                self.save_config()
                self.init_llm_provider()
                self.console.print(f"[green]✓ API Key for {provider} secured in Keyring[/green]")
        
        elif cmd == "remote":
            if not args:
                self.console.print("Usage: fuzzy remote [list|add|exec|remove]")
                return

            subcmd = args[0]
            if subcmd == "list":
                hosts = self.remote_executor.list_hosts()
                table = Table(title="Remote Hosts")
                table.add_column("Name", style="cyan")
                table.add_column("Host", style="magenta")
                table.add_column("User", style="green")
                table.add_column("Tags")
                for name, info in hosts.items():
                    table.add_row(name, info['host'], info['user'], ", ".join(info.get('tags', [])))
                self.console.print(table)
                
            elif subcmd == "add" and len(args) >= 4:
                self.remote_executor.add_host(args[1], args[2], args[3], args[4] if len(args) > 4 else None)
                
            elif subcmd == "exec" and len(args) >= 3:
                output, success = await self.remote_executor.execute_ssh(args[1], args[2])
                style = "green" if success else "red"
                self.console.print(Panel(output, title=f"Output from {args[1]}", border_style=style))
                
            elif subcmd == "remove" and len(args) >= 2:
                self.remote_executor.remove_host(args[1])
                
        elif cmd == "ansible":
            if len(args) >= 2:
                playbook = args[0]
                hosts = args[1].split(',')
                output, success = await self.remote_executor.run_ansible_playbook(playbook, hosts)
                self.console.print(output)
                
        elif cmd == "chat":
            await self.chat_mode()
            
        elif cmd == "help":
            self.show_help()

    async def chat_mode(self):
        """Interactive Chat Mode (Async)"""
        if not self.llm_provider:
            self.console.print("[red]LLM Provider not configured or failed to initialize.[/red]")
            return
            
        self.console.print(Panel(f"Chat Mode Active ({self.config.provider}) (type 'exit' to quit)", style="blue"))
        
        while True:
            try:
                # prompt_async is the async version
                user_input = await self.session.prompt_async("🤖 You: ", style=self.style, is_password=False)
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                with self.console.status("[bold green]Thinking..."):
                    response_text = await self.llm_provider.generate_text(user_input)
                
                self.console.print(Markdown(f"**AI:**\n{response_text}"))
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

    def show_help(self):
        """Show help message"""
        help_md = """
# 🚀 FuzzyTerminal Help

FuzzyTerminal is an intelligent terminal that combines standard shell capabilities with AI-powered assistance.

## 🛠 Commands

### Standard Shell Commands
You can run any standard command like `ls`, `cd`, `git`, `grep`, etc.

### Natural Language
Just type what you want to do, and the AI will suggest a command:
- `list all python files`
- `find where the logs are`
- `check my disk usage`

### Special Commands
- `/help`: Show this help message
- `/chat`: Enter interactive AI chat mode
- `/exit` or `/quit`: Leave FuzzyTerminal

### Fuzzy Management Commands
- `fuzzy config set-provider <name>`: Switch LLM provider (anthropic, openai, etc.)
- `fuzzy config set-key <provider> <key>`: Securely store your API key
- `fuzzy remote list`: List configured remote hosts
- `fuzzy remote add <name> <host> <user> [key]`: Add a new remote host
- `fuzzy remote exec <name> <cmd>`: Run a command on a remote host
- `fuzzy ansible <playbook> <hosts>`: Execute an Ansible playbook

## 💡 Tips
- Use **Tab** for autocompletion of `fuzzy` commands.
- Commands are syntax-highlighted as you type.
- Your history is saved across sessions.
"""
        self.console.print(Markdown(help_md))

    async def run_wizard(self):
        """Run first-time setup wizard"""
        self.console.print(Panel("Welcome to FuzzyTerminal! Let's get you set up.", style="bold green"))
        
        # Provider selection
        provider = await self.session.prompt_async("Select LLM Provider (openai/anthropic/gemini/deepseek/ollama) [openai]: ", style=self.style)
        provider = provider.strip() or "openai"
        self.config.provider = provider
        
        # API Key
        key = await self.session.prompt_async(f"Enter API Key for {provider}: ", is_password=True, style=self.style)
        if key.strip():
            self.set_api_key(provider, key.strip())
            
        self.save_config()
        self.init_llm_provider()
        self.console.print("[green]Setup complete![/green]")

    async def run_async(self, command: str = None):
        """Main Async Loop"""
        if command:
            # One-off command execution
            if command.startswith("fuzzy "):
                await self.handle_fuzzy_command(command[6:])
            else:
                output, success = await self.execute_command(command)
                if output:
                    self.console.print(output.strip())
            return

        # Check if first run
        if not self.config_file.exists():
            await self.run_wizard()

        self.console.print(Panel.fit(f"FuzzyTerminal v3.0 Async ({self.config.provider})", style="bold blue"))
        
        while True:
            try:
                cwd = os.path.basename(os.getcwd()) or "/"
                # Use prompt_async for non-blocking input
                user_input = await self.session.prompt_async(f"[{cwd}] fuzzy> ", style=self.style, is_password=False)
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit', '/exit', '/quit']:
                    self.console.print("Goodbye!")
                    break
                
                if user_input == "/help":
                    self.show_help()
                    continue

                if user_input == "/chat":
                    await self.chat_mode()
                    continue
                
                if user_input.startswith("fuzzy "):
                    await self.handle_fuzzy_command(user_input[6:])
                    continue
                
                is_natural_language = " " in user_input and not user_input.startswith("-") and not any(c in user_input for c in "|><&")
                
                if is_natural_language and self.config.preferences.auto_suggest:
                    with self.console.status("[bold green]Analyzing..."):
                        suggestions = await self.get_ai_suggestion(user_input)
                    
                    if suggestions:
                        selected = await self.show_suggestions_ui(suggestions)
                        if selected:
                            user_input = selected
                        else:
                            continue
                
                output, success = await self.execute_command(user_input)
                if output:
                    self.console.print(output.strip())
                
                self.add_to_history(user_input, output, success)
                
            except KeyboardInterrupt:
                continue
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
        
        self.save_history()
        self.save_config()

def main():
    parser = argparse.ArgumentParser(description="FuzzyTerminal - Intelligent Terminal")
    parser.add_argument("-c", "--command", help="Execute a single command and exit")
    args = parser.parse_args()

    terminal = FuzzyTerminal()
    try:
        asyncio.run(terminal.run_async(command=args.command))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
