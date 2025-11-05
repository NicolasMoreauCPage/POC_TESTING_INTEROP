/*
 * CreatedDate: 2 sept. 08
 * Author: drebours
 * Society: GIP CPAGE
 * $LastChangedDate: 2002-07-22 21:42:37 -0700 (Mon, 22 Jul 2002) $
 * $Revision: 0 $
 * $LastChangedBy: drebours $
 */
package fr.cpage.interfaces.hapi.custom.segment;

import ca.uhn.hl7v2.HL7Exception;
import ca.uhn.hl7v2.model.AbstractSegment;
import ca.uhn.hl7v2.model.Group;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.Type;
import ca.uhn.hl7v2.model.v25.datatype.ID;
import ca.uhn.hl7v2.model.v25.datatype.IS;
import ca.uhn.hl7v2.model.v25.datatype.NA;
import ca.uhn.hl7v2.model.v25.datatype.NM;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * Segment ZFD.
 */
public class ZFD extends AbstractSegment {

  /**
   * Constructeur.
   *
   * @param parent Element père
   * @param factory Factory du segment
   */
  public ZFD(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      //ZFD-1 Date lue sur la carte SESA       VITALE
      this.add(NA.class, false, 1, 1, new Object[]{ message }, "dateLueVitale");
      //ZFD-2 Nombre de semaines de   gestation
      this.add(NM.class, false, 1, 1, new Object[]{ message }, "nbSemaineGestation");
      //ZFD-3 Consentement SMS
      this.add( ID.class, false, 1, 1, new Object[]{ message, Integer.valueOf(0) },"consentementSMS");
      //ZFD-4 Indicateur de date de   naissance corrigée
      this.add(IS.class, false, 1, 1, new Object[]{ message },"dateFictive");
      //ZFD-5 Mode d’obtention de  l’identité
      this.add(IS.class, false, 1, 1,new Object[]{ message },"modeSaisieIdentite");
      //ZFD-6 Date d’interrogation du   téléservice INSi
      this.add(TS.class, false, 1, 1, new Object[]{ message },"dateAppelINSI");
      //ZFD-7 Type de justificatif d’identité
      this.add(IS.class, false, 1, 1, new Object[]{ message },"justifIdentite");
      //ZFD-8 Date de fin de validité du    document
      this.add(TS.class, false, 1, 1, new Object[]{ message },"dateFinValiditeJustifIdt");
    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }

  /**
   * Returns Type NA Date lunaire(ZFD-1).
   *
   * @return Date lunaire
   */
  public NA getDateLunaire() {
    NA ret = null;
    try {
      final Type t = this.getField(1, 0);
      ret = (NA) t;
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
   * Returns Type NM Nombre de semaine de gestation (ZFD-2).
   *
   * @return Nombre de semaine de gestation
   */
  public NM getNbSemainesGestation() {
    NM ret = null;
    try {
      final Type t = this.getField(2, 0);
      ret = (NM) t;
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
