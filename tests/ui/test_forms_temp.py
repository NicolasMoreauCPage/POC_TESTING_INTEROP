import pytest, time, httpx
from urllib.parse import urljoin
from playwright.sync_api import expect

pytest.skip('Temporary local-only test; skip in CI', allow_module_level=True)

def wait_for_ready(url: str, max_retries: int = 30, delay: float = 0.5):
    """Wait for server to be ready."""
    for i in range(max_retries):
        try:
            response = httpx.get(url, follow_redirects=True, timeout=5.0)
            if response.status_code < 400:
                return True
        except Exception:
            pass
        if i < max_retries - 1:
            time.sleep(delay)
    return False

def safe_navigate(page, url: str, timeout_ms: int = 10000):
    """Safely navigate to a URL with retry on timeout"""
    max_retries = 3
    for i in range(max_retries):
        try:
            response = page.goto(url, timeout=timeout_ms)
            if response and response.ok:
                return True
        except Exception as e:
            if i == max_retries - 1:
                pytest.fail(f"Failed to navigate to {url}: {str(e)}")
            time.sleep(1)
    return False

@pytest.fixture(autouse=True)
def test_server():
    """Fast API test server"""
    # Import here so we don't get pytest collection errors
    from fastapi.testclient import TestClient
    from app.app import create_app
    app = create_app()
    return app

@pytest.mark.timeout(60)  # Set timeout for slow UI tests
def test_required_fields(page, test_server):
    """Test validation of required fields in the patient form."""
    from urllib.parse import urljoin
    test_url = urljoin('http://localhost:8000', '/')

    # Ensure server is ready
    assert wait_for_ready(test_url), "Server not ready"
    
    # Navigate to form
    assert safe_navigate(page, urljoin(test_url, '/patients/new/')), "Failed to load form"
    
    # Wait for form to be visible
    page.wait_for_selector("form", state="visible")
    
    # Try to submit without filling required fields
    submit_btn = page.locator("button[type=submit]")
    submit_btn.click()
    
    # Verify error messages are displayed
    error_locator = page.locator(".error-message")
    expect(error_locator).to_have_count(2)  # family et given sont requis
    family_classes = page.locator("input[name=family]").get_attribute("class") or ""
    given_classes = page.locator("input[name=given]").get_attribute("class") or ""
    assert "border-red-500" in family_classes
    assert "border-red-500" in given_classes