"""
HL7 message type detector - identifies message structure from MSH segment.

Supports:
- MFN (Master File Notification) for structure data
- ADT (Admission/Discharge/Transfer) for PAM (Patient Administration Management)
"""
import re
from typing import Optional, Literal


MessageCategory = Literal["MFN", "ADT", "QBP", "RSP", "UNKNOWN"]


class HL7Detector:
    """Detects HL7 message type and category from message content"""
    
    @staticmethod
    def extract_msh_segment(message: str) -> Optional[str]:
        """Extract the MSH segment from an HL7 message"""
        lines = message.strip().split('\n')
        for line in lines:
            if line.startswith('MSH'):
                return line
        return None
    
    @staticmethod
    def parse_msh_fields(msh_segment: str) -> dict:
        """
        Parse MSH segment fields into a dictionary.
        
        Returns:
            dict with keys: encoding_chars, sending_app, sending_facility,
            receiving_app, receiving_facility, timestamp, message_type,
            message_control_id, processing_id, version_id
        """
        if not msh_segment or not msh_segment.startswith('MSH'):
            return {}
        
        # MSH encoding characters are at position 3-6 (|^~\&)
        # Field separator is position 3 (|)
        field_sep = msh_segment[3] if len(msh_segment) > 3 else '|'
        encoding_chars = msh_segment[4:8] if len(msh_segment) > 7 else '^~\\&'
        
        # Split by field separator
        fields = msh_segment.split(field_sep)
        
        # MSH special case: field 1 is encoding chars, field 2 is sending app
        result = {
            'encoding_chars': encoding_chars,
            'sending_app': fields[2] if len(fields) > 2 else None,
            'sending_facility': fields[3] if len(fields) > 3 else None,
            'receiving_app': fields[4] if len(fields) > 4 else None,
            'receiving_facility': fields[5] if len(fields) > 5 else None,
            'timestamp': fields[6] if len(fields) > 6 else None,
            'security': fields[7] if len(fields) > 7 else None,
            'message_type': fields[8] if len(fields) > 8 else None,  # MSH-9
            'message_control_id': fields[9] if len(fields) > 9 else None,  # MSH-10
            'processing_id': fields[10] if len(fields) > 10 else None,  # MSH-11
            'version_id': fields[11] if len(fields) > 11 else None,  # MSH-12
        }
        
        return result
    
    @staticmethod
    def get_message_category(message: str) -> MessageCategory:
        """
        Determine the category of an HL7 message.
        
        Args:
            message: Full HL7 message text
        
        Returns:
            "MFN" for master file notification (structure)
            "ADT" for admission/discharge/transfer (PAM)
            "QBP" for query
            "RSP" for response
            "UNKNOWN" if cannot determine
        """
        msh = HL7Detector.extract_msh_segment(message)
        if not msh:
            return "UNKNOWN"
        
        fields = HL7Detector.parse_msh_fields(msh)
        message_type = fields.get('message_type', '')
        
        if not message_type:
            return "UNKNOWN"
        
        # MSH-9 format: MessageType^TriggerEvent^MessageStructure
        # Examples: ADT^A01, MFN^M05, QBP^Q23
        parts = message_type.split('^')
        if not parts:
            return "UNKNOWN"
        
        category = parts[0].upper()
        
        if category == "MFN":
            return "MFN"
        elif category == "ADT":
            return "ADT"
        elif category == "QBP":
            return "QBP"
        elif category == "RSP":
            return "RSP"
        else:
            return "UNKNOWN"
    
    @staticmethod
    def get_message_type_details(message: str) -> dict:
        """
        Extract detailed information about the message type.
        
        Returns:
            dict with: category, message_code, trigger_event, message_structure,
            version, control_id
        """
        msh = HL7Detector.extract_msh_segment(message)
        if not msh:
            return {
                'category': 'UNKNOWN',
                'message_code': None,
                'trigger_event': None,
                'message_structure': None,
                'version': None,
                'control_id': None
            }
        
        fields = HL7Detector.parse_msh_fields(msh)
        message_type = fields.get('message_type', '')
        
        # Parse MSH-9: MessageType^TriggerEvent^MessageStructure
        parts = message_type.split('^') if message_type else []
        
        return {
            'category': HL7Detector.get_message_category(message),
            'message_code': parts[0] if len(parts) > 0 else None,
            'trigger_event': parts[1] if len(parts) > 1 else None,
            'message_structure': parts[2] if len(parts) > 2 else None,
            'version': fields.get('version_id'),
            'control_id': fields.get('message_control_id'),
            'sending_app': fields.get('sending_app'),
            'sending_facility': fields.get('sending_facility'),
            'receiving_app': fields.get('receiving_app'),
            'receiving_facility': fields.get('receiving_facility')
        }
    
    @staticmethod
    def is_structure_message(message: str) -> bool:
        """Returns True if message is a structure message (MFN)"""
        return HL7Detector.get_message_category(message) == "MFN"
    
    @staticmethod
    def is_pam_message(message: str) -> bool:
        """Returns True if message is a PAM message (ADT)"""
        return HL7Detector.get_message_category(message) == "ADT"


def detect_hl7_type(message: str) -> dict:
    """
    Convenience function to detect HL7 message type.
    
    Args:
        message: Full HL7 message text
    
    Returns:
        dict with message type details
    """
    return HL7Detector.get_message_type_details(message)
