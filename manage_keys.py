#!/usr/bin/env python3
import os
import subprocess
import sys
from typing import List, Dict, Optional
import re
import json
from datetime import datetime
import shutil

# Suppress Tk deprecation warning on macOS
os.environ['TK_SILENCE_DEPRECATION'] = '1'

try:
    import tkinter as tk
    from tkinter import messagebox
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

class SSHKeyManager:
    def __init__(self):
        self.keys_file = "authorized_keys"
        self.aliases_file = "key_aliases.json"
        self.backup_dir = ".key_backups"
        self.aliases: Dict[str, dict] = {}
        self.load_keys()
        self.load_aliases()
        
        # Check repository visibility
        if self.check_repo_visibility():
            print("\n⚠️  WARNING: This appears to be a public repository!")
            print("It is strongly recommended to keep SSH keys in a private repository.")
            print("Please consider making this repository private or using a different repository.")
            confirm = input("\nDo you wish to continue anyway? (yes/N): ").lower()
            if confirm != 'yes':
                print("Exiting for security...")
                sys.exit(1)

    def load_aliases(self) -> None:
        """Load aliases and metadata from JSON file."""
        if os.path.exists(self.aliases_file):
            try:
                with open(self.aliases_file, 'r') as f:
                    self.aliases = json.load(f)
            except json.JSONDecodeError:
                print("Warning: Could not load aliases file")

    def save_aliases(self) -> None:
        """Save aliases and metadata to JSON file."""
        with open(self.aliases_file, 'w') as f:
            json.dump(self.aliases, f, indent=2)

    def create_backup(self) -> None:
        """Create a backup of the keys file."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"authorized_keys_{timestamp}")
        shutil.copy2(self.keys_file, backup_file)
        print(f"Backup created: {backup_file}")

    def load_keys(self) -> None:
        """Load existing keys."""
        if not os.path.exists(self.keys_file):
            self.keys = []
            return
        
        with open(self.keys_file, 'r') as f:
            self.keys = [line.strip() for line in f if line.strip()]

    def save_keys(self) -> None:
        """Save keys to the authorized_keys file."""
        self.create_backup()
        with open(self.keys_file, 'w') as f:
            f.write('\n'.join(self.keys) + '\n')
        self.save_aliases()

    def copy_to_clipboard(self, key: str) -> None:
        """Copy key to clipboard using tkinter."""
        if not CLIPBOARD_AVAILABLE:
            print("Clipboard functionality not available (tkinter not installed)")
            print("Key:", key)
            return

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(key)
        root.update()
        print("Key copied to clipboard!")
        root.destroy()

    def list_keys(self, search: str = "") -> None:
        """List all keys with their aliases and metadata."""
        if not self.keys:
            print("No keys available")
            return

        print("\nAvailable SSH Keys:")
        print("-" * 60)
        
        for i, key in enumerate(self.keys, 1):
            name = self.get_key_name(key)
            if search and search.lower() not in name.lower() and search.lower() not in self.aliases.get(name, {}).get('alias', '').lower():
                continue
                
            key_type = key.split()[0]
            alias_info = self.aliases.get(name, {})
            alias = alias_info.get('alias', '')
            expiry = alias_info.get('expiry', '')
            
            print(f"{i}. {name}")
            if alias:
                print(f"   Alias: {alias}")
            print(f"   Type: {key_type}")
            if expiry:
                print(f"   Expires: {expiry}")
            print(f"   Added: {alias_info.get('added', 'Unknown')}")
            print("-" * 60)

    def set_expiry(self, key_idx: int, date_str: str) -> None:
        """Set expiry date for a key."""
        if not (0 <= key_idx < len(self.keys)):
            print("Invalid key index")
            return

        name = self.get_key_name(self.keys[key_idx])
        if name not in self.aliases:
            self.aliases[name] = {}
        
        self.aliases[name]['expiry'] = date_str
        self.save_aliases()
        print(f"Set expiry date {date_str} for key {name}")

    def get_system_keys(self) -> List[str]:
        """Get all public SSH keys from the current system."""
        home = os.path.expanduser("~")
        ssh_dir = os.path.join(home, ".ssh")
        keys = []
        
        if not os.path.exists(ssh_dir):
            return keys

        for file in os.listdir(ssh_dir):
            if file.endswith(".pub"):
                try:
                    with open(os.path.join(ssh_dir, file), 'r') as f:
                        key = f.read().strip()
                        if key:
                            keys.append(key)
                except:
                    continue
        return keys

    def get_key_name(self, key: str) -> str:
        """Extract name/comment from SSH key."""
        parts = key.strip().split()
        return parts[-1] if len(parts) > 2 else "Unknown"

    def get_key_parts(self, key: str) -> tuple:
        """Extract the key type and key data from an SSH key, ignoring comments."""
        parts = key.strip().split()
        if len(parts) >= 2:
            return (parts[0], parts[1])  # type and key data
        return (None, None)

    def find_existing_key(self, new_key: str) -> Optional[int]:
        """Find index of existing key with same type and data, ignoring comments."""
        new_type, new_data = self.get_key_parts(new_key)
        if not new_type or not new_data:
            return None
        
        for idx, existing_key in enumerate(self.keys):
            existing_type, existing_data = self.get_key_parts(existing_key)
            if existing_type == new_type and existing_data == new_data:
                return idx
        return None

    def sync_with_git(self, message: str) -> None:
        """Sync changes with git repository."""
        try:
            subprocess.run(["git", "add", self.keys_file], check=True)
            subprocess.run(["git", "commit", "-m", message], check=True)
            subprocess.run(["git", "pull", "--rebase"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Successfully synced with git repository")
        except subprocess.CalledProcessError as e:
            print(f"Error syncing with git: {e}")

    def capture_keys(self) -> None:
        """Capture public keys from the current system."""
        system_keys = self.get_system_keys()
        if not system_keys:
            print("No SSH keys found on this system")
            return

        print("\nFound the following SSH keys:")
        for i, key in enumerate(system_keys, 1):
            print(f"{i}. {self.get_key_name(key)}")

        selection = input("\nEnter numbers to add (comma-separated) or 'all': ").strip()
        if not selection:
            return

        added_keys = []
        if selection.lower() == 'all':
            indices = range(len(system_keys))
        else:
            try:
                indices = [int(i.strip()) - 1 for i in selection.split(',')]
            except ValueError:
                print("Invalid selection")
                return

        for idx in indices:
            if 0 <= idx < len(system_keys):
                key = system_keys[idx]
                existing_idx = self.find_existing_key(key)
                
                if existing_idx is not None:
                    existing_name = self.get_key_name(self.keys[existing_idx])
                    new_name = self.get_key_name(key)
                    print(f"\nKey {new_name} already exists as {existing_name}")
                    overwrite = input("Would you like to overwrite it? (y/N): ").lower()
                    
                    if overwrite != 'y':
                        print("Skipping key...")
                        continue
                    
                    # Remove the old key and its alias
                    old_name = self.get_key_name(self.keys[existing_idx])
                    self.aliases.pop(old_name, None)
                    del self.keys[existing_idx]
                
                name = self.get_key_name(key)
                alias = input(f"Enter alias for {name} (press Enter to skip): ").strip()
                expiry = input("Enter expiry date (YYYY-MM-DD) or press Enter to skip: ").strip()
                
                metadata = {
                    'added': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                if alias:
                    metadata['alias'] = alias
                if expiry:
                    metadata['expiry'] = expiry
                
                self.aliases[name] = metadata
                self.keys.append(key)
                added_keys.append(name)

        if added_keys:
            self.save_keys()
            if input("Would you like to sync changes? (y/N): ").lower() == 'y':
                self.sync_with_git(f"Added keys: {', '.join(added_keys)}")

    def deploy_keys(self) -> None:
        """Deploy selected keys to the current system."""
        if not self.keys:
            print("No keys available to deploy")
            return

        print("\nAvailable keys:")
        for i, key in enumerate(self.keys, 1):
            name = self.get_key_name(key)
            alias = self.aliases.get(name, {}).get('alias', '')
            print(f"{i}. {name} {f'({alias})' if alias else ''}")

        selection = input("\nEnter numbers to deploy (comma-separated) or 'all': ").strip()
        if not selection:
            return

        home = os.path.expanduser("~")
        ssh_dir = os.path.join(home, ".ssh")
        auth_keys_file = os.path.join(ssh_dir, "authorized_keys")

        try:
            os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        except OSError as e:
            print(f"Error creating .ssh directory: {e}")
            return

        if selection.lower() == 'all':
            selected_keys = self.keys
        else:
            try:
                indices = [int(i.strip()) - 1 for i in selection.split(',')]
                selected_keys = [self.keys[i] for i in indices if 0 <= i < len(self.keys)]
            except ValueError:
                print("Invalid selection")
                return

        existing_keys = set()
        if os.path.exists(auth_keys_file):
            try:
                with open(auth_keys_file, 'r') as f:
                    existing_keys = set(line.strip() for line in f if line.strip())
            except OSError as e:
                print(f"Error reading existing authorized_keys file: {e}")
                return

        keys_to_add = [key for key in selected_keys if key not in existing_keys]
        if not keys_to_add:
            print("All selected keys are already deployed!")
            return

        try:
            with open(auth_keys_file, 'a') as f:
                for key in keys_to_add:
                    f.write(key + '\n')
            
            # Set proper permissions
            try:
                os.chmod(auth_keys_file, 0o600)
            except OSError as e:
                print(f"Warning: Could not set permissions on {auth_keys_file}: {e}")

            # Verify deployment
            try:
                with open(auth_keys_file, 'r') as f:
                    deployed_keys = set(line.strip() for line in f if line.strip())
                
                successfully_deployed = []
                failed_deployments = []
                
                for key in keys_to_add:
                    name = self.get_key_name(key)
                    if key in deployed_keys:
                        successfully_deployed.append(name)
                    else:
                        failed_deployments.append(name)
                
                if successfully_deployed:
                    print("\nSuccessfully deployed keys:")
                    for name in successfully_deployed:
                        print(f"✓ {name}")
                
                if failed_deployments:
                    print("\nFailed to deploy keys:")
                    for name in failed_deployments:
                        print(f"✗ {name}")
                
                print(f"\nDeployment location: {auth_keys_file}")
                if successfully_deployed:
                    print(f"Permissions: {oct(os.stat(auth_keys_file).st_mode)[-3:]}")
                
            except OSError as e:
                print(f"Error verifying deployment: {e}")
                
        except OSError as e:
            print(f"Error writing to authorized_keys file: {e}")
            return

    def set_alias(self) -> None:
        """Set alias for existing keys."""
        if not self.keys:
            print("No keys available")
            return

        print("\nAvailable keys:")
        for i, key in enumerate(self.keys, 1):
            name = self.get_key_name(key)
            alias = self.aliases.get(name, '')
            print(f"{i}. {name} {f'({alias})' if alias else ''}")

        selection = input("\nEnter key number to set alias: ").strip()
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(self.keys):
                name = self.get_key_name(self.keys[idx])
                alias = input(f"Enter new alias for {name}: ").strip()
                if alias:
                    self.aliases[name] = alias
                    if input("Would you like to sync changes? (y/N): ").lower() == 'y':
                        self.sync_with_git(f"Updated alias for {name}: {alias}")
        except ValueError:
            print("Invalid selection")

    def delete_keys(self) -> None:
        """Delete selected keys."""
        if not self.keys:
            print("No keys available to delete")
            return

        print("\nAvailable keys:")
        for i, key in enumerate(self.keys, 1):
            name = self.get_key_name(key)
            alias = self.aliases.get(name, {}).get('alias', '')
            print(f"{i}. {name} {f'({alias})' if alias else ''}")

        selection = input("\nEnter numbers to delete (comma-separated) or 'all': ").strip()
        if not selection:
            return

        # Get list of keys to delete first
        to_delete = []
        if selection.lower() == 'all':
            print("\nYou are about to delete ALL keys:")
            for key in self.keys:
                name = self.get_key_name(key)
                alias = self.aliases.get(name, {}).get('alias', '')
                print(f"- {name} {f'({alias})' if alias else ''}")
            
            confirm = input("\nAre you sure you want to delete all keys? This cannot be undone. (yes/N): ").lower()
            if confirm == 'yes':
                to_delete = list(range(len(self.keys)))
            else:
                print("Operation cancelled.")
                return
        else:
            try:
                indices = sorted([int(i.strip()) - 1 for i in selection.split(',')], reverse=True)
                print("\nYou are about to delete these keys:")
                for idx in indices:
                    if 0 <= idx < len(self.keys):
                        name = self.get_key_name(self.keys[idx])
                        alias = self.aliases.get(name, {}).get('alias', '')
                        print(f"- {name} {f'({alias})' if alias else ''}")
                
                confirm = input("\nAre you sure you want to delete these keys? This cannot be undone. (yes/N): ").lower()
                if confirm == 'yes':
                    to_delete = indices
                else:
                    print("Operation cancelled.")
                    return
            except ValueError:
                print("Invalid selection")
                return

        # Now perform the deletion
        deleted_keys = []
        for idx in to_delete:
            if 0 <= idx < len(self.keys):
                name = self.get_key_name(self.keys[idx])
                deleted_keys.append(name)
                self.aliases.pop(name, None)
                del self.keys[idx]

        if deleted_keys:
            self.save_keys()
            print(f"\nSuccessfully deleted {len(deleted_keys)} key(s):")
            for name in deleted_keys:
                print(f"- {name}")
            if input("\nWould you like to sync changes? (y/N): ").lower() == 'y':
                self.sync_with_git(f"Deleted keys: {', '.join(deleted_keys)}")

    def get_system_key_files(self) -> List[tuple]:
        """Get all public key files from the current system with their paths."""
        home = os.path.expanduser("~")
        ssh_dir = os.path.join(home, ".ssh")
        key_files = []
        
        if not os.path.exists(ssh_dir):
            return key_files

        for file in os.listdir(ssh_dir):
            if file.endswith(".pub"):
                try:
                    path = os.path.join(ssh_dir, file)
                    with open(path, 'r') as f:
                        content = f.read().strip()
                        if content:
                            key_files.append((file, path, content))
                except:
                    continue
        return sorted(key_files)

    def manage_system_keys(self) -> None:
        """Manage SSH keys on the current system."""
        while True:
            key_files = self.get_system_key_files()
            if not key_files:
                print("No SSH keys found on this system")
                return

            print("\nSystem SSH Keys:")
            print("-" * 60)
            for i, (filename, path, content) in enumerate(key_files, 1):
                name = self.get_key_name(content)
                print(f"{i}. {filename}")
                print(f"   Name: {name}")
                print(f"   Path: {path}")
                if os.path.exists(path[:-4]):  # Check if private key exists (remove .pub)
                    print("   Private key: Yes")
                print("-" * 60)

            print("\nSystem Key Management:")
            print("1. Rename key file")
            print("2. Delete key file")
            print("3. Copy public key to clipboard")
            print("4. Back to main menu")

            choice = input("\nEnter your choice (1-4): ").strip()

            if choice == '1':
                key_num = input("Enter key number to rename: ").strip()
                try:
                    idx = int(key_num) - 1
                    if 0 <= idx < len(key_files):
                        old_file, old_path, _ = key_files[idx]
                        new_name = input(f"Enter new name for {old_file} (without .pub): ").strip()
                        if not new_name:
                            print("Invalid name")
                            continue
                            
                        new_file = f"{new_name}.pub"
                        new_path = os.path.join(os.path.dirname(old_path), new_file)
                        
                        if os.path.exists(new_path):
                            print(f"Error: {new_file} already exists")
                            continue
                            
                        # Rename both public and private key if it exists
                        try:
                            os.rename(old_path, new_path)
                            print(f"Renamed {old_file} to {new_file}")
                            
                            # Try to rename private key if it exists
                            old_private = old_path[:-4]  # remove .pub
                            new_private = new_path[:-4]
                            if os.path.exists(old_private):
                                os.rename(old_private, new_private)
                                print(f"Renamed private key {os.path.basename(old_private)} to {os.path.basename(new_private)}")
                        except OSError as e:
                            print(f"Error renaming key: {e}")
                except ValueError:
                    print("Invalid selection")

            elif choice == '2':
                key_num = input("Enter key number to delete: ").strip()
                try:
                    idx = int(key_num) - 1
                    if 0 <= idx < len(key_files):
                        filename, path, _ = key_files[idx]
                        print(f"\nYou are about to delete: {filename}")
                        if os.path.exists(path[:-4]):
                            print("Warning: This will also delete the private key!")
                            
                        confirm = input("\nAre you sure you want to delete this key? This cannot be undone. (yes/N): ").lower()
                        if confirm == 'yes':
                            try:
                                os.remove(path)
                                print(f"Deleted {filename}")
                                
                                # Try to delete private key if it exists
                                private_key = path[:-4]
                                if os.path.exists(private_key):
                                    os.remove(private_key)
                                    print(f"Deleted private key {os.path.basename(private_key)}")
                            except OSError as e:
                                print(f"Error deleting key: {e}")
                        else:
                            print("Operation cancelled.")
                except ValueError:
                    print("Invalid selection")

            elif choice == '3':
                key_num = input("Enter key number to copy: ").strip()
                try:
                    idx = int(key_num) - 1
                    if 0 <= idx < len(key_files):
                        _, _, content = key_files[idx]
                        self.copy_to_clipboard(content)
                except ValueError:
                    print("Invalid selection")

            elif choice == '4':
                break
            else:
                print("Invalid choice")

    def check_repo_visibility(self) -> bool:
        """Check if the git repository is public.
        Returns True if public, False if private or unable to determine."""
        try:
            # Get the remote URL
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()

            # Handle different git URL formats
            if remote_url.startswith('git@github.com:'):
                # Convert SSH URL to HTTPS
                repo_path = remote_url.split('git@github.com:')[1].replace('.git', '')
                api_url = f'https://api.github.com/repos/{repo_path}'
            elif remote_url.startswith('https://github.com/'):
                repo_path = remote_url.split('https://github.com/')[1].replace('.git', '')
                api_url = f'https://api.github.com/repos/{repo_path}'
            else:
                return False  # Non-GitHub repository, assume private

            # Try to access the repository anonymously
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", api_url],
                capture_output=True,
                text=True
            )
            
            # If we can access it anonymously, it's public
            return result.stdout.strip() == "200"
            
        except subprocess.CalledProcessError:
            return False  # Assume private if we can't determine

def main():
    manager = SSHKeyManager()
    
    while True:
        print("\nSSH Public Key Manager")
        print("1. Capture public key of current device")
        print("2. Deploy public keys to current device")
        print("3. Set alias for key")
        print("4. Sync with git")
        print("5. Delete keys")
        print("6. List all keys")
        print("7. Search keys")
        print("8. Copy key to clipboard")
        print("9. Set key expiry")
        print("10. Manage system keys")
        print("11. Exit")

        choice = input("\nEnter your choice (1-11): ").strip()

        if choice == '1':
            manager.capture_keys()
        elif choice == '2':
            manager.deploy_keys()
        elif choice == '3':
            manager.set_alias()
        elif choice == '4':
            manager.sync_with_git("Manual sync")
        elif choice == '5':
            manager.delete_keys()
        elif choice == '6':
            manager.list_keys()
        elif choice == '7':
            search = input("Enter search term: ").strip()
            manager.list_keys(search)
        elif choice == '8':
            manager.list_keys()
            key_num = input("\nEnter key number to copy: ").strip()
            try:
                idx = int(key_num) - 1
                if 0 <= idx < len(manager.keys):
                    manager.copy_to_clipboard(manager.keys[idx])
            except ValueError:
                print("Invalid key number")
        elif choice == '9':
            manager.list_keys()
            key_num = input("\nEnter key number to set expiry: ").strip()
            expiry = input("Enter expiry date (YYYY-MM-DD): ").strip()
            try:
                idx = int(key_num) - 1
                manager.set_expiry(idx, expiry)
            except ValueError:
                print("Invalid key number")
        elif choice == '10':
            manager.manage_system_keys()
        elif choice == '11':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0) 