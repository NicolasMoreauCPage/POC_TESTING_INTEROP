/*
 * Crée le 05/07/2005 LLR GIP CPage
 *
 */

package fr.cpage.interfaces.hapi.custom.group;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractGroup;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.v25.segment.MRG;
import ca.uhn.hl7v2.model.v25.segment.PD1;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.model.v25.segment.PV1;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.segment.ZFP;

/**
 * <p>
 * Represents the ADT_A41_PATIENT Group. A Group is an ordered collection of message segments that can repeat together or be optionally in/excluded together. This Group contains the following
 * elements:
 * </p>
 * 0: PID (PID - patient identification segment) <b></b><br>
 * 1: PD1 (PD1 - patient additional demographic segment) <b>optional </b><br>
 * 2: MRG (MRG - merge patient information segment-) <b></b><br>
 * 3: PV1 (PV1 - patient visit segment-) <b>optional </b><br>
 * 4: ZFP (Situation professionnelle) <b>optional </b><br>
 */
public class ADT_A41_PATIENT extends AbstractGroup {

  /**
   * Creates a new ADT_A41_PATIENT Group.
   */
  public ADT_A41_PATIENT(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    try {
      this.add(PID.class, false, false);
      this.add(PD1.class, false, false);
      this.add(MRG.class, true, false);
      this.add(PV1.class, false, false);
      this.add(ZFP.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A41_PATIENT - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns PID (PID - patient identification segment) - creates it if necessary
   */
  public PID getPID() {
    PID ret = null;
    try {
      ret = (PID) this.get("PID");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns PD1 (PD1 - patient additional demographic segment) - creates it if necessary
   */
  public PD1 getPD1() {
    PD1 ret = null;
    try {
      ret = (PD1) this.get("PD1");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns MRG (MRG - merge patient information segment-) - creates it if necessary
   */
  public MRG getMRG() {
    MRG ret = null;
    try {
      ret = (MRG) this.get("MRG");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns PV1 (PV1 - patient visit segment-) - creates it if necessary
   */
  public PV1 getPV1() {
    PV1 ret = null;
    try {
      ret = (PV1) this.get("PV1");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

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
