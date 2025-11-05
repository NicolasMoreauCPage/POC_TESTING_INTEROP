/*
 * Crée le 05/07/2005 LLR GIP CPage
 *
 */

package fr.cpage.interfaces.hapi.custom.group;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractGroup;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.v25.segment.GT1;
import ca.uhn.hl7v2.model.v25.segment.IN1;
import ca.uhn.hl7v2.model.v25.segment.IN2;
import ca.uhn.hl7v2.model.v25.segment.IN3;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents the ADT_A05_INSURANCE Group. A Group is an ordered collection of message segments that can repeat together or be optionally in/excluded together. This Group contains the following
 * elements:
 * </p>
 * 0: GT1 1: IN1 (IN1 - insurance segment) <b></b><br>
 * 2: IN2 (IN2 - insurance additional information segment) <b>optional </b><br>
 * 3: IN3 (IN3 - insurance additional information, certification segment) <b>optional repeating</b><br>
 */

public class ADT_A05_INSURANCE2 extends AbstractGroup {

  /**
   * Creates a new ADT_A05_INSURANCE Group.
   */
  public ADT_A05_INSURANCE2(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    try {
      this.add(GT1.class, true, false);
      this.add(IN1.class, true, false);
      this.add(IN2.class, false, false);
      this.add(IN3.class, false, true);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A05_INSURANCE - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns GT1 (GT1 - insurance segment) - creates it if necessary
   */
  public GT1 getGT1() {
    GT1 ret = null;
    try {
      ret = (GT1) this.get("GT1");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns IN1 (IN1 - insurance segment) - creates it if necessary
   */
  public IN1 getIN1() {
    IN1 ret = null;
    try {
      ret = (IN1) this.get("IN1");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns IN2 (IN2 - insurance additional information segment) - creates it if necessary
   */
  public IN2 getIN2() {
    IN2 ret = null;
    try {
      ret = (IN2) this.get("IN2");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns first repetition of IN3 (IN3 - insurance additional information, certification segment) - creates it if necessary
   */
  public IN3 getIN3() {
    IN3 ret = null;
    try {
      ret = (IN3) this.get("IN3");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of IN3 (IN3 - insurance additional information, certification segment) - creates it if necessary throws HL7Exception if the repetition requested is more than one
   * greater than the number of existing repetitions.
   */
  public IN3 getIN3(final int rep) throws HL7Exception {
    return (IN3) this.get("IN3", rep);
  }

  /**
   * Returns the number of existing repetitions of IN3
   */
  public int getIN3Reps() {
    int reps = -1;
    try {
      reps = getAll("IN3").length;
    } catch (final HL7Exception e) {
      final String message = "Unexpected error accessing data - this is probably a bug in the source code generator.";
      CPageLogFactory.getLog(this.getClass()).error(message, e);
      throw new Error(message);
    }
    return reps;
  }

}
