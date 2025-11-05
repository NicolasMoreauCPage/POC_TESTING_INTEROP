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
import ca.uhn.hl7v2.model.v25.datatype.ST;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.model.v25.datatype.XON;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an IHE France TF 5.5 radio ZFU message segment : "Identification des unités fonctionnelles des séjours". This segment has the following fields:
 * </p>
 * <p>
 * ZFU-1: Nursing Functional Unit (XON)<br>
 * ZFU-2: NFU Date/time (TS)<br>
 * ZFU-3: Housing Functional Unit (XON)<br>
 * ZFU-4: HFU Date/time (TS)<br>
 * ZFU-5: Medical Functional Unit (XON)<br>
 * ZFU-6: MFU Date/time (TS)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 *
 * @author LEYOUDEC
 */
public class ZFU extends AbstractSegment {

  /**
   * Creates a ZFU (identification des unités fonctionnelles des séjours) segment object that belongs to the given message.
   */
  public ZFU(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(XON.class, false, 1, 60, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ST.class, false, 1, 60, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ST.class, false, 1, 60, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns UF responsable des soins (ZFU-1).
   */
  public XON getNursingFunctionalUnit() {
    XON ret = null;
    try {
      final Type t = this.getField(1, 0);
      ret = (XON) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFU-1

  /**
   * Returns Date de début de période (ZFU-2).
   */
  public TS getNFUDateTime() {
    TS ret = null;
    try {
      final Type t = this.getField(2, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFU-2

  /**
   * Returns UF d'hébergement (ZFU-3).
   */
  public XON getHousingFunctionalUnit() {
    XON ret = null;
    try {
      final Type t = this.getField(3, 0);
      ret = (XON) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFU-3

  /**
   * Returns Date d'entrée dans UF d'hébergement (ZFU-4).
   */
  public TS getHFUDateTime() {
    TS ret = null;
    try {
      final Type t = this.getField(4, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFU-4

  /**
   * Returns UF de responsabilité médico-administrative (ZFU-5).
   */
  public XON getMedicalFunctionalUnit() {
    XON ret = null;
    try {
      final Type t = this.getField(5, 0);
      ret = (XON) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFU-5

  /**
   * Returns Date d'entrée dans l'UF médicale (ZFU-6).
   */
  public TS getMFUDateTime() {
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
  }// Fin ZFU-6

}// Fin classe
