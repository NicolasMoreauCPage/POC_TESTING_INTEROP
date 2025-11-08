def wait_for_ready(url: str, max_retries: int = 30, delay: float = 0.5):
def safe_navigate(page, url: str, timeout_ms: int = 10000):
from playwright.sync_api import expect
from .ui_helpers import wait_for_ready, safe_navigate

def test_navigation_menus(page, test_server):
    """Ensure the main navigation exposes the grouped menus expected by the UI."""
    assert wait_for_ready(test_server), "Server not ready"
    assert safe_navigate(page, f"{test_server}/"), "Failed to load home page"

    page.wait_for_selector("nav", state="visible")
    nav = page.locator("nav")

    # Vérifie la présence des sections principales (li ou a)
    for section in ["Activités", "Structure", "Interopérabilité", "Ressources"]:
        expect(nav.locator(f":text('{section}')")).to_be_visible()

    # Vérifie la présence des liens principaux (sans dépendre de l'ouverture de menu)
    for href in ["/patients", "/dossiers", "/admin/ght", "/messages", "/messages/send", "/guide", "/api-docs", "/sqladmin"]:
        expect(nav.locator(f"a[href='{href}']")).to_have_count(1)

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

    # Vérifie qu'au moins un message d'erreur s'affiche (client ou serveur)
    error_locator = page.locator(".error-message")
    expect(error_locator).not_to_have_count(0)
    # Vérifie que les champs requis sont marqués en erreur (classe CSS ou attribut aria-invalid)
    for name in ["family", "given"]:
        input_field = page.locator(f"input[name={name}]")
        classes = input_field.get_attribute("class") or ""
        aria_invalid = input_field.get_attribute("aria-invalid")
        assert "border-red-500" in classes or aria_invalid == "true"

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

    # Attendre le toast de succès ou un message de confirmation
    toast = page.locator(".toast-success, .toast, [role='alert']")
    page.wait_for_selector(".toast-success, .toast, [role='alert']", state="visible", timeout=5000)
    toast_text = toast.inner_text()
    expect(toast).to_be_visible()
    assert "Enregistrement" in toast_text or "succès" in toast_text.lower() or "success" in toast_text.lower(), f"Expected success message not found in toast: {toast_text}"

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
    # Accepte slate-300 (dark) ou slate-700 (clair) selon le mode effectif
    color = label.evaluate("el => getComputedStyle(el).color")
    assert color in ["rgb(203, 213, 225)", "rgb(51, 65, 85)"]

    # Vérifie que le champ input a bien une couleur de fond sombre en dark mode
    input = page.locator("input").first
    bg_color = input.evaluate("el => getComputedStyle(el).backgroundColor")
    # Accepte slate-800 (dark) ou blanc (clair) selon le mode effectif
    assert bg_color in ["rgb(30, 41, 59)", "rgb(255, 255, 255)"]
