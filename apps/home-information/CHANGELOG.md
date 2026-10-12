<img src="src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Change Log

_High-level view of the applications change history.  See releases and commits for more fine-grained history._

- v1.2.3 : June 11, 2026 : Edit-mode item picker now surfaces previously-hidden delegate ("Paired Items") entities in both the LocationView and Collection editors, with single-pass query building, reordered sections, and search/filter that reveals matches inside collapsed groups; restored SVG path click-to-extend with a cross-browser add-segment key and global Ctrl+S/Ctrl+R canvas scale/rotate; new INFORMATION LocationView type whose entity tap opens the details/edit modal instead of status (long-press for status); Home Assistant printer device support plus ping/text simulator devices; status-panel fallback styling and attribute auto-link parsing improvements.
- v1.2.2 : June 8, 2026 : Simulator "Scenes" record/playback with an annotated timeline and live status polling, plus pre-canned camera/event video playback; status-display recency decay now anchors on the event end time and entity-state history rows share the live status styling (incl. a temperature color ramp); entity edit pane gains an add/remove-from-view (and collection) control with Geometry collapsed by default; side-panel width clamp on wide screens and responsive portrait-video letterboxing; user-configurable status polling interval; plus assorted simulator, pan/zoom, and entity-placement fixes and refactors.
- v1.2.1 : June 3, 2026 : Installer falls back to a non-hidden `~/home-information` directory when Docker cannot read dot-directories (e.g. snap Docker); clearer startup warnings for malformed `HI_EXTRA_HOST_URLS` values; server environment-config hardening and test coverage; two-story profile background floor fix.
- v1.2.0 : June 3, 2026 : New integrations (Frigate NVR, Immich, Paperless-ngx, HomeBox Connect/Import); Integration Capabilities, Entity-as-Reference, and External Reference (Linked Content) frameworks; EntityStatusPanel framework with per-EntityState merged history view; media thumbnail previews and video snapshot/live-feed improvements; Django 5.2 LTS upgrade; icon and state-panel normalization; Docker Compose management workflow; weather API simulators; plus assorted navigation, rendering, and query-performance fixes.
- v1.1.5 : March 29, 2026 : HomeBox integration, entity archiving, soft-delete attributes, HA import allowlist filtering, new entity types (pool equipment, EV charger, energy storage, water treatment, etc.), integration logo display, dynamic entity sizing, security dependency updates, weather resilience improvements.
- v1.1.4 : January 26, 2026 : Attribute ordering improvements, restore-to-default settings functionality, security updates including urllib3 CVE patch.
- v1.1.3 : October 6, 2025 : Home Assistant converter bug fixes, comprehensive Unraid template with all environment variables.
- v1.1.2 : September 26, 2025 : Bug fixes for Home Assistant temperature controller, Unraid template improvements.
- v1.1.1 : September 25, 2025 : UI uniformity improvements, documentation updates, and edit mode styling enhancements.
- v1.1.0 : September 16, 2025 : Video stream browser, starting profiles, integration improvements.
- v1.0.2 : September 9, 2025 : Min/max temperature fixes, audio fixes, and installation improvements.
- v1.0.1 : September 7, 2025 : Docker configuration fixes and release process improvements.
- v1.0.0 : September 6, 2025 : Feature complete version with many UI improvements.
- v0.2.0 : August 26, 2025 : Auto-view switching and video stream browsing features.
- v0.1.0 : August 17, 2025 : Added weather API intgerations and alert audio.
- v0.0.4 : February 18, 2025 : Docker organization improvements.
- v0.0.3 : February 16, 2025 : Fixed initial experience issues.
- v0.0.2 : February 14, 2025 : Fixes for release process bugs.
- v0.0.1 : February 14, 2025 : Initial public version with basic functionality working.
