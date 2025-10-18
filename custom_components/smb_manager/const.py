"""Constants for SMB Share Manager."""

DOMAIN = "smb_manager"
VERSION = "1.0.0"

# Service names
SERVICE_DETECT_DISKS = "detect_disks"
SERVICE_MOUNT_DISK = "mount_disk"
SERVICE_UNMOUNT_DISK = "unmount_disk"
SERVICE_CREATE_SHARE = "create_share"
SERVICE_DELETE_SHARE = "delete_share"
SERVICE_UPDATE_SHARE = "update_share"
SERVICE_ADD_USER = "add_user"
SERVICE_REMOVE_USER = "remove_user"
SERVICE_RESTART_SAMBA = "restart_samba"
SERVICE_INSTALL_DEPENDENCIES = "install_dependencies"

# Paths
FSTAB_PATH = "/etc/fstab"
SMB_CONF_PATH = "/etc/samba/smb.conf"
MOUNT_BASE_PATH = "/mnt"

# File systems
SUPPORTED_FILESYSTEMS = ["ntfs", "exfat", "ext4", "fat32", "vfat"]

# Default permissions
DEFAULT_CREATE_MASK = "0644"
DEFAULT_DIRECTORY_MASK = "0755"
DEFAULT_UID = "0"
DEFAULT_GID = "0"

# Dependencies
DEPENDENCIES = [
    "samba",
    "samba-common-bin",
    "ntfs-3g",
    "exfat-fuse",
    "exfat-utils"
]
