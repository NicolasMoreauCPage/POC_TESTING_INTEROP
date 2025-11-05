"""
File system transport adapter for reading/writing HL7 messages from local directories.

Provides:
- FileSystemReader: scans inbox directories for message files, processes them alphabetically
- FileSystemWriter: writes messages to outbox directories
"""
import os
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime


class FileSystemReader:
    """
    Reads message files from a directory in alphabetical order.
    Supports filtering by file extension and processing one at a time.
    """
    
    def __init__(
        self,
        inbox_path: str,
        extensions: Optional[List[str]] = None,
        archive_path: Optional[str] = None,
        error_path: Optional[str] = None
    ):
        """
        Args:
            inbox_path: Directory to scan for message files
            extensions: List of file extensions to process (e.g., ['.hl7', '.txt']). None = all files
            archive_path: Directory to move processed files (None = delete)
            error_path: Directory to move failed files (None = keep in inbox)
        """
        self.inbox_path = Path(inbox_path)
        self.extensions = extensions or []
        self.archive_path = Path(archive_path) if archive_path else None
        self.error_path = Path(error_path) if error_path else None
        
        # Create directories if they don't exist
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        if self.archive_path:
            self.archive_path.mkdir(parents=True, exist_ok=True)
        if self.error_path:
            self.error_path.mkdir(parents=True, exist_ok=True)
    
    def list_pending_files(self) -> List[Path]:
        """Returns list of pending message files sorted alphabetically"""
        if not self.inbox_path.exists():
            return []
        
        files = []
        for item in self.inbox_path.iterdir():
            if not item.is_file():
                continue
            if self.extensions and item.suffix.lower() not in self.extensions:
                continue
            files.append(item)
        
        return sorted(files)
    
    def read_next(self) -> Optional[tuple[str, Path]]:
        """
        Reads the next message file (alphabetically first).
        Returns (content, file_path) or None if no files.
        """
        files = self.list_pending_files()
        if not files:
            return None
        
        file_path = files[0]
        try:
            content = file_path.read_text(encoding='utf-8')
            return content, file_path
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def mark_processed(self, file_path: Path, success: bool = True):
        """
        Marks a file as processed by moving it to archive or error directory.
        If no archive/error path configured, deletes the file.
        """
        try:
            if success and self.archive_path:
                # Move to archive with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_name = f"{timestamp}_{file_path.name}"
                dest_path = self.archive_path / dest_name
                file_path.rename(dest_path)
            elif not success and self.error_path:
                # Move to error directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_name = f"{timestamp}_{file_path.name}"
                dest_path = self.error_path / dest_name
                file_path.rename(dest_path)
            else:
                # Delete file if no archive/error configured
                file_path.unlink()
        except Exception as e:
            print(f"Error marking file as processed {file_path}: {e}")
    
    def process_all(self, handler: Callable[[str, Path], bool]) -> dict:
        """
        Process all pending files with the given handler function.
        
        Args:
            handler: Function that takes (content, file_path) and returns True on success
        
        Returns:
            dict with stats: {"processed": int, "succeeded": int, "failed": int}
        """
        stats = {"processed": 0, "succeeded": 0, "failed": 0}
        
        while True:
            result = self.read_next()
            if not result:
                break
            
            content, file_path = result
            stats["processed"] += 1
            
            try:
                success = handler(content, file_path)
                if success:
                    stats["succeeded"] += 1
                    self.mark_processed(file_path, success=True)
                else:
                    stats["failed"] += 1
                    self.mark_processed(file_path, success=False)
            except Exception as e:
                print(f"Handler error for {file_path}: {e}")
                stats["failed"] += 1
                self.mark_processed(file_path, success=False)
        
        return stats


class FileSystemWriter:
    """
    Writes messages to a directory.
    Supports automatic timestamped filenames and subdirectory organization.
    """
    
    def __init__(
        self,
        outbox_path: str,
        use_subdirs: bool = False,  # Organize by date (YYYY-MM-DD)
        extension: str = ".hl7"
    ):
        """
        Args:
            outbox_path: Directory to write message files
            use_subdirs: If True, create YYYY-MM-DD subdirectories
            extension: File extension for message files
        """
        self.outbox_path = Path(outbox_path)
        self.use_subdirs = use_subdirs
        self.extension = extension
        
        self.outbox_path.mkdir(parents=True, exist_ok=True)
    
    def write_message(
        self,
        content: str,
        filename: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> Path:
        """
        Write a message to a file.
        
        Args:
            content: Message content to write
            filename: Optional explicit filename (default: timestamp-based)
            message_id: Optional message ID to include in filename
        
        Returns:
            Path to the written file
        """
        # Determine target directory
        if self.use_subdirs:
            date_str = datetime.now().strftime("%Y-%m-%d")
            target_dir = self.outbox_path / date_str
            target_dir.mkdir(exist_ok=True)
        else:
            target_dir = self.outbox_path
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            if message_id:
                filename = f"{timestamp}_{message_id}{self.extension}"
            else:
                filename = f"{timestamp}{self.extension}"
        
        file_path = target_dir / filename
        
        # Write content
        file_path.write_text(content, encoding='utf-8')
        
        return file_path
    
    def write_batch(self, messages: List[tuple[str, Optional[str]]]) -> List[Path]:
        """
        Write multiple messages at once.
        
        Args:
            messages: List of (content, message_id) tuples
        
        Returns:
            List of written file paths
        """
        paths = []
        for content, message_id in messages:
            path = self.write_message(content, message_id=message_id)
            paths.append(path)
        return paths
