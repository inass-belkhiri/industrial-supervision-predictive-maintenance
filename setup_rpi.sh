#!/bin/bash
set -e  # Arreter en cas d'erreur

# ── Couleurs pour les messages ────────────────────────────────────────────────

ok()   { echo "[OK]    $1"; }
info() { echo "[INFO]  $1"; }
warn() { echo "[WARN]  $1"; }
err()  { echo "[ERREUR] $1"; exit 1; }
step() { echo "\n========== $1 =========="; }

# ── Variables a configurer AVANT de lancer ce script ─────────────────────────
STATIC_IP="192.168.0.152"        # IP statique souhaitee pour le Pi
GATEWAY="192.168.0.1"           # Adresse de votre routeur/box
INFLUX_USERNAME="admin"
INFLUX_PASSWORD="monitorTEMP26"
INFLUX_ORG="temperature-monitoring"
INFLUX_BUCKET="sensors"
PROJECT_DIR="/home/pi/industrial-supervision-predictive-maintenance"

echo ""
echo "============================================================"
echo "  Supervision Thermique Industrielle -- Setup Raspberry Pi"
echo "  ENSA Kenitra -- Yazaki -- 2025-2026"
echo "============================================================"
echo ""

info "IP statique cible     : $STATIC_IP"
info "Gateway               : $GATEWAY"
info "Repertoire projet     : $PROJECT_DIR"
echo ""
read -p "Ces valeurs sont-elles correctes ? (o/n) : " confirm
if [[ "$confirm" != "o" && "$confirm" != "O" ]]; then
  warn "Modifier les variables en haut du script puis relancer."
  exit 0
fi

# =============================================================================
# PHASE 1 -- Mise a jour du systeme
# =============================================================================
step "PHASE 1 -- Mise a jour du systeme"

sudo apt update
sudo apt upgrade -y
ok "Systeme mis a jour"

sudo apt install -y \
  python3 python3-pip python3-venv python3-dev \
  git curl wget build-essential \
  openbox x11-xserver-utils xserver-xorg xinit \
  htop nano
ok "Paquets de base installes"

# Installer Chromium -- le nom du paquet a change selon la version de Raspberry Pi OS
# Debian Trixie (actuel) : chromium
# Debian Bookworm et avant : chromium-browser
info "Installation de Chromium..."
if apt-cache show chromium > /dev/null 2>&1; then
  sudo apt install -y chromium
  CHROMIUM_BIN="chromium"
  ok "Chromium installe (paquet: chromium)"
elif apt-cache show chromium-browser > /dev/null 2>&1; then
  sudo apt install -y chromium-browser
  CHROMIUM_BIN="chromium-browser"
  ok "Chromium installe (paquet: chromium-browser)"
else
  warn "Chromium non trouve -- installer manuellement : sudo apt install chromium"
  CHROMIUM_BIN="chromium"
fi


# =============================================================================
# PHASE 2 -- Configuration systeme (serie, GPIO, reseau)
# =============================================================================
step "PHASE 2 -- Configuration systeme"

# ── Activer le port serie (RS485 MODBUS) ──────────────────────────────────────
info "Activation du port serie..."
if ! grep -q "enable_uart=1" /boot/firmware/config.txt 2>/dev/null; then
  echo "" | sudo tee -a /boot/firmware/config.txt > /dev/null
  echo "# Supervision Thermique -- configuration serie et GPIO" | sudo tee -a /boot/firmware/config.txt > /dev/null
  echo "enable_uart=1" | sudo tee -a /boot/firmware/config.txt > /dev/null
  ok "enable_uart=1 ajoute a config.txt"
else
  ok "enable_uart=1 deja present"
fi

# ── Desactiver le Bluetooth pour liberer l'UART ───────────────────────────────
if ! grep -q "dtoverlay=disable-bt" /boot/firmware/config.txt 2>/dev/null; then
  echo "dtoverlay=disable-bt" | sudo tee -a /boot/firmware/config.txt > /dev/null
  ok "Bluetooth desactive (UART libere pour RS485)"
else
  ok "Bluetooth deja desactive"
fi

# ── PWM pour la bande LED WS2812B ─────────────────────────────────────────────
if ! grep -q "dtoverlay=pwm" /boot/firmware/config.txt 2>/dev/null; then
  echo "dtoverlay=pwm,pin=18,func=2" | sudo tee -a /boot/firmware/config.txt > /dev/null
  ok "PWM GPIO18 configure pour la bande LED"
else
  ok "PWM GPIO18 deja configure"
fi

# ── Desactiver le service hciuart ─────────────────────────────────────────────
sudo systemctl disable hciuart 2>/dev/null || true
sudo systemctl stop hciuart 2>/dev/null || true
ok "Service hciuart desactive"

# ── Desactiver le login shell serie (garder le hardware actif) ────────────────
if grep -q "console=serial0" /boot/firmware/cmdline.txt 2>/dev/null; then
  sudo sed -i 's/console=serial0,[0-9]* //' /boot/firmware/cmdline.txt
  ok "Login shell serie desactive (port disponible pour MODBUS)"
fi

# ── Groupes utilisateur ───────────────────────────────────────────────────────
info "Configuration des groupes utilisateur..."
sudo usermod -a -G dialout pi   # Port serie RS485
sudo usermod -a -G gpio pi      # GPIO LEDs
sudo usermod -a -G spi pi       # SPI
ok "pi ajoute aux groupes : dialout gpio spi"

# ── Regles udev pour GPIO ─────────────────────────────────────────────────────
cat << 'EOF' | sudo tee /etc/udev/rules.d/99-gpio.rules > /dev/null
SUBSYSTEM=="bcm2835-gpiomem", GROUP="gpio", MODE="0660"
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
ok "Regles udev GPIO configurees"

# ── IP statique ───────────────────────────────────────────────────────────────
info "Configuration de l'IP statique $STATIC_IP..."
if ! grep -q "$STATIC_IP" /etc/dhcpcd.conf 2>/dev/null; then
  cat << EOF | sudo tee -a /etc/dhcpcd.conf > /dev/null

# Supervision Thermique -- IP statique
interface eth0
static ip_address=${STATIC_IP}/24
static routers=${GATEWAY}
static domain_name_servers=8.8.8.8 8.8.4.4
EOF
  ok "IP statique $STATIC_IP configuree"
else
  ok "IP statique deja configuree"
fi


# =============================================================================
# PHASE 3 -- InfluxDB
# =============================================================================
step "PHASE 3 -- Installation InfluxDB"

if systemctl is-active --quiet influxdb 2>/dev/null; then
  ok "InfluxDB deja installe et actif -- etape ignoree"
else
  info "Ajout du depot InfluxData..."
  wget -q https://repos.influxdata.com/influxdata-archive_compat.key
  echo '393e8779c89ac8d958f81f942f9ad7fb82a25e133faddaf92e15b16e6ac9ce4c influxdata-archive_compat.key' | sha256sum -c
  cat influxdata-archive_compat.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
  echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list
  rm -f influxdata-archive_compat.key

  sudo apt update
  sudo apt install influxdb2 -y
  sudo systemctl enable influxdb
  sudo systemctl start influxdb
  sleep 3
  ok "InfluxDB installe et demarre"

  info "Configuration initiale d'InfluxDB..."
  influx setup \
    --username  "$INFLUX_USERNAME" \
    --password  "$INFLUX_PASSWORD" \
    --org       "$INFLUX_ORG" \
    --bucket    "$INFLUX_BUCKET" \
    --retention 720h \
    --force
  ok "InfluxDB configure : org=$INFLUX_ORG bucket=$INFLUX_BUCKET"
fi

# Recuperer et afficher le token
info "Recuperation du token admin InfluxDB..."
INFLUX_TOKEN=$(influx auth list --json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data:
    if item.get('description') == 'admin\\'s Token':
        print(item['token'])
        break
" 2>/dev/null || echo "")

if [ -n "$INFLUX_TOKEN" ]; then
  ok "Token InfluxDB recupere"
  echo ""
  echo "IMPORTANT -- Copiez ce token dans backend/config.py :"
  echo "INFLUX_TOKEN = '$INFLUX_TOKEN'"
  echo ""
  # Ecrire le token dans un fichier temporaire
  echo "$INFLUX_TOKEN" > /tmp/influx_token.txt
else
  warn "Token non recupere automatiquement. Lancer manuellement : influx auth list --json"
fi


# =============================================================================
# PHASE 4 -- Node.js 20
# =============================================================================
step "PHASE 4 -- Installation Node.js 20"

if command -v node &>/dev/null && node --version | grep -q "v20"; then
  ok "Node.js 20 deja installe : $(node --version)"
else
  info "Installation de Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install nodejs -y
  ok "Node.js installe : $(node --version)"
fi


# =============================================================================
# PHASE 5 -- Environnement Python + dependances projet
# =============================================================================
step "PHASE 5 -- Installation des dependances Python"

if [ ! -d "$PROJECT_DIR" ]; then
  err "Dossier projet non trouve : $PROJECT_DIR\nCopier le dossier supervision_thermique dans /home/pi/ avant de lancer ce script."
fi

cd "$PROJECT_DIR/backend"

if [ ! -d "venv" ]; then
  info "Creation de l'environnement virtuel Python..."
  python3 -m venv venv
  ok "Environnement virtuel cree"
fi

info "Installation des dependances Python..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "Dependances Python installees"
deactivate

info "Installation des dependances npm (frontend)..."
cd "$PROJECT_DIR/frontend"
npm install --silent
npm run build --silent
ok "Frontend compile"


# =============================================================================
# PHASE 6 -- Mise a jour de config.py avec le token InfluxDB
# =============================================================================
step "PHASE 6 -- Mise a jour de config.py"

CONFIG_FILE="$PROJECT_DIR/backend/config.py"

if [ -f /tmp/influx_token.txt ]; then
  TOKEN=$(cat /tmp/influx_token.txt)
  if [ -n "$TOKEN" ]; then
    sed -i "s|INFLUX_TOKEN  = '.*'|INFLUX_TOKEN  = '$TOKEN'|" "$CONFIG_FILE"
    ok "Token InfluxDB mis a jour dans config.py"
    rm -f /tmp/influx_token.txt
  fi
fi

ok "Verifier les autres parametres dans : $CONFIG_FILE"
info "Notamment : MODBUS_PORT, SENSOR_MAP, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"


# =============================================================================
# PHASE 7 -- Services systemd
# =============================================================================
step "PHASE 7 -- Configuration des services systemd"

# ── Service backend ───────────────────────────────────────────────────────────
cat << EOF | sudo tee /etc/systemd/system/supervision-backend.service > /dev/null
[Unit]
Description=Supervision Thermique -- Backend FastAPI
After=network.target influxdb.service
Requires=influxdb.service

[Service]
User=pi
WorkingDirectory=${PROJECT_DIR}/backend
Environment=PATH=${PROJECT_DIR}/backend/venv/bin
ExecStart=${PROJECT_DIR}/backend/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
ok "Service supervision-backend cree"

# ── Service frontend ──────────────────────────────────────────────────────────
cat << EOF | sudo tee /etc/systemd/system/supervision-frontend.service > /dev/null
[Unit]
Description=Supervision Thermique -- Frontend React Vite
After=network.target

[Service]
User=pi
WorkingDirectory=${PROJECT_DIR}/frontend
ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 5173
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
ok "Service supervision-frontend cree"

# ── Activer et demarrer les services ─────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable supervision-backend supervision-frontend
sudo systemctl start supervision-backend supervision-frontend
sleep 3
ok "Services demarres"


# =============================================================================
# PHASE 8 -- Lancement automatique de Chromium (kiosk)
# =============================================================================
step "PHASE 8 -- Configuration Chromium kiosk"

mkdir -p /home/pi/.config/openbox

cat << 'EOF' > /home/pi/.config/openbox/autostart
# Desactiver economiseur d'ecran
xset s off
xset s noblank
xset -dpms

# Lancer Chromium en kiosk (attendre que le frontend soit pret)
sleep 6 && ${CHROMIUM_BIN:-chromium} \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  http://localhost:5173 &
EOF
ok "Configuration Chromium kiosk creee"

# Autologin + startx automatique
if ! grep -q "startx" /home/pi/.bash_profile 2>/dev/null; then
  cat << 'EOF' >> /home/pi/.bash_profile

# Supervision Thermique -- lancer X11 automatiquement sur tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    startx
fi
EOF
  ok ".bash_profile configure pour startx automatique"
fi

# Configurer autologin via raspi-config (non-interactif)
sudo raspi-config nonint do_boot_behaviour B2
ok "Autologin console configure"


# =============================================================================
# PHASE 9 -- Sauvegardes automatiques (cron)
# =============================================================================
step "PHASE 9 -- Configuration des sauvegardes cron"

mkdir -p /home/pi/backups

# Ajouter les jobs cron si pas deja presents
CRON_CONTENT=$(crontab -l 2>/dev/null || echo "")

if ! echo "$CRON_CONTENT" | grep -q "influx backup"; then
  (echo "$CRON_CONTENT"; cat << 'CRON'

# Supervision Thermique -- Sauvegardes automatiques
# InfluxDB : tous les jours a 2h30
30 2 * * * influx backup /home/pi/backups/influx-$(date +\%Y\%m\%d) 2>> /var/log/supervision-backup.log

# Purger sauvegardes > 30 jours
0 3 * * * find /home/pi/backups -name 'influx-*' -mtime +30 -exec rm -rf {} \; 2>/dev/null

# Config + modeles ML : tous les dimanches a 4h
0 4 * * 0 tar -czf /home/pi/backups/config-$(date +\%Y\%m\%d).tar.gz /home/pi/supervision_thermique/backend/config.py /home/pi/supervision_thermique/backend/models/ 2>/dev/null

CRON
) | crontab -
  ok "Cron jobs de sauvegarde configures"
else
  ok "Cron jobs deja presents"
fi


# =============================================================================
# PHASE 10 -- Verification finale
# =============================================================================
step "PHASE 10 -- Verification"

echo ""
echo "Services :"
for svc in influxdb supervision-backend supervision-frontend; do
  if systemctl is-active --quiet "$svc"; then
    ok "$svc est actif"
  else
    warn "$svc n'est pas actif -- verifier : sudo systemctl status $svc"
  fi
done

echo ""
echo "Port serie :"
if [ -e /dev/ttyUSB0 ]; then
  ok "/dev/ttyUSB0 detecte (convertisseur RS485 connecte)"
else
  warn "/dev/ttyUSB0 non trouve -- connecter le convertisseur USB-RS485"
fi

echo ""
echo "Acces reseau :"
sleep 2
if curl -s --max-time 3 http://localhost:8000 > /dev/null 2>&1; then
  ok "Backend accessible sur http://localhost:8000"
else
  warn "Backend non accessible encore -- attendre 10 secondes et reessayer"
fi

if curl -s --max-time 3 http://localhost:5173 > /dev/null 2>&1; then
  ok "Frontend accessible sur http://localhost:5173"
else
  warn "Frontend non accessible encore -- attendre 10 secondes et reessayer"
fi
