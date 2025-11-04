from sqlmodel import Session


def test_chemo_multi_venues(dossier_chemo_with_sessions):
    data = dossier_chemo_with_sessions
    venues = data["venues"]
    assert len(venues) == 3
    dossier_id = data["dossier"].id
    assert all(v.dossier_id == dossier_id for v in venues)
    assert all(v.uf_responsabilite == "HDJ-ONCO" for v in venues)
    assert all(v.code == "HDJ-ONCO" for v in venues)
    # Labels should be distinct per session
    labels = [v.label for v in venues]
    assert len(set(labels)) == 3


def test_psy_day_hospital_multi(dossier_psy_day_hospital_multi):
    data = dossier_psy_day_hospital_multi
    venues = data["venues"]
    assert len(venues) == 3
    dossier_id = data["dossier"].id
    assert all(v.dossier_id == dossier_id for v in venues)
    assert all(v.uf_responsabilite == "HDJ-PSY" for v in venues)
    assert all(v.code == "HDJ-PSY" for v in venues)
    labels = [v.label for v in venues]
    assert len(set(labels)) == 3
