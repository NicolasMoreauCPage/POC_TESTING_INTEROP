package fr.cpage.interfaces.hapi.custom.message;

import ca.uhn.hl7v2.model.v251.message.SIU_S12;
import ca.uhn.hl7v2.parser.ModelClassFactory;

/**
 * @see ca.uhn.hl7v2.model.v251.message.SIU_S12
 */

public class SIU_S17 extends SIU_S12 {

  /**
   * Creates a new SIU_S17 message with DefaultModelClassFactory. 
   */ 
  public SIU_S17() { 
     super();
  }

  /** 
   * Creates a new SIU_S17 message with custom ModelClassFactory.
   * @param factory {@link ModelClassFactory}
   */
  public SIU_S17(ModelClassFactory factory) {
     super(factory);
  }
  

}
