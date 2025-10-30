from sqlmodel import Session, select, create_engine
from app.models import Patient

engine = create_engine("sqlite:///./poc.db")
with Session(engine) as session:
    patients = session.exec(select(Patient)).all()
    if not patients:
        print("No patients found")
    for p in patients:
        print("--- Patient ---")
        print(f"id={p.id} seq={p.patient_seq} external_id={p.external_id}")
        print(f"name={p.family} {p.given} middle={getattr(p,'middle',None)} prefix={getattr(p,'prefix',None)} suffix={getattr(p,'suffix',None)}")
        print(f"birth={p.birth_date} gender={p.gender}")
        print(f"address={getattr(p,'address',None)} city={getattr(p,'city',None)} state={getattr(p,'state',None)} postal={getattr(p,'postal_code',None)}")
        print(f"phone={getattr(p,'phone',None)} ssn={getattr(p,'ssn',None)} marital={getattr(p,'marital_status',None)} mother_maiden={getattr(p,'mothers_maiden_name',None)}")
        print(f"race={getattr(p,'race',None)} religion={getattr(p,'religion',None)} pcp={getattr(p,'primary_care_provider',None)}")
