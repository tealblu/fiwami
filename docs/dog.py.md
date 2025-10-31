File system watchdog module for monitoring directory changes.

This module provides a simple interface to monitor file system events
using the watchdog library with strong typing support.

Key Features:

WatchdogConfig: A dataclass for configuration with type hints
CustomEventHandler: A flexible event handler that accepts callbacks for different event types
FileWatchdog: Main class that manages the observer lifecycle
create_watchdog(): Convenient factory function for quick setup
main(): Test function that monitors the current directory

Usage Examples:
As a module in your code:

```python
from watchdog import create_watchdog

def on_file_created(event):
    print(f"New file: {event.src_path}")

watchdog = create_watchdog(
    path="/path/to/watch",
    on_created=on_file_created,
    recursive=True
)

with watchdog:
    # Your code here
    pass
```

Run the test:
```python
python watchdog.py
```