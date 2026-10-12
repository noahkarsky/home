import os
import sys

from django.apps import AppConfig


class ServicesConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.services'

    def ready(self):
        import time
        from hi.apps.common.asyncio_utils import start_background_event_loop
        from .service_simulator_manager import ServiceSimulatorManager

        # Counterintuitive: Django's AppConfig.ready() does not behave the way
        # the docs suggest. The two surprises that drive the guards below:
        #
        # 1. Under runserver, Django itself spawns multiple processes during
        #    initialization — not because workers are configured, but as part
        #    of normal startup — and ready() runs in each one. RUN_MAIN is set
        #    only in the worker that serves requests; the other invocations
        #    must bail out to avoid duplicate startup.
        #
        # 2. Under gunicorn, ready() does not run at all. Equivalent startup
        #    is delegated to gunicorn's post_fork hook.

        if os.environ.get('RUN_MAIN') != 'true':
            return

        if (( 'gunicorn' in os.environ.get( 'SERVER_SOFTWARE', '' ))
            or ( 'gunicorn' in sys.argv[0] )):
            return

        # Django's ready() fires before the system is fully usable.
        time.sleep(1)
        start_background_event_loop(
            task_function = ServiceSimulatorManager().initialize,
        )
        return
