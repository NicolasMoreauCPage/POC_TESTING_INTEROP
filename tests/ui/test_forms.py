import pytest, time, httpx
from urllib.parse import urljoin
from playwright.sync_api import expect

def wait_for_ready(url: str, max_retries: int = 30, delay: float = 0.5):
    """Wait for server to be ready.

    We try the canonical root URL first (follows redirects). This avoids
    failing when the app issues a 307 from /health -> /health/ or similar.
    """
    for i in range(max_retries):
        try:
            # follow redirects so a 307 won't be treated as a failure
            response = httpx.get(url, follow_redirects=True, timeout=5.0)
            if response.status_code < 400:
                return True
        except Exception:
            # swallow and retry
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
            print(f"safe_navigate: requested {url}, response={getattr(response, 'status', None)}, page.url={getattr(page, 'url', None)}")
            if response and response.ok:
                return True
        except Exception as e:
            if i == max_retries - 1:
                pytest.fail(f"Failed to navigate to {url}: {str(e)}")
            time.sleep(1)
    return False

def test_navigation_menus(page, test_server):
    """Ensure the main navigation exposes the grouped menus expected by the UI."""
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/"), "Failed to load home page"

    page.wait_for_selector("nav", state="visible")
    nav = page.locator("nav")

    top_sections = ["Activités", "Structure", "Interopérabilité", "Ressources"]
    for section in top_sections:
        expect(nav.locator(f"button:has-text(\"{section}\")")).to_be_visible()

    def open_menu(label: str):
        button = nav.locator(f"button:has-text(\"{label}\")").first
        button.hover()
        page.wait_for_timeout(150)

    open_menu("Activités")
    expect(page.locator("a[href='/patients']").first).to_be_visible()
    expect(page.locator("a[href='/dossiers']").first).to_be_visible()

    open_menu("Structure")
    expect(page.locator("a[href='/structure']").first).to_be_visible()
    expect(page.locator("a[href='/admin/ght']").first).to_be_visible()

    open_menu("Interopérabilité")
    expect(page.locator("a[href='/messages']").first).to_be_visible()
    expect(page.locator("a[href='/messages/send']").first).to_be_visible()

    open_menu("Ressources")
    expect(page.locator("a[href='/guide']").first).to_be_visible()
    expect(page.locator("a[href='/api-docs']").first).to_be_visible()

    expect(nav.locator("a[href='/admin']").first).to_be_visible()

def test_required_fields(page, test_server):
    """Test validation of required fields in the patient form."""
    # Ensure server is ready
    assert wait_for_ready(test_server), "Server not ready"
    
    # Navigate to form
    assert safe_navigate(page, f"{test_server}/patients/new/"), "Failed to load form"
    
    # Wait for form to be visible
    page.wait_for_selector("form", state="visible")
    
    # Try to submit without filling required fields
    submit_btn = page.locator("button[type=submit]")
    submit_btn.click()
    
    # Verify error messages are displayed (client-side uses .error-message)
    error_locator = page.locator(".error-message")
    expect(error_locator).to_have_count(2)  # family et given sont requis
    family_classes = page.locator("input[name=family]").get_attribute("class") or ""
    given_classes = page.locator("input[name=given]").get_attribute("class") or ""
    assert "border-red-500" in family_classes
    assert "border-red-500" in given_classes

def test_form_validation(page, test_server):
    """Test field validation rules in the patient form."""
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/patients/new/"), "Failed to load form"
    
    # Wait for form to be ready
    # First, fill required fields to clear pre-load errors
    page.fill("input[name=family]", "Doe")
    page.fill("input[name=given]", "John")
    page.wait_for_timeout(500)  # Let validation clear
    
    page.wait_for_selector("form", state="visible")
    
    # Test email validation
    email_input = page.locator("input[name=email]")
    email_input.fill("invalid-email")
    email_input.blur()  # Trigger validation
    
    # Wait for client-side validation element (template uses .error-message)
    page.wait_for_selector(".error-message", timeout=2000)
    # Find the error for the email field specifically
    first_error_text = page.locator('.error-message[data-for="email"]').inner_text()
    assert 'email' in first_error_text.lower()
    assert 'invalide' in first_error_text.lower()
    
    # Test phone validation
    phone_input = page.locator("input[name=phone]")
    phone_input.fill("123")
    phone_input.blur()
    # phone validation should also create an .error-message near the phone field
    page.wait_for_selector(".error-message", timeout=2000)
    phone_error_text = page.evaluate("(selector) => { const f = document.querySelector(selector); if (!f) return ''; const c = f.closest('.space-y-2') || f.parentElement; const err = c && c.querySelector('.error-message'); return err ? err.innerText : ''; }", "input[name=phone]")
    assert ('téléphone' in phone_error_text.lower() or 'telephone' in phone_error_text.lower()) or ('phone' in phone_error_text.lower()), f"Expected phone-related error, got: {phone_error_text}"
    assert 'invalide' in phone_error_text.lower() or 'invalid' in phone_error_text.lower()

def test_successful_submit(page, test_server):
    """Test successful form submission with all required fields."""
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/patients/new/"), "Failed to load form"
    
    # Wait for form to be ready and ensure it's interactive
    page.wait_for_selector("form", state="visible")
    page.wait_for_load_state("networkidle")
    print('Page URL after navigation:', page.url)
    
    # Fill form with required fields
    page.fill("input[name=family]", "Doe")
    page.fill("input[name=given]", "John")
    page.fill("input[name=email]", "john.doe@example.com")
    
    # DEBUG: dump form HTML before submit to verify JS initialization
    print('--- FORM HTML BEFORE SUBMIT ---')
    try:
        print(page.locator('form').nth(0).inner_html())
    except Exception as _:
        print('Could not read form inner_html')
    print('--- END FORM HTML ---')

    # Submit form and ensure the request starts
    submit_btn = page.locator("button[type=submit]")
    submit_btn.click()
    
    # Wait for complete submission cycle with improved logging:
    try:
        # Prefer a deterministic DOM hook written by the client JS when
        # a submit starts/ends. This is more robust than relying on the
        # disabled attribute because multiple forms/buttons can exist.
        page.wait_for_function("() => { const el = document.getElementById('__test_debug'); return el && el.textContent && el.textContent.includes('submit-start'); }", timeout=5000)
        print("✓ Detected submit-start via __test_debug")

        page.wait_for_function("() => { const el = document.getElementById('__test_debug'); return el && el.textContent && el.textContent.includes('submit-end'); }", timeout=5000)
        print("✓ Detected submit-end via __test_debug")

        # 3. Wait for network request to complete
        page.wait_for_load_state("networkidle", timeout=5000)
        print("✓ Network request completed")

        # 4. Toast container becomes visible with success message
        toast = page.locator(".toast-success")
        page.wait_for_selector(".toast-success", state="visible", timeout=5000)
        print("✓ Toast visible")
    except Exception as e:
        # Capture l'état de la page en cas d'erreur
        page.screenshot(path="test-failure.png")
        print(f"État DOM au moment de l'erreur:\n{page.content()}")
        raise Exception(f"Erreur lors de la soumission du formulaire: {str(e)}")
    # Verify toast contents only after we know it's visible
    toast_text = toast.inner_text()
    expect(toast).to_be_visible()
    assert "Enregistrement réussi" in toast_text, f"Expected success message not found in toast: {toast_text}"
    
    # Wait a moment to ensure we catch any potential visibility flashing
    page.wait_for_timeout(500)  # Small delay to catch any animation
    # Double-check visibility is stable
    expect(toast).to_be_visible()

def test_state_transitions(page, test_server):
    """Test state transition validation"""
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/dossiers/new/"), "Failed to load form"
    
    # Wait for form and its elements to be ready
    page.wait_for_selector("form", state="visible")
    page.wait_for_selector("select[name=current_state]", state="visible")
    page.wait_for_selector("select[name=event_code]", state="visible")
    
    # Select invalid state transition with delay between selections
    page.select_option("select[name=current_state]", "Hospitalisé")
    page.wait_for_timeout(500) # Wait for any event handlers
    page.select_option("select[name=event_code]", "A38")  # Invalid transition
    page.wait_for_timeout(500) # Wait for validation to trigger
    
    # Verify error message appears (use .first to avoid strict mode violation)
    error = page.locator(".form-error").first
    expect(error).to_be_visible()
    expect(error).to_contain_text("Transition invalide")  # Message is "Transition invalide depuis l'état..."

def test_form_accessibility(page, test_server):
    """Test accessibility features of the form"""
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)  # Small delay for FormManager to execute focus
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/patients/new/"), "Failed to load form"
    
    # Wait for form to be ready
    page.wait_for_selector("form", state="visible")
    
    # Verify required fields have correct attributes
    family_input = page.locator("input[name=family]")
    expect(family_input).to_have_attribute("required", "")
    expect(family_input).to_have_attribute("data-required", "true")
    
    # Verify help text is linked to fields
    email_input = page.locator("input[name=email]")
    help_id = email_input.get_attribute("aria-describedby")
    assert help_id is not None, "Help text ID not found"
    help_text = page.locator(f"#{help_id}")
    expect(help_text).to_be_visible()
    
    # Verify auto-focus (family field should be focused automatically)
    active = page.evaluate("document.activeElement.name")
    assert active == "family", "First field not focused"

def test_responsive_layout(page, test_server):
    """Test responsive design behavior"""
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/patients/new/"), "Failed to load form"
    
    # Wait for form and styles to load
    page.wait_for_selector(".form-grid", state="visible")
    
    # Test desktop layout - check computed value (pixels) instead of CSS string
    grid_cols = page.locator(".form-grid").evaluate("el => window.getComputedStyle(el).gridTemplateColumns")
    # Should have 2 columns (e.g., "246px 246px")
    assert len(grid_cols.split()) == 2, f"Expected 2 columns in desktop mode, got: {grid_cols}"
    
    # Test mobile layout
    page.set_viewport_size({"width": 375, "height": 667})
    page.wait_for_load_state("networkidle") # Wait for responsive changes
    grid_cols_mobile = page.locator(".form-grid").evaluate("el => window.getComputedStyle(el).gridTemplateColumns")
    # Should have 1 column (e.g., "343px")
    assert len(grid_cols_mobile.split()) == 1, f"Expected 1 column in mobile mode, got: {grid_cols_mobile}"

def test_dark_mode(page, test_server):
    """Test dark mode styles"""
    assert wait_for_ready(test_server), "Server not ready"
    
    # Set dark mode before navigation
    page.emulate_media(color_scheme="dark")
    # Force Tailwind dark mode (si activé par classe)
    page.evaluate("document.documentElement.classList.add('dark')")
    assert safe_navigate(page, f"{test_server}/patients/new"), "Failed to load form"
    
    # Wait for form and styles to load
    page.wait_for_selector("form", state="visible")
    
    # Vérifie la couleur d'un label (hors astérisque)
    label = page.locator("label.block.text-sm.font-medium").first
    expect(label).to_have_css("color", "rgb(203, 213, 225)")  # slate-300
    
    # Verify input dark mode styles
    input = page.locator("input").first
    expect(input).to_have_css("background-color", "rgb(30, 41, 59)")  # slate-800
    expect(input).to_have_css("color", "rgb(226, 232, 240)")  # slate-200
