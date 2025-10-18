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
            device = user_input.get("device")
            if device:
                # Check if device needs partitioning
                if device.startswith("NOPART:"):
                    # Extract actual device path
                    actual_device = device.replace("NOPART:", "")
                    # Redirect to partition creation step
                    self.context["disk_to_partition"] = actual_device
                    return await self.async_step_create_partition()
                
                # Normal mounting
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
        
        # Get list of all disks
        disks = await self.hass.async_add_executor_job(disk_manager.detect_disks)
        
        # Helper function to parse size to bytes
        def parse_size_to_bytes(size_str):
            """Convert size string like '953.9G' to bytes."""
            if not size_str or size_str == "Unknown":
                return 0
            size_str = size_str.strip().upper()
            try:
                if 'T' in size_str:
                    return float(size_str.rstrip('TB')) * 1024 * 1024 * 1024 * 1024
                elif 'G' in size_str:
                    return float(size_str.rstrip('GB')) * 1024 * 1024 * 1024
                elif 'M' in size_str:
                    return float(size_str.rstrip('MB')) * 1024 * 1024
                elif 'K' in size_str:
                    return float(size_str.rstrip('KB')) * 1024
                else:
                    return float(size_str)
            except:
                return 0
        
        # First pass: Calculate usage percentage for all parent disks
        disk_usage = {}  # {disk_name: usage_percent}
        
        for disk in disks:
            if not disk.get("parent"):  # It's a parent disk
                disk_size_bytes = parse_size_to_bytes(disk.get("size", "0"))
                
                if disk_size_bytes == 0:
                    disk_usage[disk["name"]] = 100  # Unknown size = treat as full
                    continue
                
                # Calculate total size of ALL partitions
                used_bytes = 0
                has_any_partition = False
                
                for child in disks:
                    if child.get("parent") == disk["name"]:
                        has_any_partition = True
                        child_size = parse_size_to_bytes(child.get("size", "0"))
                        used_bytes += child_size
                
                # Calculate usage percentage
                usage_percent = (used_bytes / disk_size_bytes * 100) if disk_size_bytes > 0 else 0
                disk_usage[disk["name"]] = usage_percent if has_any_partition else 0
        
        # Second pass: Separate partitions and parent disks
        mountable_items = []
        disks_without_partitions = []
        
        for disk in disks:
            # Skip mounted items
            if disk.get("mounted"):
                continue
            
            # If it's a partition (has parent)
            if disk.get("parent"):
                # Check if parent disk usage is < 90%
                parent_usage = disk_usage.get(disk["parent"], 100)
                
                # Only add if it has valid filesystem AND parent is < 90% used
                if disk.get("fstype") and parent_usage < 90:
                    mountable_items.append(disk)
            else:
                # It's a parent disk - show only if < 90% used
                usage_percent = disk_usage.get(disk["name"], 100)
                
                if usage_percent < 90:
                    disks_without_partitions.append(disk)
        
        if not mountable_items and not disks_without_partitions:
            return self.async_abort(
                reason="no_unmounted_disks",
                description_placeholders={"info": "Aucun disque non monté détecté. Tous les disques sont déjà montés."}
            )
        
        # Create options dict with hierarchical display
        # Group partitions by parent disk
        disk_groups = {}  # {parent_name: {'disk': disk_obj, 'partitions': [partition_objs]}}
        
        # First, organize parent disks
        for disk in disks_without_partitions:
            disk_groups[disk["name"]] = {
                'disk': disk,
                'partitions': []
            }
        
        # Then, add partitions to their parent groups
        for partition in mountable_items:
            parent_name = partition.get("parent")
            if parent_name:
                if parent_name not in disk_groups:
                    # Create parent entry if doesn't exist
                    parent_disk = next((d for d in disks if d["name"] == parent_name and not d.get("parent")), None)
                    if parent_disk:
                        disk_groups[parent_name] = {
                            'disk': parent_disk,
                            'partitions': []
                        }
                    else:
                        # Parent not found, create placeholder
                        disk_groups[parent_name] = {
                            'disk': None,
                            'partitions': []
                        }
                disk_groups[parent_name]['partitions'].append(partition)
        
        # Build ordered options dict with visual hierarchy
        disk_options = {}
        
        for parent_name in sorted(disk_groups.keys()):
            group = disk_groups[parent_name]
            parent_disk = group['disk']
            partitions = group['partitions']
            
            # Add parent disk first (if it should be shown for partitioning)
            if parent_disk and parent_name in [d["name"] for d in disks_without_partitions]:
                usage = disk_usage.get(parent_name, 0)
                label = f"💾 {parent_disk['name']} ({parent_disk.get('size', '?')}) - {usage:.0f}% utilisé - CRÉER PARTITIONS"
                disk_options[f"NOPART:{parent_disk['device']}"] = label
            
            # Add partitions (indented with └─)
            for partition in sorted(partitions, key=lambda x: x['name']):
                indent = "  └─ "
                label = f"{indent}{partition['name']} ({partition.get('size', '?')}) - {partition.get('fstype', 'inconnu')}"
                if partition.get('label'):
                    label += f" [{partition['label']}]"
                disk_options[partition['device']] = label
        
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
                "info": f"{len(mountable_items)} partition(s) disponible(s) pour montage. {len(disks_without_partitions)} disque(s) sans partition valide (nécessite création de partition)."
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

    async def async_step_create_partition(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create partitions on a disk."""
        disk_device = self.context.get("disk_to_partition")
        
        if user_input is not None:
            num_partitions = user_input.get("num_partitions", 1)
            
            # Store number of partitions and go to partition details
            self.context["num_partitions"] = num_partitions
            self.context["partition_configs"] = []
            self.context["current_partition"] = 1
            
            return await self.async_step_partition_details()
        
        return self.async_show_form(
            step_id="create_partition",
            data_schema=vol.Schema(
                {
                    vol.Required("num_partitions", default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=4)
                    ),
                }
            ),
            description_placeholders={
                "info": f"Le disque {disk_device} n'a pas de partition valide. Combien de partitions souhaitez-vous créer ? (1-4)"
            },
        )

    async def async_step_partition_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure partition details."""
        current = self.context["current_partition"]
        total = self.context["num_partitions"]
        
        if user_input is not None:
            # Store partition config
            self.context["partition_configs"].append({
                "name": user_input.get("name", f"partition{current}"),
                "size": user_input.get("size", "100%"),
                "fstype": user_input.get("fstype", "ext4"),
            })
            
            # Check if we need more partitions
            if current < total:
                self.context["current_partition"] = current + 1
                return await self.async_step_partition_details()
            else:
                # All partitions configured, create them
                return await self.async_step_confirm_partition_creation()
        
        # Calculate default size
        if current == total:
            default_size = "100%"  # Last partition takes remaining space
        else:
            default_size = f"{100 // total}%"
        
        return self.async_show_form(
            step_id="partition_details",
            data_schema=vol.Schema(
                {
                    vol.Optional("name", default=f"partition{current}"): cv.string,
                    vol.Optional("size", default=default_size): cv.string,
                    vol.Required("fstype", default="ext4"): vol.In(
                        ["ext4", "ntfs", "vfat", "exfat"]
                    ),
                }
            ),
            description_placeholders={
                "info": f"Configuration de la partition {current}/{total}. Taille peut être en GB (ex: 50G) ou en % (ex: 50% ou 100% pour tout l'espace restant)."
            },
        )

    async def async_step_confirm_partition_creation(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm partition creation."""
        if user_input is not None:
            disk_device = self.context.get("disk_to_partition")
            partition_configs = self.context.get("partition_configs", [])
            
            # Create partitions via service
            await self.hass.services.async_call(
                DOMAIN,
                "create_partitions",
                {
                    "device": disk_device,
                    "partitions": partition_configs,
                },
                blocking=True,
            )
            
            return self.async_create_entry(
                title="",
                data={},
                description="Partitions créées avec succès. Vous pouvez maintenant monter les nouvelles partitions."
            )
        
        # Show summary
        partition_configs = self.context.get("partition_configs", [])
        disk_device = self.context.get("disk_to_partition")
        
        summary = f"Disque: {disk_device}\n\nPartitions à créer:\n"
        for i, config in enumerate(partition_configs, 1):
            summary += f"\n{i}. {config['name']} - {config['size']} - {config['fstype']}"
        
        return self.async_show_form(
            step_id="confirm_partition_creation",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": f"{summary}\n\n⚠️ ATTENTION: Cette opération effacera toutes les données du disque! Confirmez pour continuer."
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
