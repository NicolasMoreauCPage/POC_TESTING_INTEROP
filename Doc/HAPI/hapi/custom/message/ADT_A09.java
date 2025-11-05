/*
 * CreatedDate: 5 juil. 05
 * Author: lleyoudec
 * Society: GIP CPAGE
 * $LastChangedDate: 2009-08-11 10:46:00 $
 * $Revision: 0 $
 * $LastChangedBy: drebours $
 */

package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractMessage;
import ca.uhn.hl7v2.model.v25.group.ADT_A05_INSURANCE;
import ca.uhn.hl7v2.model.v25.group.ADT_A05_PROCEDURE;
import ca.uhn.hl7v2.model.v25.segment.ACC;
import ca.uhn.hl7v2.model.v25.segment.AL1;
import ca.uhn.hl7v2.model.v25.segment.DB1;
import ca.uhn.hl7v2.model.v25.segment.DG1;
import ca.uhn.hl7v2.model.v25.segment.DRG;
import ca.uhn.hl7v2.model.v25.segment.EVN;
import ca.uhn.hl7v2.model.v25.segment.GT1;
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
import fr.cpage.interfaces.hapi.custom.group.ADT_A05_RESPONSABLE;
import fr.cpage.interfaces.hapi.custom.group.ADT_A05_TRAITANT;
import fr.cpage.interfaces.hapi.custom.segment.ZBE;
import fr.cpage.interfaces.hapi.custom.segment.ZFD;
import fr.cpage.interfaces.hapi.custom.segment.ZFM;
import fr.cpage.interfaces.hapi.custom.segment.ZFP;
import fr.cpage.interfaces.hapi.custom.segment.ZFU;
import fr.cpage.interfaces.hapi.custom.segment.ZFV;
import fr.cpage.interfaces.hapi.custom.segment.ZPA;

/**
 * Structure ADT_A05.
 */
public class ADT_A09 extends AbstractMessage {

  /**
   * Creates a new ADT_A05 Group with custom ModelClassFactory.
   */
  public ADT_A09(final ModelClassFactory factory) {
    super(factory);
    init(factory);
  }

  /**
   * Creates a new ADT_A05 Group with DefaultModelClassFactory.
   */
  public ADT_A09() {
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
      this.add(ADT_A05_TRAITANT.class, false, true);
      this.add(NK1.class, false, true);
      this.add(PV1.class, true, false);
      this.add(PV2.class, false, false);
      this.add(ZBE.class, false, false);
      this.add(ZFP.class, false, false);
      this.add(ZFV.class, false, false);
      this.add(ZFM.class, false, false);
      this.add(ZFD.class, false, false);
      this.add(ADT_A05_RESPONSABLE.class, false, true);
      this.add(DB1.class, false, true);
      this.add(OBX.class, false, true);
      this.add(AL1.class, false, true);
      this.add(DG1.class, false, true);
      this.add(DRG.class, false, false);
      this.add(ADT_A05_PROCEDURE.class, false, true);
      this.add(GT1.class, false, true);
      this.add(ADT_A05_INSURANCE.class, false, true);
      this.add(ACC.class, false, false);
      this.add(UB1.class, false, false);
      this.add(UB2.class, false, false);
      this.add(ZFU.class, false, false);
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error creating ADT_A05 - this is probably a bug in the source code generator.", e);
    }
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
  }

  /**
   * Retourne ZFD (Informations démographiques).
   *
   * @return Segment ZFD
   */
  public ZFD getZFD() {
    ZFD ret = null;
    try {
      ret = (ZFD) this.get("ZFD");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Retourne ZBE (Informations mouvements).
   *
   * @return Segment ZBE
   */
  public ZBE getZBE() {
    ZBE ret = null;
    try {
      ret = (ZBE) this.get("ZBE");
    } catch (final HL7Exception e) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected error accessing data - this is probably a bug in the source code generator.", e);
    }
    return ret;
  }

  /**
   * Retourne ZFV (Complément venue).
   *
   * @return Segment ZFV
   */
  public ZFV getZFV() {
    ZFV ret = null;
    try {
      ret = (ZFV) this.get("ZFV");
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
}
