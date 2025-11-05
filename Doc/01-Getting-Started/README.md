# 01 - Getting Started

Documentation pour démarrer avec MedData Bridge.

## Documents

### [CONTRIBUTING.md](CONTRIBUTING.md)
Guide de contribution au projet : conventions de code, structure, workflow Git, tests.

**Sujets couverts** :
- Configuration de l'environnement de développement
- Structure du code
- Guidelines de style (PEP 8, type hints, docstrings)
- Procédure de contribution (fork, branch, PR)

## Ressources Externes

- [README.md principal](../../README.md) : Installation, configuration, démarrage
- Variables d'environnement : `TESTING`, `INIT_VOCAB`, `MLLP_TRACE`
- Scripts d'initialisation dans `tools/`

## Démarrage Rapide

```bash
# Installation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialisation complète
python tools/init_all.py --export-fhir

# Lancement développement
INIT_VOCAB=1 MLLP_TRACE=1 python -m uvicorn app.app:app --reload
```

---

[← Retour à l'index](../INDEX.md)
