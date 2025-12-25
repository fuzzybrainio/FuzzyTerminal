#!/usr/bin/env python3
"""
FuzzyTerminal - Terminal Intelligent avec NLP
Un terminal qui comprend le contexte et s'adapte aux préférences utilisateur
"""

import os
import json
import subprocess
import readline
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import anthropic

class FuzzyTerminal:
    def __init__(self):
        self.config_dir = Path.home() / ".fuzzyterminal"
        self.config_file = self.config_dir / "config.json"
        self.history_file = self.config_dir / "history.json"
        self.plugins_dir = self.config_dir / "plugins"
        
        self.setup_directories()
        self.config = self.load_config()
        self.history = self.load_history()
        self.context = {
            "current_dir": os.getcwd(),
            "last_commands": [],
            "user_preferences": {},
            "active_plugins": []
        }
        
    def setup_directories(self):
        """Créer les répertoires nécessaires"""
        self.config_dir.mkdir(exist_ok=True)
        self.plugins_dir.mkdir(exist_ok=True)
        
    def load_config(self) -> Dict:
        """Charger la configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "api_key": None,
            "preferences": {
                "auto_suggest": True,
                "context_aware": True,
                "max_suggestions": 5
            },
            "plugins": {},
            "remote_hosts": {}
        }
    
    def save_config(self):
        """Sauvegarder la configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_history(self) -> List:
        """Charger l'historique des commandes"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_history(self):
        """Sauvegarder l'historique"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history[-1000:], f, indent=2)  # Garder les 1000 dernières
    
    def add_to_history(self, command: str, result: str, success: bool):
        """Ajouter une commande à l'historique"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "result": result[:500],  # Limiter la taille
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
    
    def parse_natural_language(self, input_text: str) -> Optional[str]:
        """Convertir langage naturel en commande shell"""
        # Patterns courants
        patterns = {
            r"liste.*(fichier|file)": "ls -la",
            r"montre.*(processus|process)": "ps aux",
            r"espace.*(disque|disk)": "df -h",
            r"(efface|supprime|delete).*(fichier|file)": "rm",
            r"copie.*(fichier|file)": "cp",
            r"cherche|trouve|search": "find . -name",
            r"réseau|network|ip": "ip addr show",
            r"mémoire|memory|ram": "free -h",
        }
        
        import re
        for pattern, command in patterns.items():
            if re.search(pattern, input_text.lower()):
                return command
        
        return None
    
    def get_ai_suggestion(self, user_input: str) -> List[str]:
        """Obtenir des suggestions IA basées sur le contexte"""
        if not self.config.get("api_key"):
            return []
        
        try:
            client = anthropic.Anthropic(api_key=self.config["api_key"])
            
            context_info = f"""
Contexte actuel:
- Répertoire: {self.context['current_dir']}
- Dernières commandes: {', '.join(self.context['last_commands'][-5:])}
- Input utilisateur: {user_input}

Suggère 3 commandes shell pertinentes. Réponds uniquement avec les commandes, une par ligne.
"""
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": context_info}]
            )
            
            suggestions = message.content[0].text.strip().split('\n')
            return [s.strip() for s in suggestions if s.strip()][:3]
            
        except Exception as e:
            print(f"Erreur IA: {e}")
            return []
    
    def execute_command(self, command: str) -> tuple:
        """Exécuter une commande shell"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return output, success
        except subprocess.TimeoutExpired:
            return "Commande timeout après 30s", False
        except Exception as e:
            return f"Erreur: {str(e)}", False
    
    def install_plugin(self, plugin_name: str):
        """Installer un plugin (ansible, terraform, etc.)"""
        plugins = {
            "ansible": "pip install ansible",
            "terraform": "wget https://releases.hashicorp.com/terraform/latest/terraform_linux_amd64.zip && unzip -d ~/.local/bin/",
            "docker": "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh",
            "kubectl": "curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        }
        
        if plugin_name in plugins:
            print(f"Installation de {plugin_name}...")
            output, success = self.execute_command(plugins[plugin_name])
            if success:
                self.config["plugins"][plugin_name] = True
                self.save_config()
                print(f"✓ {plugin_name} installé avec succès")
            else:
                print(f"✗ Erreur lors de l'installation: {output}")
        else:
            print(f"Plugin {plugin_name} non disponible")
            print(f"Plugins disponibles: {', '.join(plugins.keys())}")
    
    def add_remote_host(self, name: str, host: str, user: str, key_path: Optional[str] = None):
        """Ajouter un hôte distant pour exécution remote"""
        self.config["remote_hosts"][name] = {
            "host": host,
            "user": user,
            "key_path": key_path or f"~/.ssh/id_rsa"
        }
        self.save_config()
        print(f"✓ Hôte {name} ajouté")
    
    def execute_remote(self, host_name: str, command: str):
        """Exécuter une commande sur un hôte distant"""
        if host_name not in self.config["remote_hosts"]:
            print(f"Hôte {host_name} non trouvé")
            return
        
        host_info = self.config["remote_hosts"][host_name]
        ssh_cmd = f"ssh -i {host_info['key_path']} {host_info['user']}@{host_info['host']} '{command}'"
        
        print(f"Exécution sur {host_name}...")
        output, success = self.execute_command(ssh_cmd)
        print(output)
        return output, success
    
    def ansible_mode(self, playbook: str, inventory: str, remote_hosts: List[str]):
        """Mode Ansible pour orchestration à distance"""
        if "ansible" not in self.config["plugins"]:
            print("Ansible n'est pas installé. Utilisez: fuzzy plugin install ansible")
            return
        
        # Générer un inventaire dynamique
        inventory_content = "[targets]\n"
        for host_name in remote_hosts:
            if host_name in self.config["remote_hosts"]:
                host = self.config["remote_hosts"][host_name]
                inventory_content += f"{host['host']} ansible_user={host['user']} ansible_ssh_private_key_file={host['key_path']}\n"
        
        inv_file = self.config_dir / "inventory_temp.ini"
        with open(inv_file, 'w') as f:
            f.write(inventory_content)
        
        ansible_cmd = f"ansible-playbook -i {inv_file} {playbook}"
        print(f"Exécution Ansible: {ansible_cmd}")
        output, success = self.execute_command(ansible_cmd)
        print(output)
        
        inv_file.unlink()  # Nettoyer
        return output, success
    
    def chat_mode(self):
        """Mode chat interactif avec IA"""
        if not self.config.get("api_key"):
            print("Clé API non configurée. Utilisez: fuzzy config set-api-key YOUR_KEY")
            return
        
        print("Mode Chat activé (tapez 'exit' pour quitter)")
        print("=" * 50)
        
        client = anthropic.Anthropic(api_key=self.config["api_key"])
        conversation = []
        
        while True:
            user_input = input("\n🤖 Vous: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            
            conversation.append({"role": "user", "content": user_input})
            
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=conversation
                )
                
                assistant_msg = response.content[0].text
                conversation.append({"role": "assistant", "content": assistant_msg})
                
                print(f"\n💡 Claude: {assistant_msg}")
                
            except Exception as e:
                print(f"Erreur: {e}")
    
    def run(self):
        """Boucle principale du terminal"""
        print("=" * 60)
        print("FuzzyTerminal v1.0 - Terminal Intelligent")
        print("Tapez 'help' pour l'aide, 'exit' pour quitter")
        print("=" * 60)
        
        while True:
            try:
                # Prompt avec contexte
                prompt = f"\n[{os.path.basename(self.context['current_dir'])}] fuzzy> "
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Commandes spéciales
                if user_input.lower() == 'exit':
                    print("Au revoir!")
                    break
                    
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                
                elif user_input.startswith('fuzzy '):
                    self.handle_fuzzy_command(user_input[6:])
                    continue
                
                # Obtenir des suggestions IA si activé
                if self.config["preferences"]["auto_suggest"]:
                    suggestions = self.get_ai_suggestion(user_input)
                    if suggestions:
                        print("\n💡 Suggestions:")
                        for i, sugg in enumerate(suggestions, 1):
                            print(f"  {i}. {sugg}")
                        choice = input("\nUtiliser une suggestion? (1-3 ou Entrée pour continuer): ").strip()
                        if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                            user_input = suggestions[int(choice) - 1]
                            print(f"Exécution: {user_input}")
                
                # Essayer de parser le langage naturel
                parsed = self.parse_natural_language(user_input)
                if parsed and parsed != user_input:
                    print(f"Interprété comme: {parsed}")
                    confirm = input("Exécuter? (o/n): ").lower()
                    if confirm == 'o':
                        user_input = parsed
                
                # Exécuter la commande
                output, success = self.execute_command(user_input)
                print(output)
                
                # Sauvegarder dans l'historique
                self.add_to_history(user_input, output, success)
                
                # Mettre à jour le contexte
                if user_input.startswith('cd '):
                    new_dir = user_input[3:].strip()
                    if os.path.isdir(new_dir):
                        os.chdir(new_dir)
                        self.context['current_dir'] = os.getcwd()
                
            except KeyboardInterrupt:
                print("\n\nUtilisez 'exit' pour quitter")
            except Exception as e:
                print(f"Erreur: {e}")
        
        # Sauvegarder avant de quitter
        self.save_history()
        self.save_config()
    
    def show_help(self):
        """Afficher l'aide"""
        help_text = """
FuzzyTerminal - Commandes disponibles:

Commandes Shell Standard:
  - Toutes les commandes shell habituelles (ls, cd, grep, etc.)
  - Langage naturel accepté (ex: "liste les fichiers")

Commandes FuzzyTerminal:
  fuzzy config set-api-key <key>     - Configurer la clé API Claude
  fuzzy plugin install <name>        - Installer un plugin (ansible, terraform, docker)
  fuzzy plugin list                  - Lister les plugins installés
  fuzzy remote add <name> <host> <user> - Ajouter un hôte distant
  fuzzy remote exec <name> <cmd>     - Exécuter sur un hôte distant
  fuzzy remote list                  - Lister les hôtes distants
  fuzzy ansible <playbook> <hosts>   - Exécuter un playbook Ansible
  fuzzy chat                         - Mode chat interactif avec IA
  fuzzy history                      - Afficher l'historique
  fuzzy context                      - Afficher le contexte actuel
  
Options:
  --no-suggest                       - Désactiver les suggestions IA
  --help                             - Afficher cette aide
"""
        print(help_text)
    
    def handle_fuzzy_command(self, command: str):
        """Gérer les commandes fuzzy spéciales"""
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0]
        args = parts[1:]
        
        if cmd == "config" and len(args) >= 2 and args[0] == "set-api-key":
            self.config["api_key"] = args[1]
            self.save_config()
            print("✓ Clé API configurée")
        
        elif cmd == "plugin":
            if args[0] == "install" and len(args) > 1:
                self.install_plugin(args[1])
            elif args[0] == "list":
                print("Plugins installés:", ", ".join(self.config["plugins"].keys()) or "Aucun")
        
        elif cmd == "remote":
            if args[0] == "add" and len(args) >= 4:
                self.add_remote_host(args[1], args[2], args[3], args[4] if len(args) > 4 else None)
            elif args[0] == "exec" and len(args) >= 3:
                self.execute_remote(args[1], " ".join(args[2:]))
            elif args[0] == "list":
                print("Hôtes distants:", ", ".join(self.config["remote_hosts"].keys()) or "Aucun")
        
        elif cmd == "ansible" and len(args) >= 2:
            playbook = args[0]
            hosts = args[1].split(',')
            self.ansible_mode(playbook, "inventory", hosts)
        
        elif cmd == "chat":
            self.chat_mode()
        
        elif cmd == "history":
            for entry in self.history[-10:]:
                print(f"[{entry['timestamp']}] {entry['command']}")
        
        elif cmd == "context":
            print(json.dumps(self.context, indent=2))


if __name__ == "__main__":
    terminal = FuzzyTerminal()
    terminal.run()
