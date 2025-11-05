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
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZPA segment : "Information supplémentaire du patient" This segment has the following fields:
 * </p>
 * <p>
 * ZPA-1: Catégorie socio-professionnelle (ID)<br>
 * ZPA-2: Activité socio-professionnelle (ID)<br>
 * ZPA-3: Date de naissance valide (ID)<br>
 * ZPA-4: Adresse valide (ID)<br>
 * ZPA-5: Identité validée/serveur régional (ID)<br>
 * ZPA-6: Indicateur de liaison avec le serveur régional (ID)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 *
 * @author LEYOUDEC
 */
public class ZPA extends AbstractSegment {

  /**
   * Creates a ZPA (Informations supplémentaires du patient) segment object that belongs to the given message.
   */
  public ZPA(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(ID.class, false, 1, 2, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 2, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Catégorie socio-professionnelle (ZPA-1).
   */
  public ID getCategorieSocioProfessionnelle() {
    ID ret = null;
    try {
      final Type t = this.getField(12, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPA-1

  /**
   * Returns Activité socio-professionnelle (ZPA-2).
   */
  public ID getActiviteSocioProfessionnelle() {
    ID ret = null;
    try {
      final Type t = this.getField(12, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPA-2

  /**
   * Returns Date de naissance valide (ZPA-3).
   */
  public ID getDateNaissanceValide() {
    ID ret = null;
    try {
      final Type t = this.getField(12, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPA-3

  /**
   * Returns Adresse valide (ZPA-4).
   */
  public ID getAdresseValide() {
    ID ret = null;
    try {
      final Type t = this.getField(12, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPA-4

  /**
   * Returns Identité validée/serveur régional (ZPA-5).
   */
  public ID getIdentiteValideeServeurRegional() {
    ID ret = null;
    try {
      final Type t = this.getField(12, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPA-5

  /**
   * Returns Indicateur de liaison avec le serveur régional (ZPA-6).
   */
  public ID getIndicateurLiaisonServeurRegional() {
    ID ret = null;
    try {
      final Type t = this.getField(12, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPA-6

}// Fin classe
