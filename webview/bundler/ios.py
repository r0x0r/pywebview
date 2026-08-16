"""iOS simulator packaging through the native Xcode host."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


class IOSBuildError(Exception):
    pass


def build(config: dict[str, Any], project_dir: str, output_dir: str) -> str:
    """Build the current native iOS host for the simulator on macOS.

    The embedded Python runtime is intentionally not staged by this first
    target. It builds the native host and provides the CI artifact that will
    later become the full application bundle.
    """
    if platform.system() != 'Darwin':
        raise IOSBuildError('iOS builds require a macOS GitHub Actions runner with Xcode.')

    source_dir = Path(__file__).resolve().parents[2] / 'interop' / 'ios'
    template_project = source_dir / 'PyWebViewHost.xcodeproj'
    if not template_project.exists():
        raise IOSBuildError(f'iOS host project is missing: {template_project}')

    staging_dir = Path(output_dir).resolve() / 'ios'
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    for item in source_dir.iterdir():
        if item.name == 'README.md' or item.name == 'PYTHON_RUNTIME.md':
            continue
        destination = staging_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    runtime_source = os.environ.get('PYWEBVIEW_IOS_PYTHON_XCFRAMEWORK')
    if runtime_source:
        runtime_path = Path(runtime_source).expanduser().resolve()
        if not runtime_path.is_dir():
            raise IOSBuildError(
                f'PYWEBVIEW_IOS_PYTHON_XCFRAMEWORK does not point to a directory: {runtime_path}'
            )
        shutil.copytree(runtime_path, staging_dir / 'Python.xcframework')
        _add_python_framework(staging_dir / 'PyWebViewHost.xcodeproj' / 'project.pbxproj')

    frontend_source = Path(project_dir) / config.get('frontendDist', 'frontend')
    if frontend_source.is_dir():
        shutil.copytree(frontend_source, staging_dir / 'frontend')
        _add_frontend_resources(staging_dir / 'PyWebViewHost.xcodeproj' / 'project.pbxproj')

    entry_source = Path(project_dir) / config['entry']
    if entry_source.is_file():
        python_app = staging_dir / 'python' / 'app'
        python_app.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry_source, python_app / entry_source.name)

    ios_config = config.get('mobile', {}).get('ios', {})
    product_name = config['productName']
    bundle_id = config['identifier']
    deployment_target = ios_config.get('deploymentTarget', '15.0')
    derived_data = staging_dir / '.derived-data'
    project = staging_dir / 'PyWebViewHost.xcodeproj'
    command = [
        'xcodebuild',
        '-project',
        str(project),
        '-scheme',
        ios_config.get('scheme') or 'PyWebViewHost',
        '-sdk',
        'iphonesimulator',
        '-destination',
        'generic/platform=iOS Simulator',
        '-derivedDataPath',
        str(derived_data),
        f'PRODUCT_NAME={product_name}',
        f'PRODUCT_BUNDLE_IDENTIFIER={bundle_id}',
        f'IPHONEOS_DEPLOYMENT_TARGET={deployment_target}',
        f'MARKETING_VERSION={config["version"]}',
        'CODE_SIGNING_ALLOWED=NO',
        'build',
    ]
    try:
        subprocess.run(command, cwd=project_dir, check=True)
    except FileNotFoundError as e:
        raise IOSBuildError('xcodebuild was not found. Install Xcode on the macOS runner.') from e
    except subprocess.CalledProcessError as e:
        raise IOSBuildError(f'xcodebuild failed with exit code {e.returncode}.') from e

    artifact = derived_data / 'Build' / 'Products' / 'Debug-iphonesimulator' / f'{product_name}.app'
    if not artifact.exists():
        raise IOSBuildError(f'xcodebuild completed but produced no simulator app: {artifact}')
    return os.fspath(artifact)


def _add_frontend_resources(project_file: Path) -> None:
    """Add the staged frontend directory as an Xcode folder resource."""
    marker = '/* End PBXFileReference section */'
    build_marker = '/* End PBXBuildFile section */'
    resources_marker = '/* End PBXResourcesBuildPhase section */'
    content = project_file.read_text(encoding='utf-8')

    content = content.replace(
        marker,
        '\t\tA00000110000000000000009 /* frontend */ = {isa = PBXFileReference; lastKnownFileType = folder; path = frontend; sourceTree = "<group>"; };\n'
        + marker,
        1,
    )
    content = content.replace(
        build_marker,
        '\t\tA00000010000000000000006 /* frontend in Resources */ = {isa = PBXBuildFile; fileRef = A00000110000000000000009 /* frontend */; };\n'
        + build_marker,
        1,
    )
    content = content.replace(
        'children = (A00000110000000000000006,); name = "Supporting Files";',
        'children = (A00000110000000000000006, A00000110000000000000009,); name = "Supporting Files";',
        1,
    )
    content = content.replace(
        'buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing',
        'buildActionMask = 2147483647; files = (A00000010000000000000006,); runOnlyForDeploymentPostprocessing',
        1,
    )
    if resources_marker not in content:
        raise IOSBuildError('Could not update the iOS project resources phase.')
    project_file.write_text(content, encoding='utf-8')


def _add_python_framework(project_file: Path) -> None:
    """Link and embed Python.xcframework in a runtime-enabled staging project."""
    content = project_file.read_text(encoding='utf-8')
    content = content.replace(
        '/* End PBXBuildFile section */',
        '\t\tA00000010000000000000007 /* Python.xcframework in Frameworks */ = {isa = PBXBuildFile; fileRef = A00000110000000000000010 /* Python.xcframework */; };\n'
        '\t\tA00000010000000000000008 /* Python.xcframework in Embed Frameworks */ = {isa = PBXBuildFile; fileRef = A00000110000000000000010 /* Python.xcframework */; settings = {ATTRIBUTES = (CodeSignOnCopy, RemoveHeadersOnCopy, ); }; };\n'
        '/* End PBXBuildFile section */',
        1,
    )
    content = content.replace(
        '/* End PBXFileReference section */',
        '\t\tA00000110000000000000010 /* Python.xcframework */ = {isa = PBXFileReference; lastKnownFileType = wrapper.xcframework; path = Python.xcframework; sourceTree = "<group>"; };\n'
        '/* End PBXFileReference section */',
        1,
    )
    content = content.replace(
        'files = (); runOnlyForDeploymentPostprocessing = 0; };\n/* End PBXFrameworksBuildPhase section */',
        'files = (A00000010000000000000007,); runOnlyForDeploymentPostprocessing = 0; };\n/* End PBXFrameworksBuildPhase section */',
        1,
    )
    content = content.replace(
        'children = (A00000110000000000000006, A00000110000000000000009,); name = "Supporting Files";',
        'children = (A00000110000000000000006, A00000110000000000000009, A00000110000000000000010,); name = "Supporting Files";',
        1,
    )
    content = content.replace(
        'A00000210000000000000003, A00000210000000000000004,); buildRules',
        'A00000210000000000000003, A00000210000000000000004, A00000210000000000000005,); buildRules',
        1,
    )
    content = content.replace(
        '/* End PBXShellScriptBuildPhase section */',
        '/* End PBXShellScriptBuildPhase section */\n\n/* Begin PBXCopyFilesBuildPhase section */\n\t\tA00000210000000000000005 /* Embed Frameworks */ = {isa = PBXCopyFilesBuildPhase; buildActionMask = 2147483647; dstPath = ""; dstSubfolderSpec = 10; files = (A00000010000000000000008,); runOnlyForDeploymentPostprocessing = 0; };\n/* End PBXCopyFilesBuildPhase section */',
        1,
    )
    project_file.write_text(content, encoding='utf-8')
