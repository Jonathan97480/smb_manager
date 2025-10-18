import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)

DOMAIN = "smb_manager"
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMB Share Manager from a config entry."""
    # Setup the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup services
    return await async_setup(hass, {})


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok


async def async_setup(hass, config):
    """Set up the SMB Share Manager component."""
    _LOGGER.info("Setting up SMB Share Manager")
    
    # Import des managers
    from .disk_manager import DiskManager
    from .smb_manager import SmbManager
    
    disk_manager = DiskManager(hass)
    smb_manager = SmbManager(hass)
    
    # Enregistrement des services
    async def handle_detect_disks(call):
        _LOGGER.info("Service detect_disks called")
        disks = await hass.async_add_executor_job(disk_manager.detect_disks)
        hass.bus.fire("smb_manager_disks_detected", {"disks": disks})
    
    async def handle_mount_disk(call):
        _LOGGER.info("Service mount_disk called")
        device = call.data.get("device")
        mount_point = call.data.get("mount_point")
        fs_type = call.data.get("fs_type", "auto")
        await hass.async_add_executor_job(disk_manager.mount_disk, device, mount_point, fs_type)
    
    async def handle_unmount_disk(call):
        _LOGGER.info("Service unmount_disk called")
        mount_point = call.data.get("mount_point")
        await hass.async_add_executor_job(disk_manager.unmount_disk, mount_point)
    
    async def handle_create_share(call):
        _LOGGER.info("Service create_share called")
        share_name = call.data.get("share_name")
        path = call.data.get("path")
        comment = call.data.get("comment", "")
        read_only = call.data.get("read_only", False)
        await hass.async_add_executor_job(smb_manager.create_share, share_name, path, comment, read_only)
    
    async def handle_delete_share(call):
        _LOGGER.info("Service delete_share called")
        share_name = call.data.get("share_name")
        await hass.async_add_executor_job(smb_manager.delete_share, share_name)
    
    async def handle_list_shares(call):
        _LOGGER.info("Service list_shares called")
        shares = await hass.async_add_executor_job(smb_manager.list_shares)
        hass.bus.fire("smb_manager_shares_listed", {"shares": shares})
    
    async def handle_add_user(call):
        _LOGGER.info("Service add_user called")
        username = call.data.get("username")
        password = call.data.get("password")
        await hass.async_add_executor_job(smb_manager.add_user, username, password)
    
    async def handle_delete_user(call):
        _LOGGER.info("Service delete_user called")
        username = call.data.get("username")
        await hass.async_add_executor_job(smb_manager.delete_user, username)
    
    async def handle_restart_samba(call):
        _LOGGER.info("Service restart_samba called")
        await hass.async_add_executor_job(smb_manager.restart_samba)
    
    async def handle_install_deps(call):
        _LOGGER.info("Service install_dependencies called")
        await hass.async_add_executor_job(disk_manager.install_dependencies)
    
    async def handle_create_partitions(call):
        _LOGGER.info("Service create_partitions called")
        device = call.data.get("device")
        partitions = call.data.get("partitions", [])
        await hass.async_add_executor_job(disk_manager.create_partitions, device, partitions)
    
    # Enregistrement de tous les services
    hass.services.async_register(DOMAIN, "detect_disks", handle_detect_disks)
    hass.services.async_register(DOMAIN, "mount_disk", handle_mount_disk)
    hass.services.async_register(DOMAIN, "unmount_disk", handle_unmount_disk)
    hass.services.async_register(DOMAIN, "create_share", handle_create_share)
    hass.services.async_register(DOMAIN, "delete_share", handle_delete_share)
    hass.services.async_register(DOMAIN, "list_shares", handle_list_shares)
    hass.services.async_register(DOMAIN, "add_user", handle_add_user)
    hass.services.async_register(DOMAIN, "delete_user", handle_delete_user)
    hass.services.async_register(DOMAIN, "restart_samba", handle_restart_samba)
    hass.services.async_register(DOMAIN, "install_dependencies", handle_install_deps)
    hass.services.async_register(DOMAIN, "create_partitions", handle_create_partitions)
    
    _LOGGER.info("SMB Share Manager setup complete")
    return True
