/*
 * Crée le    05/07/2005 LLR GIP CPage
 * Modifié le 29/08/2005 LLR GIP CPage - Suppression du segment ZBE suite à màj des spécifications par BM.
 *
 * Venue (admission) - Maj : "Mise à jour des informations de la venue courante"
 * Venue (admission) - Maj : "Mise à jour des informations de la venue historique"
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.segment.ACC;
import ca.uhn.hl7v2.model.v25.segment.AL1;
import ca.uhn.hl7v2.model.v25.segment.DB1;
import ca.uhn.hl7v2.model.v25.segment.DG1;
import ca.uhn.hl7v2.model.v25.segment.DRG;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.GT1;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.NK1;
import ca.uhn.hl7v2.model.v25.segment.OBX;
import ca.uhn.hl7v2.model.v25.segment.PD1;
import ca.uhn.hl7v2.model.v25.segment.PDA;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.model.v25.segment.PV1;
import ca.uhn.hl7v2.model.v25.segment.PV2;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.model.v25.segment.UB1;
import ca.uhn.hl7v2.model.v25.segment.UB2;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.group.ADT_A08_INSURANCE;
import fr.cpage.interfaces.hapi.custom.group.ADT_A08_PROCEDURE;
import fr.cpage.interfaces.hapi.custom.group.ADT_A08_RESPONSABLE;
import fr.cpage.interfaces.hapi.custom.group.ADT_A08_TRAITANT;
import fr.cpage.interfaces.hapi.custom.segment.ZFI;
import fr.cpage.interfaces.hapi.custom.segment.ZFT;
import fr.cpage.interfaces.hapi.custom.segment.ZFU;
import fr.cpage.interfaces.hapi.custom.segment.ZPA;
import fr.cpage.interfaces.hapi.custom.segment.ZPV;

/**
 * <p>
 * Represents a ADT_A08 message structure (see chapter 3.3.8). This structure contains the following elements:
 * </p>
 * 0: MSH (MSH - message header segment) <b></b><br>
 * 2: SFT (Software Segment) <b>optional repeating</b><br>
 * 3: EVN (EVN - event type segment) <b></b><br>
 * 4: PID (PID - patient identification segment) <b></b><br>
 * 5: PD1 (PD1 - patient additional demographic segment) <b>optional </b><br>
 * 6: ROL (Role) <b>optional repeating</b><br>
 * 7: NK1 (NK1 - next of kin / associated parties segment-) <b>optional repeating</b><br>
 * 8: PV1 (PV1 - patient visit segment-) <b></b><br>
 * 9: PV2 (PV2 - patient visit - additional information segment) <b>optional </b><br>
 * 10: DB1 (DB1 - Disability segment) <b>optional repeating</b><br>
 * 11: OBX (OBX - observation/result segment) <b>optional repeating</b><br>
 * 12: AL1 (AL1 - patient allergy information segment) <b>optional repeating</b><br>
 * 13: DG1 (DG1 - diagnosis segment) <b>optional repeating</b><br>
 * 14: DRG (DRG - diagnosis related group segment) <b>optional </b><br>
 * 15: ADT_A08_PROCEDURE (a Group object) <b>optional repeating</b><br>
 * 16: GT1 (GT1 - guarantor segment) <b>optional repeating</b><br>
 * 17: ADT_A08_INSURANCE (a Group object) <b>optional repeating</b><br>
 * 18: ACC (ACC - accident segment) <b>optional </b><br>
 * 19: UB1 (UB1 - UB82 data segment) <b>optional </b><br>
 * 20: UB2 (UB2 - UB92 data segment) <b>optional </b><br>
 * 21: PDA (Patient Death and Autopsy) <b>optional </b><br>
 */
/**
 * <p>
 * Ajouts des segments spécifiques IHE France , IHE Allemagne et propriétaire CPage ZFU ZBE ZPA ZPV ZFT et ZFI en fin de message
 * </p>
 * 22: ZFU (Identification des unités fonctionnelles des séjours) <b>optional </b></br>
 * Màj le 29/08/05 suite à modification des spécifications par BM : segment ZBE supprimé du message A08 23: ZBE (Identification des mouvements de localisation en unité de soin) <b>optional
 * </b></br>
 * 24: ZPA (Identification des informations additionnelles du patient) <b>optional </b></br>
 * 25: ZPV (Informations complémentaires sur le passage à l'hôpital) <b>optional </b></br>
 * 26: ZFT (Identification des périodes tarifaire dans l'unité de soins) <b>optional </b></br>
 * 27: ZFI (Identification des périodes élémentaires en unité de soins) <b>optional </b></br>
 *
 * @author LEYOUDEC
 */

public class ADT_A08 extends AbstractMessage {

  /**
   * Creates a new ADT_A08 Group with custom ModelClassFactory.
   */
  public ADT_A08(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A08 Group with DefaultModelClassFactory.
   */
  public ADT_A08() {
    super(new DefaultModelClassFactory());
    init(new DefaultModelClassFactory());
  }

  @SuppressWarnings("unused")
  private void init(final ModelClassFactory factory) {
    try {
      this.add(MSH.class, true, false);
      this.add(SFT.class, false, true);
      this.add(EVN.class, true, false);
      this.add(PID.class, true, false);
      this.add(PD1.class, false, false);
      this.add(ADT_A08_TRAITANT.class, false, true);
      this.add(NK1.class, false, true);
      this.add(PV1.class, true, false);
      this.add(PV2.class, false, false);
      this.add(ADT_A08_RESPONSABLE.class, false, true);
      this.add(DB1.class, false, true);
      this.add(OBX.class, false, true);
      this.add(AL1.class, false, true);
      this.add(DG1.class, false, true);
      this.add(DRG.class, false, false);
      this.add(ADT_A08_PROCEDURE.class, false, true);
      this.add(GT1.class, false, true);
      this.add(ADT_A08_INSURANCE.class, false, true);
      this.add(ACC.class, false, false);
      this.add(UB1.class, false, false);
      this.add(UB2.class, false, false);
      this.add(PDA.class, false, false);
      this.add(ZFU.class, false, false);
      /* Màj le 29/08/05 suite à modification des spécifications par BM : segment ZBE supprimé du message A08 */
      // this.add(ZBE.class, false, false);
      this.add(ZPA.class, false, false);
      this.add(ZPV.class, false, false);
      this.add(ZFT.class, false, false);
      this.add(ZFI.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A08 - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns first repetition of ADT_A08_TRAITANT (a Group object) (Role) - creates it if necessary
   */
  public ADT_A08_TRAITANT getTRAITANT() {
    ADT_A08_TRAITANT ret = null;
    try {
      ret = (ADT_A08_TRAITANT) this.get("TRAITANT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ADT_A08_TRAITANT (a Group object) (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of
   * existing repetitions.
   */
  public ADT_A08_TRAITANT getTRAITANT(final int rep) throws HL7Exception {
    return (ADT_A08_TRAITANT) this.get("TRAITANT", rep);
  }

  /**
   * Returns the number of existing repetitions of ADT_A08_TRAITANT
   */
  public int getTRAITANTReps() {
    int reps = -1;
    try {
      reps = getAll("TRAITANT").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

  /**
   * Returns first repetition of ROL2 (Role) - creates it if necessary
   */
  public ADT_A08_RESPONSABLE getRESP() {
    ADT_A08_RESPONSABLE ret = null;
    try {
      ret = (ADT_A08_RESPONSABLE) this.get("RESP");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ROL2 (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing repetitions.
   */
  public ADT_A08_RESPONSABLE getRESP(final int rep) throws HL7Exception {
    return (ADT_A08_RESPONSABLE) this.get("RESP", rep);
  }

  /**
   * Returns the number of existing repetitions of ROL2
   */
  public int getRESPReps() {
    int reps = -1;
    try {
      reps = getAll("RESP").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

  /**
   * Returns first repetition of ADT_A08_PROCEDURE (a Group object) - creates it if necessary
   */
  public ADT_A08_PROCEDURE getPROCEDURE() {
    ADT_A08_PROCEDURE ret = null;
    try {
      ret = (ADT_A08_PROCEDURE) this.get("PROCEDURE");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ADT_A08_PROCEDURE (a Group object) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing
   * repetitions.
   */
  public ADT_A08_PROCEDURE getPROCEDURE(final int rep) throws HL7Exception {
    return (ADT_A08_PROCEDURE) this.get("PROCEDURE", rep);
  }

  /**
   * Returns the number of existing repetitions of ADT_A08_PROCEDURE
   */
  public int getPROCEDUREReps() {
    int reps = -1;
    try {
      reps = getAll("ADT_A08_PROCEDURE").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

  /**
   * Returns first repetition of ADT_A08_INSURANCE (a Group object) - creates it if necessary
   */
  public ADT_A08_INSURANCE getINSURANCE() {
    ADT_A08_INSURANCE ret = null;
    try {
      ret = (ADT_A08_INSURANCE) this.get("INSURANCE");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ADT_A08_INSURANCE (a Group object) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing
   * repetitions.
   */
  public ADT_A08_INSURANCE getINSURANCE(final int rep) throws HL7Exception {
    return (ADT_A08_INSURANCE) this.get("INSURANCE", rep);
  }

  /**
   * Returns the number of existing repetitions of ADT_A08_INSURANCE
   */
  public int getINSURANCEReps() {
    int reps = -1;
    try {
      reps = getAll("ADT_A08_INSURANCE").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

  /**
   * Returns ZFU (Identification des unités fonctionnelles des séjours) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZFU getZFU() {
    ZFU ret = null;
    try {
      ret = (ZFU) this.get("ZV");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFU

  /**
   * Returns ZBE (Identification des mouvements de localisation en unité de soin) - creates it if necessary Modification le 29/08/05 - Màj des spécifications par BM : suppression du segment ZBE
   *
   * @author LEYOUDEC
   */
  /*
   * Màj le 29/08/05 suite à modification des spécifications par BM : segment ZBE supprimé du message A08 public ZBE getZBE() { ZBE ret = null; try { ret = (ZBE)this.get("ZBE"); }
   * catch(HL7Exception e) { CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e); } return ret; }//Fin ZBE
   */

  /**
   * Returns ZPA (Identification des informations additionnelles du patient) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZPA getZPA() {
    ZPA ret = null;
    try {
      ret = (ZPA) this.get("ZPA");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZPA

  /**
   * Returns ZPV (Informations complémentaires sur le passage à l'hôpital) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZPV getZPV() {
    ZPV ret = null;
    try {
      ret = (ZPV) this.get("ZPV");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZPV

  /**
   * Returns ZFT (Identification des périodes tarifaire dans l'unité de soins) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZFT getZFT() {
    ZFT ret = null;
    try {
      ret = (ZFT) this.get("ZFT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFT

  /**
   * Returns ZFI (Identification des périodes élémentaires en unité de soins) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZFI getZFI() {
    ZFI ret = null;
    try {
      ret = (ZFI) this.get("ZFI");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFI

}
