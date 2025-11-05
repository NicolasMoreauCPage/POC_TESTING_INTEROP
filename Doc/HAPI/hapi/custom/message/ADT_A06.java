/*
 * Crée le  05/07/2005 LLR GIP CPage
 *
 * Venue - Changement de statut : "Changement de statut externe -> hospitalisé"
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.group.ADT_A06_INSURANCE;
import ca.uhn.hl7v2.model.v25.group.ADT_A06_PROCEDURE;
import ca.uhn.hl7v2.model.v25.segment.ACC;
import ca.uhn.hl7v2.model.v25.segment.AL1;
import ca.uhn.hl7v2.model.v25.segment.DB1;
import ca.uhn.hl7v2.model.v25.segment.DG1;
import ca.uhn.hl7v2.model.v25.segment.DRG;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.GT1;
import ca.uhn.hl7v2.model.v25.segment.MRG;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.NK1;
import ca.uhn.hl7v2.model.v25.segment.OBX;
import ca.uhn.hl7v2.model.v25.segment.PD1;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.model.v25.segment.PV1;
import ca.uhn.hl7v2.model.v25.segment.PV2;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.model.v25.segment.UB1;
import ca.uhn.hl7v2.model.v25.segment.UB2;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.group.ADT_A06_RESPONSABLE;
import fr.cpage.interfaces.hapi.custom.group.ADT_A06_TRAITANT;
import fr.cpage.interfaces.hapi.custom.segment.ZBE;
import fr.cpage.interfaces.hapi.custom.segment.ZFM;
import fr.cpage.interfaces.hapi.custom.segment.ZFP;
import fr.cpage.interfaces.hapi.custom.segment.ZFU;
import fr.cpage.interfaces.hapi.custom.segment.ZFV;
import fr.cpage.interfaces.hapi.custom.segment.ZPA;

/**
 * <p>
 * Represents a ADT_A06 message structure (see chapter 3.3.6). This structure contains the following elements:
 * </p>
 * 0: MSH (Message Header) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (Event Type) <b></b><br>
 * 3: PID (Patient Identification) <b></b><br>
 * 4: PD1 (Patient Additional Demographic) <b>optional </b><br>
 * 5: ROL (Role) <b>optional repeating</b><br>
 * 6: MRG (Merge Patient Information) <b>optional </b><br>
 * 7: NK1 (Next of Kin / Associated Parties) <b>optional repeating</b><br>
 * 8: PV1 (Patient Visit) <b></b><br>
 * 9: PV2 (Patient Visit - Additional Information) <b>optional </b><br>
 * 10: ZBE (Identification des mouvements de localisation en unité de soin) <b>optional </b></br> 11: ZFP (Situation
 * professionnelle) <b>optional </b><br>
 * 12: ZFV (Informations supplémentaires sur la venue) <b>optional </b><br>
 * 13: ROL (Role) <b>optional repeating</b><br>
 * 14: DB1 (Disability) <b>optional repeating</b><br>
 * 15: OBX (Observation/Result) <b>optional repeating</b><br>
 * 16: AL1 (Patient Allergy Information) <b>optional repeating</b><br>
 * 17: DG1 (Diagnosis) <b>optional repeating</b><br>
 * 18: DRG (Diagnosis Related Group) <b>optional </b><br>
 * 19: ADT_A06_PROCEDURE (a Group object) <b></b><br>
 * 20: GT1 (Guarantor) <b>optional repeating</b><br>
 * 21: ADT_A06_INSURANCE (a Group object) <b></b><br>
 * 22: ACC (Accident) <b>optional </b><br>
 * 23: UB1 (UB82) <b>optional </b><br>
 * 24: UB2 (UB92 Data) <b>optional </b><br>
 */
/**
 * <p>
 * Ajouts des segments spécifiques IHE France , IHE Allemagne et propriétaire CPage ZFU ZBE et ZPA en fin de message
 * </p>
 * 25: ZFU (Identification des unités fonctionnelles des séjours) <b>optional </b></br>
 * 26: ZPA (Identification des informations additionnelles du patient) <b>optional </b></br>
 *
 * @author LEYOUDEC 15/06/05
 */

public class ADT_A06 extends AbstractMessage {

  /**
   * Creates a new ADT_A06 Group with custom ModelClassFactory.
   */
  public ADT_A06(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A06 Group with DefaultModelClassFactory.
   */
  public ADT_A06() {
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
      this.add(ADT_A06_TRAITANT.class, false, true);
      this.add(MRG.class, false, false);
      this.add(NK1.class, false, true);
      this.add(PV1.class, true, false);
      this.add(PV2.class, false, false);
      this.add(ZBE.class, false, false);
      this.add(ZFP.class, false, false);
      this.add(ZFV.class, false, false);
      this.add(ZFM.class, false, false);
      this.add(ADT_A06_RESPONSABLE.class, false, true);
      this.add(DB1.class, false, true);
      this.add(OBX.class, false, true);
      this.add(AL1.class, false, true);
      this.add(DG1.class, false, true);
      this.add(DRG.class, false, false);
      this.add(ADT_A06_PROCEDURE.class, false, false);
      this.add(GT1.class, false, true);
      this.add(ADT_A06_INSURANCE.class, false, false);
      this.add(ACC.class, false, false);
      this.add(UB1.class, false, false);
      this.add(UB2.class, false, false);
      this.add(ZFU.class, false, false);
      this.add(ZPA.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A06 - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns first repetition of ADT_A06_TRAITANT (a Group object) (Role) - creates it if necessary
   */
  public ADT_A06_TRAITANT getTRAITANT() {
    ADT_A06_TRAITANT ret = null;
    try {
      ret = (ADT_A06_TRAITANT) this.get("TRAITANT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ADT_A06_TRAITANT (a Group object) (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of
   * existing repetitions.
   */
  public ADT_A06_TRAITANT getTRAITANT(final int rep) throws HL7Exception {
    return (ADT_A06_TRAITANT) this.get("TRAITANT", rep);
  }

  /**
   * Returns the number of existing repetitions of ADT_A06_TRAITANT
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
  public ADT_A06_RESPONSABLE getRESP() {
    ADT_A06_RESPONSABLE ret = null;
    try {
      ret = (ADT_A06_RESPONSABLE) this.get("RESP");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ROL2 (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing repetitions.
   */
  public ADT_A06_RESPONSABLE getRESP(final int rep) throws HL7Exception {
    return (ADT_A06_RESPONSABLE) this.get("RESP", rep);
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
   * Returns ADT_A06_PROCEDURE (a Group object) - creates it if necessary
   */
  public ADT_A06_PROCEDURE getPROCEDURE() {
    ADT_A06_PROCEDURE ret = null;
    try {
      ret = (ADT_A06_PROCEDURE) this.get("PROCEDURE");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns ZFU (Identification des unités fonctionnelles des séjours) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZFU getZFU() {
    ZFU ret = null;
    try {
      ret = (ZFU) this.get("ZFU");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFU

  /**
   * Returns ZBE (Identification des mouvements de localisation en unité de soin) - creates it if necessary
   *
   * @author LEYOUDEC
   */
  public ZBE getZBE() {
    ZBE ret = null;
    try {
      ret = (ZBE) this.get("ZBE");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZBE

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
   * Returns ZFP (Situation professionnelle) - creates it if necessary
   *
   * @author REBOURS
   */
  public ZFP getZFP() {
    ZFP ret = null;
    try {
      ret = (ZFP) this.get("ZFP");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFP

  /**
   * Returns ZFV (Informations supplémentaires sur la venue) - creates it if necessary
   *
   * @author REBOURS
   */
  public ZFV getZFV() {
    ZFV ret = null;
    try {
      ret = (ZFV) this.get("ZFV");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFV

}
