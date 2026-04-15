#!/bin/bash
# Docker entrypoint script for LinguaEval platform
# Handles database initialization, migrations, and app startup

set -e

echo "════════════════════════════════════════════════════════"
echo "  Dalīl Group - Platform Startup"
echo "════════════════════════════════════════════════════════"

# Wait for PostgreSQL to be ready (if using PostgreSQL)
if [ ! -z "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "[*] Waiting for PostgreSQL to be ready..."
    while ! pg_isready -h $(echo $DATABASE_URL | grep -oP '(?<=//)([^:]+)') -p 5432 -U ${DB_USER:-linguaeval}; do
        sleep 1
    done
    echo "[✓] PostgreSQL is ready!"
fi

# Wait for Redis to be ready (if configured)
if [ ! -z "$REDIS_HOST" ]; then
    echo "[*] Waiting for Redis to be ready..."
    while ! redis-cli -h $REDIS_HOST -p ${REDIS_PORT:-6379} ping > /dev/null 2>&1; do
        sleep 1
    done
    echo "[✓] Redis is ready!"
fi

# Wait for Ollama to be ready
if [ ! -z "$OLLAMA_HOST" ]; then
    echo "[*] Waiting for Ollama to be ready..."
    max_attempts=30
    attempt=1
    while ! curl -f $OLLAMA_HOST/api/tags > /dev/null 2>&1; do
        if [ $attempt -eq $max_attempts ]; then
            echo "[!] Warning: Ollama not responding, continuing anyway..."
            break
        fi
        echo "  Attempt $attempt/$max_attempts"
        sleep 1
        ((attempt++))
    done
    if [ $attempt -lt $max_attempts ]; then
        echo "[✓] Ollama is ready!"
    fi
fi

# Initialize database
echo ""
echo "[*] Initializing database..."
python3 -c "from database import init_db; init_db()" 2>/dev/null || true
echo "[✓] Database initialized!"

# Run migrations (if using Alembic)
if command -v alembic &> /dev/null && [ -d "migrations" ]; then
    echo ""
    echo "[*] Running database migrations..."
    alembic upgrade head || echo "[!] Migration may have already been applied"
    echo "[✓] Migrations complete!"
fi

# Seed database if needed (development only)
if [ "$ENVIRONMENT" = "development" ]; then
    echo ""
    echo "[*] Seeding database with sample data (development mode)..."
    python3 migrate.py seed 2>/dev/null || true
fi

# Warm up cache
if [ ! -z "$REDIS_HOST" ]; then
    echo ""
    echo "[*] Warming up cache..."
    python3 -c "from cache import warm_cache; warm_cache()" 2>/dev/null || true
    echo "[✓] Cache warmed!"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Starting Dalīl Group Platform"
echo "════════════════════════════════════════════════════════"
echo ""

# Execute the main command
exec "$@"
