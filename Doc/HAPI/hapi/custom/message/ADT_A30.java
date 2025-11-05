package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.MRG;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.PD1;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.segment.ZFP;
import fr.cpage.interfaces.hapi.custom.segment.ZPA;

/**
 * <p>Represents a ADT_A30 message structure (see chapter 3.3.30). This structure contains the
 * following elements: </p>
 * 0: MSH (Message Header) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (Event Type) <b></b><br>
 * 3: PID (Patient Identification) <b></b><br>
 * 4: PD1 (Patient Additional Demographic) <b>optional </b><br>
 * 5: MRG (Merge patient information segment) <b></b><br>
 */
/**
 * <p>
 * Ajouts du segment propriétaire CPage ZPA en fin de message
 * </p>
 * 6: ZFP (Situation professionnelle) <b>optional </b><br>
 * 7: ZPA (Identification des informations additionnelles du patient) <b>optional </b></br>
 *
 * @author LEYOUDEC 13/07/05
 */

public class ADT_A30 extends AbstractMessage {

  /**
   * Creates a new ADT_A30 Group with custom ModelClassFactory.
   */
  public ADT_A30(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A30 Group with DefaultModelClassFactory.
   */
  public ADT_A30() {
    super(new DefaultModelClassFactory());
    init(new DefaultModelClassFactory());
  }

  private void init(final ModelClassFactory factory) {
    try {
      this.add(MSH.class, true, false);
      this.add(SFT.class, false, true);
      this.add(EVN.class, true, false);
      this.add(PID.class, true, false);
      this.add(PD1.class, false, false);
      this.add(MRG.class, true, false);
      this.add(ZFP.class, false, false);
      this.add(ZPA.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A38 - this is probably a bug in the source code generator.", e);
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
