import asyncio
import json
import threading
from types import SimpleNamespace

import pytest

import webview
from webview.util import _TOKEN, js_bridge_call


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    ready = threading.Event()

    def run():
        asyncio.set_event_loop(loop)
        loop.call_soon(ready.set)
        loop.run_forever()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

    thread = threading.Thread(target=run)
    thread.start()
    assert ready.wait(5)
    webview._state.data['event_loop'] = loop
    yield loop
    if loop.is_running():
        loop.call_soon_threadsafe(loop.stop)
    thread.join(5)
    assert not thread.is_alive()


def dispatch(func, *, exposed=False, token=_TOKEN):
    done = threading.Event()
    response = {}

    def evaluate_js(code):
        # Decode the existing native bridge's JS string literal / JSON envelope.
        payload = code.split("value: '", 1)[1].rsplit("'}", 1)[0]
        response['value'] = json.loads(payload.replace("\\'", "'").replace('\\\\', '\\'))
        response['error'] = 'isError: true' in code
        done.set()

    window = SimpleNamespace(
        gui=SimpleNamespace(renderer='edgechromium'),
        _functions={'test': func} if exposed else {},
        _js_api=SimpleNamespace(test=func),
        evaluate_js=evaluate_js,
    )
    js_bridge_call(window, 'test', [], 'test-value', token=token)
    return done, response


@pytest.mark.parametrize('exposed', [False, True])
def test_coroutine_result(event_loop, exposed):
    async def method():
        assert asyncio.get_running_loop() is event_loop
        await asyncio.sleep(0.01)
        return {'answer': 42}

    done, response = dispatch(method, exposed=exposed)
    assert done.wait(5)
    assert response == {'value': {'answer': 42}, 'error': False}


def test_sync_returning_coroutine(event_loop):
    async def method():
        return 42

    done, response = dispatch(lambda: method())
    assert done.wait(5)
    assert response == {'value': 42, 'error': False}


@pytest.mark.parametrize('configured', [False, True])
def test_sync_compatibility(configured, event_loop):
    if not configured:
        webview._state['event_loop'] = None
    done, response = dispatch(lambda: 42)
    assert done.wait(5)
    assert response == {'value': 42, 'error': False}


def test_async_exception(event_loop):
    async def method():
        raise ValueError('async failure')

    done, response = dispatch(method)
    assert done.wait(5)
    assert response['error']
    assert response['value']['name'] == 'ValueError'
    assert response['value']['message'] == 'async failure'


def test_async_timeout_exception(event_loop):
    async def method():
        raise TimeoutError('application timeout')

    done, response = dispatch(method)
    assert done.wait(5)
    assert response['error']
    assert response['value']['name'] == 'TimeoutError'
    assert response['value']['message'] == 'application timeout'


def test_submission_failure_closes_coroutine(event_loop, monkeypatch):
    async def method():
        return 42

    def fail_submission(coro, loop):
        raise RuntimeError('loop closed during submission')

    monkeypatch.setattr(asyncio, 'run_coroutine_threadsafe', fail_submission)
    coro = method()
    try:
        done, response = dispatch(lambda: coro)
        assert done.wait(5)
        assert response['error']
        assert response['value']['message'] == 'loop closed during submission'
        assert coro.cr_frame is None
    finally:
        coro.close()


@pytest.mark.parametrize('status', ['missing', 'stopped', 'closed'])
def test_invalid_loop_closes_coroutine(status):
    loop = None if status == 'missing' else asyncio.new_event_loop()
    if status == 'closed':
        loop.close()
    webview._state.data['event_loop'] = loop

    async def method():
        return 42

    coro = method()
    try:
        done, response = dispatch(lambda: coro)
        assert done.wait(5)
        assert response['error']
        assert response['value']['name'] == 'RuntimeError'
        assert 'running event_loop' in response['value']['message']
        assert coro.cr_frame is None
    finally:
        coro.close()
        if loop is not None and not loop.is_closed():
            loop.close()


def test_concurrent_calls(event_loop):
    arrived = []
    both_started = asyncio.Event()

    async def method():
        arrived.append(1)
        if len(arrived) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), 2)
        return 42

    calls = [dispatch(method), dispatch(method)]
    for done, response in calls:
        assert done.wait(5)
        assert response == {'value': 42, 'error': False}


def test_stopped_loop_releases_bridge_thread(event_loop):
    started = threading.Event()

    async def method():
        started.set()
        await asyncio.Event().wait()

    done, response = dispatch(method)
    assert started.wait(5)
    event_loop.call_soon_threadsafe(event_loop.stop)
    assert done.wait(5)
    assert response['error']


def test_cancelled_coroutine(event_loop):
    async def method():
        raise asyncio.CancelledError

    done, response = dispatch(method)
    assert done.wait(5)
    assert response['error']
    assert response['value']['name'] == 'CancelledError'


@pytest.mark.parametrize('status', ['stopped', 'closed'])
def test_start_rejects_invalid_loop(status):
    loop = asyncio.new_event_loop()
    if status == 'closed':
        loop.close()
    webview.create_window('Async loop validation')
    try:
        with pytest.raises(ValueError, match='event_loop must be running'):
            webview.start(event_loop=loop)
    finally:
        if not loop.is_closed():
            loop.close()


def test_start_stores_loop_without_taking_ownership(event_loop, monkeypatch):
    window = SimpleNamespace(original_url=None, _initialize=lambda *a, **kw: False)
    gui = SimpleNamespace(renderer='test', create_window=lambda window: None)
    monkeypatch.setattr(webview, 'windows', [window])
    monkeypatch.setattr(webview, 'initialize', lambda backend: gui)
    webview.start(event_loop=event_loop)
    assert webview._state['event_loop'] is event_loop
    assert event_loop.is_running()
    webview.start()
    assert webview._state['event_loop'] is None
    assert event_loop.is_running()
