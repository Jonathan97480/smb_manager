"""Sensor platform for SMB Share Manager."""
import logging
from datetime import timedelta
import subprocess
import socket

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .disk_manager import DiskManager
from .smb_manager import SmbManager

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMB Share Manager sensors."""
    
    disk_manager = DiskManager(hass)
    smb_manager = SmbManager(hass)
    
    # Create coordinators for data updates
    async def async_update_data():
        """Fetch all data."""
        # Get shares
        shares = await hass.async_add_executor_job(smb_manager.list_shares)
        
        # Get disks
        disks = await hass.async_add_executor_job(disk_manager.detect_disks)
        
        # Get fstab entries
        fstab_entries = await hass.async_add_executor_job(_get_fstab_entries)
        
        # Get server IP
        server_ip = await hass.async_add_executor_job(_get_server_ip)
        
        # Combine disk info with mount and share info
        enhanced_disks = []
        for disk in disks:
            disk_data = disk.copy()
            
            # Check if in fstab
            disk_data["in_fstab"] = any(
                entry.get("device") == disk["device"] or entry.get("uuid") == disk.get("uuid")
                for entry in fstab_entries
            )
            
            # Check if shared via SMB
            disk_data["shared"] = False
            disk_data["share_info"] = []
            
            if disk.get("mountpoint"):
                for share in shares:
                    share_path = share.get("path", "")
                    if share_path.startswith(disk["mountpoint"]):
                        disk_data["shared"] = True
                        disk_data["share_info"].append({
                            "name": share.get("name"),
                            "path": share_path,
                            "network_path": f"\\\\{server_ip}\\{share.get('name')}",
                            "writable": share.get("writable", False),
                        })
            
            enhanced_disks.append(disk_data)
        
        return {
            "disks": enhanced_disks,
            "shares": shares,
            "server_ip": server_ip,
        }
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="SMB Manager",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create sensors
    async_add_entities(
        [
            SmbSharesSensor(coordinator),
            DisksSensor(coordinator),
            SystemStatusSensor(coordinator),
        ]
    )


def _get_fstab_entries():
    """Get all entries from /etc/fstab."""
    try:
        with open("/etc/fstab", "r") as f:
            lines = f.readlines()
        
        entries = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            parts = line.split()
            if len(parts) >= 3:
                entries.append({
                    "device": parts[0],
                    "mountpoint": parts[1],
                    "fstype": parts[2],
                    "uuid": parts[0].replace("UUID=", "") if parts[0].startswith("UUID=") else None,
                })
        
        return entries
    except Exception as e:
        _LOGGER.error(f"Failed to read fstab: {e}")
        return []


def _get_server_ip():
    """Get the server's IP address."""
    try:
        # Get the IP address of the default network interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        _LOGGER.error(f"Failed to get server IP: {e}")
        return "localhost"


class SmbSharesSensor(CoordinatorEntity, SensorEntity):
    """Sensor for SMB shares."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "SMB Shares"
        self._attr_unique_id = f"{DOMAIN}_shares"
        self._attr_icon = "mdi:folder-network"

    @property
    def state(self) -> int:
        """Return the number of shares."""
        if self.coordinator.data and "shares" in self.coordinator.data:
            return len(self.coordinator.data["shares"])
        return 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        if not self.coordinator.data or "shares" not in self.coordinator.data:
            return {"shares": [], "server_ip": ""}
        
        shares_list = []
        for share in self.coordinator.data["shares"]:
            shares_list.append({
                "name": share.get("name", "Unknown"),
                "path": share.get("path", ""),
                "network_path": f"\\\\{self.coordinator.data.get('server_ip', 'localhost')}\\{share.get('name')}",
                "writable": share.get("writable", False),
                "browseable": share.get("browseable", True),
            })
        
        return {
            "shares": shares_list,
            "total_shares": len(self.coordinator.data["shares"]),
            "server_ip": self.coordinator.data.get("server_ip", ""),
        }


class DisksSensor(CoordinatorEntity, SensorEntity):
    """Sensor for detected disks."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Disks and Mounts"
        self._attr_unique_id = f"{DOMAIN}_disks"
        self._attr_icon = "mdi:harddisk"

    @property
    def state(self) -> int:
        """Return the number of disks."""
        if self.coordinator.data and "disks" in self.coordinator.data:
            return len(self.coordinator.data["disks"])
        return 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        if not self.coordinator.data or "disks" not in self.coordinator.data:
            return {"disks": []}
        
        disks_list = []
        for disk in self.coordinator.data["disks"]:
            disk_info = {
                "device": disk.get("device", "Unknown"),
                "name": disk.get("name", ""),
                "size": disk.get("size", ""),
                "filesystem": disk.get("fstype", "Unknown"),
                "mounted": disk.get("mounted", False),
                "mount_point": disk.get("mountpoint", "Not mounted"),
                "permanent": disk.get("in_fstab", False),
                "label": disk.get("label", ""),
                "uuid": disk.get("uuid", ""),
            }
            
            # Add share information if shared
            if disk.get("shared", False):
                disk_info["shared_via_smb"] = True
                disk_info["shares"] = disk.get("share_info", [])
            else:
                disk_info["shared_via_smb"] = False
                disk_info["shares"] = []
            
            disks_list.append(disk_info)
        
        return {
            "disks": disks_list,
            "total_disks": len(self.coordinator.data["disks"]),
            "mounted_disks": sum(1 for d in self.coordinator.data["disks"] if d.get("mounted")),
            "permanent_mounts": sum(1 for d in self.coordinator.data["disks"] if d.get("in_fstab")),
            "shared_disks": sum(1 for d in self.coordinator.data["disks"] if d.get("shared")),
        }


class SystemStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for SMB system status."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "SMB Server Status"
        self._attr_unique_id = f"{DOMAIN}_status"
        self._attr_icon = "mdi:server-network"

    @property
    def state(self) -> str:
        """Return the server status."""
        return "online"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "server_ip": self.coordinator.data.get("server_ip", ""),
            "total_shares": len(self.coordinator.data.get("shares", [])),
            "total_disks": len(self.coordinator.data.get("disks", [])),
            "mounted_disks": sum(1 for d in self.coordinator.data.get("disks", []) if d.get("mounted")),
            "shared_disks": sum(1 for d in self.coordinator.data.get("disks", []) if d.get("shared")),
        }
