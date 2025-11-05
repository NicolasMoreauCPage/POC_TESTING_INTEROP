/*
 * Crée le 05/07/2005 LLR GIP CPage
 *
 */

package fr.cpage.interfaces.hapi.custom.group;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractGroup;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.v25.segment.PR1;
import ca.uhn.hl7v2.model.v25.segment.ROL;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents the ADT_A08_PROCEDURE Group. A Group is an ordered collection of message segments that can repeat together or be optionally in/excluded together. This Group contains the following
 * elements:
 * </p>
 * 0: PR1 (PR1 - procedures segment) <b></b><br>
 * 1: ROL (Role) <b>optional repeating</b><br>
 */

public class ADT_A08_PROCEDURE extends AbstractGroup {

  /**
   * Creates a new ADT_A08_PROCEDURE Group.
   */
  public ADT_A08_PROCEDURE(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    try {
      this.add(PR1.class, true, false);
      this.add(ROL.class, false, true);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A08_PROCEDURE - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns PR1 (PR1 - procedures segment) - creates it if necessary
   */
  public PR1 getPR1() {
    PR1 ret = null;
    try {
      ret = (PR1) this.get("PR1");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns first repetition of ROL (Role) - creates it if necessary
   */
  public ROL getROL() {
    ROL ret = null;
    try {
      ret = (ROL) this.get("ROL");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of ROL (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of existing repetitions.
   */
  public ROL getROL(final int rep) throws HL7Exception {
    return (ROL) this.get("ROL", rep);
  }

  /**
   * Returns the number of existing repetitions of ROL
   */
  public int getROLReps() {
    int reps = -1;
    try {
      reps = getAll("ROL").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

}
