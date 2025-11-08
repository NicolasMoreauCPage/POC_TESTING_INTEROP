from datetime import datetime
from sqlmodel import Session

def test_edit_mouvement_page_renders(client, session: Session):
    # Arrange: create minimal Patient/Dossier/Venue/Mouvement
    from app.models import Patient, Dossier, Venue, Mouvement, DossierType

    p = Patient(family="Test", given="User")
    session.add(p)
    session.commit(); session.refresh(p)

    d = Dossier(dossier_seq=1, patient_id=p.id, uf_responsabilite="UF-TEST", admit_time=datetime.now(), dossier_type=DossierType.HOSPITALISE)
    session.add(d); session.commit(); session.refresh(d)

    v = Venue(venue_seq=1, dossier_id=d.id, uf_responsabilite="UF-TEST", start_time=datetime.now())
    session.add(v); session.commit(); session.refresh(v)

    m = Mouvement(mouvement_seq=1, venue_id=v.id, when=datetime.now(), movement_type="admission", trigger_event="A01")
    session.add(m); session.commit(); session.refresh(m)

    # Act
    r = client.get(f"/mouvements/{m.id}/edit")

    # Assert
    assert r.status_code == 200
    assert "Modifier mouvement" in r.text
    # Ensure the select has a value derived from trigger_event
    assert "ADT^A01" in r.text
