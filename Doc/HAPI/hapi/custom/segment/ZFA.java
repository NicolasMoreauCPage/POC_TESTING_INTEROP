/*
 * Créé le  11/09/2017 CSA GIP CPage
 * Modifié le 11/09/2017 - Mise en conformité spécifications des interfaces PAM 2.9 :
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
 * Represents an IHE France message segment : "Statut DMP du patient". This segment has the following fields:
 * </p>
 * <p>
 * ZFA-1: Statut du DMP du patient (ID)<br>
 * ZFA-2: Date de recueil du statut du DMP (TS)<br>
 * ZFA-3: Date de fermeture du DMP du patient (TS)<br>
 * ZFA-4: Autorisation d’accès valide au DMP du patient pour l’établissement (ID)<br>
 * ZFA-5: Date de recueil de l’état de l’autorisation d’accès au DMP du patient pour l’établissement (TS)<br>
 * ZFA-6: Opposition du patient à l’accès en mode bris de glace (ID)<br>
 * ZFA-7: Opposition du patient à l’accès en mode centre de régulation (ID)<br>
 * ZFA-8: Date de recueil de l’état des oppositions du patient (TS)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 * Création le 11/09/2017 CSA GIP CPage - Modifié le 11/09/2017 - Mise en conformité spécifications des interfaces PAM 2.9
 *
 * @author CSANTI
 */
public class ZFA extends AbstractSegment {

  /**
   * Creates a ZFA (Statut du DMP du patient) segment object that belongs to the given message.
   */
  public ZFA(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(ID.class, false, 1, 20, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ID.class, false, 1, 1, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ID.class, false, 1, 1, new Object[]{ message });
      this.add(ID.class, false, 1, 1, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }

  /**
   * Returns Statut du DMP du patient (ZFA-1).
   *
   * @return ID.
   */
  public ID[] getStatutDMPPatient() {
    ID[] ret = null;
    try {
      final Type[] t = this.getField(1);
      ret = new ID[t.length];
      for (int i = 0; i < ret.length; i++) {
        ret[i] = (ID) t[i];
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
   * Returns Date de recueil du statut du DMP (ZFA-2).
   *
   * @return TS
   */
  public TS getDateRecueilStatutDMP() {
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
   * Returns Date de fermeture du DMP du patient (ZFA-3).
   *
   * @return TS
   */
  public TS getDateFermetureDMP() {
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
   * Returns Autorisation d’accès valide au DMP du patient pour l’établissement (ZFA-4).
   *
   * @return ID
   */
  public ID getAutorisationAccesValide() {
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
   * Returns Date de recueil de l’état de l’autorisation d’accès au DMP du patient pour l’établissement (ZFA-5).
   *
   * @return TS
   */
  public TS getDateAutorisationAccesValide() {
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
  }

  /**
   * Returns Opposition du patient à l’accès en mode bris de glace (ZFA-6).
   *
   * @return ID
   */
  public ID getOppositionPatientBrisGlace() {
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
   * Returns Opposition du patient à l’accès en mode centre de régulation (ZFA-7).
   *
   * @return ID
   */
  public ID getOppositionPatientCentreRegulation() {
    ID ret = null;
    try {
      final Type t = this.getField(7, 0);
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
   * Returns Date de recueil de l’état des oppositions du patient (ZFA-8).
   *
   * @return TS
   */
  public TS getDateRecueilOpposition() {
    TS ret = null;
    try {
      final Type t = this.getField(8, 0);
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

}
