/*
 * Créé le 05/07/2005 LLR GIP CPage
 * Modifié le 21/07/05 LLR GIP CPage - Mise en conformité spécifications des interfaces V0.901
 *
 */

package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.EI;
import ca.uhn.hl7v2.model.v25.datatype.ID;
import ca.uhn.hl7v2.model.v25.datatype.ST;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZFT segment : "Identification des périodes tarifaires dans l'unité de soin". This segment has the following fields:
 * </p>
 * <p>
 * ZFT-1: Code discipline médico-tarifaire (ID)<br>
 * ZFT-2: Code tarif du séjour (ID)<br>
 * ZFT-3: Type d'activité (ID)<br>
 * ZFT-4: Activité libérale (ID)<br>
 * ZFT-5: Date de début de période (TS)<br>
 * ZFT-6: Date de fin de période (TS)<br>
 * ZFT-7: Identifiant du mouvement (EI)<br>
 * ZFT-8: Reason for triggering the movement (ST)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 * Création le 07/07/05 LLR GIP CPage Modification le 21/07/05 LLR GIP CPage - Mise en conformité spécifications des interfaces V0.901 ->Ajout de la déclaration de ZFT-6, ZFT-7 et ZFT-8.
 *
 * @author LEYOUDEC
 */
public class ZFT extends AbstractSegment {

  /**
   * Creates a ZFT (identification des périodes tarifaires dans l'unité de soins) segment object that belongs to the given message.
   */
  public ZFT(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(ID.class, true, 1, 3, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 10, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 2, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(TS.class, true, 1, 26, null);
      // Ajout LLR le 21/07/05 - Mise en conformité spécification des interfaces V0.901
      this.add(TS.class, false, 1, 26, null);
      // Ajout LLR le 21/07/05 - Mise en conformité spécification des interfaces V0.901
      this.add(EI.class, true, 0, 250, new Object[]{ message });
      // Ajout LLR le 21/07/05 - Mise en conformité spécification des interfaces V0.901
      this.add(ST.class, true, 1, 6, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Code discipline médico-tarifaire (ZFT-1).
   */
  public ID getCodeDisciplineMedicoTarifaire() {
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
  }// Fin ZFT-1

  /**
   * Returns Code tarif du séjour (ZFT-2).
   */
  public ID getCodeTarifSejour() {
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
  }// Fin ZFT-2

  /**
   * Returns Type d'activité (ZFT-3).
   */
  public ID getTypeActivite() {
    ID ret = null;
    try {
      final Type t = this.getField(3, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFT-3

  /**
   * Returns Activité libérale (ZFT-4).
   */
  public ID getActiviteLiberale() {
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
  }// Fin ZFT-4

  /**
   * Returns Date de début de période (ZFT-5).
   */
  public TS getDateDebutPeriode() {
    TS ret = null;
    try {
      final Type t = this.getField(5, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFT-5

  /**
   * Returns Date de fin de période (ZFT-6).
   */
  // Ajout de la déclaration de ZFT-6 - Mise en conformité des spécifications des interfaces V0.901
  public TS getDateFinPeriode() {
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
  }// Fin ZFT-6

  /**
   * Returns Identifiant du mouvement (ZFT-7).
   */
  // Ajout de la déclaration de ZFT-7 - Mise en conformité des spécifications des interfaces V0.901
  public EI[] getIdentifiantDuMouvement() {
    EI[] ret = null;
    try {
      final Type[] t = this.getField(7);
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
  }// Fin ZFT-7

  /**
   * Returns Reason for triggering the movement (ZFT-8).
   */
  // Ajout de la déclaration de ZFT-8 - Mise en conformité des spécifications des interfaces V0.901
  public ST getReasonForTriggeringTheMovement() {
    ST ret = null;
    try {
      final Type t = this.getField(8, 0);
      ret = (ST) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFT-8

}
