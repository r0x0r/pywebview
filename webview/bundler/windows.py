"""
Windows installer generation: .msi via WiX, .exe via NSIS.

This module only generates the tool-specific config file (.wxs / .nsi) and
shells out to the external toolchain -- it never reimplements WiX or NSIS.
Neither tool is required to be installed to generate the config files; they
are required only to actually build the installer.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from typing import Any

from webview.bundler._templating import render


class InstallerError(Exception):
    pass


def _find_exe(source_dir: str, product_name: str) -> str:
    candidate = os.path.join(source_dir, f'{product_name}.exe')
    if os.path.exists(candidate):
        return f'{product_name}.exe'
    for name in os.listdir(source_dir):
        if name.lower().endswith('.exe'):
            return name
    raise InstallerError(f'No .exe found in {source_dir}')


def build_msi(config: dict[str, Any], source_dir: str, output_dir: str) -> str:
    product_name = config['productName']
    exe_name = _find_exe(source_dir, product_name)
    upgrade_code = str(uuid.uuid5(uuid.NAMESPACE_DNS, config['identifier']))

    # WiX v4 replaced the whole candle/light CLI with a single `wix build`
    # command, and its .wxs schema changed along with it (simplified
    # <Package>/<StandardDirectory> authoring under the
    # http://wixtoolset.org/schemas/v4/wxs namespace, vs. v3's
    # <Product>/<Directory Id="TARGETDIR"> authoring under
    # http://schemas.microsoft.com/wix/2006/wi). The two are not
    # interchangeable -- feeding a v4-schema document to v3's candle.exe
    # fails immediately with CNDL0199 ("incorrect namespace"), so the
    # template picked here has to match whichever toolchain build_msi()
    # is actually about to invoke below, not just whichever happens to be
    # written first.
    wix_exe = shutil.which('wix')
    has_legacy_wix = bool(shutil.which('candle') and shutil.which('light'))
    template_name = 'app.v3.wxs.jinja' if (has_legacy_wix and not wix_exe) else 'app.wxs.jinja'

    wxs_content = render(
        template_name,
        product_name=product_name,
        version=config['version'],
        upgrade_code=upgrade_code,
        source_dir=source_dir,
        exe_name=exe_name,
    )

    os.makedirs(output_dir, exist_ok=True)
    wxs_path = os.path.join(output_dir, f'{product_name}.wxs')
    with open(wxs_path, 'w', encoding='utf-8') as f:
        f.write(wxs_content)

    msi_path = os.path.join(output_dir, f'{product_name}.msi')
    if wix_exe:
        subprocess.run([wix_exe, 'build', wxs_path, '-o', msi_path], check=True)
    elif has_legacy_wix:
        wixobj_path = os.path.join(output_dir, f'{product_name}.wixobj')
        subprocess.run(['candle', wxs_path, '-o', wixobj_path], check=True)
        subprocess.run(['light', wixobj_path, '-o', msi_path], check=True)
    else:
        raise InstallerError(
            f'WiX Toolset not found on PATH. Generated {wxs_path} (WiX v4 schema); '
            'install WiX (v3: candle/light, v4+: wix) to build the .msi.'
        )

    return msi_path


def build_nsis_exe(config: dict[str, Any], source_dir: str, output_dir: str) -> str:
    product_name = config['productName']
    exe_name = _find_exe(source_dir, product_name)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{product_name}-setup.exe')

    nsi_content = render(
        'installer.nsi.jinja',
        product_name=product_name,
        source_dir=source_dir,
        exe_name=exe_name,
        output_path=output_path,
    )
    nsi_path = os.path.join(output_dir, f'{product_name}.nsi')
    with open(nsi_path, 'w', encoding='utf-8') as f:
        f.write(nsi_content)

    makensis = shutil.which('makensis')
    if not makensis:
        raise InstallerError(
            f'NSIS not found on PATH. Generated {nsi_path}; install NSIS (makensis) to build the .exe.'
        )
    subprocess.run([makensis, nsi_path], check=True)

    return output_path
