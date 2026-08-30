import os

import pytest

import webview.store as store
from webview.errors import WebViewException


@pytest.fixture
def tmp_store(tmp_path):
    return store.Store(str(tmp_path / 'test.json'))


class TestStore:
    def test_get_default_missing_key(self, tmp_store):
        assert tmp_store.get('missing') is None
        assert tmp_store.get('missing', 'fallback') == 'fallback'

    def test_set_and_get(self, tmp_store):
        tmp_store.set('name', 'pywebview')
        assert tmp_store.get('name') == 'pywebview'

    def test_set_overwrites(self, tmp_store):
        tmp_store.set('count', 1)
        tmp_store.set('count', 2)
        assert tmp_store.get('count') == 2

    def test_nested_json_values(self, tmp_store):
        tmp_store.set('nested', {'a': [1, 2, 3], 'b': {'c': True}})
        assert tmp_store.get('nested') == {'a': [1, 2, 3], 'b': {'c': True}}

    def test_has(self, tmp_store):
        tmp_store.set('name', 'pywebview')
        assert tmp_store.has('name') is True
        assert tmp_store.has('missing') is False

    def test_keys(self, tmp_store):
        tmp_store.set('a', 1)
        tmp_store.set('b', 2)
        assert sorted(tmp_store.keys()) == ['a', 'b']

    def test_delete(self, tmp_store):
        tmp_store.set('name', 'pywebview')
        tmp_store.delete('name')
        assert tmp_store.has('name') is False

    def test_delete_nonexistent_is_noop(self, tmp_store):
        tmp_store.delete('never-existed')  # must not raise

    def test_clear(self, tmp_store):
        tmp_store.set('a', 1)
        tmp_store.set('b', 2)
        tmp_store.clear()
        assert tmp_store.keys() == []

    def test_persists_across_instances(self, tmp_path):
        path = str(tmp_path / 'test.json')
        store.Store(path).set('name', 'pywebview')

        reloaded = store.Store(path)
        assert reloaded.get('name') == 'pywebview'

    def test_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / 'nested' / 'dir' / 'test.json')
        s = store.Store(path)
        s.set('a', 1)
        assert os.path.exists(path)

    def test_invalid_json_raises_clear_error(self, tmp_path):
        path = str(tmp_path / 'bad.json')
        with open(path, 'w') as f:
            f.write('not valid json{{{')

        with pytest.raises(WebViewException, match='invalid JSON'):
            store.Store(path)

    def test_non_object_json_raises(self, tmp_path):
        path = str(tmp_path / 'list.json')
        with open(path, 'w') as f:
            f.write('[1, 2, 3]')

        with pytest.raises(WebViewException, match='JSON object'):
            store.Store(path)

    def test_missing_file_starts_empty(self, tmp_path):
        s = store.Store(str(tmp_path / 'does-not-exist.json'))
        assert s.keys() == []


class TestDefaultStoreModuleFunctions:
    @pytest.fixture(autouse=True)
    def _isolate_default_store(self, tmp_path, monkeypatch):
        monkeypatch.setattr(store, '_default_store', None)
        monkeypatch.setattr(store, 'app_data_dir', lambda: str(tmp_path))
        yield
        monkeypatch.setattr(store, '_default_store', None)

    def test_module_level_roundtrip(self):
        store.set('key', 'value')
        assert store.get('key') == 'value'
        assert store.has('key') is True
        store.delete('key')
        assert store.get('key') is None
