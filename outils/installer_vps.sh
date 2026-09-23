#!/usr/bin/env bash
# Installe le serveur de plateau Wrangle sur un VPS Ubuntu ou Debian tout neuf.
#
#   curl -fsSL https://raw.githubusercontent.com/SimonPeudevinDev/Wrangle/main/outils/installer_vps.sh \
#     | sudo bash -s -- plateau.foresight-movie.com "le-mot-de-passe-du-tournage"
#
# Ce que ca pose :
#   - le depot dans /opt/wrangle ; « sudo wrangle-maj » le met a jour et relance
#   - serveur.py en service systemd (redemarre seul), donnees dans /var/lib/wrangle,
#     ecoute seulement en local : c'est Caddy qui repond a internet
#   - Caddy devant, avec le certificat HTTPS automatique du nom donne
#   - le mot de passe du tournage dans /etc/wrangle.env, lisible du service seulement
# Le nom donne doit deja pointer vers l'adresse IP du VPS (entree A dans la zone DNS).
set -euo pipefail

DOMAINE="${1:?nom de domaine attendu, ex. plateau.foresight-movie.com}"
MDP="${2:?mot de passe du tournage attendu}"
DEPOT="https://github.com/SimonPeudevinDev/Wrangle.git"
export DEBIAN_FRONTEND=noninteractive

echo "== Paquets"
apt-get update -q
apt-get install -y -q git python3 curl gnupg debian-keyring debian-archive-keyring apt-transport-https

if ! command -v caddy >/dev/null 2>&1; then
  echo "== Caddy"
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q
  apt-get install -y -q caddy
fi

echo "== Le depot"
if [ -d /opt/wrangle/.git ]; then
  git -C /opt/wrangle pull -q
else
  git clone -q "$DEPOT" /opt/wrangle
fi

echo "== L'utilisateur et les donnees"
id -u wrangle >/dev/null 2>&1 || useradd --system --home /var/lib/wrangle --shell /usr/sbin/nologin wrangle
mkdir -p /var/lib/wrangle
chown -R wrangle:wrangle /var/lib/wrangle

echo "== Le mot de passe"
install -m 600 -o wrangle -g wrangle /dev/null /etc/wrangle.env
printf 'WRANGLE_MOTDEPASSE=%s\n' "$MDP" > /etc/wrangle.env

echo "== Le service"
cat > /etc/systemd/system/wrangle.service <<'UNIT'
[Unit]
Description=Wrangle, serveur de plateau
After=network-online.target
Wants=network-online.target

[Service]
User=wrangle
EnvironmentFile=/etc/wrangle.env
WorkingDirectory=/opt/wrangle
ExecStart=/usr/bin/python3 /opt/wrangle/serveur.py 8765 --adresse 127.0.0.1 --data /var/lib/wrangle
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now wrangle
systemctl restart wrangle

echo "== Caddy devant, en HTTPS"
cat > /etc/caddy/Caddyfile <<CADDY
$DOMAINE {
    encode gzip
    reverse_proxy 127.0.0.1:8765
}
CADDY
systemctl enable --now caddy
systemctl reload caddy

echo "== La mise a jour en une commande"
cat > /usr/local/bin/wrangle-maj <<'MAJ'
#!/usr/bin/env bash
set -e
git -C /opt/wrangle pull
systemctl restart wrangle
echo "Wrangle mis a jour et relance."
MAJ
chmod +x /usr/local/bin/wrangle-maj

sleep 2
if systemctl is-active --quiet wrangle; then
  echo
  echo "Wrangle tourne. Ouvrir : https://$DOMAINE"
  echo "Mettre a jour plus tard : sudo wrangle-maj"
  echo "Le journal par mail : deposer data/mail.json dans /var/lib/wrangle/ (voir LISEZMOI)"
else
  echo "Le service ne demarre pas : journalctl -u wrangle -n 50" >&2
  exit 1
fi
