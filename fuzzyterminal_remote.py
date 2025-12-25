#!/usr/bin/env python3
"""
FuzzyTerminal - Module d'Exécution Remote
Gestion avancée des hôtes distants et intégration Ansible/Terraform
"""

import json
import yaml
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import concurrent.futures
import paramiko
from datetime import datetime

class RemoteExecutor:
    """Gestionnaire d'exécution remote intelligent"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.hosts_file = config_dir / "remote_hosts.json"
        self.playbooks_dir = config_dir / "playbooks"
        self.scripts_dir = config_dir / "scripts"
        
        self.playbooks_dir.mkdir(exist_ok=True)
        self.scripts_dir.mkdir(exist_ok=True)
        
        self.hosts = self.load_hosts()
        
    def load_hosts(self) -> Dict:
        """Charger les hôtes configurés"""
        if self.hosts_file.exists():
            with open(self.hosts_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_hosts(self):
        """Sauvegarder les hôtes"""
        with open(self.hosts_file, 'w') as f:
            json.dump(self.hosts, f, indent=2)
    
    def add_host(self, name: str, host: str, user: str, 
                 port: int = 22, key_path: Optional[str] = None,
                 password: Optional[str] = None, tags: List[str] = None):
        """Ajouter un hôte avec métadonnées"""
        self.hosts[name] = {
            "host": host,
            "user": user,
            "port": port,
            "key_path": key_path or "~/.ssh/id_rsa",
            "password": password,
            "tags": tags or [],
            "added_at": datetime.now().isoformat(),
            "last_used": None,
            "success_count": 0,
            "fail_count": 0
        }
        self.save_hosts()
        print(f"✓ Hôte {name} ajouté")
    
    def remove_host(self, name: str):
        """Supprimer un hôte"""
        if name in self.hosts:
            del self.hosts[name]
            self.save_hosts()
            print(f"✓ Hôte {name} supprimé")
        else:
            print(f"✗ Hôte {name} non trouvé")
    
    def list_hosts(self, tag: Optional[str] = None):
        """Lister les hôtes (optionnellement filtrés par tag)"""
        filtered = self.hosts
        if tag:
            filtered = {k: v for k, v in self.hosts.items() if tag in v.get('tags', [])}
        
        if not filtered:
            print("Aucun hôte configuré")
            return
        
        print("\n" + "=" * 80)
        print(f"{'Nom':<15} {'Hôte':<25} {'User':<12} {'Tags':<20} {'Statut'}")
        print("=" * 80)
        
        for name, info in filtered.items():
            success = info.get('success_count', 0)
            fail = info.get('fail_count', 0)
            status = f"{success}✓ {fail}✗"
            tags_str = ", ".join(info.get('tags', []))
            print(f"{name:<15} {info['host']:<25} {info['user']:<12} {tags_str:<20} {status}")
    
    def execute_ssh(self, host_name: str, command: str, 
                    timeout: int = 30) -> tuple:
        """Exécuter une commande SSH sur un hôte"""
        if host_name not in self.hosts:
            return f"Hôte {host_name} non trouvé", False
        
        host_info = self.hosts[host_name]
        
        try:
            # Utiliser paramiko pour une connexion SSH native
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connexion
            connect_params = {
                'hostname': host_info['host'],
                'username': host_info['user'],
                'port': host_info.get('port', 22),
                'timeout': timeout
            }
            
            if host_info.get('password'):
                connect_params['password'] = host_info['password']
            else:
                key_path = Path(host_info['key_path']).expanduser()
                if key_path.exists():
                    connect_params['key_filename'] = str(key_path)
            
            client.connect(**connect_params)
            
            # Exécution
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            
            output = stdout.read().decode() + stderr.read().decode()
            exit_status = stdout.channel.recv_exit_status()
            
            client.close()
            
            # Mettre à jour les stats
            self.hosts[host_name]['last_used'] = datetime.now().isoformat()
            if exit_status == 0:
                self.hosts[host_name]['success_count'] = self.hosts[host_name].get('success_count', 0) + 1
            else:
                self.hosts[host_name]['fail_count'] = self.hosts[host_name].get('fail_count', 0) + 1
            self.save_hosts()
            
            return output, exit_status == 0
            
        except Exception as e:
            self.hosts[host_name]['fail_count'] = self.hosts[host_name].get('fail_count', 0) + 1
            self.save_hosts()
            return f"Erreur SSH: {str(e)}", False
    
    def execute_parallel(self, host_names: List[str], command: str, 
                        max_workers: int = 10) -> Dict:
        """Exécuter une commande sur plusieurs hôtes en parallèle"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_host = {
                executor.submit(self.execute_ssh, host, command): host 
                for host in host_names
            }
            
            for future in concurrent.futures.as_completed(future_to_host):
                host = future_to_host[future]
                try:
                    output, success = future.result()
                    results[host] = {
                        'output': output,
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    results[host] = {
                        'output': str(e),
                        'success': False,
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    def create_ansible_inventory(self, host_names: List[str], 
                                 group_name: str = "targets") -> Path:
        """Créer un fichier d'inventaire Ansible dynamique"""
        inventory = {
            group_name: {
                'hosts': {}
            }
        }
        
        for name in host_names:
            if name not in self.hosts:
                continue
            
            host_info = self.hosts[name]
            inventory[group_name]['hosts'][name] = {
                'ansible_host': host_info['host'],
                'ansible_user': host_info['user'],
                'ansible_port': host_info.get('port', 22),
                'ansible_ssh_private_key_file': host_info['key_path']
            }
            
            if host_info.get('password'):
                inventory[group_name]['hosts'][name]['ansible_password'] = host_info['password']
        
        # Sauvegarder en YAML
        inv_file = self.config_dir / f"inventory_{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml"
        with open(inv_file, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)
        
        return inv_file
    
    def run_ansible_playbook(self, playbook_path: str, host_names: List[str],
                            extra_vars: Optional[Dict] = None,
                            tags: Optional[List[str]] = None,
                            check_mode: bool = False) -> tuple:
        """Exécuter un playbook Ansible"""
        # Créer l'inventaire
        inv_file = self.create_ansible_inventory(host_names)
        
        # Construire la commande
        cmd = f"ansible-playbook -i {inv_file} {playbook_path}"
        
        if extra_vars:
            vars_str = " ".join([f"{k}={v}" for k, v in extra_vars.items()])
            cmd += f" -e '{vars_str}'"
        
        if tags:
            cmd += f" --tags {','.join(tags)}"
        
        if check_mode:
            cmd += " --check"
        
        # Exécuter
        print(f"Exécution: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            # Nettoyer l'inventaire temporaire
            # inv_file.unlink()
            
            return output, success
            
        except Exception as e:
            return f"Erreur: {str(e)}", False
    
    def create_playbook_template(self, name: str, tasks: List[Dict]) -> Path:
        """Créer un playbook Ansible à partir d'un template"""
        playbook = [{
            'name': f'Playbook {name}',
            'hosts': 'all',
            'become': True,
            'tasks': tasks
        }]
        
        pb_file = self.playbooks_dir / f"{name}.yml"
        with open(pb_file, 'w') as f:
            yaml.dump(playbook, f, default_flow_style=False)
        
        print(f"✓ Playbook créé: {pb_file}")
        return pb_file
    
    def run_terraform_remote(self, host_name: str, tf_dir: str,
                           action: str = "apply") -> tuple:
        """Exécuter Terraform sur un hôte distant"""
        if action not in ['plan', 'apply', 'destroy', 'init']:
            return "Action invalide. Utilisez: plan, apply, destroy, init", False
        
        # Préparer les commandes
        commands = [
            f"cd {tf_dir}",
            f"terraform {action} -auto-approve" if action != 'plan' else f"terraform {action}"
        ]
        
        full_command = " && ".join(commands)
        
        print(f"Exécution Terraform {action} sur {host_name}...")
        return self.execute_ssh(host_name, full_command, timeout=300)
    
    def deploy_script(self, host_names: List[str], script_path: str,
                     remote_path: str = "/tmp/script.sh") -> Dict:
        """Déployer et exécuter un script sur plusieurs hôtes"""
        if not Path(script_path).exists():
            return {"error": "Script non trouvé"}
        
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        results = {}
        
        for host in host_names:
            print(f"Déploiement sur {host}...")
            
            # Copier le script
            upload_cmd = f"echo '{script_content}' > {remote_path} && chmod +x {remote_path}"
            output1, success1 = self.execute_ssh(host, upload_cmd)
            
            if not success1:
                results[host] = {"error": "Échec de l'upload", "output": output1}
                continue
            
            # Exécuter le script
            exec_cmd = f"{remote_path}"
            output2, success2 = self.execute_ssh(host, exec_cmd)
            
            results[host] = {
                "success": success2,
                "output": output2
            }
        
        return results
    
    def health_check(self, host_names: Optional[List[str]] = None) -> Dict:
        """Vérifier la santé des hôtes"""
        if host_names is None:
            host_names = list(self.hosts.keys())
        
        check_command = "uptime && df -h / && free -h"
        
        print("Vérification de la santé des hôtes...")
        results = self.execute_parallel(host_names, check_command)
        
        print("\n" + "=" * 80)
        print("Résultats Health Check")
        print("=" * 80)
        
        for host, result in results.items():
            status = "✓ OK" if result['success'] else "✗ ÉCHEC"
            print(f"\n{host}: {status}")
            if result['success']:
                print(result['output'][:200])
        
        return results


class AutomationBuilder:
    """Constructeur d'automatisations intelligentes"""
    
    def __init__(self, remote_executor: RemoteExecutor):
        self.executor = remote_executor
    
    def setup_web_server(self, host_names: List[str], 
                        server_type: str = "nginx") -> Path:
        """Créer un playbook pour setup un serveur web"""
        tasks = []
        
        if server_type == "nginx":
            tasks = [
                {
                    'name': 'Installer Nginx',
                    'apt': {
                        'name': 'nginx',
                        'state': 'present',
                        'update_cache': True
                    }
                },
                {
                    'name': 'Démarrer Nginx',
                    'service': {
                        'name': 'nginx',
                        'state': 'started',
                        'enabled': True
                    }
                },
                {
                    'name': 'Ouvrir le firewall',
                    'ufw': {
                        'rule': 'allow',
                        'port': '80',
                        'proto': 'tcp'
                    }
                }
            ]
        
        playbook = self.executor.create_playbook_template(
            f"setup_{server_type}", tasks
        )
        
        # Exécuter
        output, success = self.executor.run_ansible_playbook(
            str(playbook), host_names
        )
        
        return playbook
    
    def deploy_docker_app(self, host_names: List[str], 
                         image: str, port: int = 80) -> Dict:
        """Déployer une application Docker"""
        tasks = [
            {
                'name': 'Installer Docker',
                'shell': 'curl -fsSL https://get.docker.com | sh'
            },
            {
                'name': 'Pull image Docker',
                'docker_image': {
                    'name': image,
                    'source': 'pull'
                }
            },
            {
                'name': 'Lancer conteneur',
                'docker_container': {
                    'name': 'app',
                    'image': image,
                    'state': 'started',
                    'ports': [f'{port}:80']
                }
            }
        ]
        
        playbook = self.executor.create_playbook_template(
            "deploy_docker_app", tasks
        )
        
        output, success = self.executor.run_ansible_playbook(
            str(playbook), host_names
        )
        
        return {"playbook": str(playbook), "output": output, "success": success}


# Exemple d'utilisation
if __name__ == "__main__":
    config_dir = Path.home() / ".fuzzyterminal"
    executor = RemoteExecutor(config_dir)
    
    # Exemples de commandes
    print("FuzzyTerminal Remote Executor")
    print("=" * 60)
    
    # Ajouter des hôtes
    # executor.add_host("server1", "192.168.1.10", "admin", tags=["web", "prod"])
    # executor.add_host("server2", "192.168.1.11", "admin", tags=["db", "prod"])
    
    # Lister les hôtes
    executor.list_hosts()
    
    # Health check
    # executor.health_check()
