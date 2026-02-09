#!/usr/bin/env python3
"""
FuzzyTerminal - Remote Execution Module (Async)
Advanced management of remote hosts and Ansible/Terraform integration using AsyncIO and AsyncSSH
"""

import json
import asyncio
# Heavy imports will be loaded lazily
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

class RemoteExecutor:
    """Intelligent Remote Execution Manager (Async)"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.hosts_file = config_dir / "remote_hosts.json"
        self.playbooks_dir = config_dir / "playbooks"
        self.scripts_dir = config_dir / "scripts"
        
        self.playbooks_dir.mkdir(exist_ok=True)
        self.scripts_dir.mkdir(exist_ok=True)
        
        self.hosts = self.load_hosts()
        
    def load_hosts(self) -> Dict:
        """Load configured hosts"""
        if self.hosts_file.exists():
            with open(self.hosts_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_hosts(self):
        """Save hosts configuration"""
        with open(self.hosts_file, 'w') as f:
            json.dump(self.hosts, f, indent=2)
    
    def add_host(self, name: str, host: str, user: str, 
                 port: int = 22, key_path: Optional[str] = None,
                 password: Optional[str] = None, tags: List[str] = None):
        """Add a host with metadata"""
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
        print(f"✓ Host {name} added")
    
    def remove_host(self, name: str):
        """Remove a host"""
        if name in self.hosts:
            del self.hosts[name]
            self.save_hosts()
            print(f"✓ Host {name} removed")
        else:
            print(f"✗ Host {name} not found")
    
    def list_hosts(self, tag: Optional[str] = None) -> Dict:
        """List hosts (optionally filtered by tag)"""
        filtered = self.hosts
        if tag:
            filtered = {k: v for k, v in self.hosts.items() if tag in v.get('tags', [])}
        return filtered
    
    async def execute_ssh(self, host_name: str, command: str, 
                          timeout: int = 30) -> Tuple[str, bool]:
        """Execute an SSH command on a host asynchronously"""
        if host_name not in self.hosts:
            return f"Host {host_name} not found", False
        
        host_info = self.hosts[host_name]
        
        try:
            import asyncssh
            # Connection parameters
            connect_kwargs = {
                'host': host_info['host'],
                'username': host_info['user'],
                'port': host_info.get('port', 22),
                'known_hosts': None, # Warning: Insecure for prod, but standard for easy tools
                'client_keys': [host_info['key_path']] if not host_info.get('password') else None,
                'password': host_info.get('password')
            }
            
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await conn.run(command, timeout=timeout)
                
                output = result.stdout + result.stderr
                success = result.exit_status == 0
                
                # Update stats
                self.hosts[host_name]['last_used'] = datetime.now().isoformat()
                if success:
                    self.hosts[host_name]['success_count'] = self.hosts[host_name].get('success_count', 0) + 1
                else:
                    self.hosts[host_name]['fail_count'] = self.hosts[host_name].get('fail_count', 0) + 1
                self.save_hosts()
                
                return output, success
            
        except (OSError, asyncssh.Error, asyncio.TimeoutError) as e:
            self.hosts[host_name]['fail_count'] = self.hosts[host_name].get('fail_count', 0) + 1
            self.save_hosts()
            return f"SSH Error: {str(e)}", False
    
    async def execute_parallel(self, host_names: List[str], command: str) -> Dict:
        """Execute a command on multiple hosts in parallel"""
        tasks = []
        for host in host_names:
            tasks.append(self.execute_ssh(host, command))
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for host, result in zip(host_names, results_list):
            if isinstance(result, Exception):
                results[host] = {
                    'output': str(result),
                    'success': False,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                output, success = result
                results[host] = {
                    'output': output,
                    'success': success,
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def create_ansible_inventory(self, host_names: List[str], 
                                 group_name: str = "targets") -> Path:
        """Create a dynamic Ansible inventory file (Synchronous as it's local FS)"""
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
        
        # Save as YAML
        try:
            import yaml
        except ImportError:
            raise ImportError("pyyaml package is not installed")
            
        inv_file = self.config_dir / f"inventory_{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml"
        with open(inv_file, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)
        
        return inv_file
    
    async def run_ansible_playbook(self, playbook_path: str, host_names: List[str],
                            extra_vars: Optional[Dict] = None,
                            tags: Optional[List[str]] = None,
                            check_mode: bool = False) -> Tuple[str, bool]:
        """Execute an Ansible playbook (Async wrapper around subprocess)"""
        # Create inventory
        inv_file = self.create_ansible_inventory(host_names)
        
        # Build command
        cmd = f"ansible-playbook -i {inv_file} {playbook_path}"
        
        if extra_vars:
            vars_str = " ".join([f"{k}={v}" for k, v in extra_vars.items()])
            cmd += f" -e '{vars_str}'"
        
        if tags:
            cmd += f" --tags {','.join(tags)}"
        
        if check_mode:
            cmd += " --check"
        
        # Execute
        print(f"Executing: {cmd}")
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            success = process.returncode == 0
            
            return output, success
            
        except Exception as e:
            return f"Error: {str(e)}", False
