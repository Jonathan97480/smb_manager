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
                    
                    # Get disk info to check if it has existing partitions
                    disks = await self.hass.async_add_executor_job(disk_manager.detect_disks)
                    disk_name = actual_device.split('/')[-1]
                    
                    # Check for existing partitions
                    existing_partitions = [d for d in disks if d.get("parent") == disk_name]
                    
                    if existing_partitions:
                        # Disk has partitions - show warning
                        self.context["disk_to_partition"] = actual_device
                        self.context["existing_partitions"] = existing_partitions
                        return await self.async_step_partition_warning()
                    else:
                        # No partitions - go directly to creation
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
        disk_has_valid_partitions = {}  # {disk_name: has_at_least_one_valid_partition}
        
        for disk in disks:
            if not disk.get("parent"):  # It's a parent disk
                disk_size_bytes = parse_size_to_bytes(disk.get("size", "0"))
                
                if disk_size_bytes == 0:
                    disk_usage[disk["name"]] = 100  # Unknown size = treat as full
                    disk_has_valid_partitions[disk["name"]] = False
                    continue
                
                # Calculate total size of ALL partitions
                used_bytes = 0
                has_any_partition = False
                has_valid_partition = False
                
                for child in disks:
                    if child.get("parent") == disk["name"]:
                        has_any_partition = True
                        child_size = parse_size_to_bytes(child.get("size", "0"))
                        used_bytes += child_size
                        
                        # Check if at least one partition has a valid filesystem
                        if child.get("fstype"):
                            has_valid_partition = True
                
                # Calculate usage percentage
                usage_percent = (used_bytes / disk_size_bytes * 100) if disk_size_bytes > 0 else 0
                disk_usage[disk["name"]] = usage_percent if has_any_partition else 0
                disk_has_valid_partitions[disk["name"]] = has_valid_partition
        
        # Second pass: Separate partitions and parent disks
        mountable_items = []
        disks_without_partitions = []
        
        for disk in disks:
            # Skip mounted items
            if disk.get("mounted"):
                continue
            
            # If it's a partition (has parent)
            if disk.get("parent"):
                # Add partition if it has valid filesystem
                # (regardless of parent usage - if partition is valid, allow mounting)
                if disk.get("fstype"):
                    mountable_items.append(disk)
            else:
                # It's a parent disk
                usage_percent = disk_usage.get(disk["name"], 100)
                has_valid_partitions = disk_has_valid_partitions.get(disk["name"], False)
                
                # Show parent disk if:
                # 1. < 90% used OR
                # 2. >= 90% used BUT has NO valid partitions (need reformatting)
                if usage_percent < 90 or not has_valid_partitions:
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

    async def async_step_partition_warning(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Warn user about existing partitions before creating new ones."""
        disk_device = self.context.get("disk_to_partition")
        existing_partitions = self.context.get("existing_partitions", [])
        
        if user_input is not None:
            action = user_input.get("action")
            
            if action == "create_new":
                # Before proceeding, check if any partitions are mounted or shared
                from .smb_manager import SmbManager
                smb_manager = SmbManager(self.hass)
                
                mounted_partitions = []
                shared_partitions = []
                
                # Check each partition
                for partition in existing_partitions:
                    # Check if mounted
                    if partition.get("mounted"):
                        mounted_partitions.append(partition)
                    
                    # Check if shared via SMB
                    if partition.get("mountpoint"):
                        shares = await self.hass.async_add_executor_job(smb_manager.list_shares)
                        for share in shares:
                            if share.get("path", "").startswith(partition["mountpoint"]):
                                shared_partitions.append({
                                    "partition": partition,
                                    "share": share
                                })
                
                # If there are mounted or shared partitions, show cleanup step
                if mounted_partitions or shared_partitions:
                    self.context["mounted_partitions"] = mounted_partitions
                    self.context["shared_partitions"] = shared_partitions
                    return await self.async_step_cleanup_before_partition()
                else:
                    # No mounted/shared partitions - proceed to creation
                    return await self.async_step_create_partition()
            else:
                # User cancelled - go back to mount selection
                return await self.async_step_mount_disk()
        
        # Build partition list for display
        partition_list = "\n".join([
            f"  • {p['name']} ({p.get('size', '?')}) - {p.get('fstype', 'non formaté')}" + 
            (f" [MONTÉ: {p['mountpoint']}]" if p.get('mounted') else "")
            for p in existing_partitions
        ])
        
        disk_name = disk_device.split('/')[-1]
        
        warning_message = f"""⚠️ ATTENTION - PARTITIONS EXISTANTES DÉTECTÉES ⚠️

Le disque {disk_name} contient {len(existing_partitions)} partition(s) existante(s):
{partition_list}

🔴 SI VOUS CONTINUEZ:
   • Toutes ces partitions seront SUPPRIMÉES
   • Toutes les données seront PERDUES
   • De nouvelles partitions seront créées

✅ SI VOUS VOULEZ MONTER CES PARTITIONS:
   • Cliquez sur "Annuler" ci-dessous
   • Retournez à la liste "Monter un disque"
   • Sélectionnez les partitions individuellement (avec └─)
   • Montez-les une par une SANS perdre de données

Que souhaitez-vous faire?"""
        
        return self.async_show_form(
            step_id="partition_warning",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In({
                        "create_new": "🔴 CONTINUER - Supprimer et créer nouvelles partitions",
                        "cancel": "✅ ANNULER - Retour à la liste pour monter les partitions existantes"
                    }),
                }
            ),
            description_placeholders={
                "info": warning_message
            },
        )

    async def async_step_cleanup_before_partition(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Clean up mounted partitions and shares before creating new partitions."""
        mounted_partitions = self.context.get("mounted_partitions", [])
        shared_partitions = self.context.get("shared_partitions", [])
        
        if user_input is not None:
            if user_input.get("confirm_cleanup"):
                # User confirmed - perform cleanup
                from .disk_manager import DiskManager
                from .smb_manager import SmbManager
                
                disk_manager = DiskManager(self.hass)
                smb_manager = SmbManager(self.hass)
                
                cleanup_errors = []
                
                # First, delete all SMB shares
                for shared_info in shared_partitions:
                    share_name = shared_info["share"].get("name")
                    try:
                        await self.hass.async_add_executor_job(
                            smb_manager.delete_share, share_name
                        )
                    except Exception as e:
                        cleanup_errors.append(f"Erreur suppression partage '{share_name}': {str(e)}")
                
                # Then, unmount all partitions
                for partition in mounted_partitions:
                    mount_point = partition.get("mountpoint")
                    try:
                        await self.hass.async_add_executor_job(
                            disk_manager.unmount_disk, mount_point
                        )
                    except Exception as e:
                        cleanup_errors.append(f"Erreur démontage '{mount_point}': {str(e)}")
                
                if cleanup_errors:
                    # Show errors
                    error_msg = "\n".join(cleanup_errors)
                    return self.async_abort(
                        reason="cleanup_failed",
                        description_placeholders={"error": error_msg}
                    )
                
                # Cleanup successful - proceed to partition creation
                return await self.async_step_create_partition()
            else:
                # User cancelled - go back
                return await self.async_step_mount_disk()
        
        # Build list of actions to perform
        actions_list = []
        
        if shared_partitions:
            actions_list.append(f"\n📤 PARTAGES SMB À SUPPRIMER ({len(shared_partitions)}):")
            for shared_info in shared_partitions:
                share = shared_info["share"]
                partition = shared_info["partition"]
                actions_list.append(f"   • Partage '{share.get('name')}' → {partition['name']}")
        
        if mounted_partitions:
            actions_list.append(f"\n💾 PARTITIONS À DÉMONTER ({len(mounted_partitions)}):")
            for partition in mounted_partitions:
                actions_list.append(f"   • {partition['name']} monté sur {partition['mountpoint']}")
        
        actions_text = "\n".join(actions_list)
        
        cleanup_message = f"""🔧 NETTOYAGE REQUIS AVANT CRÉATION DE PARTITIONS

Pour créer de nouvelles partitions, nous devons d'abord:
{actions_text}

⚠️ CETTE OPÉRATION VA:
1. Arrêter tous les partages SMB sur ce disque
2. Démonter toutes les partitions montées
3. Puis créer les nouvelles partitions (perte de données)

✅ Les fichiers actuellement sur ces partitions seront PERDUS!

Voulez-vous continuer avec le nettoyage et la création?"""
        
        return self.async_show_form(
            step_id="cleanup_before_partition",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm_cleanup", default=False): bool,
                }
            ),
            description_placeholders={
                "info": cleanup_message
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
            
            # Build partition list for success message
            disk_name = disk_device.split('/')[-1]
            partition_list = "\n".join([
                f"  └─ {disk_name}{i+1} - {p['fstype']} [{p['name']}]"
                for i, p in enumerate(partition_configs)
            ])
            
            success_message = f"""✅ Partitions créées avec succès!

Disque: {disk_device}
Partitions créées:
{partition_list}

📋 PROCHAINES ÉTAPES:
1. Retournez au menu principal
2. Sélectionnez "Monter un disque"
3. Vous verrez les nouvelles partitions avec └─ 
4. Sélectionnez chaque partition à monter individuellement

⚠️ Les partitions sont créées et formatées mais PAS encore montées.
Vous devez les monter pour pouvoir les utiliser."""
            
            return self.async_abort(
                reason="partitions_created_success",
                description_placeholders={"info": success_message}
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
