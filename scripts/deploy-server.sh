#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
ENV_FILE="$DEPLOY_DIR/player.env"
ENV_EXAMPLE="$DEPLOY_DIR/player.env.example"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.player.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin is unavailable." >&2
  exit 1
fi

check_health() {
  url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "$url" >/dev/null 2>&1
    return $?
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -qO- "$url" >/dev/null 2>&1
    return $?
  fi

  echo "ERROR: curl or wget is required for the health check." >&2
  return 1
}

if [ ! -f "$ENV_FILE" ]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created $ENV_FILE from template."
fi

if ! grep -q '^POSTGRES_PASSWORD=.\+' "$ENV_FILE"; then
  password="$(openssl rand -hex 16 2>/dev/null || date +%s%N)"
  if grep -q '^POSTGRES_PASSWORD=' "$ENV_FILE"; then
    sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$password/" "$ENV_FILE"
  else
    printf '\nPOSTGRES_PASSWORD=%s\n' "$password" >> "$ENV_FILE"
  fi
  echo "Generated POSTGRES_PASSWORD in $ENV_FILE."
fi

if grep -q '^REDIS_PASSWORD=$' "$ENV_FILE"; then
  redis_password="$(openssl rand -hex 16 2>/dev/null || date +%s%N)"
  sed -i "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$redis_password/" "$ENV_FILE"
  echo "Generated REDIS_PASSWORD in $ENV_FILE."
fi

domain="$(grep '^APP_DOMAIN=' "$ENV_FILE" | head -n 1 | cut -d= -f2-)"
port="$(grep '^HTTP_PORT=' "$ENV_FILE" | head -n 1 | cut -d= -f2-)"
port="${port:-80}"

echo "Starting No End Story server stack..."
docker compose \
  --project-name noendstory \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_FILE" \
  up -d --build

echo "Waiting for web entry health..."
for _ in $(seq 1 60); do
  if check_health "http://127.0.0.1:$port/health"; then
    echo "No End Story is healthy."
    echo "Frontend entry: http://$domain/"
    exit 0
  fi
  sleep 2
done

echo "ERROR: web health check timed out. Recent logs:" >&2
docker compose \
  --project-name noendstory \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_FILE" \
  logs --tail 120 frontend backend redis postgres >&2
exit 1
