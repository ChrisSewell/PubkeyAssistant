# SSH Public Key Manager

A minimal, user-friendly command-line tool for managing SSH public keys across multiple devices. This tool helps you maintain a centralized repository of SSH keys with features for capturing, deploying, and managing keys both locally and across systems.

## Features

- **Minimal Dependencies**: Uses only Python standard library
- **Git Integration**: Automatically syncs your keys with a git repository
- **Key Management**:
  - Capture public keys from current system
  - Deploy keys to current system
  - Set aliases for easy identification
  - Set expiry dates for keys
  - Search and filter keys
  - Copy keys to clipboard
  - Automatic backups before changes

- **System Key Management**:
  - List all SSH keys on current system
  - Rename key files (handles both public and private keys)
  - Delete keys safely
  - Copy system keys to clipboard

## Requirements

- Python 3.6+
- Git (for sync functionality)
- tkinter (optional, for clipboard functionality)

## Installation

⚠️ **IMPORTANT**: Always use a private repository for storing SSH keys. Never store SSH keys in a public repository.

1. Create a new private repository for your SSH keys, then clone it:
   ```bash
   # First create a private repository on GitHub/GitLab/etc
   git clone <your-private-repository-url>
   cd pubkeys
   ```

2. Make the script executable:
   ```bash
   chmod +x manage_keys.py
   ```

3. The tool will check if your repository is public and warn you if it is. For security:
   - Ensure your repository is private before proceeding
   - Regularly verify your repository's privacy settings
   - Never change a repository containing SSH keys to public

## Usage

Run the tool:
```bash
./manage_keys.py
```

### Main Menu Options

1. **Capture public key of current device**
   - Lists all public keys found in your ~/.ssh directory
   - Select which keys to add to the repository
   - Set optional aliases and expiry dates
   - Detects and handles duplicate keys

2. **Deploy public keys to current device**
   - Select keys to deploy to your local ~/.ssh/authorized_keys
   - Verifies successful deployment
   - Sets proper file permissions

3. **Set alias for key**
   - Add friendly names to your keys
   - Makes keys easier to identify

4. **Sync with git**
   - Manually sync changes with git repository
   - Automatic commit messages for tracking changes

5. **Delete keys**
   - Remove keys from the repository
   - Requires confirmation to prevent accidents

6. **List all keys**
   - View all keys with their metadata
   - Shows aliases, types, and expiry dates

7. **Search keys**
   - Find keys by name or alias

8. **Copy key to clipboard**
   - Quick access to key content
   - Falls back to display if clipboard unavailable

9. **Set key expiry**
   - Add expiration dates to keys
   - Helps with key rotation policies

10. **Manage system keys**
    - View all SSH keys on your system
    - Rename key files
    - Safely delete keys
    - Copy system keys to clipboard

### File Structure

- `authorized_keys`: Main storage file for SSH public keys
- `key_aliases.json`: Stores metadata (aliases, expiry dates, etc.)
- `.key_backups/`: Directory containing timestamped backups

### Security Features

- Repository visibility check (warns if public)
- Automatic backup creation before changes
- Proper file permissions (600 for authorized_keys)
- Safe key deletion with confirmation
- Verification of key deployments

## Best Practices

1. **Keep Repository Private**: Never store SSH keys in a public repository
2. **Regular Backups**: The tool automatically creates backups, but consider external backups too
3. **Key Rotation**: Use the expiry date feature to track when keys need rotation
4. **Descriptive Aliases**: Use meaningful aliases to easily identify keys
5. **Regular Syncing**: Keep the repository updated across all systems

## Contributing

Feel free to submit issues and enhancement requests!
