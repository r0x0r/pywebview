"""
PyInstaller orchestration: turn a pywebview2.conf.json + project dir into a
frozen executable. Relies on webview/__pyinstaller/hook-webview.py being
auto-discovered via the `pyinstaller40.hook-dirs` entry point already
registered in pyproject.toml -- this module never touches that hook directly.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any


class FreezeError(Exception):
    pass


# Linux/GTK only. PyInstaller's gi/PyGObject hooks bundle the core GLib/
# GObject-Introspection/GTK stack (Python code imports gi.repository.GLib
# etc. directly, so static analysis sees it), but can't see that
# gi.repository.WebKit2's typelib will need libwebkit2gtk-4.1.so.0 (and
# its own transitive libgudev-1.0.so.0 dependency) at runtime -- those are
# dlopen'd via the typelib's "shared-library" attribute, invisible to
# static analysis, so they're never bundled and always resolve from the
# host system instead.
#
# Mixing a bundled (build-machine) glib/gtk/gdk-pixbuf/pango/atk/cairo
# stack with a host-resolved webkit2gtk/gudev is worse than bundling none
# of it: ELF dynamic linking keeps one loaded instance per SONAME per
# process, so once the bundled libglib-2.0.so.0 loads first (for the
# bundled GTK core), the host's libgudev/libwebkit2gtk reuse that same
# already-loaded instance instead of their own matching glib -- producing
# an "undefined symbol" crash the first time gi.repository.WebKit2 is
# touched (reproduced via a real AppImage build: libgudev's own dependency
# on glib resolved against the bundled, older glib.so instead of the
# host's, missing a symbol only the host's newer glib provides).
#
# _unbundle_host_gtk_stack() removes this whole graph from the frozen
# output after PyInstaller runs, so it resolves from the host consistently
# -- the same place webkit2gtk/gudev were already unavoidably coming from.
_LINUX_GTK_STACK_PREFIXES = (
    'libglib-2.0',
    'libgobject-2.0',
    'libgio-2.0',
    'libgmodule-2.0',
    'libgirepository-1.0',
    # GIO module plugins, dlopen'd by libgio-2.0 itself at runtime -- same
    # "must match whatever glib is actually active" requirement.
    'libgioenvironmentproxy',
    'libgiognomeproxy',
    'libgiognutls',
    'libgiolibproxy',
    'libdconfsettings',
    'libgtk-3',
    'libgdk-3',
    'libgdk_pixbuf-2.0',
    'libpixbufloader-',
    'libatk-1.0',
    'libatk-bridge-2.0',
    'libpango-1.0',
    'libpangocairo-1.0',
    'libpangoft2-1.0',
    'libcairo-gobject',
    'libcairo.so',  # plain libcairo too: gtk/pango's
    # own dependency, and they're being forced to the host here just the
    # same -- leaving only the -gobject binding bundled would just move
    # this exact mismatch down one layer instead of removing it.
    'libharfbuzz',
    'libepoxy',
    'libfribidi',
    'libthai',
    'libdatrie',
    'libgraphite2',
)

# Whole subdirectories PyInstaller's gi hooks collect into, alongside (not
# inside) the flat _internal/ tree the prefix list above covers -- entirely
# dedicated to this same graph, so removed wholesale rather than filtered:
# gi_typelibs/ is every .typelib PyInstaller bundled (all of them belong to
# this graph in practice -- nothing here uses gi.repository for anything
# outside GTK/WebKit rendering), and gio_modules/ is GIO's own dlopen'd
# module plugins (proxy/settings backends) plus their cache index, which
# would otherwise still reference the just-removed .so files by path.
_LINUX_GTK_STACK_SUBDIRS = ('gi_typelibs', 'gio_modules')


def _unbundle_host_gtk_stack(output_path: str) -> None:
    # --onedir only: onefile builds pack everything into a single
    # self-extracting executable with no persistent _internal/ directory
    # to post-process at build time.
    internal_dir = os.path.join(output_path, '_internal')
    if not os.path.isdir(internal_dir):
        return

    for name in os.listdir(internal_dir):
        path = os.path.join(internal_dir, name)
        if name in _LINUX_GTK_STACK_SUBDIRS and os.path.isdir(path):
            shutil.rmtree(path)
        elif name.startswith(_LINUX_GTK_STACK_PREFIXES) and os.path.isfile(path):
            os.remove(path)


def build_pyinstaller_args(config: dict[str, Any], project_dir: str, dist_dir: str) -> list[str]:
    bundle = config['bundle']
    pyinstaller_cfg = bundle.get('pyinstaller', {})

    entry = os.path.join(project_dir, config['entry'])
    args = [
        entry,
        '--name',
        config['productName'],
        '--distpath',
        dist_dir,
        '--workpath',
        os.path.join(dist_dir, '.work'),
        '--specpath',
        os.path.join(dist_dir, '.spec'),
        '--noconfirm',
    ]

    if pyinstaller_cfg.get('onefile'):
        args.append('--onefile')
    else:
        args.append('--onedir')

    icon = bundle.get('icon')
    if icon:
        ico_path = f'{icon}.ico' if not icon.endswith(('.ico', '.icns')) else icon
        if os.path.exists(os.path.join(project_dir, ico_path)):
            args += ['--icon', os.path.join(project_dir, ico_path)]

    for resource in bundle.get('resources', []):
        resource_path = os.path.join(project_dir, resource.rstrip('/*'))
        if os.path.exists(resource_path):
            sep = ';' if os.name == 'nt' else ':'
            dest = os.path.relpath(resource_path, project_dir)
            args += ['--add-data', f'{resource_path}{sep}{dest}']

    for exclude in pyinstaller_cfg.get('excludes', []):
        args += ['--exclude-module', exclude]

    args += pyinstaller_cfg.get('extraArgs', [])

    return args


def freeze(config: dict[str, Any], project_dir: str, dist_dir: str) -> str:
    """
    Run PyInstaller against the project's entry point. Returns the path to
    the frozen app directory/executable produced by PyInstaller.
    """
    try:
        import PyInstaller.__main__
    except ImportError as e:
        raise FreezeError(
            'PyInstaller is not installed. Install it with `pip install pyinstaller`.'
        ) from e

    entry_path = os.path.join(project_dir, config['entry'])
    if not os.path.exists(entry_path):
        raise FreezeError(f'Entry point not found: {entry_path}')

    os.makedirs(dist_dir, exist_ok=True)
    args = build_pyinstaller_args(config, project_dir, dist_dir)

    PyInstaller.__main__.run(args)

    output_path = os.path.join(dist_dir, config['productName'])
    if not os.path.exists(output_path):
        raise FreezeError(f'PyInstaller did not produce expected output at {output_path}')

    if sys.platform.startswith('linux'):
        _unbundle_host_gtk_stack(output_path)

    return output_path
