# Système de liens vers la documentation

## Vue d'ensemble

Le système de liens harmonisés vers la documentation permet d'afficher automatiquement un bouton "Voir la documentation" sur chaque page de l'application lorsqu'une documentation correspondante existe.

## Architecture

### 1. Macro Jinja2 (`app/templates/macros/doc_link.html`)

La macro `doc_link()` contient le mapping entre les pages et leur documentation :

```jinja2
{% from "macros/doc_link.html" import doc_link %}

{{ doc_link(request.url.path) }}
```

### 2. Page d'index (`/documentation`)

La page `/documentation` affiche un index visuel de toute la documentation disponible, organisée par thème :

- **Guide de démarrage** : Installation et configuration
- **Validation HL7** : Règles, profils IHE PAM, datatypes
- **Validation de dossier** : Workflow et cohérence
- **Supervision des messages** : Analyse des échanges
- **Endpoints** : Configuration MLLP/FHIR/FILE
- **Scénarios IHE** : Workflows cliniques
- **Patients** : Gestion de l'identité
- **Dossiers** : Types et venues
- **Structure** : Organisation GHT/EJ/EG
- **Standards** : Conformité HL7/FHIR/IHE
- **Vocabulaires** : Tables de codes
- **API Reference** : OpenAPI/Swagger

### 3. Router de documentation (`app/routers/documentation.py`)

Le router gère trois types de pages :

- `GET /documentation` : Page d'index (nouveau)
- `GET /documentation/{category}/{filename}` : Affichage d'un document markdown
- `GET /documentation/search?q=...` : Recherche dans la documentation

## Utilisation dans les templates

### Ajout du lien sur une nouvelle page

1. **Importer la macro** en haut du template :

```jinja2
{% extends "base.html" %}
{% from "macros/doc_link.html" import doc_link %}
```

2. **Afficher le lien** (généralement juste après l'ouverture du block content) :

```jinja2
{% block content %}
<div class="max-w-7xl mx-auto">
    <!-- Lien vers la documentation -->
    <div class="mb-4 flex justify-end">
        {{ doc_link(request.url.path) }}
    </div>
    
    <!-- Reste du contenu -->
    ...
</div>
{% endblock %}
```

3. **Ajouter le mapping** dans `app/templates/macros/doc_link.html` :

```jinja2
{% set doc_map = {
    ...
    "/ma-nouvelle-page": {"url": "/documentation#section", "title": "Documentation: Ma page"},
    ...
} %}
```

4. **Mettre à jour la page d'index** dans `app/templates/documentation_index.html` :

Ajouter une carte dans le grid pour votre section.

## Pages actuellement configurées

| Page | Documentation |
|------|---------------|
| `/validation` | Documentation: Validation HL7 |
| `/messages` | Documentation: Supervision des messages |
| `/messages/validate-dossier` | Documentation: Validation de dossier |
| `/endpoints` | Documentation: Configuration des endpoints |
| `/scenarios` | Documentation: Scénarios IHE PAM |
| `/patients` | Documentation: Gestion des patients |
| `/dossiers` | Documentation: Dossiers |
| `/structure/*` | Documentation: Structure organisationnelle |
| `/standards` | Documentation: Standards |
| `/vocabularies` | Documentation: Vocabulaires |

## Apparence

Le bouton de documentation a un style harmonisé :

- **Couleur** : Bleu (bg-blue-50, text-blue-600)
- **Icône** : Livre ouvert + flèche externe
- **Taille** : text-sm (14px)
- **Position** : En haut à droite de la page (flex justify-end)
- **Hover** : bg-blue-100

## Ajout d'une nouvelle documentation

Pour ajouter une documentation pour une nouvelle page :

1. Créer le fichier markdown dans `Doc/` (suivre la structure existante)
2. Ajouter l'entrée dans `doc_map` (macro)
3. Ajouter une carte dans `documentation_index.html`
4. Inclure la macro dans le template de la page

## Conventions

- **Ancres** : Utiliser des IDs en kebab-case (#validation-dossier)
- **Titres** : Format "Documentation: [Nom de la page]"
- **Organisation** : Suivre la structure des dossiers Doc/
- **Liens externes** : Toujours avec `target="_blank"`

## Maintenance

Le système est centralisé dans la macro `doc_link.html`. Pour modifier l'apparence globale des liens, il suffit de modifier cette macro une seule fois.

## Exemple complet

```jinja2
{# app/templates/ma_page.html #}
{% extends "base.html" %}
{% from "macros/doc_link.html" import doc_link %}

{% block title %}Ma Page{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto">
    <!-- Lien vers la documentation -->
    <div class="mb-4 flex justify-end">
        {{ doc_link(request.url.path) }}
    </div>
    
    <div class="bg-white shadow-md rounded-lg p-6">
        <h1>Ma Page</h1>
        <!-- Contenu -->
    </div>
</div>
{% endblock %}
```

## Évolutions futures possibles

- Détection automatique des pages sans documentation
- Génération automatique du mapping depuis les fichiers markdown
- Système de tags et de recherche avancée
- Versioning de la documentation
- Export PDF des documents
