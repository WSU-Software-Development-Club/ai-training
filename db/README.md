# Database (self-hosted Postgres on troyster)

The predictions datastore migrated off Supabase to a self-hosted Postgres 16
container running on troyster, alongside the backend, on the compose network.

- **Schema:** [`schema.sql`](./schema.sql) — the `predictions` table + indexes.
- **Backend access:** `backend/utils/db.py` (`PredictionsDB` via `psycopg[pool]`),
  configured by `DATABASE_URL`.
- **Writer:** `ml/m1/predict_upcoming.py` (`save_to_postgres`, upsert on `ncaa_game_id`).

## 1. Bring up Postgres on troyster

`schema.sql` is mounted into the container's `/docker-entrypoint-initdb.d/`, so it
runs automatically the first time the `pgdata` volume is created.

```bash
# On troyster, in /home/troymuehlbauer/ai-training
# Set POSTGRES_PASSWORD (and optionally POSTGRES_USER/DB) in .env first.
docker compose up -d db
docker compose logs db        # confirm "database system is ready to accept connections"
```

To (re)apply the schema by hand against a running DB:

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

## 2. Migrate existing data from Supabase

Export the `predictions` table from the old Supabase project and load it into
the new DB. (Supabase exposes a standard Postgres connection string in
Project Settings → Database.)

```bash
# Export data only (schema already created by schema.sql)
pg_dump "postgresql://postgres:<SUPABASE_DB_PW>@db.<PROJECT>.supabase.co:5432/postgres" \
  --table=public.predictions --data-only --column-inserts \
  > predictions_data.sql

# Import into troyster Postgres
psql "$DATABASE_URL" -f predictions_data.sql

# Reset the id sequence so new inserts don't collide with imported ids
psql "$DATABASE_URL" -c \
  "SELECT setval(pg_get_serial_sequence('predictions','id'), COALESCE(MAX(id),1)) FROM predictions;"

# Sanity check
psql "$DATABASE_URL" -c "SELECT count(*), max(season), max(week) FROM predictions;"
```

## 3. Weekly job connectivity (GitHub Actions → troyster)

The weekly workflow runs on GitHub-hosted runners, which reach the private DB by
joining the tailnet. Required repo secrets:

- `DATABASE_URL` — e.g. `postgresql://aitraining:<pw>@192.168.1.126:5432/aitraining`
- `TS_AUTHKEY` — a Tailscale **ephemeral, tagged** auth key
- `CFBD_API_KEY` — unchanged

In the Tailscale admin console, add an ACL grant so `tag:ci` may reach troyster
on `tcp:5432` (and tag `troyster` / the DB host accordingly). Postgres is **not**
exposed via the Cloudflare Tunnel; restrict host port 5432 to the Tailscale
interface with the firewall.

The old `SUPABASE_URL` / `SUPABASE_KEY` secrets can be deleted after cutover.

## 4. Local development

`docker compose -f docker-compose.dev.yml up --build` starts a local `db` service;
the backend gets `DATABASE_URL` pointing at it automatically. No troyster or
Tailscale needed for local work.
