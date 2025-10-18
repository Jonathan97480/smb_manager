"""Config flow for SMB Share Manager integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmbManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMB Share Manager."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SmbManagerOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id("smb_manager")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title="SMB Share Manager",
                data={},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Cette intégration permet de gérer les partages SMB, les disques et les utilisateurs Samba."
            },
        )


class SmbManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SMB Share Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the main menu."""
        return self.async_show_menu(
            step_id="menu",
            menu_options=[
                "detect_disks",
                "mount_disk",
                "unmount_disk",
                "manage_shares",
                "manage_users",
                "restart_samba",
            ],
        )

    async def async_step_detect_disks(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Detect available disks."""
        if user_input is not None:
            # Call the detect_disks service
            await self.hass.services.async_call(
                DOMAIN,
                "detect_disks",
                {},
                blocking=True,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="detect_disks",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Cliquez sur Soumettre pour détecter tous les disques connectés. Les résultats seront disponibles dans les événements Home Assistant (smb_manager_disks_detected)."
            },
        )

    async def async_step_mount_disk(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Mount a disk."""
        # Import disk manager
        from .disk_manager import DiskManager
        disk_manager = DiskManager(self.hass)
        
        if user_input is not None:
            # If device was selected, proceed with mounting
            device = user_input.get("device")
            if device:
                await self.hass.services.async_call(
                    DOMAIN,
                    "mount_disk",
                    {
                        "device": device,
                        "mount_point": user_input.get("mount_point", f"/mnt/{device.split('/')[-1]}"),
                        "fs_type": user_input.get("fs_type", "auto"),
                    },
                    blocking=True,
                )
                return self.async_create_entry(title="", data={})
        
        # Get list of unmounted disks
        disks = await self.hass.async_add_executor_job(disk_manager.detect_disks)
        unmounted_disks = [d for d in disks if not d.get("mounted")]
        
        if not unmounted_disks:
            return self.async_abort(
                reason="no_unmounted_disks",
                description_placeholders={"info": "Aucun disque non monté détecté. Tous les disques sont déjà montés."}
            )
        
        # Create options dict with disk info
        disk_options = {}
        for disk in unmounted_disks:
            label = f"{disk['name']} ({disk.get('size', 'Taille inconnue')}) - {disk.get('fstype', 'Type inconnu')}"
            if disk.get('label'):
                label += f" [{disk['label']}]"
            disk_options[disk['device']] = label
        
        return self.async_show_form(
            step_id="mount_disk",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In(disk_options),
                    vol.Optional("mount_point"): cv.string,
                    vol.Optional("fs_type", default="auto"): vol.In(
                        ["auto", "ntfs-3g", "ext4", "vfat", "exfat"]
                    ),
                }
            ),
            description_placeholders={
                "info": f"Sélectionnez un disque à monter parmi les {len(unmounted_disks)} disque(s) non monté(s). Le point de montage sera créé automatiquement si vous le laissez vide."
            },
        )

    async def async_step_unmount_disk(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Unmount a disk."""
        # Import disk manager
        from .disk_manager import DiskManager
        disk_manager = DiskManager(self.hass)
        
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "unmount_disk",
                {"mount_point": user_input["mount_point"]},
                blocking=True,
            )
            return self.async_create_entry(title="", data={})
        
        # Get list of mounted disks
        disks = await self.hass.async_add_executor_job(disk_manager.detect_disks)
        mounted_disks = [d for d in disks if d.get("mounted") and d.get("mountpoint")]
        
        if not mounted_disks:
            return self.async_abort(
                reason="no_mounted_disks",
                description_placeholders={"info": "Aucun disque monté détecté. Rien à démonter."}
            )
        
        # Create options dict with mounted disk info
        mount_options = {}
        for disk in mounted_disks:
            label = f"{disk['name']} ({disk.get('size', 'Taille inconnue')}) - {disk['mountpoint']}"
            if disk.get('label'):
                label += f" [{disk['label']}]"
            mount_options[disk['mountpoint']] = label

        return self.async_show_form(
            step_id="unmount_disk",
            data_schema=vol.Schema(
                {
                    vol.Required("mount_point"): vol.In(mount_options),
                }
            ),
            description_placeholders={
                "info": f"Sélectionnez un disque à démonter parmi les {len(mounted_disks)} disque(s) monté(s)."
            },
        )

    async def async_step_manage_shares(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage SMB shares."""
        return self.async_show_menu(
            step_id="manage_shares",
            menu_options=[
                "create_share",
                "delete_share",
                "list_shares",
            ],
        )

    async def async_step_create_share(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create an SMB share."""
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "create_share",
                {
                    "share_name": user_input["share_name"],
                    "path": user_input["path"],
                    "comment": user_input.get("comment", ""),
                    "read_only": user_input.get("read_only", False),
                },
                blocking=True,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="create_share",
            data_schema=vol.Schema(
                {
                    vol.Required("share_name"): cv.string,
                    vol.Required("path"): cv.string,
                    vol.Optional("comment", default=""): cv.string,
                    vol.Optional("read_only", default=False): cv.boolean,
                }
            ),
            description_placeholders={
                "info": "Créez un nouveau partage SMB en spécifiant le nom, le chemin et les options."
            },
        )

    async def async_step_delete_share(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delete an SMB share."""
        # Import SMB manager
        from .smb_manager import SmbManager
        smb_manager = SmbManager(self.hass)
        
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "delete_share",
                {"share_name": user_input["share_name"]},
                blocking=True,
            )
            return self.async_create_entry(title="", data={})
        
        # Get list of existing shares
        shares = await self.hass.async_add_executor_job(smb_manager.list_shares)
        
        if not shares:
            return self.async_abort(
                reason="no_shares",
                description_placeholders={"info": "Aucun partage SMB configuré. Rien à supprimer."}
            )
        
        # Create options dict with share info
        share_options = {}
        for share in shares:
            label = f"{share['name']} ({share.get('path', 'Chemin inconnu')})"
            share_options[share['name']] = label

        return self.async_show_form(
            step_id="delete_share",
            data_schema=vol.Schema(
                {
                    vol.Required("share_name"): vol.In(share_options),
                }
            ),
            description_placeholders={
                "info": f"Sélectionnez un partage à supprimer parmi les {len(shares)} partage(s) configuré(s)."
            },
        )

    async def async_step_list_shares(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """List all SMB shares."""
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "list_shares",
                {},
                blocking=True,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="list_shares",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Cliquez sur Soumettre pour lister tous les partages SMB configurés. Les résultats seront disponibles dans les événements Home Assistant (smb_manager_shares_listed)."
            },
        )

    async def async_step_manage_users(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Samba users."""
        return self.async_show_menu(
            step_id="manage_users",
            menu_options=[
                "add_user",
                "delete_user",
            ],
        )

    async def async_step_add_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a Samba user."""
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "add_user",
                {
                    "username": user_input["username"],
                    "password": user_input["password"],
                },
                blocking=True,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): cv.string,
                    vol.Required("password"): cv.string,
                }
            ),
            description_placeholders={
                "info": "Ajoutez un nouvel utilisateur Samba avec un nom d'utilisateur et un mot de passe."
            },
        )

    async def async_step_delete_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delete a Samba user."""
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "delete_user",
                {"username": user_input["username"]},
                blocking=True,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="delete_user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): cv.string,
                }
            ),
            description_placeholders={
                "info": "Supprimez un utilisateur Samba existant en spécifiant son nom d'utilisateur."
            },
        )

    async def async_step_restart_samba(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Restart Samba services."""
        if user_input is not None:
            await self.hass.services.async_call(
                DOMAIN,
                "restart_samba",
                {},
                blocking=True,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="restart_samba",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Cliquez sur Soumettre pour redémarrer les services Samba (smbd et nmbd)."
            },
        )
