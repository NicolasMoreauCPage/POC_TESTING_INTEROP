// Gestion des transitions d'état pour les dossiers
const StateTransitionManager = {
    transitions: {
        'Hospitalisé': ['A03', 'A02', 'A12'],  // Exemple de transitions valides
        'Pré-admis': ['A01', 'A11'],  // A38 n'est pas une transition valide
        'Sorti': ['A02', 'A21', 'A38']
    },

    setupTransitionValidation(form) {
        const currentStateSelect = form.querySelector('select[name="current_state"]');
        const eventCodeSelect = form.querySelector('select[name="event_code"]');
        
        if (!currentStateSelect || !eventCodeSelect) return;
        
        const validateTransition = () => {
            const state = currentStateSelect.value;
            const event = eventCodeSelect.value;
            
            if (!state || !event) return;
            
            const allowedEvents = this.transitions[state] || [];
            if (!allowedEvents.includes(event)) {
                const errorDiv = document.createElement('p');
                errorDiv.className = 'form-error mt-2 text-sm text-red-600';
                errorDiv.textContent = 'Transition invalide';
                eventCodeSelect.parentNode.appendChild(errorDiv);
                return false;
            }
            return true;
        };
        
        // Clear previous validation when selections change
        const clearError = () => {
            const errorDiv = eventCodeSelect.parentNode.querySelector('.form-error');
            if (errorDiv) errorDiv.remove();
        };
        
        currentStateSelect.addEventListener('change', () => {
            clearError();
            validateTransition();
        });
        
        eventCodeSelect.addEventListener('change', () => {
            clearError();
            validateTransition();
        });
    }
};

// Export for use in forms.js
window.StateTransitionManager = StateTransitionManager;