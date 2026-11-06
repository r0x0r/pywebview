"""Snap geometry for frameless windows.

A frameless window on Windows loses the system's edge snapping: the caption is gone, and the web
content is hosted in a child window that answers ``WM_NCHITTEST`` with ``HTCLIENT`` for every point,
so the top-level window is never asked whether the cursor is over a caption or a resize border. A
drag started from the page is therefore a plain move and the shell never offers a snap target.

``webview.settings['SNAP_ON_DRAG']`` closes that gap from the page side: while a drag region is being
dragged the page tracks the pointer, reports the zone it is in, and on release reports the work area
of the screen it is on. This module turns that into the window rectangle to apply. The zone maths
live here rather than in JavaScript so they can be unit tested; the browser side only decides *which*
zone the cursor is in, which needs the screen's work area it already knows.

The preview overlay that shows where the window will land is platform specific - on Windows it is a
layered, click-through window - so it lives in the platform backends and the functions below forward
to it.
"""

from __future__ import annotations

import sys

ZONES = ('left', 'right', 'max', 'tl', 'tr', 'bl', 'br')


def rect_for_zone(
    zone: str | None, work_area: tuple[int, int, int, int]
) -> tuple[int, int, int, int] | None:
    """Return the ``(x, y, width, height)`` a snap ``zone`` maps to inside ``work_area``.

    ``work_area`` is ``(x, y, width, height)`` of a screen's work area, i.e. the screen minus the
    taskbar/dock. ``left``/``right`` take half the work area, ``max`` all of it and the four corner
    zones a quarter. Returns ``None`` for an unknown or missing zone, so callers can treat it as
    "no snap requested".
    """
    if zone not in ZONES:
        return None

    x, y, width, height = (int(value) for value in work_area)
    half_w, half_h = width // 2, height // 2
    rest_w, rest_h = width - half_w, height - half_h

    return {
        'left': (x, y, half_w, height),
        'right': (x + half_w, y, rest_w, height),
        'max': (x, y, width, height),
        'tl': (x, y, half_w, half_h),
        'tr': (x + half_w, y, rest_w, half_h),
        'bl': (x, y + half_h, half_w, rest_h),
        'br': (x + half_w, y + half_h, rest_w, rest_h),
    }[zone]


def show_preview(rect: tuple[int, int, int, int] | None) -> bool:
    """Show (or hide, with ``None``) the snap preview overlay, if the platform has one."""
    if sys.platform != 'win32':
        return False

    from webview.platforms.win32 import show_snap_preview

    return show_snap_preview(rect)


def hide_preview() -> bool:
    """Hide the snap preview overlay."""
    if sys.platform != 'win32':
        return False

    from webview.platforms.win32 import hide_snap_preview

    return hide_snap_preview()


def warm_up_preview() -> None:
    """Create the overlay ahead of the first drag: creating it lazily stalls that drag."""
    if sys.platform != 'win32':
        return

    from webview.platforms.win32 import warm_up_snap_preview

    warm_up_snap_preview()


def stop_preview() -> None:
    """Destroy the overlay, e.g. when the last window it belonged to is gone."""
    if sys.platform != 'win32':
        return

    from webview.platforms.win32 import stop_snap_preview

    stop_snap_preview()
