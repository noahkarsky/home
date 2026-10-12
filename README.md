# home

A monorepo for our house: its floor plan, and the information that goes with it.

| App | What it is | Origin |
|---|---|---|
| [`apps/floorplan-3d`](apps/floorplan-3d) | Single-file 2D/3D floor-plan designer, traced to our house | fork of [wy51ai/floorplan-3d](https://github.com/wy51ai/floorplan-3d) |
| [`apps/home-information`](apps/home-information) | Django app for manuals, maintenance records, devices and cameras, placed on a map of the house | subtree of [cassandra/home-information](https://github.com/cassandra/home-information) |

## How they fit together

- **floorplan-3d → Home Information.** The designer's *File ▾ → Export SVG for Home Information* writes a background in HI's editor format: rooms become floor regions, walls become wall strokes, and doors, windows and sliders become HI icons, at 1 SVG unit = 10 mm. HI themes it and can edit it in its background editor. Room labels sit outside the editable group, so they show in HI, but HI's background editor drops them when it saves.
- **Home Information → floorplan-3d.** HI's new `floorplan3d` app (`apps/home-information/src/hi/apps/floorplan3d`) adds a **3D PLAN** button and a *CONFIGURE → 3D Floor Plan* tab. They embed the designer and have an **Apply as background** button, which sets a location's map (or creates a new location) straight from the current plan.

## Running it

**Designer only.** Open `apps/floorplan-3d/index.html`, or serve it:

```bash
python -m http.server 8765 --directory apps/floorplan-3d
```

**Home Information (dev).** This needs Python 3.11 and a Redis on `localhost:6379`.

```bash
python3.11 -m venv apps/home-information/venv
apps/home-information/venv/bin/pip install -r apps/home-information/src/hi/requirements/development.txt
scripts/hi-dev.sh
```

Then open http://localhost:8411. Data is kept in `.data/hi/`.

**Home Information (Docker).** See the comments in [`docker-compose.yml`](docker-compose.yml). It builds HI from this repo and mounts the designer read-only.

## Keeping up with upstream

```bash
# Home Information (git subtree)
git fetch hi-upstream master
git subtree pull --prefix=apps/home-information hi-upstream master

# floorplan-3d (original repo, files now live under apps/floorplan-3d)
git fetch upstream master
git merge -X subtree=apps/floorplan-3d upstream/master
```

Local changes to HI outside `apps/floorplan3d/` are kept small to ease merges:

- one line each in `settings/base.py`, `urls.py` and `apps/config/enums.py`
- one button in `templates/panes/bottom_buttons.html`

## Licenses

floorplan-3d is MIT. Home Information is MIT for personal and non-commercial use, and commercial use needs a license (see [`apps/home-information/LICENSE.md`](apps/home-information/LICENSE.md)).
