/*
 * Crée le  13/01/2006 DRE GIP CPage
 *
 */

package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.IS;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZFM segment : "Identification des périodes élémentaires en unité de soin" "support du recueil du PMSI court ou moyen séjour". This segment has the following
 * fields:
 * </p>
 * <p>
 * ZFM-1: Mode d'entrée PMSI (IS)<br>
 * ZFM-2: Mode de sortie PMSI (IS)<br>
 * ZFM-3: Mode de provenance PMSI (IS)<br>
 * ZFM-4: Mode de destination PMSI (IS)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 *
 * @author REBOURS
 */
public class ZFM extends AbstractSegment {

  /**
   * Creates a ZFM (Mouvement PMSI) segment object that belongs to the given message.
   */
  public ZFM(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(IS.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(IS.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(IS.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(IS.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Mode d'entrée PMSI (ZFM-1).
   */
  public IS getModeEntreePMSI() {
    IS ret = null;
    try {
      final Type t = this.getField(1, 0);
      ret = (IS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFM-1

  /**
   * Returns Mode de sortie PMSI (ZFM-2).
   */
  public IS getModeSortiePMSI() {
    IS ret = null;
    try {
      final Type t = this.getField(2, 0);
      ret = (IS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFM-2

  /**
   * Returns Mode de provenance PMSI (ZFM-3).
   */
  public IS getModeProvenancePMSI() {
    IS ret = null;
    try {
      final Type t = this.getField(3, 0);
      ret = (IS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFM-3

  /**
   * Returns Mode de destination PMSI (ZFM-4).
   */
  public IS getModeDestinationPMSI() {
    IS ret = null;
    try {
      final Type t = this.getField(4, 0);
      ret = (IS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFM-4
}
