# SMB Share Manager for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/Jonathan97480/smb_manager.svg)](https://github.com/Jonathan97480/smb_manager/releases)

Un plugin Home Assistant pour gérer facilement les partages SMB/CIFS sur Raspberry Pi. Détectez, montez et configurez vos disques USB/SSD et créez des partages SMB directement depuis l'interface Home Assistant !

## ✨ Fonctionnalités

- 🔍 **Détection automatique** des disques USB/SSD branchés
- 💾 **Montage/démontage** des disques avec support multi-filesystem (NTFS, exFAT, EXT4, FAT32)
- 📌 **Configuration fstab** pour le montage permanent au démarrage
- 🌐 **Gestion complète des partages SMB** (création, modification, suppression)
- 👤 **Gestion des utilisateurs Samba** (ajout, suppression, mot de passe)
- 🔧 **Installation automatique** des dépendances nécessaires
- 🎯 **Interface graphique** intégrée à Home Assistant
- 🔄 **Services** utilisables dans les automations

## 📦 Installation

### Via HACS (Recommandé)

1. Ouvrez HACS dans Home Assistant
2. Cliquez sur "Integrations"
3. Cliquez sur les 3 points en haut à droite et sélectionnez "Custom repositories"
4. Ajoutez l'URL : `https://github.com/Jonathan97480/smb_manager`
5. Catégorie : `Integration`
6. Cliquez sur "Add"
7. Recherchez "SMB Share Manager" et installez-le
8. Redémarrez Home Assistant

### Installation Manuelle

1. Copiez le dossier `custom_components/smb_manager` dans votre dossier `config/custom_components/`
2. Redémarrez Home Assistant

## ⚙️ Configuration

Ajoutez simplement cette ligne dans votre `configuration.yaml` :

```yaml
smb_manager:
```

Redémarrez Home Assistant pour charger le plugin.

## 🚀 Utilisation

### Services Disponibles

Le plugin expose les services suivants :

#### 📂 Gestion des Disques

**`smb_manager.detect_disks`**
- Détecte tous les disques branchés
- Retourne les informations : taille, filesystem, état de montage, UUID, etc.

**`smb_manager.mount_disk`**
- Monte un disque sur un point de montage
- Paramètres :
  - `device` (requis) : Chemin du périphérique (ex: `/dev/sda1`)
  - `mount_point` (optionnel) : Point de montage (auto-généré si non fourni)
  - `filesystem` (optionnel) : Type de filesystem (auto-détecté si non fourni)
  - `permanent` (optionnel) : Ajouter à fstab pour montage automatique

**`smb_manager.unmount_disk`**
- Démonte un disque
- Paramètres :
  - `mount_point` (requis) : Point de montage à démonter
  - `remove_from_fstab` (optionnel) : Supprimer aussi de fstab

#### 🌐 Gestion des Partages SMB

**`smb_manager.create_share`**
- Crée un nouveau partage SMB
- Paramètres :
  - `share_name` (requis) : Nom du partage
  - `path` (requis) : Chemin local à partager
  - `browseable` (optionnel, défaut: true)
  - `writable` (optionnel, défaut: true)
  - `guest_ok` (optionnel, défaut: false)
  - `create_mask` (optionnel, défaut: "0644")
  - `directory_mask` (optionnel, défaut: "0755")
  - `force_user` (optionnel, défaut: "root")
  - `force_group` (optionnel, défaut: "root")

**`smb_manager.delete_share`**
- Supprime un partage SMB existant
- Paramètres :
  - `share_name` (requis) : Nom du partage à supprimer

**`smb_manager.update_share`**
- Met à jour la configuration d'un partage existant
- Paramètres : Mêmes que `create_share` (tous optionnels sauf `share_name`)

#### 👤 Gestion des Utilisateurs

**`smb_manager.add_user`**
- Ajoute un utilisateur Samba
- Paramètres :
  - `username` (requis) : Nom d'utilisateur
  - `password` (requis) : Mot de passe

**`smb_manager.remove_user`**
- Supprime un utilisateur Samba
- Paramètres :
  - `username` (requis) : Nom d'utilisateur à supprimer

#### 🔧 Maintenance

**`smb_manager.restart_samba`**
- Redémarre les services Samba (smbd et nmbd)

**`smb_manager.install_dependencies`**
- Installe les dépendances nécessaires (samba, ntfs-3g, exfat-fuse, etc.)

### Exemples d'utilisation

#### Via l'interface Home Assistant

Allez dans **Outils de développement** → **Services** et sélectionnez un service `smb_manager.*`

#### Via Automation

```yaml
automation:
  - alias: "Auto-mount USB disk"
    trigger:
      - platform: event
        event_type: smb_manager_disks_detected
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.disks | length > 0 }}"
    action:
      - service: smb_manager.mount_disk
        data:
          device: "{{ trigger.event.data.disks[0].device }}"
          permanent: true
```

#### Via Script

```yaml
script:
  create_movie_share:
    sequence:
      - service: smb_manager.create_share
        data:
          share_name: "films"
          path: "/mnt/verbatim/film"
          browseable: true
          writable: true
          guest_ok: false
```

## 🔔 Événements

Le plugin émet des événements que vous pouvez utiliser dans vos automations :

- `smb_manager_disks_detected` : Émis quand des disques sont détectés
- `smb_manager_disk_mounted` : Émis quand un disque est monté
- `smb_manager_disk_unmounted` : Émis quand un disque est démonté
- `smb_manager_share_created` : Émis quand un partage est créé
- `smb_manager_share_updated` : Émis quand un partage est modifié
- `smb_manager_share_deleted` : Émis quand un partage est supprimé
- `smb_manager_user_added` : Émis quand un utilisateur est ajouté
- `smb_manager_user_removed` : Émis quand un utilisateur est supprimé
- `smb_manager_samba_restarted` : Émis quand Samba redémarre
- `smb_manager_dependencies_installed` : Émis quand les dépendances sont installées

## 🛠️ Dépendances

Le plugin nécessite les paquets suivants (installés automatiquement via le service `install_dependencies`) :

- `samba` et `samba-common-bin`
- `ntfs-3g` (support NTFS)
- `exfat-fuse` et `exfat-utils` (support exFAT)

## ⚠️ Prérequis

- Home Assistant OS ou Supervised sur Raspberry Pi
- Accès sudo (normalement disponible sur Home Assistant OS)
- Droits root pour monter des disques et configurer Samba

## 🐛 Problèmes connus

- Le plugin nécessite les privilèges root pour fonctionner
- Testez les services manuellement avant de les utiliser dans des automations critiques
- Sauvegardez toujours `/etc/fstab` et `/etc/samba/smb.conf` avant des modifications importantes

## 📝 Changelog

### v1.0.0 (2025-10-18)

- Version initiale
- Détection des disques
- Montage/démontage avec gestion fstab
- Gestion complète des partages SMB
- Gestion des utilisateurs Samba
- Installation des dépendances

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📄 Licence

MIT License - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

Développé par **Jonathan** ([@Jonathan97480](https://github.com/Jonathan97480))

## ⭐ Support

Si ce plugin vous est utile, n'hésitez pas à lui donner une étoile sur GitHub ! ⭐
