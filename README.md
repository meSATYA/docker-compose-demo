# Docker Compose demo: nginx + Flask + Redis

Shows **networking**, **volumes** and **orchestration** features of Docker Compose.

```
Browser -> nginx :8080 -> web (Flask, xN) -> redis
           [frontend]      [frontend+backend]  [backend]
```

## Run

```bash
docker compose up -d --build
curl localhost:8080
```

## Demo script

1. **Basics**: `docker compose ps`, then `curl localhost:8080` a few times. The visit counter increases.
2. **Networking**
   - Name-based DNS: `docker compose exec web python -c "import socket;print(socket.gethostbyname('redis'))"`
   - Isolation: nginx is on `frontend` only, so it cannot see Redis:
     `docker compose exec nginx ping -c1 redis` fails.
   - Only port 8080 is published. `redis` and `web` have no host ports.
3. **Volumes**
   - `docker compose down` (containers removed), then `docker compose up -d`, and the counter continues.
   - `docker compose down -v` deletes the volume, and the counter resets to 1.
   - Bind mount: change the message in `app/app.py`. Gunicorn reloads it, no rebuild needed.
4. **Orchestration**
   - Scale: `docker compose up -d --scale web=3`, then run `for i in $(seq 6); do curl -s localhost:8080; done` and watch `served_by` change.
   - Self-healing: `docker kill $(docker compose ps -q redis)` and Compose restarts it (`restart: unless-stopped`).
   - Start order: Redis has a healthcheck, and `web` waits for it (`depends_on: condition: service_healthy`).
5. **Limits (lead into Kubernetes)**: this all runs on ONE machine. If the host dies, everything dies.

## Clean up

```bash
docker compose down -v
```

