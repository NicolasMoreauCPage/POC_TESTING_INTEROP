# Temporary file to fix conftest.py
import pytest
from app.app import create_app
from app.db import get_session, engine
from fastapi import FastAPI
import os
import uvicorn
from multiprocessing import Process
from playwright.sync_api import Page, sync_playwright


def run_app(host, port):
    """Function to run the application in a separate process"""
    app = create_app()
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        timeout_keep_alive=0,
    )
    server = uvicorn.Server(config)
    server.run()


@pytest.fixture(scope="session")
def server():
    """Fixture that starts a FastAPI server for UI tests"""
    import socket
    import time
    import httpx

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]

    host = "127.0.0.1"

    # Start server in a separate process
    # Ensure the DB schema exists on disk so the server process can access it
    try:
        from sqlmodel import SQLModel
        from app.db import engine
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass

    proc = Process(target=run_app, args=(host, port))
    proc.start()

    # Wait for server to be ready by checking root URL (more robust)
    url = f"http://{host}:{port}"
    max_retries = 60

    for i in range(max_retries):
        try:
            response = httpx.get(url, follow_redirects=True)
            if response.status_code < 400:
                break
        except Exception as e:
            if i == max_retries - 1:
                raise Exception(f"Server failed to start (timeout): {str(e)}")
            time.sleep(0.5)

    yield url

    # Cleanup: stop the server
    proc.terminate()
    proc.join(timeout=5)
    if proc.is_alive():
        proc.kill()
        proc.join()


@pytest.fixture(scope="session")
def test_server(server):
    """Returns the test server URL"""
    return server


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Browser context configuration with improved defaults"""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        },
        "accept_downloads": False,
        "java_script_enabled": True,
        "ignore_https_errors": True,
        "bypass_csp": True,
    }


@pytest.fixture(scope="session")
def browser(playwright):
    """Session-scoped browser with error handling"""
    browser = playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    try:
        yield browser
    finally:
        try:
            browser.close()
        except Exception:
            pass


@pytest.fixture
def page(browser, test_server):
    """Fixture that creates a new page with timeout configuration"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
        bypass_csp=True,
        accept_downloads=False,
    )
    page = context.new_page()
    # Capture browser console logs to help debugging client-side behavior
    try:
        page.on('console', lambda msg: print(f"BROWSER CONSOLE: {msg.type}: {msg.text}"))
    except Exception:
        # Playwright versions/signatures vary; best-effort only
        pass
    page.set_default_timeout(10000)  # 10s default for most operations

    # Ensure a GHT context is selected in the browser session to bypass guards
    # and make UI routes like /patients/new/ directly accessible in tests.
    try:
        from sqlmodel import Session as DBSession, select
        from app.db import engine as db_engine
        from app.models_structure_fhir import GHTContext

        with DBSession(db_engine) as s:
            ctx = s.exec(select(GHTContext)).first()
            if not ctx:
                ctx = GHTContext(name="Test GHT", code="TEST_GHT", is_active=True)
                s.add(ctx)
                s.commit()
                s.refresh(ctx)
            # Hit the selection route using the browser to set the session cookie
            page.goto(f"{test_server}/admin/ght/{ctx.id}", wait_until="domcontentloaded")
    except Exception:
        # If anything fails here, tests may redirect to /admin/ght and time out;
        # leave it best-effort to not mask other errors.
        pass

    try:
        yield page
    finally:
        context.close()