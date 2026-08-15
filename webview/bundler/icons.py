"""
Generate platform icon sets (.ico, .icns, PNGs) from a single source image.
"""

from __future__ import annotations

import os

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]
PNG_SIZES = [32, 128, 256, 512]


def generate(source_path: str, output_dir: str) -> list[str]:
    """
    Generate icon.ico, icon.icns, and a set of icon-<size>.png files from
    source_path into output_dir. Returns the list of generated file paths.
    Requires Pillow (pip install pywebview2[cli]).
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            'Icon generation requires Pillow. Install it with `pip install pywebview2[cli]`.'
        ) from e

    if not os.path.exists(source_path):
        raise FileNotFoundError(f'Icon source not found: {source_path}')

    os.makedirs(output_dir, exist_ok=True)
    source = Image.open(source_path).convert('RGBA')
    generated = []

    ico_path = os.path.join(output_dir, 'icon.ico')
    source.save(ico_path, format='ICO', sizes=[(s, s) for s in ICO_SIZES])
    generated.append(ico_path)

    icns_path = os.path.join(output_dir, 'icon.icns')
    try:
        source.save(icns_path, format='ICNS', sizes=[(s, s) for s in ICNS_SIZES])
        generated.append(icns_path)
    except (ValueError, OSError):
        # Pillow's ICNS writer requires specific square sizes; skip rather than fail the whole run
        pass

    for size in PNG_SIZES:
        png_path = os.path.join(output_dir, f'icon-{size}.png')
        source.resize((size, size), Image.LANCZOS).save(png_path, format='PNG')
        generated.append(png_path)

    return generated
