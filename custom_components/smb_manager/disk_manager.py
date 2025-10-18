"""Disk Manager for SMB Share Manager."""
import logging
import subprocess
import re
import os
from typing import Dict, List, Optional

from .const import (
    FSTAB_PATH,
    MOUNT_BASE_PATH,
    SUPPORTED_FILESYSTEMS,
    DEPENDENCIES,
)

_LOGGER = logging.getLogger(__name__)


class DiskManager:
    """Manage disk detection, mounting, and fstab configuration."""

    def __init__(self, hass):
        """Initialize the disk manager."""
        self.hass = hass

    def _run_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command with sudo."""
        try:
            if command[0] != "sudo":
                command = ["sudo"] + command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            _LOGGER.error(f"Command failed: {' '.join(command)}")
            _LOGGER.error(f"Error: {e.stderr}")
            raise

    def detect_disks(self) -> List[Dict]:
        """Detect all available disks and their properties."""
        try:
            result = self._run_command(["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,UUID,LABEL"])
            import json
            data = json.loads(result.stdout)
            
            disks = []
            for device in data.get("blockdevices", []):
                disk_info = self._parse_disk_info(device)
                if disk_info:
                    disks.append(disk_info)
                    
                # Check partitions
                for partition in device.get("children", []):
                    part_info = self._parse_disk_info(partition, parent=device["name"])
                    if part_info:
                        disks.append(part_info)
            
            return disks
        except Exception as e:
            _LOGGER.error(f"Failed to detect disks: {e}")
            return []

    def _parse_disk_info(self, device: Dict, parent: Optional[str] = None) -> Optional[Dict]:
        """Parse disk information from lsblk output."""
        name = device.get("name")
        if not name:
            return None
            
        # Skip loop devices and system partitions
        if name.startswith("loop") or name.startswith("mmcblk0"):
            return None
            
        return {
            "device": f"/dev/{name}",
            "name": name,
            "parent": parent,
            "size": device.get("size", "Unknown"),
            "fstype": device.get("fstype"),
            "mountpoint": device.get("mountpoint"),
            "uuid": device.get("uuid"),
            "label": device.get("label"),
            "mounted": bool(device.get("mountpoint")),
        }

    def mount_disk(
        self,
        device: str,
        mount_point: Optional[str] = None,
        filesystem: Optional[str] = None,
        permanent: bool = False
    ) -> Dict:
        """Mount a disk to a mount point."""
        try:
            # Detect filesystem if not provided
            if not filesystem:
                filesystem = self._detect_filesystem(device)
                if not filesystem:
                    return {"success": False, "error": "Could not detect filesystem"}
            
            # Generate mount point if not provided
            if not mount_point:
                device_name = os.path.basename(device).replace("/", "_")
                mount_point = os.path.join(MOUNT_BASE_PATH, device_name)
            
            # Create mount point directory
            self._run_command(["mkdir", "-p", mount_point])
            
            # Mount the disk
            mount_cmd = ["mount", "-t"]
            if filesystem in ["ntfs"]:
                mount_cmd.extend(["ntfs-3g", device, mount_point])
            else:
                mount_cmd.extend([filesystem, device, mount_point])
            
            self._run_command(mount_cmd)
            
            # Add to fstab if permanent
            if permanent:
                self._add_to_fstab(device, mount_point, filesystem)
            
            return {
                "success": True,
                "device": device,
                "mount_point": mount_point,
                "filesystem": filesystem,
                "permanent": permanent,
            }
        except Exception as e:
            _LOGGER.error(f"Failed to mount {device}: {e}")
            return {"success": False, "error": str(e)}

    def unmount_disk(self, mount_point: str, remove_from_fstab: bool = False) -> Dict:
        """Unmount a disk from a mount point."""
        try:
            # Unmount the disk
            self._run_command(["umount", mount_point])
            
            # Remove from fstab if requested
            if remove_from_fstab:
                self._remove_from_fstab(mount_point)
            
            return {
                "success": True,
                "mount_point": mount_point,
                "removed_from_fstab": remove_from_fstab,
            }
        except Exception as e:
            _LOGGER.error(f"Failed to unmount {mount_point}: {e}")
            return {"success": False, "error": str(e)}

    def _detect_filesystem(self, device: str) -> Optional[str]:
        """Detect the filesystem type of a device."""
        try:
            result = self._run_command(["file", "-s", device])
            output = result.stdout.lower()
            
            if "ntfs" in output:
                return "ntfs"
            elif "exfat" in output:
                return "exfat"
            elif "ext4" in output:
                return "ext4"
            elif "fat32" in output or "vfat" in output:
                return "vfat"
            
            return None
        except Exception as e:
            _LOGGER.error(f"Failed to detect filesystem for {device}: {e}")
            return None

    def _add_to_fstab(self, device: str, mount_point: str, filesystem: str) -> None:
        """Add an entry to /etc/fstab for permanent mounting."""
        try:
            # Get UUID or use device path
            uuid = self._get_uuid(device)
            device_id = f"UUID={uuid}" if uuid else device
            
            # Prepare fstab entry
            options = "defaults,uid=0,gid=0,umask=000,nofail,x-systemd.automount"
            if filesystem == "ntfs":
                filesystem = "ntfs-3g"
            
            fstab_entry = f"{device_id} {mount_point} {filesystem} {options} 0 0\n"
            
            # Check if entry already exists
            with open(FSTAB_PATH, 'r') as f:
                content = f.read()
                if mount_point in content:
                    _LOGGER.warning(f"Entry for {mount_point} already exists in fstab")
                    return
            
            # Append to fstab
            self._run_command(["bash", "-c", f"echo '{fstab_entry}' >> {FSTAB_PATH}"])
            _LOGGER.info(f"Added {mount_point} to fstab")
        except Exception as e:
            _LOGGER.error(f"Failed to add to fstab: {e}")
            raise

    def _remove_from_fstab(self, mount_point: str) -> None:
        """Remove an entry from /etc/fstab."""
        try:
            # Read fstab
            with open(FSTAB_PATH, 'r') as f:
                lines = f.readlines()
            
            # Filter out the line with this mount point
            new_lines = [line for line in lines if mount_point not in line]
            
            # Write back to fstab
            with open(FSTAB_PATH, 'w') as f:
                f.writelines(new_lines)
            
            _LOGGER.info(f"Removed {mount_point} from fstab")
        except Exception as e:
            _LOGGER.error(f"Failed to remove from fstab: {e}")
            raise

    def _get_uuid(self, device: str) -> Optional[str]:
        """Get the UUID of a device."""
        try:
            result = self._run_command(["blkid", device], check=False)
            match = re.search(r'UUID="([^"]+)"', result.stdout)
            return match.group(1) if match else None
        except Exception:
            return None

    def install_dependencies(self) -> Dict:
        """Install required dependencies for disk mounting and Samba."""
        try:
            _LOGGER.info("Updating package lists...")
            self._run_command(["apt", "update"])
            
            _LOGGER.info("Installing dependencies...")
            for package in DEPENDENCIES:
                try:
                    self._run_command(["apt", "install", "-y", package])
                    _LOGGER.info(f"Installed {package}")
                except Exception as e:
                    _LOGGER.warning(f"Failed to install {package}: {e}")
            
            return {"success": True, "installed": DEPENDENCIES}
        except Exception as e:
            _LOGGER.error(f"Failed to install dependencies: {e}")
            return {"success": False, "error": str(e)}

    def create_partitions(self, device: str, partitions: List[Dict]) -> Dict:
        """Create partitions on a disk using parted.
        
        Args:
            device: Device path (e.g., /dev/sda)
            partitions: List of partition configs with 'name', 'size', 'fstype'
        
        Returns:
            Dict with success status
        """
        try:
            _LOGGER.info(f"Creating partitions on {device}")
            
            # First, unmount any existing partitions
            try:
                result = self._run_command(["lsblk", "-J", "-o", "NAME,MOUNTPOINT", device])
                import json
                data = json.loads(result.stdout)
                for block in data.get("blockdevices", []):
                    if block.get("mountpoint"):
                        _LOGGER.info(f"Unmounting {block['mountpoint']}")
                        self._run_command(["umount", block["mountpoint"]])
            except Exception as e:
                _LOGGER.warning(f"Could not unmount existing partitions: {e}")
            
            # Create new partition table (GPT)
            _LOGGER.info(f"Creating GPT partition table on {device}")
            self._run_command(["parted", "-s", device, "mklabel", "gpt"])
            
            # Create partitions
            start = "0%"
            for i, part_config in enumerate(partitions, 1):
                size = part_config.get("size", "100%")
                
                # Calculate end position
                if size.endswith("%"):
                    if i == len(partitions):
                        end = "100%"
                    else:
                        end = size
                elif size.endswith("G"):
                    # Convert GB to end position
                    gb = float(size.rstrip("G"))
                    end = f"{gb}GB"
                else:
                    end = size
                
                _LOGGER.info(f"Creating partition {i}: {start} to {end}")
                self._run_command([
                    "parted", "-s", device, "mkpart",
                    f"primary", start, end
                ])
                
                # Update start for next partition
                start = end
            
            # Wait for kernel to recognize new partitions
            import time
            time.sleep(2)
            self._run_command(["partprobe", device])
            time.sleep(1)
            
            # Format partitions
            for i, part_config in enumerate(partitions, 1):
                partition_device = f"{device}{i}"
                fstype = part_config.get("fstype", "ext4")
                label = part_config.get("name", f"partition{i}")
                
                _LOGGER.info(f"Formatting {partition_device} as {fstype} with label {label}")
                
                if fstype == "ext4":
                    self._run_command(["mkfs.ext4", "-F", "-L", label, partition_device])
                elif fstype == "ntfs":
                    self._run_command(["mkfs.ntfs", "-f", "-L", label, partition_device])
                elif fstype == "vfat":
                    self._run_command(["mkfs.vfat", "-n", label, partition_device])
                elif fstype == "exfat":
                    self._run_command(["mkfs.exfat", "-n", label, partition_device])
                else:
                    _LOGGER.warning(f"Unknown filesystem type: {fstype}")
            
            _LOGGER.info(f"Successfully created {len(partitions)} partition(s) on {device}")
            return {"success": True, "partitions": len(partitions)}
            
        except Exception as e:
            _LOGGER.error(f"Failed to create partitions on {device}: {e}")
            return {"success": False, "error": str(e)}
