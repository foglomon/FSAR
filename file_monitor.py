import os
import sys
import time
import threading
import subprocess
import platform
import difflib
from pathlib import Path
from datetime import datetime, timedelta

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.tree import Tree
from rich.live import Live
from rich.panel import Panel



class Handler(FileSystemEventHandler):
    def __init__(self, mon):
        self.mon = mon
        
    def on_created(self, event):
        if not event.is_directory:
            self.mon.mark_changed(event.src_path, 'created')
            
    def on_modified(self, event):
        if not event.is_directory:
            self.mon.mark_changed(event.src_path, 'modified')
            
    def on_deleted(self, event):
        if not event.is_directory:
            self.mon.mark_changed(event.src_path, 'deleted')


class Monitor:
    def __init__(self, directory, enable_chime=False):
        self.dir = Path(directory).resolve()
        self.console = Console()
        self.changed = {}
        self.deleted = {}
        self.created = {}
        self.contents = {}
        self.backups = {}
        self.observer = None
        self.running = False
        self.chime = enable_chime
        self.chime_file = self.dir / "chime.mp3"
        self.input = ""
        self.lock = threading.Lock()
        self.diff_file = None
        self.file_idx = {}
        self.idx = 1
        
        self._init_contents()
        
        if not self.dir.exists():
            raise ValueError(f"Directory does not exist: {directory}")
            
    def play_chime(self):
        if not self.chime or not self.chime_file.exists():
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
            else:
                players = ["mpg123", "mpv", "vlc", "mplayer", "ffplay"]
                for player in players:
                    try:
                        subprocess.Popen([player, str(self.chime_file)], 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            pass
            
    def mark_changed(self, path, event='modified'):
        t = datetime.now()
        self.changed[path] = (t, event)
        
        if event == 'deleted':
            self.deleted[path] = t
        elif event == 'created':
            self.created[path] = t
            
        threading.Thread(target=self.play_chime, daemon=True).start()
        
        if event in ['modified', 'created'] and Path(path).is_file():
            self._update_content(Path(path))
    
    def _init_contents(self):
        try:
            for p in self.dir.rglob('*'):
                if p.is_file() and self._is_text(p):
                    try:
                        content = p.read_text(encoding='utf-8', errors='ignore')
                        self.contents[str(p)] = content
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _update_content(self, path):
        if not self._is_text(path):
            return
            
        try:
            path_str = str(path)
            current = self.contents.get(path_str, "")
            
            # Always store backup - empty string for new files
            self.backups[path_str] = current
            
            new = path.read_text(encoding='utf-8', errors='ignore')
            self.contents[path_str] = new
        except Exception:
            pass
    
    def _is_text(self, path):
        try:
            exts = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', 
                   '.yml', '.yaml', '.ini', '.cfg', '.conf', '.log', '.sql', '.sh', 
                   '.bat', '.ps1', '.c', '.cpp', '.h', '.java', '.cs', '.go', '.rs',
                   '.php', '.rb', '.pl', '.r', '.swift', '.kt', '.dart', '.ts', '.jsx',
                   '.tsx', '.vue', '.svelte', '.scss', '.sass', '.less', '.styl'}
            
            if path.suffix.lower() in exts:
                return True
            
            if not path.suffix:
                try:
                    with open(path, 'rb') as f:
                        chunk = f.read(512)
                        if b'\0' in chunk:
                            return False
                        try:
                            chunk.decode('utf-8')
                            return True
                        except UnicodeDecodeError:
                            return False
                except Exception:
                    return False
            
            return False
        except Exception:
            return False
    
    def get_diff(self, path):
        s = str(path)
        if s not in self.backups or s not in self.contents:
            return None
        
        old = self.backups[s]
        new = self.contents[s]
        
        if old == new:
            return None
        
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"{path.name} (before)",
            tofile=f"{path.name} (after)",
            n=3
        ))
        
        return diff if diff else None
    
    def handle_diff_input(self, key):
        if key == 'q' or key == 'Q':
            self.diff_file = None
            return True
        
        try:
            num = int(key)
            if num in self.file_idx:
                self.diff_file = self.file_idx[num]
                return True
        except ValueError:
            pass
        
        return False
        
    def is_recent(self, path, sec=5):
        path_str = str(path)
        if path_str in self.changed:
            t, _ = self.changed[path_str]
            diff = datetime.now() - t
            return diff.total_seconds() < sec
        return False
        
    def get_event(self, path):
        path_str = str(path)
        if path_str in self.changed:
            _, event = self.changed[path_str]
            return event
        return None
        
    def is_deleted(self, path, sec=30):
        path_str = str(path)
        if path_str in self.deleted:
            diff = datetime.now() - self.deleted[path_str]
            return diff.total_seconds() < sec
        return False
        
    def is_created(self, path, sec=10):
        path_str = str(path)
        if path_str in self.changed:
            t, event = self.changed[path_str]
            if event == 'created':
                diff = datetime.now() - t
                return diff.total_seconds() < sec
        if path_str in self.created:
            diff = datetime.now() - self.created[path_str]
            return diff.total_seconds() < sec
        return False
        
    def get_color_style(self, path):
        event = self.get_event(path)
        
        if self.is_deleted(path):
            return "dim red", "strike"
        
        if event == 'created':
            if self.is_recent(path, 2):
                return "bright_green", None
            elif self.is_recent(path, 5):
                return "green", None
            elif self.is_recent(path, 10):
                return "dark_green", None
        elif event == 'modified':
            if self.is_recent(path, 2):
                return "bright_red", None
            elif self.is_recent(path, 5):
                return "red", None
            elif self.is_recent(path, 10):
                return "yellow", None
            elif self.is_recent(path, 30):
                return "orange3", None
        
        return "white", None
            
    def build_tree(self):
        if not self.dir.exists():
            tree = Tree(f"❌ [bold red]Directory not found: {self.dir}[/bold red]")
            tree.add("[dim red]The monitored directory has been deleted or moved[/dim red]")
            tree.add("[dim yellow]Press Ctrl+C to change to a different directory[/dim yellow]")
            return tree
            
        tree = Tree(f"📁 [bold blue]{self.dir.name}[/bold blue]")
        self.file_idx = {}
        self.idx = 1
        self._add_dir(tree, self.dir)
        return tree
        
    def _add_dir(self, tree_node, directory, max_depth=10, depth=0):
        if depth >= max_depth:
            return
            
        if not directory.exists():
            tree_node.add("[dim red]Directory deleted or moved[/dim red]")
            return
            
        try:
            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            
            for deleted_path in list(self.deleted.keys()):
                deleted_file = Path(deleted_path)
                if deleted_file.parent == directory and self.is_deleted(deleted_file):
                    items.append(deleted_file)
            
            for item in items:
                if item.name.startswith('.'):
                    continue
                    
                color, style = self.get_color_style(item)
                
                if item.is_dir() and item.exists():
                    icon = "📁"
                    new_tag = " [bold green][NEW][/bold green]" if self.is_created(item) else ""
                    
                    if style:
                        text = f"{icon} [{color} {style}]{item.name}[/{style} {color}]{new_tag}"
                    else:
                        text = f"{icon} [{color}]{item.name}[/{color}]{new_tag}"
                    branch = tree_node.add(text)
                    
                    self._add_dir(branch, item, max_depth, depth + 1)
                else:
                    event = self.get_event(item)
                    
                    if event == 'created':
                        icon = "📄"
                    elif event == 'deleted':
                        icon = "🗑️ "
                    else:
                        icon = "📄"
                    
                    # Show file size for existing files
                    size_str = ""
                    if item.exists():
                        try:
                            size = item.stat().st_size
                            if size < 1024:
                                size_str = f" [dim]({size}B)[/dim]"
                            elif size < 1024 * 1024:
                                size_str = f" [dim]({size/1024:.1f}KB)[/dim]"
                            else:
                                size_str = f" [dim]({size/(1024*1024):.1f}MB)[/dim]"
                        except:
                            size_str = ""
                    
                    # Check if diff is available for this file
                    diff_button = ""
                    if self._is_text(item) and self.get_diff(item) is not None:
                        self.file_idx[self.idx] = str(item)
                        diff_button = f"[bold cyan][[{self.idx}]][/bold cyan] "
                        self.idx += 1
                    
                    # Add tags after the filename
                    new_tag = " [bold green][NEW][/bold green]" if event == 'created' else ""
                    edited_tag = " [bold yellow][EDITED][/bold yellow]" if (event == 'modified' and event != 'created') else ""
                    
                    # Apply styling
                    if style:
                        node_text = f"{diff_button}{icon} [{color} {style}]{item.name}[/{style} {color}]{new_tag}{edited_tag}{size_str}"
                    else:
                        node_text = f"{diff_button}{icon} [{color}]{item.name}[/{color}]{new_tag}{edited_tag}{size_str}"
                        
                    tree_node.add(node_text)
                    
        except PermissionError:
            tree_node.add("[dim red]Permission Denied[/dim red]")
        except FileNotFoundError:
            tree_node.add("[dim red]Directory not found[/dim red]")
        except OSError as e:
            tree_node.add(f"[dim red]Error accessing directory: {e}[/dim red]")
            
    def create_display(self):
        tree = self.build_tree()
        
        dir_exists = self.check_dir_exists()
        
        now = datetime.now()
        recent_created = sum(1 for t, event in self.changed.values() 
                            if event == 'created' and (now - t).total_seconds() < 30)
        recent_modified = sum(1 for t, event in self.changed.values() 
                             if event == 'modified' and (now - t).total_seconds() < 30)
        recent_deleted = sum(1 for t in self.deleted.values() 
                            if (now - t).total_seconds() < 30)
        
        chime_status = "[green]ON[/green]" if self.chime else "[red]OFF[/red]"
        
        if not dir_exists:
            status = "[bold red]DIRECTORY DELETED[/bold red]"
            info_text = (f"Monitoring: [red]{self.dir}[/red] {status}\n"
                        f"[yellow]⚠️ The monitored directory has been deleted or moved![/yellow]\n"
                        f"Chime: {chime_status}")
        else:
            info_text = (f"Monitoring: [cyan]{self.dir}[/cyan]\n"
                        f"Created: [bright_green]{recent_created}[/bright_green] | "
                        f"Modified: [red]{recent_modified}[/red] | "
                        f"Deleted: [dim red]{recent_deleted}[/dim red] | "
                        f"Chime: {chime_status}")
            
        info_panel = Panel(info_text, title="[bold green]File System Monitor[/bold green]", 
                          border_style="green" if dir_exists else "red")
        
        tree_panel = Panel(tree, title="[bold blue]Directory Tree[/bold blue]", 
                          border_style="blue" if dir_exists else "red")
        
        instructions = []
        if hasattr(self, 'file_idx') and self.file_idx:
            instructions.append("[dim]Type a number [bold cyan][1-N][/bold cyan] to view file diffs • [/dim]")
        instructions.append("[dim]Press Ctrl+C to access menu (change path, toggle chime, exit)[/dim]")
        instructions_text = "".join(instructions)
        
        from rich.layout import Layout
        layout = Layout()
        
        if self.diff_file:
            diff = self.get_diff(Path(self.diff_file))
            if diff:
                diff_content = "".join(diff)
                diff_panel = Panel(diff_content, title=f"[bold yellow]Diff for {Path(self.diff_file).name}[/bold yellow]", 
                                 border_style="yellow")
                layout.split_column(
                    Layout(info_panel, size=6 if not dir_exists else 5),
                    Layout(tree_panel),
                    Layout(diff_panel),
                    Layout(Panel(instructions_text + " • [dim]Press 'q' to close diff[/dim]", border_style="dim"), size=3)
                )
            else:
                layout.split_column(
                    Layout(info_panel, size=6 if not dir_exists else 5),
                    Layout(tree_panel),
                    Layout(Panel(instructions_text, border_style="dim"), size=3)
                )
        else:
            layout.split_column(
                Layout(info_panel, size=6 if not dir_exists else 5),
                Layout(tree_panel),
                Layout(Panel(instructions_text, border_style="dim"), size=3)
            )
        
        return layout
        
    def change_path(self, new_path):
        new_dir = Path(new_path).resolve()
        if not new_dir.exists():
            raise ValueError(f"Directory does not exist: {new_path}")
        
        self.stop_monitoring()
        
        self.changed.clear()
        self.created.clear()
        self.deleted.clear()
        
        self.dir = new_dir
        self.chime_file = self.dir / "chime.mp3"
        
        self.start_monitoring()
        
    def start_monitoring(self):
        if not self.dir.exists():
            raise ValueError(f"Directory does not exist: {self.dir}")
            
        self.running = True
        self.observer = Observer()
        event_handler = Handler(self)
        self.observer.schedule(event_handler, str(self.dir), recursive=True)
        self.observer.start()
        
    def check_dir_exists(self):
        return self.dir.exists()
        
    def stop_monitoring(self):
        self.running = False
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join()
            except Exception:
                pass
            
    def run(self):
        self.console.print(f"[green]Starting file system monitor for: {self.dir}[/green]")
        chime_status = "[green]ON[/green]" if self.chime else "[red]OFF[/red]"
        self.console.print(f"[dim]Chime: {chime_status} | Interactive controls available during monitoring[/dim]")
        
        self.start_monitoring()
        
        try:
            with Live(self.create_display(), refresh_per_second=2, screen=True) as live:
                counter = 0
                while self.running:
                    live.update(self.create_display())
                    
                    counter += 1
                    if counter >= 10:
                        counter = 0
                        if not self.check_dir_exists():
                            self.stop_monitoring()
                    
                    time.sleep(0.5)
                        
        except KeyboardInterrupt:
            self.stop_monitoring()
            while True:
                try:
                    dir_exists = self.check_dir_exists()
                    
                    if not dir_exists:
                        self.console.print("\n[red]⚠️ DIRECTORY DELETED OR MOVED![/red]")
                        self.console.print(f"[dim]The monitored directory no longer exists: {self.dir}[/dim]")
                        self.console.print("\n[yellow]🔧 Recovery Options:[/yellow]")
                        self.console.print("  [cyan]1.[/cyan] Change to a different directory")
                        self.console.print("  [cyan]2.[/cyan] Exit program")
                        
                        choice = input("\nEnter choice (1-2): ").strip()
                        
                        if choice == '1':
                            new_path = input("Enter new directory path: ").strip()
                            if new_path:
                                try:
                                    self.change_path(new_path)
                                    self.console.print(f"[green]✅ Now monitoring: {self.dir}[/green]")
                                    self.console.print("[green]Resuming monitoring... (Press Ctrl+C again to return to menu)[/green]")
                                    with Live(self.create_display(), refresh_per_second=2, screen=True) as live:
                                        counter = 0
                                        while self.running:
                                            live.update(self.create_display())
                                            
                                            counter += 1
                                            if counter >= 10:
                                                counter = 0
                                                if not self.check_dir_exists():
                                                    self.stop_monitoring()
                                            
                                            time.sleep(0.5)
                                except ValueError as e:
                                    self.console.print(f"[red]❌ Error: {e}[/red]")
                            else:
                                self.console.print("[yellow]No path entered[/yellow]")
                                
                        elif choice == '2':
                            break
                        else:
                            self.console.print("[red]Invalid choice. Please enter 1 or 2.[/red]")
                    else:
                        self.console.print("\n[yellow]🔧 Monitor Controls:[/yellow]")
                        self.console.print("  [cyan]1.[/cyan] Change directory path")
                        self.console.print("  [cyan]2.[/cyan] Toggle chime notifications")
                        self.console.print("  [cyan]3.[/cyan] View file diffs")
                        self.console.print("  [cyan]4.[/cyan] Resume monitoring")
                        self.console.print("  [cyan]5.[/cyan] Exit")
                        
                        choice = input("\nEnter choice (1-5): ").strip()
                        
                        if choice == '1':
                            new_path = input("Enter new directory path: ").strip()
                            if new_path:
                                try:
                                    self.change_path(new_path)
                                    self.console.print(f"[green]✅ Now monitoring: {self.dir}[/green]")
                                except ValueError as e:
                                    self.console.print(f"[red]❌ Error: {e}[/red]")
                            else:
                                self.console.print("[yellow]No path entered[/yellow]")
                                
                        elif choice == '2':
                            self.chime = not self.chime
                            chime_status = "[green]ON[/green]" if self.chime else "[red]OFF[/red]"
                            self.console.print(f"[blue]🔔 Chime toggled: {chime_status}[/blue]")
                            
                            if self.chime and not self.chime_file.exists():
                                self.console.print(f"[yellow]⚠️ Note: chime.mp3 not found at {self.chime_file}[/yellow]")
                                self.console.print(f"[dim]Audio notifications will be disabled until chime.mp3 is available[/dim]")
                                
                        elif choice == '3':
                            self._show_diff_menu()
                                
                        elif choice == '4':
                            self.console.print("[green]Resuming monitoring... (Press Ctrl+C again to return to menu)[/green]")
                            self.start_monitoring()
                            with Live(self.create_display(), refresh_per_second=2, screen=True) as live:
                                counter = 0
                                while self.running:
                                    live.update(self.create_display())
                                    
                                    counter += 1
                                    if counter >= 10:
                                        counter = 0
                                        if not self.check_dir_exists():
                                            self.stop_monitoring()
                                    
                                    time.sleep(0.5)
                                    
                        elif choice == '5':
                            break
                            
                        else:
                            self.console.print("[red]Invalid choice. Please enter 1-5.[/red]")
                        
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                    
        finally:
            self.stop_monitoring()
            self.console.print("\n[yellow]Monitoring stopped.[/yellow]")
    
    def _show_diff_menu(self):
        tree = self.build_tree()
        
        if not hasattr(self, 'file_idx') or not self.file_idx:
            self.console.print("[yellow]No files with diffs available.[/yellow]")
            return
        
        self.console.print("\n[bold blue]📄 Files with Available Diffs:[/bold blue]")
        for num, path in self.file_idx.items():
            name = Path(path).name
            self.console.print(f"  [cyan]{num}.[/cyan] {name}")
        
        self.console.print("\n[dim]Enter a number to view diff, or 'q' to go back[/dim]")
        choice = input("Choice: ").strip()
        
        if choice.lower() == 'q':
            return
        
        try:
            num = int(choice)
            if num in self.file_idx:
                path = Path(self.file_idx[num])
                diff = self.get_diff(path)
                
                if diff:
                    self.console.print(f"\n[bold yellow]📋 Diff for {path.name}:[/bold yellow]")
                    self.console.print("-" * 60)
                    for line in diff:
                        line = line.rstrip('\n')
                        if line.startswith('+++') or line.startswith('---'):
                            self.console.print(f"[bold blue]{line}[/bold blue]")
                        elif line.startswith('@@'):
                            self.console.print(f"[bold cyan]{line}[/bold cyan]")
                        elif line.startswith('+'):
                            self.console.print(f"[green]{line}[/green]")
                        elif line.startswith('-'):
                            self.console.print(f"[red]{line}[/red]")
                        else:
                            self.console.print(f"[dim]{line}[/dim]")
                    self.console.print("-" * 60)
                    input("\nPress Enter to continue...")
                else:
                    self.console.print("[yellow]No diff available for this file.[/yellow]")
            else:
                self.console.print("[red]Invalid file number.[/red]")
        except ValueError:
            self.console.print("[red]Invalid input. Please enter a number.[/red]")
            
    def _input_handler(self):
        pass


def main():
    console = Console()
    
    console.print("[bold blue]🚀 File System Activity Monitor[/bold blue]")
    console.print("[dim]Watch files and directories light up as they change![/dim]\n")
    
    while True:
        cwd = os.getcwd()
        print(f"Current directory: {cwd}")
        directory = input("📁 Enter directory path to monitor (or '.' for current directory): ").strip()
        if not directory:
            directory = "."
        
        path = Path(directory).resolve()
        if path.exists():
            break
        else:
            console.print(f"[red]❌ Directory does not exist: {directory}[/red]")
            console.print("[dim]Please try again...[/dim]\n")
    
    console.print()
    while True:
        choice = input("🔔 Enable audio chime notifications? (y/n) [y]: ").strip().lower()
        if choice in ['n', 'no']:
            chime = False
            break
        elif choice in ['','y', 'yes']:
            chime = True
            break
        else:
            console.print("[red]Please enter 'y' for yes or 'n' for no[/red]")
    
    console.print("\n[green]✅ Configuration:[/green]")
    console.print(f"  📂 Directory: [cyan]{path}[/cyan]")
    status = "[green]Enabled[/green]" if chime else "[red]Disabled[/red]"
    console.print(f"  🔔 Chime: {status}")
    
    if chime:
        chime_file = path / "chime.mp3"
        if not chime_file.exists():
            console.print(f"  [yellow]⚠️ Note: chime.mp3 not found in {path}[/yellow]")
            console.print(f"  [dim]Audio notifications will be disabled until chime.mp3 is available[/dim]")
    
    console.print("\n[dim]Starting monitor...[/dim]")
    
    try:
        monitor = Monitor(str(path), enable_chime=chime)
        monitor.run()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
