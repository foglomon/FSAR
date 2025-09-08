import os
import time
import threading
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel


class Handler(FileSystemEventHandler):
    def __init__(self, monitor):
        self.monitor = monitor
        
    def on_created(self, event):
        if not event.is_directory:
            self.monitor.mark_changed(event.src_path, 'created')
            
    def on_modified(self, event):
        if not event.is_directory:
            self.monitor.mark_changed(event.src_path, 'modified')
            
    def on_deleted(self, event):
        if not event.is_directory:
            self.monitor.mark_changed(event.src_path, 'deleted')


class Monitor:
    def __init__(self, directory, enable_chime=False):
        self.directory = Path(directory).resolve()
        self.console = Console()
        self.changed_files = {}
        self.observer = None
        self.running = False
        self.chime_enabled = enable_chime
        self.chime_file = self.directory / "chime.mp3"
        
        if not self.directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
    
    def play_chime(self):
        if not self.chime_enabled or not self.chime_file.exists():
            return
            
        try:
            system = platform.system().lower()
            if system == "windows":
                subprocess.Popen([
                    "powershell", "-c", 
                    f"Add-Type -AssemblyName presentationCore; "
                    f"$mediaPlayer = New-Object system.windows.media.mediaplayer; "
                    f"$mediaPlayer.open([uri]'{self.chime_file}'); "
                    f"$mediaPlayer.Play(); Start-Sleep 1; $mediaPlayer.Stop()"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "darwin":
                subprocess.Popen(["afplay", str(self.chime_file)], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    
    def mark_changed(self, file_path, event_type):
        timestamp = datetime.now()
        self.changed_files[file_path] = (timestamp, event_type)
        
        # Play chime in background thread
        threading.Thread(target=self.play_chime, daemon=True).start()
    
    def is_recent(self, file_path, seconds=10):
        if file_path in self.changed_files:
            timestamp, _ = self.changed_files[file_path]
            time_diff = datetime.now() - timestamp
            return time_diff.total_seconds() < seconds
        return False
    
    def get_file_color(self, file_path):
        if file_path not in self.changed_files:
            return "white"
        
        _, event_type = self.changed_files[file_path]
        
        if event_type == 'created':
            if self.is_recent(file_path, 5):
                return "bright_green"
            elif self.is_recent(file_path, 15):
                return "green"
        elif event_type == 'modified':
            if self.is_recent(file_path, 5):
                return "bright_red"
            elif self.is_recent(file_path, 15):
                return "red"
        elif event_type == 'deleted':
            return "dim red"
            
        return "white"
    
    def build_directory_tree(self):
        tree = Tree(f"📁 [bold blue]{self.directory.name}[/bold blue]")
        self._add_directory_to_tree(tree, self.directory)
        return tree
    
    def _add_directory_to_tree(self, tree_node, directory, max_depth=5, current_depth=0):
        if current_depth >= max_depth or not directory.exists():
            return
        
        try:
            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            
            for item in items:
                if item.name.startswith('.'):
                    continue
                
                if item.is_dir():
                    icon = "📁"
                    color = self.get_file_color(str(item))
                    branch = tree_node.add(f"{icon} [{color}]{item.name}[/{color}]")
                    self._add_directory_to_tree(branch, item, max_depth, current_depth + 1)
                else:
                    icon = "📄"
                    color = self.get_file_color(str(item))
                    
                    # Add event indicators
                    if str(item) in self.changed_files:
                        _, event_type = self.changed_files[str(item)]
                        if event_type == 'created' and self.is_recent(str(item), 30):
                            indicator = " [bold green][NEW][/bold green]"
                        elif event_type == 'modified' and self.is_recent(str(item), 30):
                            indicator = " [bold yellow][MODIFIED][/bold yellow]"
                        else:
                            indicator = ""
                    else:
                        indicator = ""
                    
                    tree_node.add(f"{icon} [{color}]{item.name}[/{color}]{indicator}")
                    
        except PermissionError:
            tree_node.add("[dim red]Permission Denied[/dim red]")
        except OSError:
            tree_node.add("[dim red]Error accessing directory[/dim red]")
    
    def create_status_display(self):
        # Calculate recent activity
        now = datetime.now()
        recent_created = sum(1 for timestamp, event in self.changed_files.values() 
                           if event == 'created' and (now - timestamp).total_seconds() < 60)
        recent_modified = sum(1 for timestamp, event in self.changed_files.values() 
                            if event == 'modified' and (now - timestamp).total_seconds() < 60)
        recent_deleted = sum(1 for timestamp, event in self.changed_files.values() 
                           if event == 'deleted' and (now - timestamp).total_seconds() < 60)
        
        chime_status = "[green]ON[/green]" if self.chime_enabled else "[red]OFF[/red]"
        
        status_text = (f"Monitoring: [cyan]{self.directory}[/cyan]\n"
                      f"Created: [bright_green]{recent_created}[/bright_green] | "
                      f"Modified: [red]{recent_modified}[/red] | "
                      f"Deleted: [dim red]{recent_deleted}[/dim red] | "
                      f"Chime: {chime_status}")
        
        status_panel = Panel(status_text, title="[bold green]File Monitor Status[/bold green]", 
                           border_style="green")
        
        tree = self.build_directory_tree()
        tree_panel = Panel(tree, title="[bold blue]Directory Tree[/bold blue]", 
                         border_style="blue")
        
        return status_panel, tree_panel
    
    def start_monitoring(self):
        self.console.print(f"[green]Starting  file monitor for: {self.directory}[/green]")
        chime_status = "[green]ON[/green]" if self.chime_enabled else "[red]OFF[/red]"
        self.console.print(f"[dim]Chime notifications: {chime_status}[/dim]")
        
        self.running = True
        self.observer = Observer()
        event_handler = Handler(self)
        self.observer.schedule(event_handler, str(self.directory), recursive=True)
        self.observer.start()
        
        try:
            while self.running:
                # Clear screen and show updated display
                self.console.clear()
                status_panel, tree_panel = self.create_status_display()
                self.console.print(status_panel)
                self.console.print(tree_panel)
                self.console.print("[dim]Press Ctrl+C to stop monitoring[/dim]")
                
                time.sleep(2)  # Update every 2 seconds
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Stopping monitor...[/yellow]")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.console.print("[yellow]Monitor stopped.[/yellow]")


def main():
    console = Console()
    
    console.print("[bold blue] File System Monitor[/bold blue]")
    console.print("[dim]Enhanced file monitoring with visual feedback[/dim]\n")
    
    # Get directory
    while True:
        cwd = os.getcwd()
        print(f"Current directory: {cwd}")
        directory = input("Enter directory to monitor (or '.' for current): ").strip()
        if not directory:
            directory = "."
        
        path = Path(directory).resolve()
        if path.exists():
            break
        else:
            console.print(f"[red]Directory does not exist: {directory}[/red]")
    
    # Get chime preference
    while True:
        choice = input("Enable audio chime notifications? (y/n) [n]: ").strip().lower()
        if choice in ['n', 'no', '']:
            chime = False
            break
        elif choice in ['y', 'yes']:
            chime = True
            break
        else:
            console.print("[red]Please enter 'y' or 'n'[/red]")
    
    console.print(f"\n[green]Starting monitor for: {path}[/green]")
    
    try:
        monitor = Monitor(str(path), enable_chime=chime)
        monitor.start_monitoring()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")


if __name__ == "__main__":
    main()
