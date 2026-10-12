import logging
import os
import tempfile
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.urls import reverse

from hi.apps.common.svg_models import SvgViewBox
from hi.apps.location.models import Location, LocationView
from hi.testing.view_test_base import DualModeViewTestCase, SyncViewTestCase

logging.disable(logging.CRITICAL)

DESIGNER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1943 2376">'
    '<g data-hi-editor="1" data-hi-name="Our House">'
    '<g id="bg-f3d00000" class="hi-bg-element" data-bg-type="interior-floors"'
    ' data-bg-edit-type="closed" data-bg-layer="130">'
    '<path class="interior-floors" d=" M 166,166 L 537,166 L 537,617 L 166,617 Z" /></g>'
    '</g>'
    '<g class="fp3d-room-labels"><text x="351" y="412">Bedroom 2</text></g>'
    '</svg>'
)
NEW_VIEW_BOX_STR = str(SvgViewBox.from_attribute_value('0 0 1943 2376'))


class TestFloorplan3dView(DualModeViewTestCase):

    def test_renders_config_tab_with_designer(self):
        response = self.client.get(reverse('floorplan3d_home'))

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'floorplan3d/panes/floorplan3d.html')
        # Running inside the monorepo, so apps/floorplan-3d/index.html is found
        self.assertTrue(response.context['designer_available'])

    def test_shows_warning_when_designer_missing(self):
        with patch('hi.apps.floorplan3d.views.get_designer_html_path', return_value=None):
            response = self.client.get(reverse('floorplan3d_home'))

        self.assertSuccessResponse(response)
        self.assertFalse(response.context['designer_available'])
        self.assertContains(response, 'designer was not found')


class TestFloorplan3dDesignerView(SyncViewTestCase):

    def test_serves_designer_framable_with_cdn_allowed(self):
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write('<!doctype html><title>Designer</title>')
        self.addCleanup(os.unlink, f.name)

        with patch.dict(os.environ, {'HI_FLOORPLAN3D_HTML': f.name}):
            response = self.client.get(reverse('floorplan3d_designer'))

        self.assertSuccessResponse(response)
        self.assertContains(response, '<title>Designer</title>')
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        self.assertIn('https://cdn.jsdelivr.net', response['Content-Security-Policy'])

    def test_missing_designer_is_404(self):
        with patch('hi.apps.floorplan3d.views.get_designer_html_path', return_value=None):
            response = self.client.get(reverse('floorplan3d_designer'))

        self.assertResponseStatusCode(response, 404)


class TestFloorplan3dApplyView(SyncViewTestCase):

    def setUp(self):
        super().setUp()
        self.enterContext(self.in_memory_media_storage())
        self.location = Location.objects.create(
            name='Home',
            svg_fragment_filename='location/svg/old.svg',
            svg_view_box_str='0 0 2000 2000',
        )
        self.full_view = LocationView.objects.create(
            location=self.location, name='All', svg_view_box_str='0 0 2000 2000', svg_rotate=0,
        )
        self.cropped_view = LocationView.objects.create(
            location=self.location, name='Kitchen', svg_view_box_str='100 100 400 400', svg_rotate=0,
        )

    def test_replaces_location_background(self):
        response = self.client.post(reverse('floorplan3d_apply'), {
            'svg_content': DESIGNER_SVG,
            'location_id': str(self.location.id),
        })

        self.assertSuccessResponse(response)
        self.assertEqual(
            response.json()['redirect_url'],
            reverse('location_switch', kwargs={'location_id': self.location.id}),
        )
        self.location.refresh_from_db()
        self.assertEqual(self.location.svg_view_box_str, NEW_VIEW_BOX_STR)
        fragment = default_storage.open(self.location.svg_fragment_filename).read()
        if isinstance(fragment, bytes):
            fragment = fragment.decode('utf-8')
        self.assertIn('data-hi-editor="1"', fragment)
        self.assertIn('Bedroom 2', fragment)
        self.assertNotIn('<svg', fragment)

        # Uncropped views follow the new background; cropped ones are left alone
        self.full_view.refresh_from_db()
        self.cropped_view.refresh_from_db()
        self.assertEqual(self.full_view.svg_view_box_str, NEW_VIEW_BOX_STR)
        self.assertEqual(self.cropped_view.svg_view_box_str, '100 100 400 400')

    def test_creates_new_location(self):
        response = self.client.post(reverse('floorplan3d_apply'), {
            'svg_content': DESIGNER_SVG,
            'location_id': 'new',
            'name': 'Our House',
        })

        self.assertSuccessResponse(response)
        location = Location.objects.get(name='Our House')
        self.assertEqual(location.svg_view_box_str, NEW_VIEW_BOX_STR)
        self.assertEqual(location.views.count(), 1)

    def test_rejects_svg_without_viewbox(self):
        response = self.client.post(reverse('floorplan3d_apply'), {
            'svg_content': '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            'location_id': str(self.location.id),
        })

        self.assertResponseStatusCode(response, 400)
        self.location.refresh_from_db()
        self.assertEqual(self.location.svg_view_box_str, '0 0 2000 2000')

    def test_rejects_malformed_xml(self):
        response = self.client.post(reverse('floorplan3d_apply'), {
            'svg_content': '<svg',
            'location_id': str(self.location.id),
        })

        self.assertResponseStatusCode(response, 400)

    def test_rejects_missing_content(self):
        response = self.client.post(reverse('floorplan3d_apply'), {'location_id': str(self.location.id)})

        self.assertResponseStatusCode(response, 400)

    def test_unknown_location_is_404(self):
        response = self.client.post(reverse('floorplan3d_apply'), {
            'svg_content': DESIGNER_SVG,
            'location_id': '999999',
        })

        self.assertResponseStatusCode(response, 404)

    def test_strips_dangerous_content(self):
        svg = DESIGNER_SVG.replace('</svg>', '<script>alert(1)</script></svg>')
        response = self.client.post(reverse('floorplan3d_apply'), {
            'svg_content': svg,
            'location_id': str(self.location.id),
        })

        self.assertSuccessResponse(response)
        self.location.refresh_from_db()
        fragment = default_storage.open(self.location.svg_fragment_filename).read()
        if isinstance(fragment, bytes):
            fragment = fragment.decode('utf-8')
        self.assertNotIn('script', fragment)
