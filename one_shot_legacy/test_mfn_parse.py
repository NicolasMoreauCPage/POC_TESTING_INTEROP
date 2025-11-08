"""Debug du parsing MFN"""
from app.services.mfn_importer import parse_mfn_message

payload = """MSH|^~\\&|APPLI_GHT|GHT|APPLI_DEST|DEST|20250124140000||MFN^M05|MSG000007|P|2.5|||||FRA||UTF-8
MFI|M05|UPD|||AL|
MFE|MAD|20250124140000|20250124140000|M|CE
ZBE|1.2.250.1.111.44.1.1.111^1.3.6.1.4.1.21367.2017.2.1.109^ISO|69
LOC|69|69|GRGAP|A||||^^^^^FINESS^^^^700004591&1.2.250.1.71.4.2.2&ISO||||||||||||||||||||||||||||||
LCH|M|CD|69
LCH|M|FNS|700004591
LCH|M|LBL|GRGAP
LCH|M|ADRS|1 Avenue de la Paix
LCH|M|VILLE|Lyon
LCH|M|CP|69000
MFE|MAD|20250124140000|20250124140000|ETBL_GRPQ|CE
ZBE|1.2.250.1.111.44.1.1.111^1.3.6.1.4.1.21367.2017.2.1.109^ISO|888888888
LOC|888888888|888888888|Service d'urgences générales|A||||^^^^^FINESS^^^^888888888&1.2.250.1.71.4.2.2&ISO||||||||||||||||||^^^^^M^^^^69&1.2.250.1.71.4.2.2&ISO|||||||||
LCH|ETBL_GRPQ|CD|888888888
LCH|ETBL_GRPQ|FNS|888888888
LCH|ETBL_GRPQ|LBL|Hôpital Lyon Sud
LCH|ETBL_GRPQ|ADRS|165 Chemin du Grand Revoyet
LCH|ETBL_GRPQ|VILLE|Pierre-Bénite
LCH|ETBL_GRPQ|CP|69310
LRL|M|69|1|
MFE|MAD|20250124140000|20250124140000|D|CE
ZBE|1.2.250.1.111.44.1.1.111^1.3.6.1.4.1.21367.2017.2.1.109^ISO|URG_SERVICE
LOC|URG_SERVICE|URG_SERVICE|Service d'urgences|A||||^^^^^D^^^^URG_SERVICE&1.2.250.1.71.4.2.2&ISO||||||||||||||||||^^^^^ETBL_GRPQ^^^^888888888&1.2.250.1.71.4.2.2&ISO|||||||||
LCH|D|CD|URG_SERVICE
LCH|D|LBL|Service d'urgences
LRL|ETBL_GRPQ|888888888|1|
MFE|MAD|20250124140000|20250124140000|N|CE
ZBE|1.2.250.1.111.44.1.1.111^1.3.6.1.4.1.21367.2017.2.1.109^ISO|UF_URG_01
LOC|UF_URG_01|UF_URG_01|UF Accueil Urgences|A||||^^^^^N^^^^UF_URG_01&1.2.250.1.71.4.2.2&ISO||||||||||||||||||^^^^^D^^^^URG_SERVICE&1.2.250.1.71.4.2.2&ISO|||||||||
LCH|N|CD|UF_URG_01
LCH|N|LBL|UF Accueil Urgences
LRL|D|URG_SERVICE|1|
MFE|MAD|20250124140000|20250124140000|R|CE
ZBE|1.2.250.1.111.44.1.1.111^1.3.6.1.4.1.21367.2017.2.1.109^ISO|URG_CHAMBRE_01
LOC|URG_CHAMBRE_01|URG_CHAMBRE_01|Chambre Urgences 01|A||||^^^^^R^^^^URG_CHAMBRE_01&1.2.250.1.71.4.2.2&ISO||||||||||||||||||^^^^^N^^^^UF_URG_01&1.2.250.1.71.4.2.2&ISO|||||||||
LCH|R|CD|URG_CHAMBRE_01
LCH|R|LBL|Chambre Urgences 01
LRL|N|UF_URG_01|1|
MFE|MAD|20250124140000|20250124140000|B|CE
ZBE|1.2.250.1.111.44.1.1.111^1.3.6.1.4.1.21367.2017.2.1.109^ISO|URG_LIT_01A
LOC|URG_LIT_01A|URG_LIT_01A|Lit A - Chambre 01|A||||^^^^^B^^^^URG_LIT_01A&1.2.250.1.71.4.2.2&ISO||||||||||||||||||^^^^^R^^^^URG_CHAMBRE_01&1.2.250.1.71.4.2.2&ISO|||||||||
LCH|B|CD|URG_LIT_01A
LCH|B|LBL|Lit A - Chambre 01
LRL|R|URG_CHAMBRE_01|1|
"""

entities = parse_mfn_message(payload)
print(f"Nombre d'entités parsées: {len(entities)}\n")

for i, ent in enumerate(entities):
    print(f"Entité {i+1}:")
    print(f"  type_code: '{ent.type_code}'")
    print(f"  key_composite: '{ent.key_composite}'")
    print(f"  parent_ref: {ent.parent_ref}")
    print(f"  props: {ent.props}")
    print(f"  get('CD'): '{ent.get('CD')}'")
    print(f"  get('FNS'): '{ent.get('FNS')}'")
    print(f"  get('LBL'): '{ent.get('LBL')}'")
    print()
