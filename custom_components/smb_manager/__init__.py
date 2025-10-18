"""SMB Share Manager - Home Assistant Integration."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_DETECT_DISKS,
    SERVICE_MOUNT_DISK,
    SERVICE_UNMOUNT_DISK,
    SERVICE_CREATE_SHARE,
    SERVICE_DELETE_SHARE,
    SERVICE_UPDATE_SHARE,
    SERVICE_ADD_USER,
    SERVICE_REMOVE_USER,
    SERVICE_RESTART_SAMBA,
    SERVICE_INSTALL_DEPENDENCIES,
)
from .disk_manager import DiskManager
from .smb_manager import SmbManager

_LOGGER = logging.getLogger(__name__)

# Service schemas
DETECT_DISKS_SCHEMA = vol.Schema({})

MOUNT_DISK_SCHEMA = vol.Schema({
    vol.Required("device"): cv.string,
    vol.Optional("mount_point"): cv.string,
    vol.Optional("filesystem"): cv.string,
    vol.Optional("permanent", default=False): cv.boolean,
})

UNMOUNT_DISK_SCHEMA = vol.Schema({
    vol.Required("mount_point"): cv.string,
    vol.Optional("remove_from_fstab", default=False): cv.boolean,
})

CREATE_SHARE_SCHEMA = vol.Schema({
    vol.Required("share_name"): cv.string,
    vol.Required("path"): cv.string,
    vol.Optional("browseable", default=True): cv.boolean,
    vol.Optional("writable", default=True): cv.boolean,
    vol.Optional("guest_ok", default=False): cv.boolean,
    vol.Optional("create_mask", default="0644"): cv.string,
    vol.Optional("directory_mask", default="0755"): cv.string,
    vol.Optional("force_user", default="root"): cv.string,
    vol.Optional("force_group", default="root"): cv.string,
})

DELETE_SHARE_SCHEMA = vol.Schema({
    vol.Required("share_name"): cv.string,
})

UPDATE_SHARE_SCHEMA = vol.Schema({
    vol.Required("share_name"): cv.string,
    vol.Optional("path"): cv.string,
    vol.Optional("browseable"): cv.boolean,
    vol.Optional("writable"): cv.boolean,
    vol.Optional("guest_ok"): cv.boolean,
    vol.Optional("create_mask"): cv.string,
    vol.Optional("directory_mask"): cv.string,
    vol.Optional("force_user"): cv.string,
    vol.Optional("force_group"): cv.string,
})

ADD_USER_SCHEMA = vol.Schema({
    vol.Required("username"): cv.string,
    vol.Required("password"): cv.string,
})

REMOVE_USER_SCHEMA = vol.Schema({
    vol.Required("username"): cv.string,
})

RESTART_SAMBA_SCHEMA = vol.Schema({})

INSTALL_DEPENDENCIES_SCHEMA = vol.Schema({})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the SMB Share Manager component."""
    _LOGGER.info("Setting up SMB Share Manager")
    
    # Initialize managers
    disk_manager = DiskManager(hass)
    smb_manager = SmbManager(hass)
    
    # Store managers in hass.data
    hass.data[DOMAIN] = {
        "disk_manager": disk_manager,
        "smb_manager": smb_manager,
    }

    # Register services
    async def handle_detect_disks(call: ServiceCall) -> None:
        """Handle detect_disks service call."""
        _LOGGER.info("Detecting disks...")
        result = await hass.async_add_executor_job(disk_manager.detect_disks)
        hass.bus.fire(f"{DOMAIN}_disks_detected", {"disks": result})
        _LOGGER.info(f"Detected {len(result)} disks")

    async def handle_mount_disk(call: ServiceCall) -> None:
        """Handle mount_disk service call."""
        device = call.data["device"]
        mount_point = call.data.get("mount_point")
        filesystem = call.data.get("filesystem")
        permanent = call.data.get("permanent", False)
        
        _LOGGER.info(f"Mounting disk {device}...")
        result = await hass.async_add_executor_job(
            disk_manager.mount_disk, device, mount_point, filesystem, permanent
        )
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_disk_mounted", result)
            _LOGGER.info(f"Successfully mounted {device} to {result['mount_point']}")
        else:
            _LOGGER.error(f"Failed to mount {device}: {result.get('error')}")

    async def handle_unmount_disk(call: ServiceCall) -> None:
        """Handle unmount_disk service call."""
        mount_point = call.data["mount_point"]
        remove_from_fstab = call.data.get("remove_from_fstab", False)
        
        _LOGGER.info(f"Unmounting disk from {mount_point}...")
        result = await hass.async_add_executor_job(
            disk_manager.unmount_disk, mount_point, remove_from_fstab
        )
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_disk_unmounted", result)
            _LOGGER.info(f"Successfully unmounted {mount_point}")
        else:
            _LOGGER.error(f"Failed to unmount {mount_point}: {result.get('error')}")

    async def handle_create_share(call: ServiceCall) -> None:
        """Handle create_share service call."""
        share_name = call.data["share_name"]
        path = call.data["path"]
        options = {k: v for k, v in call.data.items() if k not in ["share_name", "path"]}
        
        _LOGGER.info(f"Creating SMB share: {share_name}")
        result = await hass.async_add_executor_job(
            smb_manager.create_share, share_name, path, options
        )
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_share_created", result)
            _LOGGER.info(f"Successfully created share {share_name}")
        else:
            _LOGGER.error(f"Failed to create share {share_name}: {result.get('error')}")

    async def handle_delete_share(call: ServiceCall) -> None:
        """Handle delete_share service call."""
        share_name = call.data["share_name"]
        
        _LOGGER.info(f"Deleting SMB share: {share_name}")
        result = await hass.async_add_executor_job(smb_manager.delete_share, share_name)
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_share_deleted", result)
            _LOGGER.info(f"Successfully deleted share {share_name}")
        else:
            _LOGGER.error(f"Failed to delete share {share_name}: {result.get('error')}")

    async def handle_update_share(call: ServiceCall) -> None:
        """Handle update_share service call."""
        share_name = call.data["share_name"]
        options = {k: v for k, v in call.data.items() if k != "share_name"}
        
        _LOGGER.info(f"Updating SMB share: {share_name}")
        result = await hass.async_add_executor_job(
            smb_manager.update_share, share_name, options
        )
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_share_updated", result)
            _LOGGER.info(f"Successfully updated share {share_name}")
        else:
            _LOGGER.error(f"Failed to update share {share_name}: {result.get('error')}")

    async def handle_add_user(call: ServiceCall) -> None:
        """Handle add_user service call."""
        username = call.data["username"]
        password = call.data["password"]
        
        _LOGGER.info(f"Adding Samba user: {username}")
        result = await hass.async_add_executor_job(smb_manager.add_user, username, password)
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_user_added", result)
            _LOGGER.info(f"Successfully added user {username}")
        else:
            _LOGGER.error(f"Failed to add user {username}: {result.get('error')}")

    async def handle_remove_user(call: ServiceCall) -> None:
        """Handle remove_user service call."""
        username = call.data["username"]
        
        _LOGGER.info(f"Removing Samba user: {username}")
        result = await hass.async_add_executor_job(smb_manager.remove_user, username)
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_user_removed", result)
            _LOGGER.info(f"Successfully removed user {username}")
        else:
            _LOGGER.error(f"Failed to remove user {username}: {result.get('error')}")

    async def handle_restart_samba(call: ServiceCall) -> None:
        """Handle restart_samba service call."""
        _LOGGER.info("Restarting Samba services...")
        result = await hass.async_add_executor_job(smb_manager.restart_samba)
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_samba_restarted", result)
            _LOGGER.info("Successfully restarted Samba services")
        else:
            _LOGGER.error(f"Failed to restart Samba: {result.get('error')}")

    async def handle_install_dependencies(call: ServiceCall) -> None:
        """Handle install_dependencies service call."""
        _LOGGER.info("Installing dependencies...")
        result = await hass.async_add_executor_job(disk_manager.install_dependencies)
        
        if result["success"]:
            hass.bus.fire(f"{DOMAIN}_dependencies_installed", result)
            _LOGGER.info("Successfully installed dependencies")
        else:
            _LOGGER.error(f"Failed to install dependencies: {result.get('error')}")

    # Register all services
    hass.services.async_register(DOMAIN, SERVICE_DETECT_DISKS, handle_detect_disks, schema=DETECT_DISKS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_MOUNT_DISK, handle_mount_disk, schema=MOUNT_DISK_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_UNMOUNT_DISK, handle_unmount_disk, schema=UNMOUNT_DISK_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CREATE_SHARE, handle_create_share, schema=CREATE_SHARE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_SHARE, handle_delete_share, schema=DELETE_SHARE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_SHARE, handle_update_share, schema=UPDATE_SHARE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_USER, handle_add_user, schema=ADD_USER_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_USER, handle_remove_user, schema=REMOVE_USER_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RESTART_SAMBA, handle_restart_samba, schema=RESTART_SAMBA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_INSTALL_DEPENDENCIES, handle_install_dependencies, schema=INSTALL_DEPENDENCIES_SCHEMA)

    _LOGGER.info("SMB Share Manager setup complete")
    return True
