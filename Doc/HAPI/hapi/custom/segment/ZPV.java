/*
 * Créé le 05/07/2005 LLR GIP CPage
 * Modifié le 21/07/05 LLR GIP CPage - Mise en conformité spécifications des interfaces V0.901
 *                                     ->Ajout des déclarations de ZPV-13 et ZPV-14.
 */

package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.CX;
import ca.uhn.hl7v2.model.v25.datatype.ID;
import ca.uhn.hl7v2.model.v25.datatype.ST;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.model.v25.datatype.XAD;
import ca.uhn.hl7v2.model.v25.datatype.XTN;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZPV segment : "Information complémentaires sur le passage à l'hôpital" This segment has the following fields:
 * </p>
 * <p>
 * ZPV-1: Dossier hôpital précédent (ST)<br>
 * ZPV-2: Adresse de provenance (XAD)<br>
 * ZPV-3: Code FINESS établissement précédent (ID)<br>
 * ZPV-4: Mode de transport d'entrée (ID)<br>
 * ZPV-5: Commentaire d'entrée (ST)<br>
 * ZPV-6: Dossier Hôpital suivant (ST)<br>
 * ZPV-7: Adresse de sortie (XAD)<br>
 * ZPV-8: Code FINESS établissement de sortie (ID)<br>
 * ZPV-9: Mode de transport de sortie (ID)<br>
 * ZPV-10: Commentaire de sortie (ST)<br>
 * ZPV-11: Téléphone SDA (attaché à la venue (XTN)<br>
 * ZPV-12: Réservation d'un lit Y/N (ID)<br>
 * ZPV-13: Date d'ouverture du dossier (TS)<br>
 * ZPV-14: Date de clôture du dossier (TS)<br>
 * ZPV-15: Autorisation d'opérer (ID)<br>
 * ZPV-16: Autorisation d'anésthésier (ID)<br>
 * ZPV-17: Autorisation d'autopsier (ID)<br>
 * ZPV-18: Autorisation de visiter (ID)<br>
 * ZPV-19: Autorisation de prélever (ID)<br>
 * ZPV-20: Identifiant de venue élémentaires (CX)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 * Création le 05/07/05 LLR GIP CPage. Modification le 21/07/05 LLR GIP CPage : Mise en conformité spécifications des interfaces V0.901 ->Ajout de la déclaration de ZPV-13 et ZPV-14. Modification
 * le 30/08/05 LLR GIP CPage : Mise en conformité spécifications des interfaces V0.902 ->Ajout de la déclaration de ZPV-15, ZPV-16, ZPV-17, ZPV-18, ZPV-19 et ZPV-20.
 *
 * @author LEYOUDEC
 */
public class ZPV extends AbstractSegment {

  /**
   * Creates a ZPV (Informations complémentaires sur le passage à l'hôpital) segment object that belongs to the given message.
   */
  public ZPV(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(ST.class, false, 1, 35, new Object[]{ message });
      this.add(XAD.class, false, 1, 250, new Object[]{ message });
      this.add(ID.class, false, 1, 26, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ST.class, false, 1, 199, new Object[]{ message });
      this.add(ST.class, false, 1, 35, new Object[]{ message });
      this.add(XAD.class, false, 1, 250, new Object[]{ message });
      this.add(ID.class, false, 1, 26, new Object[]{ message, Integer.valueOf(0) });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      this.add(ST.class, false, 1, 199, new Object[]{ message });
      this.add(XTN.class, false, 1, 250, new Object[]{ message });
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      // Ajout LLR le 21/07/05 - Mise en conformité spécification des interfaces V0.901
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      // Ajout LLR le 21/07/05 - Mise en conformité spécification des interfaces V0.901
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      // Ajout LLR le 30/08/05 - Mise en conformité spécification des interfaces V0.902
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      // Ajout LLR le 30/08/05 - Mise en conformité spécification des interfaces V0.902
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      // Ajout LLR le 30/08/05 - Mise en conformité spécification des interfaces V0.902
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      // Ajout LLR le 30/08/05 - Mise en conformité spécification des interfaces V0.902
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      // Ajout LLR le 30/08/05 - Mise en conformité spécification des interfaces V0.902
      this.add(ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) });
      // Ajout LLR le 30/08/05 - Mise en conformité spécification des interfaces V0.902
      this.add(CX.class, false, 1, 250, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Dossier de l'hôpital précédent (ZPV-1).
   */
  public ST getDossierHopitalPrecedent() {
    ST ret = null;
    try {
      final Type t = this.getField(1, 0);
      ret = (ST) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-1

  /**
   * Returns Adresse de provenance (ZPV-2).
   */
  public XAD getAdresseProvenance() {
    XAD ret = null;
    try {
      final Type t = this.getField(2, 0);
      ret = (XAD) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-2

  /**
   * Returns Code FINESS de l'établissement précédent (ZPV-3).
   */
  public ID getCodeFinessEtablPrecedent() {
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
  }// Fin ZPV-3

  /**
   * Returns Mode de transport d'entrée (ZPV-4).
   */
  public ID getModeTransportEntree() {
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
  }// Fin ZPV-4

  /**
   * Returns Commentaire d'entrée (ZPV-5).
   */
  public ST getCommentaireEntree() {
    ST ret = null;
    try {
      final Type t = this.getField(5, 0);
      ret = (ST) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-5

  /**
   * Returns Dossier hôpital suivant (ZPV-6).
   */
  public ST getDossierHopitalSuivant() {
    ST ret = null;
    try {
      final Type t = this.getField(6, 0);
      ret = (ST) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-6

  /**
   * Returns Adresse de sortie (ZPV-7).
   */
  public XAD getAdresseSortie() {
    XAD ret = null;
    try {
      final Type t = this.getField(7, 0);
      ret = (XAD) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-7

  /**
   * Returns Code FINESS établissement de sortie (ZPV-8).
   */
  public ID getCodeFinessEtablSortie() {
    ID ret = null;
    try {
      final Type t = this.getField(8, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-8

  /**
   * Returns Mode de transport de sortie (ZPV-9).
   */
  public ID getModeTransportSortie() {
    ID ret = null;
    try {
      final Type t = this.getField(9, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-9

  /**
   * Returns Commentaire de sortie (ZPV-10).
   */
  public ST getCommentaireSortie() {
    ST ret = null;
    try {
      final Type t = this.getField(10, 0);
      ret = (ST) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-10

  /**
   * Returns Téléphone SDA (attaché à la venue) (ZPV-11).
   */
  public XTN getTelephoneSDA() {
    XTN ret = null;
    try {
      final Type t = this.getField(11, 0);
      ret = (XTN) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-11

  /**
   * Returns Réservation d'un lit (Y/N) (ZPV-12).
   */
  public ID getReservationLit() {
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
  }// Fin ZPV-12

  /**
   * Returns Date d'ouverture du dossier (ZPV-13).
   */
  public TS getDateOuvertureDossier() {
    TS ret = null;
    try {
      final Type t = this.getField(13, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-13

  /**
   * Returns Date de clôture du dossier (ZPV-14).
   */
  public TS getDateClotureDossier() {
    TS ret = null;
    try {
      final Type t = this.getField(14, 0);
      ret = (TS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-14

  /**
   * Returns Autorisation d'opérer (ZPV-15).
   */
  public ID getAutorisationOperer() {
    ID ret = null;
    try {
      final Type t = this.getField(15, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-15

  /**
   * Returns Autorisation d'anéthésier (ZPV-16).
   */
  public ID getAutorisationAnesthesier() {
    ID ret = null;
    try {
      final Type t = this.getField(16, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-16

  /**
   * Returns Autorisation d'autopsier (ZPV-17).
   */
  public ID getAutorisationAutopsier() {
    ID ret = null;
    try {
      final Type t = this.getField(17, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-17

  /**
   * Returns Autorisation de visite (ZPV-18).
   */
  public ID getAutorisationDeVisite() {
    ID ret = null;
    try {
      final Type t = this.getField(18, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-18

  /**
   * Returns Autorisation de prélever (ZPV-19).
   */
  public ID getAutorisationPrelever() {
    ID ret = null;
    try {
      final Type t = this.getField(19, 0);
      ret = (ID) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZPV-19

  /**
   * Returns Identifiant de venue élémentaire (ZPV-20).
   */
  public CX getIDVenueElementaire() {
    CX ret = null;
    try {
      final Type t = this.getField(20, 0);
      ret = (CX) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// ZPV-20

}
