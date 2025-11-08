"""Test de l'interface de validation"""
import requests

# Message HL7 de test
hl7_message = """MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20251105120000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20251105120000|||APPLI^IHE
PID|1||123456^^^HOPITAL||DUPONT^JEAN||19800101|M
PV1|1|I|CARDIO^101^1|||||||||||||||||1|||||||||||||||||||||||||20251105120000"""

# Préparer les données du formulaire
data = {
    "hl7_message": hl7_message,
    "direction": "inbound",
    "profile": "IHE_PAM_FR"
}

# Envoyer la requête
print("Envoi de la requête de validation...")
response = requests.post(
    "http://127.0.0.1:8000/validation/validate",
    data=data
)

print(f"Status code: {response.status_code}")
print(f"Content length: {len(response.content)}")

# Vérifier si "validation_done" apparaît dans la réponse
if "validation_done" in response.text:
    print("✓ validation_done trouvé dans la réponse")
else:
    print("✗ validation_done NON trouvé dans la réponse")

# Vérifier si "Résultats de la validation" apparaît
if "Résultats de la validation" in response.text:
    print("✓ Section résultats trouvée")
else:
    print("✗ Section résultats NON trouvée")

# Vérifier si les erreurs sont affichées
if "Erreurs" in response.text and "Warnings" in response.text:
    print("✓ Compteurs d'erreurs/warnings trouvés")
else:
    print("✗ Compteurs NON trouvés")

# Sauvegarder la réponse pour inspection
with open("test_validation_response.html", "w", encoding="utf-8") as f:
    f.write(response.text)
print("\nRéponse sauvegardée dans test_validation_response.html")
