# Guide d'Affichage des Disques et Partages SMB

## 📊 Capteurs Disponibles

Après l'installation, vous verrez **3 capteurs** dans Home Assistant :

### 1. **SMB Shares** (Partages SMB)
- **État** : Nombre total de partages SMB configurés
- **Attributs** :
  - Liste de tous les partages avec :
    - Nom du partage
    - Chemin local
    - Chemin réseau (`\\IP\NomPartage`)
    - Lecture seule ou Écriture
  - IP du serveur

### 2. **Disks and Mounts** (Disques et Montages)
- **État** : Nombre total de disques détectés
- **Attributs** :
  - Pour chaque disque :
    - **device** : Périphérique (`/dev/sda1`)
    - **name** : Nom court (`sda1`)
    - **size** : Taille du disque
    - **filesystem** : Type de système de fichiers (NTFS, ext4, etc.)
    - **mounted** : `true` si monté, `false` sinon
    - **mount_point** : Point de montage ou "Not mounted"
    - **permanent** : `true` si dans `/etc/fstab` (montage permanent)
    - **shared_via_smb** : `true` si partagé via SMB
    - **shares** : Liste des partages SMB sur ce disque
  - Statistiques globales :
    - **total_disks** : Nombre total de disques
    - **mounted_disks** : Nombre de disques montés
    - **permanent_mounts** : Nombre de montages permanents
    - **shared_disks** : Nombre de disques partagés en SMB

### 3. **SMB Server Status** (État du Serveur)
- **État** : "online"
- **Attributs** :
  - IP du serveur
  - Nombre total de partages
  - Nombre total de disques
  - Nombre de disques montés
  - Nombre de disques partagés

## 🎨 Affichage dans l'Interface Home Assistant

### Option 1 : Vue Simple (Entités)

1. Allez dans **Paramètres** → **Tableaux de bord**
2. Cliquez sur votre tableau de bord
3. **+ AJOUTER UNE CARTE** → **Entités**
4. Ajoutez les 3 capteurs :
   - `sensor.smb_shares`
   - `sensor.disks_and_mounts`
   - `sensor.smb_server_status`

### Option 2 : Carte Markdown Détaillée

Ajoutez une **Carte Markdown** avec ce code pour voir tous les détails :

```yaml
type: markdown
title: 📁 Gestion SMB - Disques et Partages
content: |
  ## 🖥️ Serveur SMB
  **IP**: {{ state_attr('sensor.smb_shares', 'server_ip') }}
  
  ---
  
  ## 💾 Disques Détectés ({{ states('sensor.disks_and_mounts') }})
  
  {% for disk in state_attr('sensor.disks_and_mounts', 'disks') %}
  ### 🔹 {{ disk.name }} ({{ disk.size }})
  - **Périphérique**: `{{ disk.device }}`
  - **Système de fichiers**: {{ disk.filesystem }}
  - **Monté**: {% if disk.mounted %}✅ Oui → `{{ disk.mount_point }}`{% else %}❌ Non{% endif %}
  - **Permanent (fstab)**: {% if disk.permanent %}✅ Oui{% else %}❌ Non{% endif %}
  - **Partagé SMB**: {% if disk.shared_via_smb %}✅ Oui{% else %}❌ Non{% endif %}
  {% if disk.shared_via_smb %}
  - **Partages**:
    {% for share in disk.shares %}
    - 📂 **{{ share.name }}** → `{{ share.network_path }}`
    {% endfor %}
  {% endif %}
  
  ---
  {% endfor %}
  
  ## 📂 Partages SMB ({{ states('sensor.smb_shares') }})
  
  {% for share in state_attr('sensor.smb_shares', 'shares') %}
  - **{{ share.name }}**
    - Chemin: `{{ share.path }}`
    - Réseau: `{{ share.network_path }}`
    - Type: {% if share.writable %}✍️ Lecture/Écriture{% else %}👁️ Lecture seule{% endif %}
  {% endfor %}
```

### Option 3 : Carte Auto-Entities (Avancé)

Si vous avez **auto-entities** installé via HACS :

```yaml
type: custom:auto-entities
card:
  type: entities
  title: 📁 SMB Manager - Vue Complète
filter:
  include:
    - entity_id: "sensor.smb_*"
    - entity_id: "sensor.disks_*"
show_empty: false
sort:
  method: name
```

## 🔧 Utilisation

### Voir les Disques Non Montés
Dans l'entité `sensor.disks_and_mounts`, regardez les attributs :
- Si `mounted: false` → le disque n'est pas monté
- Utilisez le service `smb_manager.mount_disk` pour le monter

### Voir les Disques Non Permanents
- Si `permanent: false` → le disque ne sera pas remonté au redémarrage
- Le service `mount_disk` ajoute automatiquement à fstab si vous le configurez

### Accéder aux Partages depuis Windows
Utilisez le chemin réseau affiché dans `network_path` :
```
\\192.168.1.22\NomDuPartage
```

### Voir les Disques Partagés
- `shared_via_smb: true` indique que le disque est partagé
- La liste `shares` montre tous les partages sur ce disque

## 📱 Notification Automatique

Créez une automatisation pour être notifié quand un disque est branché :

```yaml
automation:
  - alias: "Notification nouveau disque"
    trigger:
      - platform: state
        entity_id: sensor.disks_and_mounts
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state|int > trigger.from_state.state|int }}"
    action:
      - service: notify.mobile_app_votre_telephone
        data:
          title: "💾 Nouveau disque détecté"
          message: "Un nouveau disque a été branché sur le système"
```

## 🎯 Exemple de Données

Voici un exemple de ce que vous verrez dans les attributs :

**sensor.disks_and_mounts** :
```json
{
  "disks": [
    {
      "device": "/dev/sda1",
      "name": "sda1",
      "size": "256G",
      "filesystem": "ntfs",
      "mounted": true,
      "mount_point": "/mnt/kingston",
      "permanent": true,
      "shared_via_smb": true,
      "shares": [
        {
          "name": "films",
          "path": "/mnt/kingston/films",
          "network_path": "\\\\192.168.1.22\\films"
        }
      ]
    }
  ],
  "total_disks": 1,
  "mounted_disks": 1,
  "permanent_mounts": 1,
  "shared_disks": 1
}
```
