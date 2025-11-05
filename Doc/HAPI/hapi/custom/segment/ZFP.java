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
import ca.uhn.hl7v2.model.v25.datatype.ID;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZFP segment : "Identification des périodes élémentaires en unité de soin" "support du recueil du PMSI court ou moyen séjour". This segment has the following
 * fields:
 * </p>
 * <p>
 * ZFP-1: Activité socio-professionnelle (ID)<br>
 * ZFP-2: Catégorie socio-professionnelle (ID)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 *
 * @author REBOURS
 */
public class ZFP extends AbstractSegment {

  /**
   * Creates a ZFP (Situation professionnelle) segment object that belongs to the given message.
   */
  public ZFP(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 2, new Object[]{ message, Integer.valueOf(0) });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Activité socio-professionnelle (ZFP-1).
   */
  public ID getActiviteSocioProf() {
    ID ret = null;
    try {
      final Type t = this.getField(1, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFP-1

  /**
   * Returns Catégorie socio-professionnelle (ZFP-2).
   */
  public ID getCategorieSocioProf() {
    ID ret = null;
    try {
      final Type t = this.getField(2, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFP-2

}
