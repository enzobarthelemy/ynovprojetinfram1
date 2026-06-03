#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log | logger -t user-data) 2>&1

# ============================================================
# CONFIG — à adapter ou passer via variables CDK/SSM
# ============================================================
SECRET_DB="prod/wordpress/db"            # user applicatif WordPress (moindre privilege)
SECRET_DB_ADMIN="prod/wordpress/db-admin" # compte master (admin) pour creer le user app
SECRET_WP="prod/wordpress/app"
# EFS_ID, RDS_HOST, ALB_DNS_NAME, SITE_FQDN exportes en entete par le launch template (tokens CDK)
EFS_ID="${EFS_ID:?EFS_ID manquant}"
RDS_HOST="${RDS_HOST:-}"   # vide sur le secondary cold standby (DB via secret au failover)
ALB_DNS_NAME="${ALB_DNS_NAME:?ALB_DNS_NAME manquant}"
SITE_FQDN="${SITE_FQDN:-$ALB_DNS_NAME}"   # FQDN Route53 (failover), fallback ALB DNS
WP_SITE_URL="http://${SITE_FQDN}"

AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
COMPOSE_DIR="/opt/wordpress"
EFS_MOUNT="/mnt/efs/wordpress"

# ============================================================
# 1. Packages système
# ============================================================
yum update -y
yum install -y docker amazon-efs-utils jq aws-cli mariadb

# docker-compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

systemctl enable --now docker

# ============================================================
# 2. Montage EFS (avant Docker — WordPress écrira directement ici)
# ============================================================
mkdir -p "$EFS_MOUNT"

# Montage via amazon-efs-utils (TLS + retry automatique)
mount -t efs -o tls,_netdev "$EFS_ID":/ "$EFS_MOUNT"

# Persistance au reboot
if ! grep -q "$EFS_ID" /etc/fstab; then
  echo "$EFS_ID:/ $EFS_MOUNT efs _netdev,tls 0 0" >> /etc/fstab
fi

# Droits www-data (UID 33) — uniquement si l'EFS est accessible en ecriture
# (un EFS cible de replication serait read-only : on saute le chown dans ce cas)
if touch "$EFS_MOUNT/.mount_test" 2>/dev/null; then
  rm -f "$EFS_MOUNT/.mount_test"
  echo "EFS en Lecture-Ecriture : application des droits 33:33"
  chown -R 33:33 "$EFS_MOUNT"
  chmod 755 "$EFS_MOUNT"
else
  echo "EFS en Lecture seule : chown saute"
fi

# ============================================================
# 3. Récupération des secrets
# ============================================================
fetch_secret() {
  aws secretsmanager get-secret-value \
    --region "$AWS_REGION" \
    --secret-id "$1" \
    --query SecretString \
    --output text
}

DB_SECRET=$(fetch_secret "$SECRET_DB")
DB_ADMIN_SECRET=$(fetch_secret "$SECRET_DB_ADMIN")
WP_SECRET=$(fetch_secret "$SECRET_WP")

# User applicatif WordPress (moindre privilege)
# DB_HOST : priorite au secret (.host) si renseigne (cas FAILOVER : on repointe vers
# le RDS restaure), sinon fallback sur le token RDS injecte (fonctionnement normal).
DB_HOST=$(echo "$DB_SECRET" | jq -r '.host // empty')
[ -z "$DB_HOST" ] && DB_HOST="$RDS_HOST"
DB_PORT=$(echo "$DB_SECRET"     | jq -r '.port')
DB_NAME=$(echo "$DB_SECRET"     | jq -r '.name')
DB_USER=$(echo "$DB_SECRET"     | jq -r '.username')
DB_PASS=$(echo "$DB_SECRET"     | jq -r '.password')

# Compte master (admin) — sert uniquement a creer le user applicatif
ADMIN_USER=$(echo "$DB_ADMIN_SECRET" | jq -r '.username')
ADMIN_PASS=$(echo "$DB_ADMIN_SECRET" | jq -r '.password')

WP_ADMIN_USER=$(echo "$WP_SECRET"  | jq -r '.admin_user')
WP_ADMIN_PASS=$(echo "$WP_SECRET"  | jq -r '.admin_password')
WP_ADMIN_EMAIL=$(echo "$WP_SECRET" | jq -r '.admin_email')

# ============================================================
# 3b. Creation du user applicatif WordPress (idempotent)
#     SKIP si DB_HOST vide (secondary cold standby : pas de DB tant qu'il n'y a pas de failover)
# ============================================================
if [ -n "$DB_HOST" ]; then
  echo "Attente disponibilite MySQL ($DB_HOST)..."
  for i in $(seq 1 30); do
    if mysqladmin ping -h "$DB_HOST" -P "$DB_PORT" -u "$ADMIN_USER" -p"$ADMIN_PASS" --silent 2>/dev/null; then
      echo "MySQL repond."
      break
    fi
    echo "  pas encore pret (tentative $i/30), attente 10s..."
    sleep 10
  done

  echo "Creation du user applicatif '$DB_USER'..."
  mysql -h "$DB_HOST" -P "$DB_PORT" -u "$ADMIN_USER" -p"$ADMIN_PASS" <<SQL || echo "AVERTISSEMENT: creation user echouee (DB peut-etre non prete)"
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;
CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
SQL
  echo "User applicatif pret."
else
  echo "DB_HOST vide -> COLD STANDBY (pas de DB). Creation user SQL sautee."
fi

# ============================================================
# 4. docker-compose.yml
#    Bind mount EFS → /var/www/html : aucun fichier WP sur l'instance
# ============================================================
mkdir -p "$COMPOSE_DIR"
cat > "$COMPOSE_DIR/docker-compose.yml" << EOF
services:
  wordpress:
    image: wordpress:latest
    restart: always
    ports:
      - "80:80"
    environment:
      WORDPRESS_DB_HOST: "${DB_HOST}:${DB_PORT}"
      WORDPRESS_DB_NAME: "${DB_NAME}"
      WORDPRESS_DB_USER: "${DB_USER}"
      WORDPRESS_DB_PASSWORD: "${DB_PASS}"
      WORDPRESS_TABLE_PREFIX: "wp_"
    volumes:
      # Bind mount EFS — tous les fichiers WP vivent sur EFS, pas sur l'instance
      - ${EFS_MOUNT}:/var/www/html
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  # Service WP-CLI dedie (UID 33 = www-data, respecte les droits EFS)
  wp-cli:
    image: wordpress:cli
    volumes:
      - ${EFS_MOUNT}:/var/www/html
    environment:
      WORDPRESS_DB_HOST: "${DB_HOST}:${DB_PORT}"
      WORDPRESS_DB_NAME: "${DB_NAME}"
      WORDPRESS_DB_USER: "${DB_USER}"
      WORDPRESS_DB_PASSWORD: "${DB_PASS}"
      WP_CLI_CACHE_DIR: "/tmp/.wp-cli-cache"
      HOME: "/tmp"
    user: "33:33"
EOF

chmod 600 "$COMPOSE_DIR/docker-compose.yml"

# ============================================================
# 5. Démarrage
# ============================================================
cd "$COMPOSE_DIR"
docker compose up -d

# ============================================================
# 6. WP-CLI : installation WordPress + WooCommerce (idempotent)
#    SKIP si pas de DB (secondary cold standby) : l'install se fera apres failover.
# ============================================================
if [ -n "$DB_HOST" ]; then
  WP_CLI="docker compose -f $COMPOSE_DIR/docker-compose.yml run --rm wp-cli wp"

  echo "Attente démarrage WordPress..."
  for i in $(seq 1 30); do
    docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T wordpress curl -sf http://localhost > /dev/null 2>&1 && break
    sleep 5
  done

  if ! $WP_CLI core is-installed 2>/dev/null; then
    echo "Installation WordPress..."
    $WP_CLI core install \
      --url="$WP_SITE_URL" \
      --title="My Store" \
      --admin_user="$WP_ADMIN_USER" \
      --admin_password="$WP_ADMIN_PASS" \
      --admin_email="$WP_ADMIN_EMAIL" \
      --skip-email || echo "AVERTISSEMENT: install WP echouee"
  fi

  if ! $WP_CLI plugin is-installed woocommerce 2>/dev/null; then
    echo "Installation WooCommerce..."
    $WP_CLI plugin install woocommerce --activate || echo "AVERTISSEMENT: install WooCommerce echouee"
  else
    $WP_CLI plugin activate woocommerce || true
  fi

  $WP_CLI rewrite flush || true
else
  echo "DB_HOST vide -> COLD STANDBY : install WP/WooCommerce sautee (se fera au failover)."
fi

echo "===> User data terminé avec succès."