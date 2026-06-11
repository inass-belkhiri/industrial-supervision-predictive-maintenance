# Fix HDMI — Raspberry Pi : écran 24/24 sans perte de signal

## Cause
Quand l'écran HDMI s'éteint ou se met en veille, le Raspberry Pi désactive la sortie HDMI. Au rallumage, le moniteur ne détecte plus de signal (EDID perdu). Ce guide configure la RPi pour une sortie HDMI **permanente et stable 24/24**.

## Solution — Tout appliquer dans l'ordre

### 1. Forcer la sortie HDMI dans `/boot/config.txt`

```bash
sudo nano /boot/config.txt
```

Ajouter **à la fin du fichier** ces lignes :

```
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
hdmi_drive=2
config_hdmi_boost=4
hdmi_ignore_edid=0xa5000080
disable_overscan=1
```

**Explication :**
- `hdmi_force_hotplug=1` : Force la sortie HDMI même si l'écran est éteint/débranché
- `hdmi_group=2` / `hdmi_mode=82` : 1920×1080 à 60 Hz (adaptez à votre écran)
- `hdmi_drive=2` : Mode HDMI (pas DVI)
- `config_hdmi_boost=4` : Augmente la puissance du signal HDMI
- `hdmi_ignore_edid=0xa5000080` : Ignore les erreurs EDID au réveil de l'écran
- `disable_overscan=1` : Évite les problèmes de surbalayage

**Si 1920×1080 ne marche pas**, essayez :
- `hdmi_mode=16` : 1080p 60 Hz (autre code)
- `hdmi_mode=4` : 720p 60 Hz
- `hdmi_group=1` + `hdmi_mode=4` : 1080p 60 Hz (mode DMT)

### 2. Désactiver le console blanking dans `/boot/cmdline.txt`

```bash
sudo nano /boot/cmdline.txt
```

Ajouter `consoleblank=0` à la fin de la ligne (un seul espace avant).

Exemple :
```
console=serial0,115200 console=tty1 root=PARTUUID=... rootfstype=ext4 fsck.repair=yes rootwait consoleblank=0
```

### 3. Désactiver DPMS et screen blanking au démarrage

**Pour Raspberry Pi OS Desktop (basé sur LXDE) :**

```bash
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

Ajouter ces lignes **avant** `@lxpanel` :
```
@xset s off
@xset -dpms
@xset s noblank
```

Fichier final :
```
@xset s off
@xset -dpms
@xset s noblank
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
```

### 4. Désactiver le blanking de la console (même sans bureau X)

Ajouter dans `/etc/rc.local` (avant `exit 0`) :

```bash
setterm -blank 0 -powerdown 0 -powersave off > /dev/tty1 2>&1 || true
```

### 5. Désactiver le Wi-Fi power saving (optionnel)

```bash
sudo iwconfig wlan0 power off
```

Pour le rendre permanent, ajouter dans `/etc/rc.local` :
```bash
iwconfig wlan0 power off 2>/dev/null || true
```

### 6. Vérifier et redémarrer

```bash
# Vérifier que tout est bien écrit
cat /boot/config.txt | grep -E "hdmi|disable_overscan"
cat /boot/cmdline.txt | grep consoleblank

# Redémarrer
sudo reboot
```

## Vérification après redémarrage

```bash
# Vérifier que l'HDMI est actif
tvservice -s

# Vérifier que le blanking est désactivé
cat /sys/module/kernel/parameters/consoleblank
# Doit afficher "0"
```

## Test 24/24

1. Laissez l'écran allumé normalement
2. Éteignez l'écran (bouton power)
3. Attendez 30 secondes
4. Rallumez l'écran
5. Le signal doit revenir immédiatement

Si le signal ne revient toujours pas, essayez de remplacer `hdmi_mode=82` par `hdmi_mode=16` (cela dépend du modèle exact de votre écran HP).
