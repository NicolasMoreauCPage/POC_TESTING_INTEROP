/*
 * Crée le  08/06/2008 DI GIP CPage
 *
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.group.ADT_A39_PATIENT;
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
 * Represents a ADT_A39 message structure (see chapter 3.3.40). This structure contains the following elements:
 * </p>
 * 0: MSH (Message header segment) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (EVN - event type segment) <b></b><br>
 * 3: ADT_A39_PATIENT (a Group object) <b>repeating</b><br>
 * 4: ZFP (Situation professionnelle) <b>optional </b><br>
 */
/**
 * <p>
 * Ajouts du segment propriétaire CPage ZPA en fin de message
 * </p>
 * 5: ZPA (Identification des informations additionnelles du patient) <b>optional </b></br>
 */

public class ADT_A39 extends AbstractMessage {

  /**
   * Creates a new ADT_A39 Group with custom ModelClassFactory.
   */
  public ADT_A39(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A39 Group with DefaultModelClassFactory.
   */
  public ADT_A39() {
    super(new DefaultModelClassFactory());
    init(new DefaultModelClassFactory());
  }

  private void init(final ModelClassFactory factory) {
    try {
      this.add(MSH.class, true, false);
      this.add(SFT.class, false, true);
      this.add(EVN.class, true, false);
      // this.add(PID.class, true, false);
      this.add(ADT_A39_PATIENT.class, false, true);
      this.add(ZFP.class, false, false);
      this.add(ZPA.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A39 - this is probably a bug in the source code generator.", e);
    }
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

}
