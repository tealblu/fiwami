"""
File system watchdog module for monitoring directory changes.

This module provides a simple interface to monitor file system events
using the watchdog library with strong typing support.
"""

import time
from pathlib import Path
from typing import Callable, Optional, List
from dataclasses import dataclass

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
)
from watchdog.observers import Observer


@dataclass
class WatchdogConfig:
    """Configuration for the file watchdog."""
    
    path: str
    recursive: bool = True
    patterns: Optional[List[str]] = None
    ignore_patterns: Optional[List[str]] = None
    ignore_directories: bool = False
    case_sensitive: bool = True


class CustomEventHandler(FileSystemEventHandler):
    """Custom event handler with callbacks for different event types."""
    
    def __init__(
        self,
        on_created: Optional[Callable[[FileSystemEvent], None]] = None,
        on_deleted: Optional[Callable[[FileSystemEvent], None]] = None,
        on_modified: Optional[Callable[[FileSystemEvent], None]] = None,
        on_moved: Optional[Callable[[FileSystemEvent], None]] = None,
        on_any: Optional[Callable[[FileSystemEvent], None]] = None,
    ) -> None:
        """
        Initialize the event handler with optional callbacks.
        
        Args:
            on_created: Callback for file/directory creation events
            on_deleted: Callback for file/directory deletion events
            on_modified: Callback for file/directory modification events
            on_moved: Callback for file/directory move events
            on_any: Callback for any event (called for all events)
        """
        super().__init__()
        self._on_created = on_created
        self._on_deleted = on_deleted
        self._on_modified = on_modified
        self._on_moved = on_moved
        self._on_any = on_any
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file/directory creation events."""
        if self._on_created:
            self._on_created(event)
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file/directory deletion events."""
        if self._on_deleted:
            self._on_deleted(event)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file/directory modification events."""
        if self._on_modified:
            self._on_modified(event)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file/directory move events."""
        if self._on_moved:
            self._on_moved(event)
    
    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        if self._on_any:
            self._on_any(event)


class FileWatchdog:
    """File system watchdog for monitoring directory changes."""
    
    def __init__(self, config: WatchdogConfig) -> None:
        """
        Initialize the file watchdog.
        
        Args:
            config: Configuration for the watchdog
        """
        self.config = config
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[FileSystemEventHandler] = None
    
    def set_event_handler(self, handler: FileSystemEventHandler) -> None:
        """
        Set a custom event handler.
        
        Args:
            handler: The event handler to use
        """
        self.event_handler = handler
    
    def start(self) -> None:
        """Start monitoring the file system."""
        if self.observer is not None:
            raise RuntimeError("Watchdog is already running")
        
        if self.event_handler is None:
            raise RuntimeError("Event handler not set. Call set_event_handler() first")
        
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            self.config.path,
            recursive=self.config.recursive
        )
        self.observer.start()
    
    def stop(self) -> None:
        """Stop monitoring the file system."""
        if self.observer is None:
            raise RuntimeError("Watchdog is not running")
        
        self.observer.stop()
        self.observer.join()
        self.observer = None
    
    def is_running(self) -> bool:
        """Check if the watchdog is currently running."""
        return self.observer is not None and self.observer.is_alive()
    
    def __enter__(self) -> "FileWatchdog":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self.is_running():
            self.stop()


def create_watchdog(
    path: str,
    on_created: Optional[Callable[[FileSystemEvent], None]] = None,
    on_deleted: Optional[Callable[[FileSystemEvent], None]] = None,
    on_modified: Optional[Callable[[FileSystemEvent], None]] = None,
    on_moved: Optional[Callable[[FileSystemEvent], None]] = None,
    on_any: Optional[Callable[[FileSystemEvent], None]] = None,
    recursive: bool = True,
) -> FileWatchdog:
    """
    Create and configure a file watchdog with callbacks.
    
    Args:
        path: Path to monitor
        on_created: Callback for creation events
        on_deleted: Callback for deletion events
        on_modified: Callback for modification events
        on_moved: Callback for move events
        on_any: Callback for any event
        recursive: Whether to monitor subdirectories
    
    Returns:
        Configured FileWatchdog instance
    """
    config = WatchdogConfig(path=path, recursive=recursive)
    handler = CustomEventHandler(
        on_created=on_created,
        on_deleted=on_deleted,
        on_modified=on_modified,
        on_moved=on_moved,
        on_any=on_any,
    )
    
    watchdog = FileWatchdog(config)
    watchdog.set_event_handler(handler)
    
    return watchdog


def main() -> None:
    """Test function demonstrating watchdog usage."""
    print("Starting file watchdog test...")
    print("Monitoring current directory for changes (Press Ctrl+C to stop)")
    print("-" * 60)
    
    def log_event(event: FileSystemEvent) -> None:
        """Log file system events."""
        event_type = type(event).__name__
        print(f"[{event_type}] {event.src_path}")
        
        if isinstance(event, (FileMovedEvent, DirMovedEvent)):
            print(f"  → Moved to: {event.dest_path}")
    
    # Create watchdog with the log_event callback
    watchdog = create_watchdog(
        path=".",
        on_any=log_event,
        recursive=True
    )
    
    try:
        with watchdog:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n" + "-" * 60)
        print("Watchdog stopped")


if __name__ == "__main__":
    main()