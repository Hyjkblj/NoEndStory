# No End Story Server Docker Deployment

This deployment exposes only the frontend Nginx service publicly. PostgreSQL, Redis, generated images, generated audio, and vector data are kept in Docker volumes and are not copied into application images.

## Domain

Use `hyjkblj.online/galgame` as the frontend entry. The app is built with a path prefix so it can share the same domain with other projects.

1. Point the DNS `A` record for `hyjkblj.online` to the server public IP.
2. Optional: point `www.hyjkblj.online` to the same IP.
3. Open server firewall port `80`.
4. If HTTPS is terminated by a cloud load balancer or host Nginx, forward traffic to this stack's `HTTP_PORT`.

The container Nginx is configured with `server_name hyjkblj.online www.hyjkblj.online localhost _;` and serves this app under `/galgame/`.

If this domain is shared by multiple projects, run this stack on a private host port and let a host-level Nginx route only `/galgame/` to it:

```env
HTTP_BIND=127.0.0.1
HTTP_PORT=18081
VITE_APP_BASE_PATH=/galgame
```

```nginx
location /galgame/ {
    proxy_pass http://127.0.0.1:18081;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Keep the `/galgame` prefix when proxying; do not strip it.

## Configure

```bash
cp deploy/player.env.example deploy/player.env
```

Edit `deploy/player.env`:

```env
APP_DOMAIN=hyjkblj.online
VITE_APP_BASE_PATH=/galgame
HTTP_BIND=0.0.0.0
HTTP_PORT=80
ALLOWED_ORIGINS=http://hyjkblj.online,https://hyjkblj.online
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
```

Fill the AI/TTS keys required by your selected providers.

The compose file has `build` contexts for both frontend and backend. `BACKEND_IMAGE` and `FRONTEND_IMAGE` are the local tags assigned to those built images.

`postgres` uses the `pgvector/pgvector:pg16` image. The SQL files in `deploy/postgres-init/` run only when the PostgreSQL volume is first created, enabling `uuid-ossp` and `vector`.

## Start

```bash
sh scripts/deploy-server.sh
```

Manual equivalent:

```bash
docker compose --project-name noendstory \
  --env-file deploy/player.env \
  -f deploy/docker-compose.player.yml \
  up -d --build
```

Use `deploy/docker-compose.player.yml` for server deployment. Do not use the legacy root `docker-compose.yml` as the production entry.

## Services

- `frontend`: Nginx + built frontend, public entry on `HTTP_PORT`.
- `backend`: FastAPI, internal only.
- `postgres`: PostgreSQL, default bound to `127.0.0.1`.
- `redis`: Redis, default bound to `127.0.0.1`.

## Runtime Volumes

- `noendstory_pgdata`: PostgreSQL data.
- `noendstory_redisdata`: Redis append-only data.
- `noendstory_vector_db`: local vector database.
- `noendstory_runtime_images`: generated characters, scenes, small scenes, and composite images.
- `noendstory_runtime_audio`: generated TTS audio cache.

These runtime artifacts are intentionally excluded from Docker build contexts by `.dockerignore`.

## Useful Commands

```bash
docker compose --project-name noendstory --env-file deploy/player.env -f deploy/docker-compose.player.yml ps
docker compose --project-name noendstory --env-file deploy/player.env -f deploy/docker-compose.player.yml logs -f frontend backend
docker compose --project-name noendstory --env-file deploy/player.env -f deploy/docker-compose.player.yml down
```

Reset all runtime data:

```bash
docker compose --project-name noendstory --env-file deploy/player.env -f deploy/docker-compose.player.yml down --volumes --remove-orphans
```
