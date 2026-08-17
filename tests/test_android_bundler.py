from configparser import ConfigParser

from webview.bundler.android import DEFAULT_REQUIREMENTS, write_buildozer_spec


def test_android_spec_does_not_pull_kivy(tmp_path):
    config = {
        'productName': 'Test app',
        'identifier': 'com.example.testapp',
        'version': '1.0.0',
        'entry': str(tmp_path / 'main.py'),
        'bundle': {},
        'mobile': {'android': {}},
    }

    spec_path = write_buildozer_spec(config, str(tmp_path))

    parser = ConfigParser()
    parser.read(spec_path)
    requirements = parser['app']['requirements'].split(',')

    assert 'kivy' not in requirements
    assert requirements == DEFAULT_REQUIREMENTS.split(',')
