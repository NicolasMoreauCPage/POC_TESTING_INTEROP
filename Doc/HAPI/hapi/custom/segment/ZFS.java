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
import ca.uhn.hl7v2.model.v25.datatype.CE;
import ca.uhn.hl7v2.model.v25.datatype.EI;
import ca.uhn.hl7v2.model.v25.datatype.FT;
import ca.uhn.hl7v2.model.v25.datatype.SI;
import ca.uhn.hl7v2.model.v25.datatype.ST;
import ca.uhn.hl7v2.model.v25.datatype.TS;
import ca.uhn.hl7v2.parser.ModelClassFactory;
import fr.cpage.fmk.core.tools.logging.CPageLogFactory;

/**
 * Ce segment, spécifique à l’extension française, est optionnel. Il est requis pour les évènements A28 et A31, de la transaction ITI-30, lors de l’échange d’informations concernant le
 * mode légal de soin, en psychiatrie. SEQ LEN DT Usage Card. HL7 TBL# ELEMENT NAME IHE FR 1 4 SI R [1..1] Set ID - ZFS * 2 427 EI R [1..*] Identifiant du mode légal de soin * 3 26 TS R [1..1] Date
 * et heure du début du mode légal de soin * 4 26 TS RE [0..1] Date et heure de la fin du mode légal de soin * 5 6 ID R [1..1] Action du mode légal de soin * 6 250 CE R [1..1] Mode légal de soins
 * * 7 2 IS O [0..1] Code RIM-P du mode légal de soin * 8 65536 FT O [0..1] Commentaire **
 */
public class ZFS extends AbstractSegment {

  /**
   * Creates a ZBE (identification des mouvements de localisation en unité de soins) segment object that belongs to the given message.
   */
  public ZFS(final Group parent, final ModelClassFactory factory) {
    super(parent, factory);
    final Message message = getMessage();
    try {
      this.add(SI.class, true, 1, 4, new Object[]{ message });
      this.add(EI.class, true, 0, 427, new Object[]{ message });
      this.add(TS.class, true, 1, 26, new Object[]{ message });
      this.add(TS.class, false, 1, 26, new Object[]{ message });
      this.add(ST.class, true, 1, 6, new Object[]{ message });
      this.add(CE.class, true, 1, 250, new Object[]{ message });
      this.add(ST.class, false, 1, 2, new Object[]{ message });
      this.add(FT.class, false, 1, 200, new Object[]{ message });

    } catch (final HL7Exception he) {
      CPageLogFactory.getLog(this.getClass()).error("Can't instantiate " + this.getClass().getName(), he);
    }
  }

}
