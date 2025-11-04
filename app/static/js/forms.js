// forms.js - Logique des formulaires MedData Bridge

console.debug('forms.js loaded');

class FormManager {
    constructor(formElement, options = {}) {
        this.form = formElement;
        this.options = {
            showToasts: true,
            validateOnType: true,
            scrollToError: true,
            autoFocus: true,
            ...options
        };

        this.setupResponsiveLayout();
        
        // Ensure family field gets focus
        this.setupInitialFocus();
        
        this.validators = {
            required: (value) => value && value.trim() !== '',
            email: (value) => !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
            phone: (value) => !value || /^(\+\d{1,3}[- ]?)?\d{10}$/.test(value),
            numeric: (value) => !value || !isNaN(value),
            date: (value) => !value || !isNaN(Date.parse(value)),
            ...options.validators
        };

        this.setupEventListeners();
        this.setupToastContainer();
    }

    setupEventListeners() {
        if (this.options.validateOnType) {
            this.form.querySelectorAll('input, select, textarea').forEach(field => {
                field.addEventListener('input', () => this.validateField(field));
                field.addEventListener('blur', () => this.validateField(field));
            });
        }

        // Ensure family field gets focus
        const familyField = this.form.querySelector('input[name="family"]');
        if (familyField) {
            setTimeout(() => familyField.focus(), 0);
        }

        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    setupInitialFocus() {
        if (this.options.autoFocus) {
            const doFocus = () => {
                const familyField = this.form.querySelector('input[name="family"]');
                if (familyField) {
                    // Use requestAnimationFrame to ensure focus happens after layout
                    requestAnimationFrame(() => {
                        familyField.focus();
                        console.debug('FormManager: focused family field');
                    });
                }
            };
            
            // If DOM is already loaded, focus immediately
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                doFocus();
            } else {
                // Otherwise wait for DOMContentLoaded
                document.addEventListener('DOMContentLoaded', doFocus);
            }
        }
    }

    setupResponsiveLayout() {
        const formGrid = this.form.querySelector('.form-grid');
        if (!formGrid) return;

        // Initial layout
        this.updateGridLayout(formGrid);

        // Update on window resize
        const handleResize = () => this.updateGridLayout(formGrid);
        window.addEventListener('resize', handleResize);
    }

    updateGridLayout(grid) {
        // Set explicit grid template columns for test consistency
        const mediaQuery = window.matchMedia('(min-width: 768px)');
        const updateColumns = (e) => {
            grid.style.gridTemplateColumns = e.matches ? 
                'repeat(2, minmax(0, 1fr))' : 
                'repeat(1, minmax(0, 1fr))';
        };
        
        // Initial setup
        updateColumns(mediaQuery);
        
        // Listen for changes
        mediaQuery.addListener(updateColumns);
    }

    setupToastContainer() {
        if (this.options.showToasts) {
            // Always use the container from base.html
            let container = document.getElementById('toast-container');
            if (!container) {
                console.warn('Toast container not found in DOM, creating one');
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2';
                document.body.appendChild(container);
            }
            // Make sure container is visible
            container.style.opacity = '1';
            container.style.visibility = 'visible';
            this.toastContainer = container;
        }
    }

    // Write a small DOM-visible debug marker so tests can assert on it even
    // when console messages are not captured. Keeps a short JSON with
    // events like submit-start and submit-end along with timestamps.
    writeTestDebug(eventName, details = {}) {
        try {
            let el = document.getElementById('__test_debug');
            if (!el) {
                el = document.createElement('div');
                el.id = '__test_debug';
                el.style.display = 'none';
                document.body.appendChild(el);
            }
            const previous = el.dataset.events ? JSON.parse(el.dataset.events) : [];
            previous.push({ event: eventName, at: new Date().toISOString(), details });
            // keep only last 10
            const sliced = previous.slice(-10);
            el.dataset.events = JSON.stringify(sliced);
            // also set textContent for easy page.evaluate readout
            el.textContent = JSON.stringify(sliced);
        } catch (e) {
            // non-fatal
            console.debug('writeTestDebug failed', e);
        }
    }

    validateField(field) {
        this.clearFieldError(field);
        const validations = this.getFieldValidations(field);
        
        // If the field is empty and required, show required error
        if ((!field.value || field.value.trim() === '') && validations.required) {
            this.showFieldError(field, validations.required);
            return false;
        }
        
        // If field has value, check type-specific validations
        if (field.value && field.value.trim() !== '') {
            for (const [validationType, message] of Object.entries(validations)) {
                if (validationType === 'required') continue;
                const validator = this.validators[validationType];
                if (validator && !validator(field.value)) {
                    this.showFieldError(field, message);
                    return false;
                }
            }
        }
        
        return true;
    }

    getFieldValidations(field) {
        const validations = {};
        const type = field.getAttribute('type');
        
        // Add type-specific validations first
        const fieldLabel = field.labels?.[0]?.textContent?.trim() || field.name;
        
        if (type === 'email') {
            validations.email = `L'adresse email '${fieldLabel}' est invalide`;
        } else if (type === 'tel') {
            validations.phone = `Le numéro de téléphone '${fieldLabel}' est invalide`;
        } else if (type === 'number') {
            validations.numeric = `La valeur numérique '${fieldLabel}' est invalide`;
        } else if (type === 'date') {
            validations.date = `La date '${fieldLabel}' est invalide`;
        }
        
        // Add required validation last so it takes precedence if field is empty
        if (field.hasAttribute('required')) {
            validations.required = 'Ce champ est obligatoire';
        }

        // Custom data-validate attributes
        const customValidation = field.dataset.validate;
        if (customValidation) {
            try {
                const rules = JSON.parse(customValidation);
                Object.assign(validations, rules);
            } catch (e) {
                console.error('Invalid data-validate format:', e);
            }
        }

        return validations;
    }

    showFieldError(field, message) {
        // Use the same container structure and classes as the server-side
        // templates to keep client and tests consistent. The template uses
        // a wrapper with classes like 'space-y-2' and renders errors with
        // the class 'error-message'. We add Tailwind-like classes to the
        // field to visually mark it as invalid.
        let container = null;
        try {
            container = field.closest ? field.closest('.space-y-2') : null;
        } catch (e) {
            container = null;
        }
        if (!container) container = field.parentElement || document.body;

        // Look for existing error for THIS specific field using data-for
        const selector = `.error-message[data-for="${field.name}"]`;
        const existing = container.querySelector ? container.querySelector(selector) : null;
        if (!existing) {
            const error = document.createElement('p');
            error.className = 'error-message form-error text-sm text-red-600 flex items-center gap-1 mt-1';
            error.setAttribute('data-for', field.name || '');
            error.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                ${message}
            `;
            container.appendChild(error);
        } else {
            // Update existing error message
            const textNode = existing.lastChild;
            if (textNode) textNode.textContent = message;
        }
        if (field.classList) field.classList.add('border-red-500', 'ring-red-500');
    }

    clearFieldError(field) {
        let container = null;
        try {
            container = field.closest ? field.closest('.space-y-2') : null;
        } catch (e) {
            container = null;
        }
        if (!container) container = field.parentElement || document.body;
    // Remove error for THIS specific field using data-for
    const selector = `.error-message[data-for="${field.name}"]`;
    const error = container && container.querySelector ? container.querySelector(selector) : null;
        if (error) error.remove();
        if (field.classList) field.classList.remove('border-red-500', 'ring-red-500');
    }

    async handleSubmit(event) {
        event.preventDefault();
        console.debug('FormManager.handleSubmit called for', this.form.action, this.form.method);
        
        const isDownload = (this.form.dataset && this.form.dataset.download === '1');
        // Validate and collect errors unless this is a download form
        let hasError = false;
        const allFields = Array.from(this.form.querySelectorAll('input, select, textarea'));
        
        if (!isDownload) {
            // Clear all previous errors
            allFields.forEach(field => this.clearFieldError(field));
            
            // Validate each field and collect errors
            allFields.forEach(field => {
                // Check if field is required and empty
                if (field.hasAttribute('required') && (!field.value || field.value.trim() === '')) {
                    this.showFieldError(field, 'Ce champ est obligatoire');
                    hasError = true;
                }
                // Then check other validations if the field has a value
                else if (field.value && field.value.trim() !== '') {
                    if (!this.validateField(field)) {
                        hasError = true;
                    }
                }
            });
        }

        if (hasError) {
            // Ensure all empty required fields have their error node created
            allFields.forEach(field => {
                if (field.hasAttribute('required') && (!field.value || field.value.trim() === '')) {
                    // Check if an error element for this field already exists; if not, create it
                    let container = null;
                    try { container = field.closest ? field.closest('.space-y-2') : null; } catch (e) { container = null; }
                    if (!container) container = field.parentElement || document.body;
                    const selector = `.error-message[data-for="${field.name}"]`;
                    const existing = container.querySelector ? container.querySelector(selector) : null;
                    if (!existing) {
                        this.showFieldError(field, 'Ce champ est obligatoire');
                    }
                }
            });

            if (this.options.scrollToError) {
                const firstError = this.form.querySelector('.form-error');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            return;
        }

        // Désactiver le formulaire pendant la soumission
        const submitBtn = this.form.querySelector('button[type="submit"]');
        console.debug('Attempting to disable submit button', submitBtn);
        const originalBtnContent = submitBtn.innerHTML;
        // set both property and attribute for robustness
        try { submitBtn.disabled = true; } catch(e) {}
        try { submitBtn.setAttribute('disabled', ''); } catch(e) {}
        submitBtn.innerHTML = this.getLoadingButtonContent();
        console.debug('Submit button disabled attribute present?', submitBtn.hasAttribute && submitBtn.hasAttribute('disabled'));

        try {
            const formData = new FormData(this.form);
            console.debug('Submitting form via fetch to', this.form.action);
            // Mark submit-start in a DOM-readable debug element for tests
            this.writeTestDebug('submit-start', { action: this.form.action, download: isDownload });

            if (isDownload) {
                const response = await fetch(this.form.action, {
                    method: this.form.method,
                    body: formData
                });
                if (!response.ok) {
                    const raw = await response.text().catch(() => '');
                    this.showToast('error', 'Échec du téléchargement');
                    console.error('Download failed', response.status, raw);
                    return;
                }
                const disposition = response.headers.get('content-disposition') || '';
                let filename = 'download';
                const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
                if (match) {
                    filename = decodeURIComponent(match[1] || match[2]);
                }
                const contentType = response.headers.get('content-type') || 'application/octet-stream';
                const blob = await response.blob();
                const url = window.URL.createObjectURL(new Blob([blob], { type: contentType }));
                const a = document.createElement('a');
                a.href = url;
                a.setAttribute('download', filename);
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                this.showToast('success', 'Téléchargement démarré');
                return;
            } else {
                const response = await fetch(this.form.action, {
                    method: this.form.method,
                    body: formData,
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                const contentType = response.headers.get('content-type') || '';
                let data;
                if (contentType.includes('application/json')) {
                    data = await response.json();
                } else {
                    const raw = await response.text();
                    data = {
                        ok: response.ok,
                        message: response.ok ? 'Opération réussie' : 'Erreur lors de l\'enregistrement',
                        rawResponse: raw
                    };
                }
                console.debug('Fetch response', response.status, data);

                if (response.ok) {
                    // Use exact same success message as the one expected by the test
                    this.showToast('success', 'Enregistrement réussi');
                    
                    // Delay redirect to ensure toast is visible
                    if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1000); // Longer delay for test stability
                    }
                } else {
                    this.showToast('error', data.message || 'Erreur lors de l\'enregistrement');
                    if (data.errors) {
                        this.handleServerErrors(data.errors);
                    }
                }
            }
        } catch (error) {
            console.error('Erreur de soumission:', error);
            this.showToast('error', 'Erreur technique lors de l\'enregistrement');
        } finally {
            try { submitBtn.disabled = false; } catch(e) {}
            try { submitBtn.removeAttribute('disabled'); } catch(e) {}
            submitBtn.innerHTML = originalBtnContent;
            // Mark submit-end for tests
            this.writeTestDebug('submit-end', { action: this.form.action, download: isDownload });
            console.debug('Submit button re-enabled, disabled attribute present?', submitBtn.hasAttribute && submitBtn.hasAttribute('disabled'));
        }
    }

    handleServerErrors(errors) {
        Object.entries(errors).forEach(([fieldName, message]) => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                this.showFieldError(field, message);
            }
        });
    }

    showToast(type, message) {
        if (!this.options.showToasts || !this.toastContainer) return;

        // Create the toast element
        let classNames = [
            `toast-${type}`,
            'flex', 'items-center', 'gap-3', 'p-4', 'rounded-xl', 'shadow-lg',
            type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : '',
            type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' : '',
            'animate-slideIn'
        ].filter(Boolean).join(' ');

        const toast = document.createElement('div');
        toast.className = classNames;
        // Ensure toast is visible for tests
        toast.style.opacity = '1';
        toast.style.visibility = 'visible';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        toast.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                ${this.getToastIcon(type)}
            </svg>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" class="ml-auto" aria-label="Fermer">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>`;
        
        // Add to container and ensure visibility
        this.toastContainer.appendChild(toast);
        
        // Handle auto-removal
        const removeToast = () => {
            if (toast.parentElement) {
                // Add fade out animation
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                toast.style.transition = 'opacity 150ms ease-out, transform 150ms ease-out';
                
                // Remove after animation
                setTimeout(() => toast.remove(), 150);
            }
        };

        // Auto-remove after delay, but keep long enough for tests
        setTimeout(removeToast, 5000);
    }

    getToastIcon(type) {
        switch (type) {
            case 'success':
                return '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>';
            case 'error':
                return '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>';
            case 'warning':
                return '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>';
            default:
                return '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>';
        }
    }

    getLoadingButtonContent() {
        return `
            <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Enregistrement...</span>
        `;
    }
}

// Transitions d'état spécifiques à l'application
const StateTransitionManager = {
    validTransitions: {
        "Pas de venue courante": ["A05", "A38"],
        "Pré-admis consult.ext.": ["A04", "A11"],
        "Pré-admis hospit.": ["A01", "A11"],
        "Hospitalisé": ["A03", "A13", "A21", "A52", "A53"],
        "Absence temporaire": ["A22", "A52"],
        "Consultant externe": ["A06", "A07"]
    },

    isValidTransition(currentState, newState) {
        return this.validTransitions[currentState]?.includes(newState);
    },

    setupTransitionValidation(form) {
        const currentStateField = form.querySelector('[name="current_state"]');
        const eventCodeField = form.querySelector('[name="event_code"]');
        
        if (currentStateField && eventCodeField) {
            // Clear any previous error when changing current state
            currentStateField.addEventListener('change', () => {
                if (form.manager) {
                    form.manager.clearFieldError(eventCodeField);
                }
            });

            // Validate transition when changing event code
            eventCodeField.addEventListener('change', () => {
                const isValid = this.isValidTransition(
                    currentStateField.value,
                    eventCodeField.value
                );
                
                if (!isValid) {
                    form.manager.showFieldError(
                        eventCodeField,
                        `Transition invalide depuis l'état "${currentStateField.value}"`
                    );
                    // Add form-error class for test
                    const errorElement = eventCodeField.closest('.space-y-2').querySelector('.error-message');
                    if (errorElement) {
                        errorElement.classList.add('form-error');
                    }
                }
            });
        }
    }
};

// Initialisation automatique
function initializeForms() {
    document.querySelectorAll('form').forEach(form => {
        // Créer une instance de FormManager pour chaque formulaire
    const manager = new FormManager(form);
    form.manager = manager; // Stocker la référence pour un accès facile
    try { form.setAttribute('data-forms-manager', '1'); } catch(e) {}

        // Setup transition validation si nécessaire
        if (form.classList.contains('has-state-transitions')) {
            StateTransitionManager.setupTransitionValidation(form);
        }
    });
}

// If the script is injected after DOMContentLoaded (cache-busting or deferred
// loading), ensure we still initialize forms immediately.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeForms);
} else {
    // DOM already ready — initialize right away
    try {
        initializeForms();
    } catch (e) {
        console.error('Failed to initialize forms:', e);
    }
}

// Fallback: capture submit events early and ensure a FormManager exists.
// This prevents a race where the form is submitted before the script
// attached handlers (e.g., due to deferred/dynamic script loading).
document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!form) return;
    // If a manager already exists, let it handle the event
    if (form.manager) return;

    // Prevent the native submit and create a manager to handle it
    try {
        e.preventDefault();
    } catch (err) {
        // ignore
    }
    try {
    const mgr = new FormManager(form);
    form.manager = mgr;
    try { form.setAttribute('data-forms-manager', '1'); } catch(e) {}
        // Call handleSubmit with the original event where possible
        if (typeof mgr.handleSubmit === 'function') {
            mgr.handleSubmit(e);
        } else {
            // Fallback: submit the form normally if handler missing
            form.submit();
        }
    } catch (err) {
        console.error('Fallback form submission failed:', err);
        try { form.submit(); } catch (e) {}
    }
}, true);
