/*
 * Créé le  07/07/2005 LLR GIP CPage
 * Modifié le 21/07/05 - Mise en conformité spécifications des interfaces V0.901 :
 * 						 ->Ajout de la déclaration de ZBE-4, ZBE-5 et ZBE-6.
 *
 */

package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.CWE;
import ca.uhn.hl7v2.model.v25.datatype.EI;
import ca.uhn.hl7v2.model.v25.datatype.ID;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.model.v25.datatype.XON;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an IHE Allemagne TF 5.5 message segment : "Identification des mouvements de localisation en unité de soins". This segment has the following fields:
 * </p>
 * <p>
 * ZBE-1: Movement ID (EI)<br>
 * ZBE-2: Start of Movement Date/Time (TS)<br>
 * ZBE-3: End of Movement Date/Time (TS)<br>
 * ZBE-4: Reason for Triggering the Movement (ST)<br>
 * ZBE-5: Historical Movement Indicator (ID)<br>
 * ZBE-6: Original trigger event code (if upd/canc) (ID)<br>
 * ZBE-7: Responsible Ward (Médical ou Housing ou vide) (XON)<br>
 * ZBE-8: Ward of care responsibility in the period starting with this movement (XON)<br>
 * ZBE-9: Nature of this movement (CWE)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 * Création le 07/07/05 LLR GIP CPage Modification le 21/07/05 LLR GIP CPage : Mise en conformité spécifications des interfaces V0.901 ->Ajout de la déclaration de ZBE-4, ZBE-5 et ZBE-6.
 *
 * @author LEYOUDEC
 */
public class ZBE extends AbstractSegment {

  /**
   * Creates a ZBE (identification des mouvements de localisation en unité de soins) segment object that belongs to the given message.
   */
  public ZBE(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(EI.class, true, 0, 250, new Object[]{ message });
      this.add(TS.class, true, 1, 26, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ID.class, true, 1, 6, new Object[]{ message });
      this.add(ID.class, true, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 3, new Object[]{ message, Integer.valueOf(0) });
      this.add(XON.class, false, 1, 6, new Object[]{ message });
      this.add(XON.class, false, 1, 6, new Object[]{ message });
      this.add(CWE.class, true, 1, 3, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }

  /**
   * Returns Identifiant du mouvement (ZBE-1).
   *
   * @return EI.
   */
  public EI[] getMovementID() {
    EI[] ret = null;
    try {
      final Type[] t = this.getField(1);
      ret = new EI[t.length];
      for (int i = 0; i < ret.length; i++) {
        ret[i] = (EI) t[i];
      }
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }

  /**
   * Returns Date de début de la période élémentaire. débutant par le mouvement (ZBE-2).
   *
   * @return TS
   */
  public TS getStartOfMovementDateTime() {
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
  }

  /**
   * Returns Date de fin de la période élémentaire s'achevant par une sortie ou un nouveau mouvement (ZBE-3).
   *
   * @return TS
   */
  public TS getEndOfMovementDateTime() {
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
  }

  /**
   * Returns Nature de la mise à jour de la période (ZBE-4).
   *
   * @return ID
   */
  public ID getReasonForTriggeringTheMovement() {
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
  }

  /**
   * Returns Indicateur de mouvement historique (ZBE-5).
   *
   * @return ID
   */
  public ID getHistoricMovementIndicator() {
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
  }

  /**
   * Returns Original Trigger Event Code (ZBE-6).
   *
   * @return ID
   */
  public ID getOriginalTriggerEventCode() {
    ID ret = null;
    try {
      final Type t = this.getField(6, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }

  /**
   * Returns Responsible Ward (ZBE-7).
   *
   * @return XON
   */
  public XON getResponsibleWard() {
    XON ret = null;
    try {
      final Type t = this.getField(7, 0);
      ret = (XON) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }

  /**
   * Returns UF de soins (ZBE-8).
   *
   * @return XON
   */
  public XON getUFSoins() {
    XON ret = null;
    try {
      final Type t = this.getField(8, 0);
      ret = (XON) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }

  /**
   * Returns Nature du mouvement(ZBE-9).
   *
   * @retunr CWE
   */
  public CWE getNatureMovement() {
    CWE ret = null;
    try {
      final Type t = this.getField(9, 0);
      ret = (CWE) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;

  }// Fin ZBE-9
}
