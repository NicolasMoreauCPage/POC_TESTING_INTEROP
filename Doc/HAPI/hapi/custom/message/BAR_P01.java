/*
 * Crée le  13/07/2005 LLR GIP CPage
 *
 * Venue (admission)- Entrée : "Création du dossier administratif"
 *
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.group.BAR_P01_VISIT;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.PD1;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.model.v25.segment.SFT;
import ca.uhn.hl7v2.parser.DefaultModelClassFactory;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;
import fr.cpage.interfaces.hapi.custom.group.BAR_P01_TRAITANT;

/**
 * <p>
 * Represents a BAR_P01 message structure (see chapter 6.4.1). This structure contains the following elements:
 * </p>
 * 0: MSH (Message Header) <b></b><br>
 * 1: SFT (Software Segment) <b>optional repeating</b><br>
 * 2: EVN (Event Type) <b></b><br>
 * 3: PID (Patient Identification) <b></b><br>
 * 4: PD1 (Patient Additional Demographic) <b>optional </b><br>
 * 5: ROL (Role) <b>optional repeating</b><br>
 * 6: BAR_P01_VISIT (a Group object) <b>repeating</b><br>
 */
public class BAR_P01 extends AbstractMessage {

  /**
   * Creates a new BAR_P01 Group with custom ModelClassFactory.
   */
  public BAR_P01(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new BAR_P01 Group with DefaultModelClassFactory.
   */
  public BAR_P01() {
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
      this.add(BAR_P01_TRAITANT.class, false, true);
      this.add(BAR_P01_VISIT.class, true, true);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating BAR_P01 - this is probably a bug in the source code generator.", e);
    }
  }

  /**
   * Returns first repetition of BAR_P01_TRAITANT (a Group object) (Role) - creates it if necessary
   */
  public BAR_P01_TRAITANT getTRAITANT() {
    BAR_P01_TRAITANT ret = null;
    try {
      ret = (BAR_P01_TRAITANT) this.get("TRAITANT");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Returns a specific repetition of BAR_P01_TRAITANT (a Group object) (Role) - creates it if necessary throws HL7Exception if the repetition requested is more than one greater than the number of
   * existing repetitions.
   */
  public BAR_P01_TRAITANT getTRAITANT(final int rep) throws HL7Exception {
    return (BAR_P01_TRAITANT) this.get("TRAITANT", rep);
  }

}
