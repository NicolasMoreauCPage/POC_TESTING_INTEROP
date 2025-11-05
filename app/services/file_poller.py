"""
File polling service - scans file-based endpoints and processes messages.

Automatically detects message type (MFN structure vs ADT PAM) and routes
to the appropriate handler.
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
from sqlmodel import Session, select

from app.models_shared import SystemEndpoint, MessageLog
from app.models_structure_fhir import GHTContext
from app.adapters.filesystem_transport import FileSystemReader
from app.utils.hl7_detector import HL7Detector
from app.services.mfn_importer import import_mfn
from app.services.pam import handle_adt_message


class FilePollerService:
    """
    Service to poll file-based endpoints and process messages.
    
    Scans inbox directories, detects message type, and routes to:
    - MFN importer for structure messages
    - PAM handler for ADT messages
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.stats = {
            'endpoints_scanned': 0,
            'files_processed': 0,
            'mfn_messages': 0,
            'adt_messages': 0,
            'unknown_messages': 0,
            'errors': []
        }
    
    def scan_all_file_endpoints(self) -> Dict[str, Any]:
        """
        Scan all enabled FILE endpoints and process pending messages.
        
        Returns:
            dict with processing statistics
        """
        # Find all FILE endpoints that are enabled
        stmt = select(SystemEndpoint).where(
            SystemEndpoint.kind == "FILE",
            SystemEndpoint.is_enabled == True
        )
        endpoints = self.session.exec(stmt).all()
        
        for endpoint in endpoints:
            try:
                self._scan_endpoint(endpoint)
                self.stats['endpoints_scanned'] += 1
            except Exception as e:
                error_msg = f"Error scanning endpoint {endpoint.name}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(error_msg)
        
        return self.stats
    
    def _scan_endpoint(self, endpoint: SystemEndpoint):
        """Scan a single file endpoint"""
        if not endpoint.inbox_path:
            return
        
        # Parse file extensions
        extensions = []
        if endpoint.file_extensions:
            extensions = [ext.strip() for ext in endpoint.file_extensions.split(',')]
        
        # Create file reader
        reader = FileSystemReader(
            inbox_path=endpoint.inbox_path,
            extensions=extensions if extensions else None,
            archive_path=endpoint.archive_path,
            error_path=endpoint.error_path
        )
        
        # Process all pending files
        def process_message(content: str, file_path: Path) -> bool:
            """Handler function for processing each message"""
            try:
                return self._process_message(content, file_path, endpoint)
            except Exception as e:
                error_msg = f"Error processing {file_path.name}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(error_msg)
                return False
        
        result = reader.process_all(process_message)
        self.stats['files_processed'] += result['processed']
    
    def _process_message(self, content: str, file_path: Path, endpoint: SystemEndpoint) -> bool:
        """
        Process a single message file.
        
        Returns:
            True if successful, False otherwise
        """
        # Detect message type
        details = HL7Detector.get_message_type_details(content)
        category = details['category']
        
        # Log incoming message
        msg_log = MessageLog(
            direction="in",
            kind="HL7",
            message_type=f"{details['message_code']}^{details['trigger_event']}" if details['trigger_event'] else details['message_code'],
            endpoint_id=endpoint.id,
            correlation_id=details['control_id'],
            status="received",
            payload=content
        )
        self.session.add(msg_log)
        self.session.commit()
        
        # Route based on category
        if category == "MFN":
            return self._handle_mfn(content, msg_log, endpoint)
        elif category == "ADT":
            return self._handle_adt(content, msg_log, endpoint)
        else:
            self.stats['unknown_messages'] += 1
            msg_log.status = "error"
            msg_log.ack_payload = f"Unknown message category: {category}"
            self.session.add(msg_log)
            self.session.commit()
            return False
    
    def _handle_mfn(self, content: str, msg_log: MessageLog, endpoint: SystemEndpoint) -> bool:
        """Handle MFN structure message"""
        try:
            # Get GHT context for this endpoint
            ght_context = None
            if endpoint.ght_context_id:
                ght_context = self.session.get(GHTContext, endpoint.ght_context_id)
            
            if not ght_context:
                # Try to find default GHT context
                stmt = select(GHTContext).where(GHTContext.is_active == True).limit(1)
                ght_context = self.session.exec(stmt).first()
            
            if not ght_context:
                raise ValueError("No GHT context available for import")
            
            # Import MFN structure
            result = import_mfn(content, self.session, ght_context)
            
            self.stats['mfn_messages'] += 1
            msg_log.status = "ack_ok"
            msg_log.ack_payload = f"MFN import completed: {result}"
            self.session.add(msg_log)
            self.session.commit()
            
            return True
        except Exception as e:
            self.stats['errors'].append(f"MFN import error: {str(e)}")
            msg_log.status = "error"
            msg_log.ack_payload = f"MFN import failed: {str(e)}"
            self.session.add(msg_log)
            self.session.commit()
            return False
    
    def _handle_adt(self, content: str, msg_log: MessageLog, endpoint: SystemEndpoint) -> bool:
        """Handle ADT PAM message"""
        try:
            # Use existing PAM handler
            result = handle_adt_message(content, self.session, endpoint)
            
            self.stats['adt_messages'] += 1
            msg_log.status = "ack_ok"
            msg_log.ack_payload = "ADT processed successfully"
            self.session.add(msg_log)
            self.session.commit()
            
            return True
        except Exception as e:
            self.stats['errors'].append(f"ADT processing error: {str(e)}")
            msg_log.status = "error"
            msg_log.ack_payload = f"ADT processing failed: {str(e)}"
            self.session.add(msg_log)
            self.session.commit()
            return False


def scan_file_endpoints(session: Session) -> Dict[str, Any]:
    """
    Convenience function to scan all file endpoints.
    
    Args:
        session: SQLModel session
    
    Returns:
        dict with processing statistics
    """
    poller = FilePollerService(session)
    return poller.scan_all_file_endpoints()
