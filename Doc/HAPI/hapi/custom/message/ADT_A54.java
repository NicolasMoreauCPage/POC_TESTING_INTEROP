/*
 * Crée le  05/07/2005 LLR GIP CPage
 *
 * Mouvement - Chang. resp. médico-admin. : "Changement de responsabilité médicale (médecin)"
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.segment.ACC;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.PD1;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.model.v25.segment.PV1;
import ca.uhn.hl7v2.model.v25.segment.PV2;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.group.ADT_A54_RESPONSABLE;
import fr.cpage.interfaces.hapi.custom.group.ADT_A54_TRAITANT;
import fr.cpage.interfaces.hapi.custom.segment.ZBE;
import fr.cpage.interfaces.hapi.custom.segment.ZFI;
import fr.cpage.interfaces.hapi.custom.segment.ZFM;
import fr.cpage.interfaces.hapi.custom.segment.ZFP;
import fr.cpage.interfaces.hapi.custom.segment.ZFT;
import fr.cpage.interfaces.hapi.custom.segment.ZFU;
import fr.cpage.interfaces.hapi.custom.segment.ZFV;
import fr.cpage.interfaces.hapi.custom.segment.ZPA;
import fr.cpage.interfaces.hapi.custom.segment.ZPV;

/**
 * <p>
 * Represents a ADT_A54 message structure (see chapter 3.3.54). This structure contains the following elements:
 * </p>
 * 0: MSH (Message Header) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (Event Type) <b></b><br>
 * 3: PID (Patient Identification) <b></b><br>
 * 4: PD1 (Patient Additional Demographic) <b>optional </b><br>
 * 5: ROL (Role) <b>optional repeating</b><br>
 * 6: PV1 (Patient Visit) <b></b><br>
 * 7: PV2 (Patient Visit - Additional Information) <b>optional </b><br>
 * 8: ZBE (Identification des mouvements de localisation en unité de soin) <b>optional </b></br> 9: ZFP (Situation
 * professionnelle) <b>optional </b><br>
 * 10: ZFV (Informations supplémentaires sur la venue) <b>optional </b><br>
 * 11: ZFM (Mouvement PMSI) <b>optional </b><br>
 * 12: ROL (Role) <b>optional repeating</b><br>
 * 13: ACC (Accident) <b>optional </b><br>
 */
/**
 * <p>
 * Ajouts des segments spécifiques IHE France , IHE Allemagne et propriétaire CPage ZFU ZBE ZPA ZPV ZFT et ZFI en fin de message
 * </p>
 * 14: ZFU (Identification des unités fonctionnelles des séjours) <b>optional </b></br>
 * 15: ZPA (Identification des informations additionnelles du patient) <b>optional </b></br>
 * 16: ZPV (Informations complémentaires sur le passage à l'hôpital) <b>optional </b></br>
 * 17: ZFT (Identification des périodes tarifaire dans l'unité de soins) <b>optional </b></br>
 * 18: ZFI (Identification des périodes élémentaires en unité de soins) <b>optional </b></br>
 *
 * @author LEYOUDEC
 */

public class ADT_A54 extends AbstractMessage {

  /**
   * Creates a new ADT_A54 Group with custom ModelClassFactory.
   */
  public ADT_A54(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A54 Group with DefaultModelClassFactory.
   */
  public ADT_A54() {
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
      this.add(ADT_A54_TRAITANT.class, false, true);
      this.add(PV1.class, true, false);
      this.add(PV2.class, false, false);
      this.add(ZBE.class, false, false);
      this.add(ZFP.class, false, false);
      this.add(ZFV.class, false, false);
      this.add(ZFM.class, false, false);
      this.add(ADT_A54_RESPONSABLE.class, false, true);
      this.add(ACC.class, false, false);
      this.add(ZFU.class, false, false);
      this.add(ZPA.class, false, false);
      this.add(ZPV.class, false, false);
      this.add(ZFT.class, false, false);
      this.add(ZFI.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A54 - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns first repetition of ADT_A54_TRAITANT (a Group object) (Role) - creates it if necessary
   */
  public ADT_A54_TRAITANT getTRAITANT() {
    ADT_A54_TRAITANT ret = null;
    try {
      ret = (ADT_A54_TRAITANT) this.get("TRAITANT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ADT_A54_TRAITANT (a Group object) (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of
   * existing repetitions.
   */
  public ADT_A54_TRAITANT getTRAITANT(final int rep) throws HL7Exception {
    return (ADT_A54_TRAITANT) this.get("TRAITANT", rep);
  }

  /**
   * Returns the number of existing repetitions of ADT_A54_TRAITANT
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
  public ADT_A54_RESPONSABLE getRESP() {
    ADT_A54_RESPONSABLE ret = null;
    try {
      ret = (ADT_A54_RESPONSABLE) this.get("RESP");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ROL2 (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing repetitions.
   */
  public ADT_A54_RESPONSABLE getRESP(final int rep) throws HL7Exception {
    return (ADT_A54_RESPONSABLE) this.get("RESP", rep);
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

  /**
   * Returns ZFM (Mouvement PMSI) - creates it if necessary
   *
   * @author REBOURS
   */
  public ZFM getZFM() {
    ZFM ret = null;
    try {
      ret = (ZFM) this.get("ZFM");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }// Fin ZFM

}
