# Success Database

## Overview

This folder contains the PostgreSQL database configuration and files required to set up the `success` database for local development.

The database runs in Docker using PostgreSQL 16. Each developer can create and run their own local database instance without needing access to another developer's Docker container.

## Files

| File | Description |
|---|---|
| `compose.yaml` | Docker Compose configuration for running PostgreSQL. |
| `.gitignore` | Defines files and directories that Git should ignore. |
| `success_db.sql` | SQL script containing the database schema and related definitions. |
| `success.dump` | PostgreSQL backup that may contain both schema and data. Review its contents before sharing or restoring it. |
| `.env` | Local environment variables and credentials. This file must not be committed to Git. |
| `.env.example` | Example environment variables for developers to use when creating their own `.env` file. |

## Requirements

- Docker Desktop
- Docker Compose
- Git

## Setup

### 1. Configure environment variables

Create a local `.env` file in the same directory as `compose.yaml`.

Use `.env.example` as a template and configure the following variables:

```dotenv
POSTGRES_DB=success
POSTGRES_USER=admin
POSTGRES_PASSWORD=change_me
```

Replace `change_me` with a strong, private password. Do not commit the real `.env` file.

### 2. Start PostgreSQL

From this directory, run:

```bash
docker compose up -d
```

This starts the PostgreSQL container in the background.

### 3. Verify the container

Check its status:

```bash
docker compose ps
```

Check whether PostgreSQL is ready:

```bash
docker exec success_db pg_isready -U admin -d success
```

### 4. Connect to the database

Connect through the container with:

```bash
docker exec -it success_db psql -U admin -d success
```

The configured host port is `5432`, bound to `127.0.0.1`. This makes the database accessible from the local machine, not directly from other computers on the network.

## Database files and restoration

- Use `success_db.sql` to create the database structure from the SQL definitions.
- Use `success.dump` when a backup-based restoration is required, after verifying that it is appropriate for the target environment.
- Do not assume that the dump contains only the schema. It may include records or other sensitive information.
- Back up any important local data before replacing or restoring a database.

A custom-format PostgreSQL dump can generally be restored using `pg_restore`. The exact command depends on how the backup was created and whether the target database already exists.

## Security guidelines

- Never commit real passwords, API keys, tokens, or other secrets.
- Keep `.env` out of version control.
- Commit `.env.example` only with placeholder values.
- Review database backups before uploading or sharing them.
- Do not commit PostgreSQL data directories or Docker volumes.
- If a real credential has already been committed, removing it from the current file is not enough. Rotate the credential and assess whether the Git history also needs to be cleaned up.

## Team workflow

Each developer should clone the repository, configure their own `.env` file, and start their own local PostgreSQL instance with Docker Compose.

The repository shares the configuration and database files needed for development. It does not share a running Docker container or a live database connection.

## Notes

The default database name, username, and port are configured for local development. Coordinate any changes to the database schema or setup with the backend team.
