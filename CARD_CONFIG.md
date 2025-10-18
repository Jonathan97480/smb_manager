# Configuration de la Carte d'Affichage des Disques

## 🎨 Carte Markdown - Affichage Complet des Disques

Copiez ce code YAML et ajoutez-le comme **Carte Markdown** dans votre tableau de bord Home Assistant :

```yaml
type: markdown
title: 💾 Disques et Partages SMB
content: |
  ## 🖥️ Serveur: {{ state_attr('sensor.smb_shares', 'server_ip') }}
  
  {% set disks = state_attr('sensor.disks_and_mounts', 'disks') %}
  {% if disks %}
  
  ### 📊 Statistiques
  - **Total disques**: {{ state_attr('sensor.disks_and_mounts', 'total_disks') }}
  - **Disques montés**: {{ state_attr('sensor.disks_and_mounts', 'mounted_disks') }}
  - **Montages permanents**: {{ state_attr('sensor.disks_and_mounts', 'permanent_mounts') }}
  - **Disques partagés**: {{ state_attr('sensor.disks_and_mounts', 'shared_disks') }}
  
  ---
  
  {% for disk in disks %}
  ### {% if disk.mounted %}✅{% else %}❌{% endif %} {{ disk.name }} - {{ disk.size }}
  
  **Périphérique**: `{{ disk.device }}`  
  **Type**: {{ disk.filesystem if disk.filesystem else 'Inconnu' }}  
  **Label**: {{ disk.label if disk.label else 'Sans nom' }}
  
  {% if disk.mounted %}
  📁 **Monté sur**: `{{ disk.mount_point }}`  
  {% if disk.permanent %}🔒 **Permanent** (auto-monté au démarrage){% else %}⚠️ **Temporaire** (non persistant){% endif %}
  {% else %}
  ⚠️ **Non monté**
  {% endif %}
  
  {% if disk.shared_via_smb %}
  🌐 **Partages SMB**:
  {% for share in disk.shares %}
  - 📂 **{{ share.name }}**
    - Chemin réseau: `{{ share.network_path }}`
    - Type: {% if share.writable %}✍️ Lecture/Écriture{% else %}👁️ Lecture seule{% endif %}
  {% endfor %}
  {% else %}
  ℹ️ Pas de partage SMB
  {% endif %}
  
  ---
  {% endfor %}
  
  {% else %}
  ⚠️ Aucun disque détecté
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

## 📋 Instructions d'Installation

1. Allez dans Home Assistant
2. Cliquez sur votre **Tableau de bord**
3. Cliquez sur les **3 points** en haut à droite → **Modifier le tableau de bord**
4. Cliquez sur **+ AJOUTER UNE CARTE**
5. Cherchez **Markdown** et sélectionnez-le
6. Collez le code YAML ci-dessus
7. Cliquez sur **ENREGISTRER**

---

## 🎯 Alternative: Carte Entities avec Custom Template

Si vous préférez une vue plus compacte, utilisez cette carte **Entities** :

```yaml
type: entities
title: 💾 Disques et Montages
entities:
  - entity: sensor.disks_and_mounts
    type: custom:template-entity-row
    name: "{{ state_attr('sensor.disks_and_mounts', 'total_disks') }} disques"
    secondary: "{{ state_attr('sensor.disks_and_mounts', 'mounted_disks') }} montés | {{ state_attr('sensor.disks_and_mounts', 'shared_disks') }} partagés"
  - type: section
    label: Détails des disques
  - entity: sensor.smb_shares
  - entity: sensor.smb_server_status
state_color: true
```

---

## 🔧 Option Avancée: Carte Multiple avec Tabs

Pour une interface encore plus riche avec onglets (nécessite **card-mod** et **layout-card** de HACS) :

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      ## 💾 Gestion SMB - Serveur {{ state_attr('sensor.smb_shares', 'server_ip') }}
  
  - type: custom:tabbed-card
    tabs:
      - attributes:
          label: Disques
          icon: mdi:harddisk
        card:
          type: markdown
          content: |
            {% set disks = state_attr('sensor.disks_and_mounts', 'disks') %}
            {% for disk in disks %}
            ### {% if disk.mounted %}✅{% else %}❌{% endif %} {{ disk.name }} ({{ disk.size }})
            - **Device**: `{{ disk.device }}`
            - **Type**: {{ disk.filesystem }}
            - **Monté**: {% if disk.mounted %}`{{ disk.mount_point }}`{% else %}Non{% endif %}
            - **Permanent**: {% if disk.permanent %}Oui 🔒{% else %}Non ⚠️{% endif %}
            - **Partagé**: {% if disk.shared_via_smb %}Oui 🌐{% else %}Non{% endif %}
            ---
            {% endfor %}
      
      - attributes:
          label: Partages
          icon: mdi:folder-network
        card:
          type: markdown
          content: |
            {% set shares = state_attr('sensor.smb_shares', 'shares') %}
            ### 📂 {{ states('sensor.smb_shares') }} Partages SMB
            {% for share in shares %}
            - **{{ share.name }}**
              - `{{ share.network_path }}`
              - {% if share.writable %}✍️ R/W{% else %}👁️ RO{% endif %}
            {% endfor %}
      
      - attributes:
          label: Actions
          icon: mdi:cog
        card:
          type: entities
          entities:
            - entity: sensor.smb_server_status
              name: État du serveur
```

---

## 📱 Voir les Attributs Détaillés

En attendant la carte personnalisée, vous pouvez voir tous les détails :

1. Cliquez sur l'entité **Disks and Mounts**
2. Faites défiler jusqu'à **Attributs** ▼
3. Vous verrez la liste complète JSON avec toutes les informations :
   - device, size, filesystem
   - mounted, mount_point
   - permanent (fstab)
   - shared_via_smb
   - shares (avec chemins réseau)

---

## 🎨 Personnalisation des Icônes

Pour des icônes personnalisées selon l'état du disque :

```yaml
type: entities
entities:
  - entity: sensor.disks_and_mounts
    icon: mdi:harddisk-plus
    name: Disques détectés
  - entity: sensor.smb_shares
    icon: mdi:folder-network-outline
    name: Partages SMB
  - entity: sensor.smb_server_status
    icon: mdi:server-network
    name: Serveur SMB
```

---

## 💡 Astuce

Si vous ne voyez pas les informations détaillées :
1. Attendez 60 secondes (délai de mise à jour)
2. Ou redémarrez Home Assistant
3. Les capteurs devraient alors afficher toutes les données
