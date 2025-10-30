from typing import List
from app.models import Dossier, Patient, Venue, Mouvement

try:
    from adapters.hl7_pam_fr import build_message_for_movement
except Exception:
    build_message_for_movement = None

def generate_pam_messages_for_dossier(dossier: Dossier) -> List[str]:
    patient: Patient = dossier.patient
    venues: List[Venue] = sorted(dossier.venues, key=lambda v: v.start_time or "")
    messages: List[str] = []

    for v in venues:
        mouvements: List[Mouvement] = sorted(v.mouvements, key=lambda m: m.when)
        for m in mouvements:
            if build_message_for_movement:
                messages.append(build_message_for_movement(dossier=dossier, venue=v, movement=m, patient=patient))
                continue

            msh = f"MSH|^~\\&|POC|POC|DST|DST|{m.when:%Y%m%d%H%M%S}||{m.type}|{dossier.dossier_seq}|P|2.5"
            pid = f"PID|||{patient.external_id}||{patient.family}^{patient.given}||{patient.birth_date}|{patient.gender}"
            pv1_loc = m.location or v.code or "UNKNOWN"
            pv1 = f"PV1||I|{pv1_loc}|||^^^^^{v.uf_responsabilite}"
            messages.append("\r".join([msh, pid, pv1]))
    return messages
