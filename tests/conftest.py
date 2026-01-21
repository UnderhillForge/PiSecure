import asyncio
import inspect
import pytest


def pytest_configure(config):
    # Register asyncio marker to silence unknown marker warnings
    config.addinivalue_line("markers", "asyncio: mark test as asyncio")


def _run_async(func, *args, **kwargs):
    """Run coroutine function in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(func(*args, **kwargs))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    # Wrap async fixtures so they run via asyncio without external plugin
    if inspect.iscoroutinefunction(fixturedef.func):
        original = fixturedef.func

        def sync_wrapper(*args, **kwargs):
            return _run_async(original, *args, **kwargs)

        fixturedef.func = sync_wrapper

    yield


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    # Execute async test functions using a local event loop
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        testargs = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        _run_async(test_func, **testargs)
        return True
    return None
