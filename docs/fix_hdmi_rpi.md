# Fix HDMI — Raspberry Pi : écran "No Signal" après extinction

## Cause
Quand l'écran HDMI s'éteint (standby/mise en veille), le Raspberry Pi désactive la sortie HDMI. Au rallumage de l'écran, le moniteur ne détecte plus de signal.

## Solution

### 1. Forcer la sortie HDMI dans `/boot/config.txt`

```bash
sudo nano /boot/config.txt
```

Ajouter ou décommenter ces lignes :

```
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
hdmi_drive=2
config_hdmi_boost=4
```

**Explication :**
- `hdmi_force_hotplug=1` : Force la sortie HDMI même si l'écran est éteint/débranché
- `hdmi_group=2` : Mode CEA (compatible moniteurs/TV)
- `hdmi_mode=82` : 1920×1080 à 60 Hz (adaptez à votre écran)
- `hdmi_drive=2` : Mode HDMI (pas DVI)
- `config_hdmi_boost=4` : Augmente la puissance du signal HDMI (utile pour longs câbles)

**Résolutions alternatives :**
- `hdmi_mode=16` : 1080p 60 Hz (mode CEA)
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

### 3. Désactiver DPMS (mise en veille écran)

**Pour Raspberry Pi OS Desktop (basé sur LXDE) :**

```bash
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

Ajouter ces lignes :
```
@xset s off
@xset -dpms
@xset s noblank
```

**Alternative (dans le fichier `~/.config/lxsession/LXDE-pi/autostart`) :**

```bash
nano ~/.config/lxsession/LXDE-pi/autostart
```

```
@xset s off
@xset -dpms
@xset s noblank
```

### 4. Redémarrer

```bash
sudo reboot
```

## Vérification

Après redémarrage :
1. Éteignez l'écran (bouton power)
2. Attendez 10 secondes
3. Rallumez l'écran
4. Le signal doit revenir immédiatement
