/*
 * Crée le  13/01/2006 DRE GIP CPage
 * Modifié le 11/09/2017 CSA - Ajout de ZFV-6, ZFV-7, ZFV-8, ZFV-9, ZFV-10, ZFV-11
 */

package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.CE;
import ca.uhn.hl7v2.model.v25.datatype.CX;
import ca.uhn.hl7v2.model.v25.datatype.DLD;
import ca.uhn.hl7v2.model.v25.datatype.IS;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.model.v25.datatype.XAD;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * <p>
 * Represents an "Propriétaire CPage" ZFV segment : "Identification des périodes élémentaires en unité de soin" "support du recueil du PMSI court ou moyen séjour". This segment has the following
 * fields:
 * </p>
 * <p>
 * ZFV-1: Etablissement de provenance et date de dernier séjour dans cet établissement(DLD)<br>
 * ZFV-2: Mode de transport de sortie (CE)<br>
 * ZFV-3: Type de préadmission (IS)<br>
 * ZFV-4: Date de début de placement psy (TS)<br>
 * ZFV-5: Date de fin de placement psy (TS)<br>
 * ZFV-6: Adresse de l'établissement de provenance ou de destination (XAD)<br>
 * ZFV-7: NDA de l'établissement de provenance (CX)<br>
 * ZFV-8: Numéro d’archives (CX)<br>
 * ZFV-9: Mode de sortie personnalisé (IS)<br>
 * ZFV-10: Code RIM-P du mode légal de soin transmis dans le PV2-3 (IS)<br>
 * ZFV-11: Prise en charge durant le transport (CE)<br>
 * </p>
 * <p>
 * The get...() methods return data from individual fields. These methods do not throw exceptions and may therefore have to handle exceptions internally. If an exception is handled internally, it is
 * logged and null is returned. This is not expected to happen - if it does happen this indicates not so much an exceptional circumstance as a bug in the code for this class.
 * </p>
 *
 * @author REBOURS
 */
public class ZFV extends AbstractSegment {

  /**
   * Creates a ZFV (informations supplémentaires sur la venue) segment object that belongs to the given message.
   */
  public ZFV(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(DLD.class, false, 1, 47, new Object[]{ message });
      this.add(CE.class, false, 1, 250, new Object[]{ message });
      this.add(IS.class, false, 1, 1, new Object[]{ message, Integer.valueOf(1) });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(XAD.class, false, 2, 250, new Object[]{ message });
      this.add(CX.class, false, 2, 250, new Object[]{ message });
      this.add(CX.class, false, 2, 250, new Object[]{ message });
      this.add(IS.class, false, 2, 250, new Object[]{ message });
      this.add(IS.class, false, 2, 250, new Object[]{ message });
      this.add(CE.class, false, 2, 250, new Object[]{ message });
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }// Fin constructeur

  /**
   * Returns Etablissement de provenance et date du dernier séjour dans cet établissement (ZFV-1).
   */
  public DLD getTypeEtaProvenance() {
    DLD ret = null;
    try {
      final Type t = this.getField(1, 0);
      ret = (DLD) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-1

  /**
   * Returns Mode de transport de sortie (ZFV-2).
   */
  public CE getModeTransportSortie() {
    CE ret = null;
    try {
      final Type t = this.getField(2, 0);
      ret = (CE) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-2

  /**
   * Returns Type de préadmission (ZFV-3).
   */
  public IS getTypePreadmission() {
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
  }// Fin ZFV-3

  /**
   * Returns Date de début de placement psy (ZFV-4).
   */
  public TS getDateDebPlacement() {
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
  }// Fin ZFV-4

  /**
   * Returns Date de fin de placement psy (ZFV-5).
   */
  public TS getDateFinPlacement() {
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
  }// Fin ZFV-5

  /**
   * Returns Adresse de l'établissement de provenance ou de destination (ZFV-6).
   */
  public XAD getAdresseEtablissement() {
    XAD ret = null;
    try {
      final Type t = this.getField(6, 0);
      ret = (XAD) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-6

  /**
   * Returns NDA de l'établissement de provenance (ZFV-7).
   */
  public CX getNDAEtablissementProvenance() {
    CX ret = null;
    try {
      final Type t = this.getField(7, 0);
      ret = (CX) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-7

  /**
   * Returns Numéro d’archives (ZFV-8).
   */
  public CX getNumeroArchives() {
    CX ret = null;
    try {
      final Type t = this.getField(8, 0);
      ret = (CX) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-8

  /**
   * Returns Mode de sortie personnalisé (ZFV-9).
   */
  public IS getModeSortiePersonnalise() {
    IS ret = null;
    try {
      final Type t = this.getField(9, 0);
      ret = (IS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-9

  /**
   * Returns Code RIM-P du mode légal de soin transmis dans le PV2-3 (ZFV-10).
   */
  public IS getCodeRIMP() {
    IS ret = null;
    try {
      final Type t = this.getField(10, 0);
      ret = (IS) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-10

  /**
   * Returns Prise en charge durant le transport (ZFV-11).
   */
  public CE getPriseEnChargeDuTransport() {
    CE ret = null;
    try {
      final Type t = this.getField(11, 0);
      ret = (CE) t;
    } catch (final ClassCastException cce) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", cce);
      throw new RuntimeException(cce);
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Unexpected problem obtaining field value.  This is a bug.", he);
      throw new RuntimeException(he);
    }
    return ret;
  }// Fin ZFV-11
}
