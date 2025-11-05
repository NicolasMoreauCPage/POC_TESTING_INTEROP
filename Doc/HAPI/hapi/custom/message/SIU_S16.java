package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.model.v251.message.SIU_S12;
import ca.uhn.hl7v2.parser.ModelClassFactory;

/**
 * @see ca.uhn.hl7v2.model.v251.message.SIU_S12
 */

public class SIU_S16 extends SIU_S12 {

  /**
   * Creates a new SIU_S16 message with DefaultModelClassFactory. 
   */ 
  public SIU_S16() { 
     super();
  }

  /** 
   * Creates a new SIU_S16 message with custom ModelClassFactory.
   * @param factory {@link ModelClassFactory}
   */
  public SIU_S16(ModelClassFactory factory) {
     super(factory);
  }
  

}
