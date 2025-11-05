# Contributing Guide

Ce guide explique comment contribuer au projet MedData Bridge.

## Environnement de développement

1. Cloner le dépôt
2. Créer un environnement virtuel
3. Installer les dépendances

```bash
git clone <repo>
cd MedData_Bridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Structure du code

```
app/
├── app.py                  # Point d'entrée FastAPI
├── db.py                   # Configuration SQLModel
├── models/                 # Modèles de données
├── routers/               # Routes FastAPI
├── services/             # Services métier
│   ├── mllp.py           # Protocol MLLP
│   ├── fhir.py          # Mapping FHIR
│   └── vocabulary_*.py   # Gestion vocabulaires
└── templates/            # Templates Jinja2
```

## Guidelines

### Code style

- Suivre PEP 8
- Utiliser des type hints
- Documenter les fonctions avec docstrings
- Maximum 88 caractères par ligne

### Tests

- Écrire des tests pour les nouvelles fonctionnalités
- Exécuter les tests avant de commiter
- Maintenir une couverture > 80%

### Commits

Format des messages :
```
<type>(<scope>): <description>

[corps optionnel]

[footer optionnel]
```

Types:
- feat: nouvelle fonctionnalité
- fix: correction de bug
- docs: documentation
- chore: maintenance
- refactor: refactoring
- test: ajout/modification de tests

### Branches

- main: branche principale
- feature/*: nouvelles fonctionnalités
- fix/*: corrections
- docs/*: documentation

## Process de développement

1. Créer une branche
2. Développer la fonctionnalité
3. Écrire les tests
4. Créer une PR
5. Code review
6. Merge

## Tests

```bash
# Exécuter les tests
PYTHONPATH=. pytest

# Avec couverture
PYTHONPATH=. pytest --cov=app

# Tests spécifiques
PYTHONPATH=. pytest tests/test_specific.py -v
```

## Documentation

La documentation doit être maintenue à jour :

- README.md: guide d'utilisation
- CONTRIBUTING.md: guide de contribution
- Docstrings: documentation du code
- Comments: explications complexes

## Vocabulaires

### Ajout d'un système

1. Créer un fichier dans `app/services/vocabulary_*.py`
2. Définir les fonctions `create_*_vocabularies()`
3. Ajouter dans `vocabulary_init.py`
4. Créer les mappings si nécessaire

### Modification d'un système

1. Modifier les valeurs dans le fichier concerné
2. Mettre à jour les mappings si nécessaire
3. Incrémenter la version dans setup.py
4. Documenter dans CHANGELOG.md

## Release

1. Mettre à jour la version
2. Mettre à jour CHANGELOG.md
3. Créer un tag
4. Build et publish

## Support

Pour toute question :
1. Consulter la documentation
2. Vérifier les issues existantes
3. Créer une nouvelle issue

## License

[A définir]