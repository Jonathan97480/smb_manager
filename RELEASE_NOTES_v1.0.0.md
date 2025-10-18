# SMB Share Manager v1.0.0

## 🎉 Première Release Officielle

SMB Share Manager est une intégration personnalisée pour Home Assistant qui permet de gérer facilement les partages SMB/Samba, les disques et les utilisateurs directement depuis l'interface Home Assistant.

## ✨ Fonctionnalités

### Gestion des Disques
- **Détection automatique** : Détecte tous les disques connectés (USB, SSD, etc.)
- **Montage/Démontage** : Monte et démonte les disques avec support de différents systèmes de fichiers (NTFS, ext4, FAT32, exFAT)
- **Configuration fstab** : Ajoute automatiquement les entrées dans /etc/fstab pour un montage permanent
- **Installation de dépendances** : Installe automatiquement ntfs-3g et autres outils nécessaires

### Gestion des Partages SMB
- **Création de partages** : Crée facilement des partages SMB avec configuration personnalisée
- **Suppression de partages** : Supprime proprement les partages existants
- **Liste des partages** : Affiche tous les partages configurés
- **Configuration avancée** : Support des options read-only, commentaires, etc.

### Gestion des Utilisateurs Samba
- **Ajout d'utilisateurs** : Crée des utilisateurs Samba avec mot de passe
- **Suppression d'utilisateurs** : Supprime les utilisateurs Samba existants
- **Gestion automatique** : Synchronisation avec les utilisateurs système

### Contrôle des Services
- **Redémarrage Samba** : Redémarre les services smbd et nmbd
- **Logs détaillés** : Tous les événements sont journalisés

## 📦 Installation

### Via HACS (Recommandé)

1. Ouvrez HACS dans Home Assistant
2. Cliquez sur "Integrations"
3. Cliquez sur le menu ⋮ en haut à droite
4. Sélectionnez "Custom repositories"
5. Ajoutez l'URL : `https://github.com/Jonathan97480/smb_manager`
6. Sélectionnez la catégorie "Integration"
7. Cliquez sur "Add"
8. Recherchez "SMB Share Manager"
9. Cliquez sur "Download"
10. Redémarrez Home Assistant

### Installation Manuelle

1. Téléchargez le fichier `smb_manager_v1.0.0.zip`
2. Extrayez le contenu dans le dossier `custom_components` de votre configuration Home Assistant
3. Redémarrez Home Assistant

## ⚙️ Configuration

Ajoutez dans votre `configuration.yaml` :

```yaml
smb_manager: {}
```

Puis redémarrez Home Assistant.

## 🚀 Utilisation

Tous les services sont disponibles dans le menu "Services" de Home Assistant :

### Services Disponibles

- `smb_manager.detect_disks` : Détecte les disques connectés
- `smb_manager.mount_disk` : Monte un disque
- `smb_manager.unmount_disk` : Démonte un disque
- `smb_manager.create_share` : Crée un partage SMB
- `smb_manager.delete_share` : Supprime un partage SMB
- `smb_manager.list_shares` : Liste tous les partages
- `smb_manager.add_user` : Ajoute un utilisateur Samba
- `smb_manager.delete_user` : Supprime un utilisateur Samba
- `smb_manager.restart_samba` : Redémarre les services Samba
- `smb_manager.install_dependencies` : Installe les dépendances nécessaires

### Exemple d'Automatisation

```yaml
automation:
  - alias: "Monter automatiquement une clé USB"
    trigger:
      platform: event
      event_type: smb_manager_disks_detected
    condition:
      - condition: template
        value_template: "{{ '/dev/sda1' in trigger.event.data.disks }}"
    action:
      - service: smb_manager.mount_disk
        data:
          device: "/dev/sda1"
          mount_point: "/mnt/usb_drive"
          fs_type: "ntfs-3g"
```

## 🔧 Configuration Requise

- Home Assistant version 2023.1 ou supérieure
- Accès sudo pour l'utilisateur exécutant Home Assistant
- Samba installé sur le système hôte

## 📝 Notes

- **Permissions** : Cette intégration nécessite des privilèges sudo pour gérer les disques et Samba
- **Sécurité** : Assurez-vous de sécuriser l'accès à Home Assistant car cette intégration peut modifier la configuration système
- **Backup** : Il est recommandé de faire une sauvegarde de votre configuration Samba avant utilisation

## 🐛 Problèmes Connus

- Les logs INFO peuvent ne pas apparaître par défaut dans journalctl (utiliser le niveau DEBUG si nécessaire)

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer de nouvelles fonctionnalités
- Soumettre des pull requests

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👤 Auteur

**Jonathan**
- GitHub: [@Jonathan97480](https://github.com/Jonathan97480)
- Email: jonathanfrt97480@gmail.com

## 🙏 Remerciements

Merci à la communauté Home Assistant pour le support et les ressources !

---

**Note**: Cette intégration n'est pas officiellement testée par Home Assistant. Utilisez-la à vos propres risques.
