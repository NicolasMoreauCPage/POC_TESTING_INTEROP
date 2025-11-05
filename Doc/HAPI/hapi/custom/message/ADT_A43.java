/*
 * Crée le  05/07/2005 LLR GIP CPage
 *
 * Mouvement - Fusion et rattachement : "Changement de lien de rattachement d'un dossier administratif à un IPP"
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.group.ADT_A43_PATIENT;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.segment.ZFP;
import fr.cpage.interfaces.hapi.custom.segment.ZPA;

/**
 * <p>
 * Represents a ADT_A43 message structure (see chapter 3.3.43). This structure contains the following elements:
 * </p>
 * 0: MSH (MSH - message header segment) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (EVN - event type segment) <b></b><br>
 * 3: ADT_A43_PIDPD1MRG (a Group object) <b>repeating</b><br>
 * 4: ZFP (Situation professionnelle) <b>optional </b><br>
 * <p>
 * Ajouts du segment propriétaire CPage ZPA en fin de message
 * </p>
 * 5: ZPA (Identification des informations additionnelles du patient) <b>optional </b></br>
 *
 * @author LEYOUDEC 13/07/05
 */
public class ADT_A43 extends AbstractMessage {

  /**
   * Creates a new ADT_A43 Group with custom ModelClassFactory.
   */
  public ADT_A43(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A43 Group with DefaultModelClassFactory.
   */
  public ADT_A43() {
    super(new DefaultModelClassFactory());
    init(new DefaultModelClassFactory());
  }

  private void init(final ModelClassFactory factory) {
    try {
      this.add(MSH.class, true, false);
      this.add(SFT.class, false, true);
      this.add(EVN.class, true, false);
      this.add(ADT_A43_PATIENT.class, true, true);
      this.add(ZFP.class, false, false);
      this.add(ZPA.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A43 - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns MSH (MSH - message header segment) - creates it if necessary
   */
  public MSH getMSH() {
    MSH ret = null;
    try {
      ret = (MSH) this.get("MSH");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns first repetition of SFT (Software Segment) - creates it if necessary
   */
  public SFT getSFT() {
    SFT ret = null;
    try {
      ret = (SFT) this.get("SFT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of SFT (Software Segment) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing repetitions.
   */
  public SFT getSFT(final int rep) throws HL7Exception {
    return (SFT) this.get("SFT", rep);
  }

  /**
   * Returns the number of existing repetitions of SFT
   */
  public int getSFTReps() {
    int reps = -1;
    try {
      reps = getAll("SFT").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

  /**
   * Returns EVN (EVN - event type segment) - creates it if necessary
   */
  public EVN getEVN() {
    EVN ret = null;
    try {
      ret = (EVN) this.get("EVN");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns first repetition of ADT_A43_PATIENT (a Group object) - creates it if necessary
   */
  public ADT_A43_PATIENT getPATIENT() {
    ADT_A43_PATIENT ret = null;
    try {
      ret = (ADT_A43_PATIENT) this.get("PATIENT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ADT_A43_PATIENT (a Group object) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing
   * repetitions.
   */
  public ADT_A43_PATIENT getPATIENT(final int rep) throws HL7Exception {
    return (ADT_A43_PATIENT) this.get("PATIENT", rep);
  }

  /**
   * Returns the number of existing repetitions of ADT_A43_PATIENT
   */
  public int getPATIENTReps() {
    int reps = -1;
    try {
      reps = getAll("ADT_A43_PATIENT").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

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

}
