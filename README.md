# SMB Share Manager for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/Jonathan97480/smb_manager.svg)](https://github.com/Jonathan97480/smb_manager/releases)

Un plugin Home Assistant pour gérer facilement les partages SMB/CIFS sur Raspberry Pi. Détectez, montez et configurez vos disques USB/SSD et créez des partages SMB directement depuis l'interface Home Assistant !

## 📸 Aperçu

Le plugin affiche en temps réel :
- 💾 **Tous vos disques** avec nom, capacité, et espace utilisé
- 🔒 **État de montage** : monté/non monté, permanent/temporaire
- 🌐 **Partages SMB actifs** avec chemins réseau Windows (`\\IP\Partage`)
- 📊 **Statistiques globales** : disques montés, permanents, partagés
- ⚙️ **Interface de configuration** pour gérer disques et partages en un clic

## ✨ Fonctionnalités

### 🎯 Interface Graphique Intégrée
- � **3 Capteurs en temps réel** affichant l'état complet du système
- 💾 **Vue détaillée des disques** : nom, capacité, espace, montage, permanent, partagé
- 🌐 **Chemins réseau automatiques** pour accès Windows (`\\IP\Partage`)
- 🎨 **Cartes personnalisables** pour visualiser vos disques et partages
- ⚙️ **Menu de configuration** intégré pour toutes les actions

### 💾 Gestion des Disques
- �🔍 **Détection automatique** des disques USB/SSD branchés
- � **Montage/démontage** avec support multi-filesystem (NTFS, exFAT, EXT4, FAT32)
- 📌 **Configuration fstab** pour le montage permanent au démarrage
- 🔒 **Indication visuelle** : permanent/temporaire

### 🌐 Gestion des Partages SMB
- ➕ **Création, modification, suppression** de partages
- 📋 **Liste complète** de tous les partages avec chemins réseau
- � **Association automatique** disques ↔ partages
- 🌍 **Accès réseau Windows** prêt à l'emploi

### 👤 Gestion des Utilisateurs
- ➕ **Ajout/suppression** d'utilisateurs Samba
- 🔐 **Gestion des mots de passe** sécurisée

### 🔧 Maintenance
- 🔄 **Redémarrage Samba** en un clic
- � **Installation automatique** des dépendances nécessaires
- 🎯 **Services** utilisables dans les automations

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

### Configuration Initiale

1. Allez dans **Paramètres** → **Appareils et Services**
2. Cliquez sur **+ AJOUTER UNE INTÉGRATION**
3. Recherchez **"SMB Share Manager"**
4. Cliquez dessus et suivez les instructions
5. L'intégration est maintenant configurée !

> **Note** : Pour les versions antérieures, vous pouvez aussi ajouter `smb_manager:` dans `configuration.yaml`

### Interface Graphique

Le plugin ajoute automatiquement **3 capteurs** dans Home Assistant :

- 🖥️ **SMB Server Status** : État du serveur avec IP
- 💾 **Disks and Mounts** : Liste de tous les disques détectés
- 📂 **SMB Shares** : Liste de tous les partages configurés

#### Voir les Options de Configuration

1. Allez dans **Paramètres** → **Appareils et Services**
2. Trouvez la carte **SMB Share Manager**
3. Cliquez sur **CONFIGURER**
4. Vous accéderez à un menu avec toutes les actions :
   - Détecter les disques
   - Monter/Démonter un disque
   - Gérer les partages SMB
   - Gérer les utilisateurs Samba
   - Redémarrer Samba

## 📊 Affichage des Disques et Partages

### Vue Simple : Voir les Détails

Pour voir les informations détaillées de vos disques :

1. Dans votre tableau de bord, cliquez sur **"Disks and Mounts"**
2. Une fenêtre s'ouvre - faites défiler vers le bas
3. Cliquez sur **"Attributs ▼"**
4. Vous verrez toutes les informations :
   - Liste complète des disques
   - Nom, taille, type de système de fichiers
   - Si monté, point de montage
   - Si permanent (dans fstab)
   - Si partagé via SMB avec chemins réseau

### Vue Avancée : Carte Markdown Personnalisée

Pour une visualisation complète et formatée :

1. Cliquez sur l'**icône crayon** ✏️ en haut à droite de votre tableau de bord
2. Cliquez sur **"+ AJOUTER UNE CARTE"** en bas
3. Sélectionnez **"Markdown"**
4. Collez ce code :

```yaml
type: markdown
title: 💾 Disques et Partages SMB
content: |
  ## 🖥️ Serveur: {{ state_attr('sensor.smb_shares', 'server_ip') }}
  
  {% set disks = state_attr('sensor.disks_and_mounts', 'disks') %}
  {% if disks %}
  
  ### 📊 Résumé
  - **Total**: {{ state_attr('sensor.disks_and_mounts', 'total_disks') }} disques
  - **Montés**: {{ state_attr('sensor.disks_and_mounts', 'mounted_disks') }}
  - **Permanents**: {{ state_attr('sensor.disks_and_mounts', 'permanent_mounts') }}
  - **Partagés**: {{ state_attr('sensor.disks_and_mounts', 'shared_disks') }}
  
  ---
  
  {% for disk in disks %}
  ### {% if disk.mounted %}✅{% else %}❌{% endif %} {{ disk.name }} - **{{ disk.size }}**
  
  - **Périphérique**: `{{ disk.device }}`
  - **Type**: {{ disk.filesystem if disk.filesystem else 'Inconnu' }}
  - **Label**: {{ disk.label if disk.label else 'Sans nom' }}
  {% if disk.mounted %}
  - **Monté sur**: `{{ disk.mount_point }}`
  - {% if disk.permanent %}🔒 Permanent (fstab){% else %}⚠️ Temporaire{% endif %}
  {% else %}
  - ⚠️ **Non monté**
  {% endif %}
  
  {% if disk.shared_via_smb %}
  **🌐 Partages SMB**:
  {% for share in disk.shares %}
  - 📂 {{ share.name }}: `{{ share.network_path }}`
  {% endfor %}
  {% endif %}
  
  ---
  {% endfor %}
  
  {% else %}
  ⚠️ Aucun disque détecté - Attendez 60 secondes pour la mise à jour
  {% endif %}
  
  ## 📂 Tous les Partages SMB ({{ states('sensor.smb_shares') }})
  
  {% set shares = state_attr('sensor.smb_shares', 'shares') %}
  {% if shares %}
  {% for share in shares %}
  - 📁 **{{ share.name }}**
    - Local: `{{ share.path }}`
    - Réseau: `{{ share.network_path }}`
    - {% if share.writable %}✍️ Lecture/Écriture{% else %}👁️ Lecture seule{% endif %}
  {% endfor %}
  {% else %}
  ℹ️ Aucun partage configuré
  {% endif %}
```

5. Cliquez sur **ENREGISTRER**
6. Cliquez sur **ENREGISTRER** en haut pour sauvegarder le tableau de bord

#### Ce que vous verrez :

La carte affichera pour chaque disque :
- ✅/❌ État de montage
- 💾 **Nom et capacité** du disque
- 📁 **Point de montage** (si monté)
- 🔒 Si **permanent** (auto-monté au démarrage)
- 🌐 Si **partagé en SMB** avec le chemin réseau complet (ex: `\\192.168.1.22\films`)
- 📊 **Statistiques globales** (total, montés, permanents, partagés)

### Alternative : Carte Entités Simple

Pour une vue plus compacte :

```yaml
type: entities
title: 💾 Disques et Partages
entities:
  - entity: sensor.disks_and_mounts
  - entity: sensor.smb_shares
  - entity: sensor.smb_server_status
state_color: true
```

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

### v1.1.0 (2025-10-18)

- ✨ **Nouvelle interface graphique complète**
- 📊 **3 capteurs en temps réel** (Disks and Mounts, SMB Shares, SMB Server Status)
- 💾 **Affichage détaillé des disques** avec capacité, espace, montage, permanent, partagé
- 🌐 **Chemins réseau automatiques** pour Windows (`\\IP\Partage`)
- ⚙️ **Menu de configuration** intégré dans l'interface
- 🎨 **Cartes Markdown personnalisables** pour visualisation avancée
- 🔗 **Association automatique** disques ↔ partages SMB
- 🔒 **Indication visuelle** du statut (monté, permanent, partagé)

### v1.0.0 (2025-10-18)

- 🎉 Version initiale
- 🔍 Détection des disques
- 💾 Montage/démontage avec gestion fstab
- 🌐 Gestion complète des partages SMB
- 👤 Gestion des utilisateurs Samba
- 📦 Installation des dépendances

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📄 Licence

MIT License - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

Développé par **Jonathan** ([@Jonathan97480](https://github.com/Jonathan97480))

## ⭐ Support

Si ce plugin vous est utile, n'hésitez pas à lui donner une étoile sur GitHub ! ⭐
