#!/usr/bin/env python
"""
Script d'initialisation des vocabulaires dans la base de données
"""
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour importer les modules de l'application
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session
from app.db import engine, init_db
from app.vocabulary_init import init_vocabularies

def main():
    """
    Initialise ou met à jour les vocabulaires dans la base de données
    """
    # Créer les tables si elles n'existent pas
    init_db()
    
    # Créer une session
    with Session(engine) as session:
        print("Initialisation des vocabulaires...")
        
        try:
            # Initialiser tous les vocabulaires et leurs mappings
            init_vocabularies(session)
            print("Initialisation terminée avec succès!")
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation : {e}", file=sys.stderr)
            session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    main()