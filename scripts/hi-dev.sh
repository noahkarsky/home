#!/usr/bin/env bash
# Run Home Information's Django dev server from the monorepo, with the
# floorplan-3d designer available under CONFIGURE > 3D Floor Plan.
#
# First run: python3.11 -m venv apps/home-information/venv
#            apps/home-information/venv/bin/pip install -r apps/home-information/src/hi/requirements/development.txt
#
# Data lives in .data/hi/ (git-ignored). The defaults are in scripts/hi.env
# and any of them can be overridden from the environment; for the full set
# use HI's own `make env-build-dev`.
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
HI="$ROOT/apps/home-information"
PORT="${1:-8411}"

if [ -f "$HI/venv/bin/activate" ]; then . "$HI/venv/bin/activate"
elif [ -f "$HI/venv/Scripts/activate" ]; then . "$HI/venv/Scripts/activate"
else echo "No venv at $HI/venv (see the comment at the top of this script)." >&2; exit 1
fi

DATA="${HI_DATA_DIR:-$ROOT/.data/hi}"
while IFS='=' read -r key value; do
  case "$key" in ''|\#*) continue ;; esac
  value="${value%$'\r'}"; value="${value//@ROOT@/$ROOT}"
  [ -n "${!key:-}" ] || export "$key=${value//@DATA@/$DATA}"
done < "$ROOT/scripts/hi.env"
mkdir -p "$HI_DB_PATH" "$HI_MEDIA_PATH"

cd "$HI/src"
python manage.py migrate --no-input
python manage.py hi_createsuperuser
python manage.py hi_creategroups
exec python manage.py runserver "$PORT"
