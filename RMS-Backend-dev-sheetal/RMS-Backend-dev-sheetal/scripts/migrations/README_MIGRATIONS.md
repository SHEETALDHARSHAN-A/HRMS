DB migration guidance — career activation fields

Two options to add the new columns introduced by recent changes:

1) Use Alembic (recommended for production)

- If your project already uses Alembic, create a new revision:

```bash
alembic revision -m "add career activation fields to job_details" --autogenerate
# then edit the revision (if needed) and apply it:
alembic upgrade head
```

- If you don't have Alembic configured, see step 2 or follow Alembic docs to initialise:

```bash
alembic init alembic
# configure alembic.ini and env.py to use your SQLAlchemy URL/metadata
```

2) Run the SQL directly (fast, suitable for small deployments)

- The SQL file `scripts/migrations/001_add_career_activation.sql` contains the ALTER statements. Apply it using psql:

```powershell
psql "postgresql://user:password@host:port/dbname" -f scripts/migrations/001_add_career_activation.sql
```

Notes / Safety
- Always run migrations in a transaction or snapshot the DB before applying in production.
- If you use dockerized DBs, run the SQL from inside a container that has network access to the DB.
- Validate that your application code reads/writes the new columns correctly after migration and that you have appropriate backups.

Postgres trigger for immediate shortlist notifications
---------------------------------------------------
We add a DB trigger that emits a NOTIFY on the `profile_shortlisted` channel when a
`profiles` row is updated and its `curated_results` becomes `shortlisted`.

Apply `scripts/migrations/002_profile_shortlist_notify.sql` to create the trigger and
function. The activation worker listens to this channel and will evaluate activation
rules immediately without any manual trigger.

Important: The trigger uses `pg_notify` and does a simple SELECT to find `job_id` from
`curation_jobs`. Ensure your schema names match and that the `profiles.curation_id` FK
points to `curation_jobs.id`.
