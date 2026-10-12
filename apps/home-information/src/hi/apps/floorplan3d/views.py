"""
Embeds the floorplan-3d designer (apps/floorplan-3d in the home monorepo)
and lets its plan be applied as a Location's background SVG.

The designer is a single self-contained HTML file. It exports an
editor-compatible background SVG (see docs/dev/domain/svg-background-system.md)
through window.FloorplanExport.hiSvg(), which the config pane posts to
Floorplan3dApplyView.
"""
import logging
import os
from pathlib import Path
import time
import urllib.request
import xml.etree.ElementTree as ET

from csp.decorators import csp_update
from django.conf import settings
from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import View

from hi.apps.common.svg_forms import SvgFileForm
from hi.apps.common.svg_utils import process_svg_content
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location

logger = logging.getLogger(__name__)

# The designer loads three.js as ES modules from this CDN (see its importmap).
DESIGNER_CDN_URL = 'https://cdn.jsdelivr.net'

NEW_LOCATION_ID = 'new'
DEFAULT_NEW_LOCATION_NAME = 'My Home'
SVG_MEDIA_DIRECTORY = 'location/svg'
SVG_SOURCE_FILENAME = 'floorplan-3d.svg'


def get_designer_html_path() -> Path:
    """
    The first designer HTML file that exists, or None.

    HI_FLOORPLAN3D_HTML overrides; otherwise look in the monorepo checkout
    (dev) and at the read-only mount used by the monorepo docker-compose.
    """
    candidates = [
        os.environ.get( 'HI_FLOORPLAN3D_HTML' ),
        Path( settings.BASE_DIR ).parent.parent.parent / 'floorplan-3d' / 'index.html',
        '/floorplan3d/index.html',
    ]
    for candidate in candidates:
        if candidate and Path( candidate ).is_file():
            return Path( candidate )
        continue
    return None


def get_backyard_html_path() -> Path:
    """ Same lookup as the designer: HI_BACKYARD_HTML, the monorepo checkout, then the docker mount. """
    candidates = [
        os.environ.get( 'HI_BACKYARD_HTML' ),
        Path( settings.BASE_DIR ).parent.parent.parent / 'backyard' / 'index.html',
        '/backyard/index.html',
    ]
    for candidate in candidates:
        if candidate and Path( candidate ).is_file():
            return Path( candidate )
        continue
    return None


class Floorplan3dView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.FLOORPLAN_3D

    def get_main_template_name( self ) -> str:
        return 'floorplan3d/panes/floorplan3d.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        return {
            'designer_available': bool( get_designer_html_path() ),
            'location_list': list( Location.objects.all().order_by( 'order_id' )),
            'new_location_id': NEW_LOCATION_ID,
            'default_new_location_name': DEFAULT_NEW_LOCATION_NAME,
        }


@method_decorator( xframe_options_sameorigin, name = 'dispatch' )
@method_decorator( csp_update({ 'script-src': [ DESIGNER_CDN_URL ] }), name = 'dispatch' )
class Floorplan3dDesignerView( View ):
    """ Serves the designer page itself, framed by the config pane. """

    def get( self, request, *args, **kwargs ):
        html_path = get_designer_html_path()
        if not html_path:
            raise Http404( 'The floorplan-3d designer was not found.' )
        return HttpResponse( html_path.read_text( encoding = 'utf-8' ),
                             content_type = 'text/html; charset=utf-8' )


class BackyardView( ConfigPageView ):
    """ The Backyard tab: the backyard planner framed inside the config pages. """

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.BACKYARD

    def get_main_template_name( self ) -> str:
        return 'floorplan3d/panes/backyard.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        return { 'backyard_available': bool( get_backyard_html_path() ) }


@method_decorator( xframe_options_sameorigin, name = 'dispatch' )
@method_decorator( csp_update({ 'script-src': [ DESIGNER_CDN_URL ] }), name = 'dispatch' )
class BackyardAppView( View ):
    """ Serves the backyard planner page itself, framed by the Backyard tab. """

    def get( self, request, *args, **kwargs ):
        html_path = get_backyard_html_path()
        if not html_path:
            raise Http404( 'The backyard planner was not found.' )
        return HttpResponse( html_path.read_text( encoding = 'utf-8' ),
                             content_type = 'text/html; charset=utf-8' )


SPEED_TEST_URL = 'https://speed.cloudflare.com/__down?bytes=8000000'
SPEED_TEST_TIMEOUT_SECS = 20
SPEED_TEST_MIN_INTERVAL_SECS = 30


class SpeedTestView( View ):
    """
    Command-center internet speed tile. Downloads a fixed payload from
    Cloudflare's speed endpoint on the server (the browser's CSP does not
    allow third-party connections) and reports Mbps and time to first byte.
    Results are cached briefly so reloads and rapid clicks don't re-run it.
    """

    _last_result = None
    _last_time = 0.0

    def get( self, request, *args, **kwargs ):
        cls = type( self )
        if cls._last_result and ( time.monotonic() - cls._last_time ) < SPEED_TEST_MIN_INTERVAL_SECS:
            return JsonResponse( cls._last_result )
        try:
            started = time.monotonic()
            req = urllib.request.Request( SPEED_TEST_URL, headers = { 'User-Agent': 'home-information' } )
            with urllib.request.urlopen( req, timeout = SPEED_TEST_TIMEOUT_SECS ) as response:
                response.read( 1 )
                first_byte = time.monotonic()
                total_bytes = 1 + len( response.read() )
            transfer_secs = max( time.monotonic() - first_byte, 0.001 )
            result = {
                'ok': True,
                'mbps': round( total_bytes * 8 / transfer_secs / 1_000_000, 1 ),
                'latency_ms': round( ( first_byte - started ) * 1000 ),
            }
        except Exception as e:
            logger.warning( f'Speed test failed: {e}' )
            return JsonResponse({ 'ok': False, 'error': 'Offline' })
        cls._last_result = result
        cls._last_time = time.monotonic()
        return JsonResponse( result )


class Floorplan3dApplyView( View ):
    """
    Sets a Location's background from designer-exported SVG content, or
    creates a new Location with it.
    """

    def post( self, request, *args, **kwargs ):
        svg_content = request.POST.get( 'svg_content', '' )
        if not svg_content:
            raise BadRequest( 'No SVG content.' )
        if len( svg_content.encode( 'utf-8' )) > SvgFileForm.MAX_SVG_FILE_SIZE_BYTES:
            raise BadRequest( 'SVG content is too large.' )

        try:
            result = process_svg_content(
                svg_content = svg_content,
                media_destination_directory = SVG_MEDIA_DIRECTORY,
                source_filename = SVG_SOURCE_FILENAME,
                remove_dangerous = True,
            )
        except ( ValueError, ET.ParseError ) as e:
            raise BadRequest( f'Invalid SVG: {e}' )

        location_id = request.POST.get( 'location_id', '' )
        if location_id == NEW_LOCATION_ID:
            name = request.POST.get( 'name', '' ).strip() or DEFAULT_NEW_LOCATION_NAME
            location = LocationManager().create_location(
                name = name,
                svg_fragment_filename = result['svg_fragment_filename'],
                svg_fragment_content = result['svg_fragment_content'],
                svg_viewbox = result['svg_viewbox'],
            )
        else:
            location = self._update_location( location_id = location_id, result = result )

        return JsonResponse({
            'redirect_url': reverse( 'location_switch', kwargs = { 'location_id': location.id } ),
        })

    def _update_location( self, location_id, result ) -> Location:
        try:
            location = Location.objects.get( id = int( location_id ))
        except ( TypeError, ValueError ):
            raise BadRequest( 'Invalid location id.' )
        except Location.DoesNotExist:
            raise Http404( 'Location not found.' )

        # Views that showed the whole old background follow the new one;
        # cropped views (e.g. "Kitchen") are left for the user to adjust.
        old_view_box_str = location.svg_view_box_str
        new_view_box_str = str( result['svg_viewbox'] )
        with transaction.atomic():
            LocationManager().update_location_svg(
                location = location,
                svg_fragment_filename = result['svg_fragment_filename'],
                svg_fragment_content = result['svg_fragment_content'],
                svg_viewbox = result['svg_viewbox'],
            )
            location.views.filter( svg_view_box_str = old_view_box_str ).update(
                svg_view_box_str = new_view_box_str,
            )
        return location
