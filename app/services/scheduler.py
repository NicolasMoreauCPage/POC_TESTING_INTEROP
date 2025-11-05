"""
Background task scheduler for file endpoint polling.

Runs periodic tasks like scanning file-based endpoints.
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

from sqlmodel import Session
from app.db import get_session
from app.services.file_poller import scan_file_endpoints

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Background task scheduler for periodic jobs.
    
    Currently handles:
    - File endpoint polling (configurable interval)
    """
    
    def __init__(self, poll_interval_seconds: int = 60):
        """
        Initialize the scheduler.
        
        Args:
            poll_interval_seconds: Interval between file polls (default: 60s = 1 minute)
        """
        self.poll_interval_seconds = poll_interval_seconds
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info(f"Background scheduler started (poll interval: {self.poll_interval_seconds}s)")
    
    async def stop(self):
        """Stop the background scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background scheduler stopped")
    
    async def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                await self._scan_file_endpoints()
            except Exception as e:
                logger.error(f"Error in file endpoint polling: {e}", exc_info=True)
            
            # Wait for next poll
            try:
                await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break
    
    async def _scan_file_endpoints(self):
        """Scan all file endpoints"""
        # Create a session for this scan
        session_gen = get_session()
        session = next(session_gen)
        
        try:
            logger.debug("Scanning file endpoints...")
            stats = await scan_file_endpoints(session)
            
            if stats['files_processed'] > 0 or stats['errors']:
                logger.info(
                    f"File scan complete: {stats['endpoints_scanned']} endpoints, "
                    f"{stats['files_processed']} files processed, "
                    f"{stats['mfn_messages']} MFN, {stats['adt_messages']} ADT, "
                    f"{len(stats['errors'])} errors"
                )
                
                if stats['errors']:
                    for error in stats['errors']:
                        logger.error(f"  - {error}")
        finally:
            try:
                next(session_gen, None)  # Close the session
            except StopIteration:
                pass


# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler(poll_interval_seconds: int = 60) -> BackgroundScheduler:
    """
    Get or create the global scheduler instance.
    
    Args:
        poll_interval_seconds: Polling interval (default: 60s)
    
    Returns:
        BackgroundScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(poll_interval_seconds)
    return _scheduler


async def start_scheduler(poll_interval_seconds: int = 60):
    """
    Start the background scheduler.
    
    Args:
        poll_interval_seconds: Polling interval (default: 60s = 1 minute)
    """
    scheduler = get_scheduler(poll_interval_seconds)
    await scheduler.start()


async def stop_scheduler():
    """Stop the background scheduler"""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None
