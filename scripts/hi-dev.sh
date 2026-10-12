#!/usr/bin/env bash
# Run Home Information's Django dev server from the monorepo, with the
# floorplan-3d designer available under CONFIGURE > 3D Floor Plan.
#
# First run: python3.11 -m venv apps/home-information/venv
#            apps/home-information/venv/bin/pip install -r apps/home-information/src/hi/requirements/development.txt
#
# Data lives in .data/hi/ (git-ignored). Any variable below can be overridden
# from the environment; for the full set use HI's own `make env-build-dev`.
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
HI="$ROOT/apps/home-information"
PORT="${1:-8411}"

if [ -f "$HI/venv/bin/activate" ]; then . "$HI/venv/bin/activate"
elif [ -f "$HI/venv/Scripts/activate" ]; then . "$HI/venv/Scripts/activate"
else echo "No venv at $HI/venv (see the comment at the top of this script)." >&2; exit 1
fi

mkdir -p "$ROOT/.data/hi/database" "$ROOT/.data/hi/media"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-hi.settings.development}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-django-insecure-local-dev-only}"
export DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
export DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-admin}"
export HI_DB_PATH="${HI_DB_PATH:-$ROOT/.data/hi/database}"
export HI_MEDIA_PATH="${HI_MEDIA_PATH:-$ROOT/.data/hi/media}"
export HI_REDIS_HOST="${HI_REDIS_HOST:-localhost}"
export HI_REDIS_PORT="${HI_REDIS_PORT:-6379}"
export HI_SUPPRESS_AUTHENTICATION="${HI_SUPPRESS_AUTHENTICATION:-true}"
export HI_FLOORPLAN3D_HTML="${HI_FLOORPLAN3D_HTML:-$ROOT/apps/floorplan-3d/index.html}"

cd "$HI/src"
python manage.py migrate --no-input
python manage.py hi_createsuperuser
python manage.py hi_creategroups
exec python manage.py runserver "$PORT"
