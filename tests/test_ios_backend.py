from types import SimpleNamespace

import pytest


@pytest.fixture
def ios_backend(monkeypatch):
    calls = []

    class Native:
        def __getattr__(self, name):
            def method(*args):
                calls.append((name, args))
                if name == 'get_size':
                    return (390, 844)
                if name == 'get_screens':
                    return []
                if name == 'evaluate_js':
                    return {'result': True}
                return None

            return method

    import sys

    monkeypatch.setitem(sys.modules, 'pywebview_ios', Native())
    sys.modules.pop('webview.platforms.ios', None)
    import importlib

    module = importlib.import_module('webview.platforms.ios')
    return module, calls


def test_ios_backend_delegates_core_operations(ios_backend):
    module, calls = ios_backend
    window = SimpleNamespace(uid='main', title='Test', real_url='https://example.com', html='')

    module.create_window(window)
    module.load_html('<h1>Test</h1>', '', 'main')
    assert module.evaluate_js('1 + 1', 'main') == {'result': True}
    assert module.get_size('main') == (390, 844)

    assert calls[:2] == [
        ('create_window', ('main', 'Test')),
        ('load_url', ('https://example.com', 'main')),
    ]


def test_ios_backend_rejects_desktop_file_dialogs(ios_backend):
    module, _ = ios_backend

    with pytest.raises(module.WebViewException, match='File dialogs'):
        module.create_file_dialog()


def test_ios_bundler_adds_frontend_resource(tmp_path):
    from webview.bundler.ios import _add_frontend_resources

    project = tmp_path / 'project.pbxproj'
    project.write_text(
        '''
/* Begin PBXBuildFile section */
/* End PBXBuildFile section */
/* Begin PBXFileReference section */
/* End PBXFileReference section */
children = (A00000110000000000000006,); name = "Supporting Files";
buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;
/* End PBXResourcesBuildPhase section */
''',
        encoding='utf-8',
    )

    _add_frontend_resources(project)
    result = project.read_text(encoding='utf-8')

    assert 'path = frontend;' in result
    assert 'frontend in Resources' in result
    assert 'files = (A00000010000000000000006,);' in result
