"""Background services for the Home launcher (scripts/home-launcher.ps1).

    pythonw home_services.py redis PORT RUN_DIR   # in-memory Redis stand-in
    pythonw home_services.py hi    PORT RUN_DIR   # Home Information server

Each service sends its output to RUN_DIR/<name>.log and writes its PID to
RUN_DIR/<name>.pid, so it can run under pythonw.exe (no console window) and
be stopped later. The `hi` service expects the environment from scripts/hi.env
to already be set (the launcher does that).
"""
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HI_SRC = ROOT / 'apps' / 'home-information' / 'src'


def run_redis(port):
    # HI's redis client speaks RESP2; fakeredis's TCP server defaults to RESP3.
    from fakeredis import _tcp_server
    _tcp_server.Resp3Writer = _tcp_server.Resp2Writer
    server = _tcp_server.TcpFakeServer(('127.0.0.1', port), server_type='redis')
    print(f'fakeredis (RESP2) listening on 127.0.0.1:{port}', flush=True)
    server.serve_forever()


def run_hi(port):
    # Same steps as scripts/hi-dev.sh, in one process and without the reloader.
    os.chdir(HI_SRC)
    sys.path.insert(0, str(HI_SRC))
    # HI starts its background tasks (weather polling, integration sync) only when RUN_MAIN is
    # 'true', which Django's reloader normally sets. There is no reloader here, so set it
    # ourselves; otherwise weather, sunrise/sunset and clouds never load.
    os.environ.setdefault('RUN_MAIN', 'true')
    import django
    from django.core.management import call_command
    django.setup()
    call_command('migrate', interactive=False)
    call_command('hi_createsuperuser')
    call_command('hi_creategroups')
    call_command('runserver', f'127.0.0.1:{port}', use_reloader=False)


def main():
    name, port, run_dir = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    run_dir.mkdir(parents=True, exist_ok=True)
    log = open(run_dir / f'{name}.log', 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    print(f'--- {datetime.now():%Y-%m-%d %H:%M:%S} starting {name} (pid {os.getpid()})')
    pid_file = run_dir / f'{name}.pid'
    pid_file.write_text(str(os.getpid()))
    try:
        {'redis': run_redis, 'hi': run_hi}[name](port)
    finally:
        if pid_file.read_text() == str(os.getpid()):
            pid_file.unlink()


if __name__ == '__main__':
    main()
