"""Snap-zone geometry for frameless windows (webview.snapping)."""

from __future__ import annotations

import pytest

from webview.snapping import rect_for_zone

WORK_AREA = (0, 0, 2560, 1400)


class TestRectForZone:
    def test_halves_split_the_work_area(self):
        assert rect_for_zone('left', WORK_AREA) == (0, 0, 1280, 1400)
        assert rect_for_zone('right', WORK_AREA) == (1280, 0, 1280, 1400)

    def test_max_fills_the_work_area(self):
        assert rect_for_zone('max', WORK_AREA) == (0, 0, 2560, 1400)

    def test_corners_are_quarters(self):
        assert rect_for_zone('tl', WORK_AREA) == (0, 0, 1280, 700)
        assert rect_for_zone('tr', WORK_AREA) == (1280, 0, 1280, 700)
        assert rect_for_zone('bl', WORK_AREA) == (0, 700, 1280, 700)
        assert rect_for_zone('br', WORK_AREA) == (1280, 700, 1280, 700)

    def test_work_area_offsets_are_respected(self):
        """A second monitor's work area starts somewhere else - zones must be relative to it."""
        second = (2560, 40, 1920, 1040)

        assert rect_for_zone('left', second) == (2560, 40, 960, 1040)
        assert rect_for_zone('max', second) == (2560, 40, 1920, 1040)
        assert rect_for_zone('br', second) == (3520, 560, 960, 520)

    def test_taskbar_height_is_respected(self):
        """The work area excludes the taskbar, so a 2560x1440 screen with a 40px taskbar is 1400 tall."""
        assert rect_for_zone('max', (0, 0, 2560, 1400))[3] == 1400

    @pytest.mark.parametrize('zone', [None, '', 'middle', 'LEFT', 'left '])
    def test_unknown_zones_return_none(self, zone):
        assert rect_for_zone(zone, WORK_AREA) is None

    def test_odd_sizes_do_not_overlap_or_gap(self):
        """Halves must tile the work area exactly, even for odd widths/heights."""
        area = (0, 0, 1281, 1401)
        left = rect_for_zone('left', area)
        right = rect_for_zone('right', area)
        tl = rect_for_zone('tl', area)
        br = rect_for_zone('br', area)

        assert left[0] + left[2] == right[0]
        assert right[0] + right[2] == area[2]
        assert tl[0] + tl[2] == br[0]
        assert br[0] + br[2] == area[2]
        assert left[1] + left[3] == area[3]
        assert tl[1] + tl[3] == br[1]
