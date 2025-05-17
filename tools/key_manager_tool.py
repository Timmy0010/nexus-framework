"""
Key management utility for the authentication system.

This script provides command-line utilities for managing signing keys,
including key generation, rotation, backup, and restoration.
"""

import argparse
import json
import logging
import os
import time
import sys
from typing import Dict, Any, Optional

from nexus_framework.security.authentication import (
    KeyManager,
    AuthenticationService,
    SigningKeyError,
    KeyRotationError
)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_parser() -> argparse.ArgumentParser:
    """Set up the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Key management utility for the Nexus Authentication System"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Generate keys
    generate_parser = subparsers.add_parser("generate", help="Generate new keys")
    generate_parser.add_argument(
        "--output", "-o",
        help="Output file for the generated keys",
        default="auth_keys.json"
    )
    generate_parser.add_argument(
        "--rotation-days", "-r",
        help="Key rotation interval in days",
        type=int,
        default=30
    )
    
    # Rotate keys
    rotate_parser = subparsers.add_parser("rotate", help="Rotate signing keys")
    rotate_parser.add_argument(
        "--keys-file", "-k",
        help="Keys file to read and update",
        required=True
    )
    rotate_parser.add_argument(
        "--output", "-o",
        help="Output file for the updated keys (defaults to keys-file)",
        default=None
    )
    rotate_parser.add_argument(
        "--emergency", "-e",
        help="Perform emergency rotation (invalidates all previous keys)",
        action="store_true"
    )
    
    # Backup keys
    backup_parser = subparsers.add_parser("backup", help="Backup keys to a file")
    backup_parser.add_argument(
        "--keys-file", "-k",
        help="Keys file to backup",
        required=True
    )
    backup_parser.add_argument(
        "--output", "-o",
        help="Output file for the backup",
        default="auth_keys_backup.json"
    )
    
    # Restore keys
    restore_parser = subparsers.add_parser("restore", help="Restore keys from a backup")
    restore_parser.add_argument(
        "--backup-file", "-b",
        help="Backup file to restore from",
        required=True
    )
    restore_parser.add_argument(
        "--output", "-o",
        help="Output file for the restored keys",
        default="auth_keys_restored.json"
    )
    
    # Purge expired keys
    purge_parser = subparsers.add_parser("purge", help="Purge expired keys")
    purge_parser.add_argument(
        "--keys-file", "-k",
        help="Keys file to read and update",
        required=True
    )
    purge_parser.add_argument(
        "--output", "-o",
        help="Output file for the updated keys (defaults to keys-file)",
        default=None
    )
    purge_parser.add_argument(
        "--grace-days", "-g",
        help="Grace period in days for expired keys",
        type=int,
        default=7
    )
    
    # List keys
    list_parser = subparsers.add_parser("list", help="List all keys and their status")
    list_parser.add_argument(
        "--keys-file", "-k",
        help="Keys file to list",
        required=True
    )
    list_parser.add_argument(
        "--verbose", "-v",
        help="Show detailed information",
        action="store_true"
    )
    
    # Import external key
    import_parser = subparsers.add_parser("import", help="Import an external key")
    import_parser.add_argument(
        "--keys-file", "-k",
        help="Keys file to update",
        required=True
    )
    import_parser.add_argument(
        "--key-id", "-i",
        help="ID for the imported key",
        required=True
    )
    import_parser.add_argument(
        "--key-value", "-v",
        help="Value for the imported key",
        required=True
    )
    import_parser.add_argument(
        "--active", "-a",
        help="Set the imported key as active",
        action="store_true"
    )
    import_parser.add_argument(
        "--output", "-o",
        help="Output file for the updated keys (defaults to keys-file)",
        default=None
    )
    
    return parser

def load_keys(file_path: str) -> Dict[str, Any]:
    """
    Load keys from a file.
    
    Args:
        file_path: Path to the keys file.
        
    Returns:
        Dictionary of keys.
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Keys file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in keys file: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading keys: {e}")
        sys.exit(1)

def save_keys(keys: Dict[str, Any], file_path: str) -> None:
    """
    Save keys to a file.
    
    Args:
        keys: Dictionary of keys.
        file_path: Path to save the keys to.
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(keys, f, indent=2)
        logger.info(f"Keys saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving keys: {e}")
        sys.exit(1)

def generate_keys(args: argparse.Namespace) -> None:
    """
    Generate new keys.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Create a new key manager
        key_manager = KeyManager(rotation_interval_days=args.rotation_days)
        
        # Export keys
        keys = key_manager.export_keys()
        
        # Save to file
        save_keys(keys, args.output)
        
        # Print success message
        key_id, _ = key_manager.get_current_key()
        logger.info(f"Generated new keys with initial key ID: {key_id}")
        logger.info(f"Rotation interval: {args.rotation_days} days")
    except Exception as e:
        logger.error(f"Error generating keys: {e}")
        sys.exit(1)

def rotate_keys(args: argparse.Namespace) -> None:
    """
    Rotate signing keys.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Load existing keys
        keys_data = load_keys(args.keys_file)
        
        # Create key manager with loaded keys
        key_manager = KeyManager()  # Create empty manager first
        
        # Import existing keys
        for key_id, key_info in keys_data.items():
            key_manager.import_key(
                key_id,
                key_info["key"],
                key_info["created_at"],
                key_info["expires_at"],
                key_info["active"]
            )
        
        # Perform rotation
        if args.emergency:
            new_key_id = key_manager.emergency_rotation()
            logger.info(f"Emergency key rotation completed. New key ID: {new_key_id}")
        else:
            new_key_id = key_manager.rotate_key()
            logger.info(f"Key rotation completed. New key ID: {new_key_id}")
        
        # Export updated keys
        updated_keys = key_manager.export_keys()
        
        # Save to file
        output_file = args.output or args.keys_file
        save_keys(updated_keys, output_file)
    except Exception as e:
        logger.error(f"Error rotating keys: {e}")
        sys.exit(1)

def backup_keys(args: argparse.Namespace) -> None:
    """
    Backup keys to a file.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Load existing keys
        keys_data = load_keys(args.keys_file)
        
        # Add backup metadata
        backup = {
            "backup_timestamp": time.time(),
            "backup_source": args.keys_file,
            "keys": keys_data
        }
        
        # Save to backup file
        with open(args.output, 'w') as f:
            json.dump(backup, f, indent=2)
            
        logger.info(f"Keys backup saved to {args.output}")
    except Exception as e:
        logger.error(f"Error backing up keys: {e}")
        sys.exit(1)

def restore_keys(args: argparse.Namespace) -> None:
    """
    Restore keys from a backup.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Load backup file
        with open(args.backup_file, 'r') as f:
            backup = json.load(f)
        
        # Check if it's a valid backup
        if "keys" not in backup:
            logger.error("Invalid backup file: missing 'keys' field")
            sys.exit(1)
            
        # Get keys from backup
        keys_data = backup["keys"]
        
        # Save to output file
        save_keys(keys_data, args.output)
        
        logger.info(f"Keys restored from {args.backup_file} to {args.output}")
        logger.info(f"Backup was created on: {time.ctime(backup.get('backup_timestamp', 0))}")
        logger.info(f"Backup source: {backup.get('backup_source', 'unknown')}")
    except FileNotFoundError:
        logger.error(f"Backup file not found: {args.backup_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in backup file: {args.backup_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error restoring keys: {e}")
        sys.exit(1)

def purge_expired_keys(args: argparse.Namespace) -> None:
    """
    Purge expired keys.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Load existing keys
        keys_data = load_keys(args.keys_file)
        
        # Create key manager with loaded keys
        key_manager = KeyManager()  # Create empty manager first
        
        # Import existing keys
        for key_id, key_info in keys_data.items():
            key_manager.import_key(
                key_id,
                key_info["key"],
                key_info["created_at"],
                key_info["expires_at"],
                key_info["active"]
            )
        
        # Count keys before purge
        key_count_before = len(key_manager.keys)
        
        # Purge expired keys
        key_manager.purge_expired_keys(args.grace_days)
        
        # Count keys after purge
        key_count_after = len(key_manager.keys)
        
        # Export updated keys
        updated_keys = key_manager.export_keys()
        
        # Save to file
        output_file = args.output or args.keys_file
        save_keys(updated_keys, output_file)
        
        logger.info(f"Purged {key_count_before - key_count_after} expired keys")
        logger.info(f"Grace period: {args.grace_days} days")
        logger.info(f"Updated keys saved to {output_file}")
    except Exception as e:
        logger.error(f"Error purging keys: {e}")
        sys.exit(1)

def list_keys(args: argparse.Namespace) -> None:
    """
    List all keys and their status.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Load existing keys
        keys_data = load_keys(args.keys_file)
        
        # Print keys info
        print("\nKeys in file:", args.keys_file)
        print("=" * 50)
        
        for key_id, key_info in keys_data.items():
            created = time.ctime(key_info["created_at"])
            expires = time.ctime(key_info["expires_at"])
            active = "YES" if key_info["active"] else "NO"
            
            status = "ACTIVE" if key_info["active"] else "INACTIVE"
            
            # Check if expired
            if key_info["expires_at"] < time.time():
                status = "EXPIRED"
                
            print(f"Key ID: {key_id}")
            print(f"Status: {status}")
            
            if args.verbose:
                print(f"Created: {created}")
                print(f"Expires: {expires}")
                print(f"Active: {active}")
                
                # Show key value only in verbose mode
                key_value = key_info["key"]
                # Show only first 10 chars for security
                print(f"Key: {key_value[:10]}...")
                
            print("-" * 50)
            
        print(f"Total keys: {len(keys_data)}")
    except Exception as e:
        logger.error(f"Error listing keys: {e}")
        sys.exit(1)

def import_key(args: argparse.Namespace) -> None:
    """
    Import an external key.
    
    Args:
        args: Command-line arguments.
    """
    try:
        # Load existing keys if file exists
        try:
            keys_data = load_keys(args.keys_file)
        except FileNotFoundError:
            keys_data = {}
        
        # Create key manager with loaded keys
        key_manager = KeyManager()  # Create empty manager first
        
        # Import existing keys
        for key_id, key_info in keys_data.items():
            key_manager.import_key(
                key_id,
                key_info["key"],
                key_info["created_at"],
                key_info["expires_at"],
                key_info["active"]
            )
        
        # Import the new key
        now = time.time()
        expires = now + (30 * 24 * 60 * 60)  # Default: 30 days
        
        key_manager.import_key(
            args.key_id,
            args.key_value,
            now,
            expires,
            args.active
        )
        
        # Export updated keys
        updated_keys = key_manager.export_keys()
        
        # Save to file
        output_file = args.output or args.keys_file
        save_keys(updated_keys, output_file)
        
        logger.info(f"Imported key with ID: {args.key_id}")
        if args.active:
            logger.info("Key set as active")
        logger.info(f"Updated keys saved to {output_file}")
    except Exception as e:
        logger.error(f"Error importing key: {e}")
        sys.exit(1)

def main():
    """
    Main entry point for the key management utility.
    """
    parser = setup_parser()
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "generate":
        generate_keys(args)
    elif args.command == "rotate":
        rotate_keys(args)
    elif args.command == "backup":
        backup_keys(args)
    elif args.command == "restore":
        restore_keys(args)
    elif args.command == "purge":
        purge_expired_keys(args)
    elif args.command == "list":
        list_keys(args)
    elif args.command == "import":
        import_key(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
