import os
import time
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class BasicHandler(FileSystemEventHandler):
    def __init__(self, monitor):
        self.monitor = monitor
        
    def on_created(self, event):
        if not event.is_directory:
            self.monitor.log_change(event.src_path, 'CREATED')
            
    def on_modified(self, event):
        if not event.is_directory:
            self.monitor.log_change(event.src_path, 'MODIFIED')
            
    def on_deleted(self, event):
        if not event.is_directory:
            self.monitor.log_change(event.src_path, 'DELETED')


class BasicMonitor:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.observer = None
        self.running = False
        
        if not self.directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
    
    def log_change(self, file_path, event_type):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {event_type}: {file_path}")
    
    def start_monitoring(self):
        print(f"Starting basic file monitor for: {self.directory}")
        
        self.running = True
        self.observer = Observer()
        event_handler = BasicHandler(self)
        self.observer.schedule(event_handler, str(self.directory), recursive=True)
        self.observer.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitor...")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        print("Monitor stopped.")


def main():
    print("Basic File System Monitor")
    print("=" * 40)
    
    directory = input("Enter directory to monitor (or '.' for current): ").strip()
    if not directory:
        directory = "."
    
    try:
        monitor = BasicMonitor(directory)
        monitor.start_monitoring()
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
