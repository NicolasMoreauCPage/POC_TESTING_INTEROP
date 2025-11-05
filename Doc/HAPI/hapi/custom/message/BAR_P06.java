/*
 * Crée le  13/07/2005 LLR GIP CPage
 *
 * Venue (admission)- Sortie : "Clôture du dossier administratif"
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.group.BAR_P06_PATIENT;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents a BAR_P06 message structure (see chapter 6.4.6). This structure contains the following elements:
 * </p>
 * 0: MSH (Message Header) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (Event Type) <b></b><br>
 * 3: BAR_P06_PATIENT (a Group object) <b>repeating</b><br>
 */
public class BAR_P06 extends AbstractMessage {

  /**
   * Creates a new BAR_P06 Group with custom ModelClassFactory.
   */
  public BAR_P06(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new BAR_P06 Group with DefaultModelClassFactory.
   */
  public BAR_P06() {
    super(new DefaultModelClassFactory());
    init(new DefaultModelClassFactory());
  }

  @SuppressWarnings("unused")
  private void init(final ModelClassFactory factory) {
    try {
      this.add(MSH.class, true, false);
      this.add(SFT.class, false, true);
      this.add(EVN.class, true, false);
      this.add(BAR_P06_PATIENT.class, true, true);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating BAR_P06 - this is probably a bug in the source code generator.", e);
    }
  }

}
