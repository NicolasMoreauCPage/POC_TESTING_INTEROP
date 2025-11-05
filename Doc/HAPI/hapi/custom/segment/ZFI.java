/*
 * Crée le  05/07/2005 LLR GIP CPage
 *
 */

package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.ID;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZFV segment : "Identification des périodes élémentaires en unité de soin" "support du recueil du PMSI court ou moyen séjour". This segment has the following
 * fields:
 * </p>
 * <p>
 * ZFI-1: Type RSS UF provenance (ID)<br>
 * ZFI-2: Code RSS entrée (ID)<br>
 * ZFI-3: Date d'entrée (TS)<br>
 * ZFI-4: Type RSS UF de destination (ID)<br>
 * ZFI-5: Code RSS de sortie (ID)<br>
 * ZFI-6: Date de sortie (TS)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 *
 * @author LEYOUDEC
 */
public class ZFI extends AbstractSegment {

  /**
   * Creates a ZFI (identification des périodes élémentaires en unité de soins) segment object that belongs to the given message.
   */
  public ZFI(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Type RSS UF provenance (ZFI-1).
   */
  public ID getTypeRSSufProvenance() {
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
  }// Fin ZFI-1

  /**
   * Returns Code RSS entrée (ZFI-2).
   */
  public ID getCodeRSSEntree() {
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
  }// Fin ZFI-2

  /**
   * Returns Date d'entrée (ZFI-3).
   */
  public TS getDateEntree() {
    TS ret = null;
    try {
      final Type t = this.getField(3, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFI-3

  /**
   * Returns Type RSS UF de destination (ZFI-4).
   */
  public ID getTypeRSSufDestination() {
    ID ret = null;
    try {
      final Type t = this.getField(4, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFI-4

  /**
   * Returns Code RSS de sortie (ZFI-5).
   */
  public ID getCodeRSSSortie() {
    ID ret = null;
    try {
      final Type t = this.getField(5, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFI-5

  /**
   * Returns Date de sortie (ZFI-6).
   */
  public TS getDateSortie() {
    TS ret = null;
    try {
      final Type t = this.getField(6, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFI-6
}
