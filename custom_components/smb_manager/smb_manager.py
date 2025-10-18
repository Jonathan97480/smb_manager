"""SMB Configuration Manager for SMB Share Manager."""
import logging
import subprocess
import re
from typing import Dict, List, Optional

from .const import (
    SMB_CONF_PATH,
    DEFAULT_CREATE_MASK,
    DEFAULT_DIRECTORY_MASK,
    DEFAULT_UID,
    DEFAULT_GID,
)

_LOGGER = logging.getLogger(__name__)


class SmbManager:
    """Manage Samba configuration and services."""

    def __init__(self, hass):
        """Initialize the SMB manager."""
        self.hass = hass

    def _run_command(self, command: List[str], check: bool = True, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a shell command with sudo."""
        try:
            if command[0] != "sudo":
                command = ["sudo"] + command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check,
                input=input_text
            )
            return result
        except subprocess.CalledProcessError as e:
            _LOGGER.error(f"Command failed: {' '.join(command)}")
            _LOGGER.error(f"Error: {e.stderr}")
            raise

    def list_shares(self) -> List[Dict]:
        """List all SMB shares configured in smb.conf."""
        try:
            with open(SMB_CONF_PATH, 'r') as f:
                content = f.read()
            
            shares = []
            share_pattern = r'\[([^\]]+)\]\s*\n((?:.*\n)*?)(?=\n\[|\Z)'
            matches = re.finditer(share_pattern, content, re.MULTILINE)
            
            for match in matches:
                share_name = match.group(1)
                share_config = match.group(2)
                
                # Skip system shares
                if share_name in ["global", "homes", "printers", "print$"]:
                    continue
                
                share_info = self._parse_share_config(share_name, share_config)
                shares.append(share_info)
            
            return shares
        except Exception as e:
            _LOGGER.error(f"Failed to list shares: {e}")
            return []

    def _parse_share_config(self, share_name: str, config: str) -> Dict:
        """Parse share configuration from smb.conf."""
        share = {"name": share_name}
        
        patterns = {
            "path": r'path\s*=\s*(.+)',
            "browseable": r'browseable\s*=\s*(yes|no)',
            "writable": r'writable\s*=\s*(yes|no)',
            "guest_ok": r'guest ok\s*=\s*(yes|no)',
            "create_mask": r'create mask\s*=\s*(\d+)',
            "directory_mask": r'directory mask\s*=\s*(\d+)',
            "force_user": r'force user\s*=\s*(.+)',
            "force_group": r'force group\s*=\s*(.+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, config, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key in ["browseable", "writable", "guest_ok"]:
                    share[key] = value.lower() == "yes"
                else:
                    share[key] = value
        
        return share

    def create_share(self, share_name: str, path: str, options: Optional[Dict] = None) -> Dict:
        """Create a new SMB share."""
        try:
            # Check if share already exists
            shares = self.list_shares()
            if any(s["name"] == share_name for s in shares):
                return {"success": False, "error": f"Share {share_name} already exists"}
            
            # Prepare share configuration
            if options is None:
                options = {}
            
            config = self._build_share_config(share_name, path, options)
            
            # Append to smb.conf
            self._run_command(["bash", "-c", f"echo '{config}' >> {SMB_CONF_PATH}"])
            
            # Restart Samba
            self.restart_samba()
            
            return {
                "success": True,
                "share_name": share_name,
                "path": path,
                "options": options,
            }
        except Exception as e:
            _LOGGER.error(f"Failed to create share {share_name}: {e}")
            return {"success": False, "error": str(e)}

    def delete_share(self, share_name: str) -> Dict:
        """Delete an SMB share."""
        try:
            # Read smb.conf
            with open(SMB_CONF_PATH, 'r') as f:
                content = f.read()
            
            # Remove the share section
            pattern = rf'\[{re.escape(share_name)}\]\s*\n(?:.*\n)*?(?=\n\[|\Z)'
            new_content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
            if content == new_content:
                return {"success": False, "error": f"Share {share_name} not found"}
            
            # Write back to smb.conf
            with open(SMB_CONF_PATH, 'w') as f:
                f.write(new_content)
            
            # Restart Samba
            self.restart_samba()
            
            return {"success": True, "share_name": share_name}
        except Exception as e:
            _LOGGER.error(f"Failed to delete share {share_name}: {e}")
            return {"success": False, "error": str(e)}

    def update_share(self, share_name: str, options: Dict) -> Dict:
        """Update an existing SMB share."""
        try:
            # Read smb.conf
            with open(SMB_CONF_PATH, 'r') as f:
                content = f.read()
            
            # Find the share section
            pattern = rf'(\[{re.escape(share_name)}\]\s*\n)((?:.*\n)*?)(?=\n\[|\Z)'
            match = re.search(pattern, content, re.MULTILINE)
            
            if not match:
                return {"success": False, "error": f"Share {share_name} not found"}
            
            # Parse current config
            current_config = self._parse_share_config(share_name, match.group(2))
            
            # Merge with new options
            current_config.update(options)
            
            # Build new config
            new_config = self._build_share_config(
                share_name,
                current_config.get("path", ""),
                current_config
            )
            
            # Replace in content
            new_content = re.sub(pattern, new_config, content, flags=re.MULTILINE)
            
            # Write back to smb.conf
            with open(SMB_CONF_PATH, 'w') as f:
                f.write(new_content)
            
            # Restart Samba
            self.restart_samba()
            
            return {"success": True, "share_name": share_name, "options": options}
        except Exception as e:
            _LOGGER.error(f"Failed to update share {share_name}: {e}")
            return {"success": False, "error": str(e)}

    def _build_share_config(self, share_name: str, path: str, options: Dict) -> str:
        """Build a share configuration string."""
        config = f"\n[{share_name}]\n"
        config += f"   path = {path}\n"
        config += f"   browseable = {'yes' if options.get('browseable', True) else 'no'}\n"
        config += f"   writable = {'yes' if options.get('writable', True) else 'no'}\n"
        config += f"   guest ok = {'yes' if options.get('guest_ok', False) else 'no'}\n"
        config += f"   public = {'yes' if options.get('guest_ok', False) else 'no'}\n"
        config += f"   create mask = {options.get('create_mask', DEFAULT_CREATE_MASK)}\n"
        config += f"   directory mask = {options.get('directory_mask', DEFAULT_DIRECTORY_MASK)}\n"
        config += f"   force user = {options.get('force_user', 'root')}\n"
        config += f"   force group = {options.get('force_group', 'root')}\n"
        return config

    def add_user(self, username: str, password: str) -> Dict:
        """Add a Samba user."""
        try:
            # Check if system user exists, create if not
            try:
                self._run_command(["id", username], check=False)
            except:
                # Create system user
                self._run_command(["useradd", "-M", "-s", "/usr/sbin/nologin", username])
            
            # Add Samba password
            password_input = f"{password}\n{password}\n"
            self._run_command(["smbpasswd", "-a", username], input_text=password_input)
            
            # Enable the user
            self._run_command(["smbpasswd", "-e", username])
            
            return {"success": True, "username": username}
        except Exception as e:
            _LOGGER.error(f"Failed to add user {username}: {e}")
            return {"success": False, "error": str(e)}

    def remove_user(self, username: str) -> Dict:
        """Remove a Samba user."""
        try:
            # Remove from Samba
            self._run_command(["smbpasswd", "-x", username])
            
            # Optionally remove system user (commented out for safety)
            # self._run_command(["userdel", username])
            
            return {"success": True, "username": username}
        except Exception as e:
            _LOGGER.error(f"Failed to remove user {username}: {e}")
            return {"success": False, "error": str(e)}

    def restart_samba(self) -> Dict:
        """Restart Samba services."""
        try:
            self._run_command(["systemctl", "restart", "smbd"])
            self._run_command(["systemctl", "restart", "nmbd"])
            
            return {"success": True}
        except Exception as e:
            _LOGGER.error(f"Failed to restart Samba: {e}")
            return {"success": False, "error": str(e)}

    def get_samba_status(self) -> Dict:
        """Get the status of Samba services."""
        try:
            smbd_result = self._run_command(["systemctl", "is-active", "smbd"], check=False)
            nmbd_result = self._run_command(["systemctl", "is-active", "nmbd"], check=False)
            
            return {
                "smbd": smbd_result.stdout.strip(),
                "nmbd": nmbd_result.stdout.strip(),
                "running": smbd_result.stdout.strip() == "active" and nmbd_result.stdout.strip() == "active",
            }
        except Exception as e:
            _LOGGER.error(f"Failed to get Samba status: {e}")
            return {"smbd": "unknown", "nmbd": "unknown", "running": False}
