import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import os
import json
import datetime
import platform
from pathlib import Path

from utils.file_handler import FileHandler
from utils.dog import create_watchdog

DATA_FILE = "config_manager_data.json"

class OrcaSlicerConfigManager(tb.Window):
    def __init__(self, theme='darkly'):
        super().__init__(themename=theme)
        self.title("Orca Slicer Config Manager")
        self.geometry("1000x500")
        self.minsize(1000, 500)

        # Data/persistence
        self.file_handler = FileHandler()
        self.managed_files = {}  # {file_id: path}
        self.file_counter = 0
        self.backup_dir = ""  # Chosen backup root
        self.auto_backup_enabled = True  # Default

        self.file_watchdogs = {}
        
        self.detection_config = {
            "app_name": "OrcaSlicer",
            "subdirectories": ["user"],  # NEW: changed from single subdirectory to list
            "file_patterns": ["*.json", "*.ini", "*.conf"],
            "exclude_patterns": ["cache", "temp", "log"],
            "search_dirs": self._get_default_search_dirs()
        }

        self.load_data()

        # UI --- Button bar, File list, Detection config, Status bar
        main_frame = tb.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=YES)
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # --- Top Button Bar ---
        button_frame = tb.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky=EW, pady=(0, 10))

        self.add_btn = tb.Button(master=button_frame, text="Add Config File", command=self.add_file, bootstyle=SUCCESS)
        self.add_btn.pack(side=LEFT, padx=5)

        self.remove_btn = tb.Button(master=button_frame, text="Remove Selected", command=self.remove_file, bootstyle=DANGER)
        self.remove_btn.pack(side=LEFT, padx=5)

        self.backup_btn = tb.Button(master=button_frame, text="Backup Now", command=self.backup_all, bootstyle=(PRIMARY, OUTLINE))
        self.backup_btn.pack(side=LEFT, padx=5)

        self.restore_btn = tb.Button(master=button_frame, text="Restore...", command=self.restore_files, bootstyle=(INFO, OUTLINE))
        self.restore_btn.pack(side=LEFT, padx=5)

        self.choose_backup_btn = tb.Button(master=button_frame, text="Set Backup Folder", command=self.choose_backup_dir, bootstyle=SECONDARY)
        self.choose_backup_btn.pack(side=LEFT, padx=5)

        self.auto_backup_var = tb.BooleanVar(value=self.auto_backup_enabled)
        self.auto_backup_check = tb.Checkbutton(
            master=button_frame, text="Auto-Backup on Change", variable=self.auto_backup_var, 
            command=self.toggle_auto_backup, bootstyle=SUCCESS
        )
        self.auto_backup_check.pack(side=RIGHT, padx=8)

        # --- Detection Configuration Frame ---
        detect_frame = tb.LabelFrame(main_frame, text="Auto-Detection Settings", padding=10)
        detect_frame.grid(row=1, column=0, sticky=EW, pady=(0, 10))

        # App name entry
        app_label = tb.Label(detect_frame, text="App Name:")
        app_label.grid(row=0, column=0, sticky=W, padx=(0, 5))
        
        self.app_name_var = tb.StringVar(value=self.detection_config["app_name"])
        app_entry = tb.Entry(detect_frame, textvariable=self.app_name_var, width=20)
        app_entry.grid(row=0, column=1, sticky=W, padx=(0, 10))

        # File patterns entry
        pattern_label = tb.Label(detect_frame, text="File Patterns (comma-separated):")
        pattern_label.grid(row=0, column=2, sticky=W, padx=(0, 5))
        
        self.pattern_var = tb.StringVar(value=", ".join(self.detection_config["file_patterns"]))
        pattern_entry = tb.Entry(detect_frame, textvariable=self.pattern_var, width=25)
        pattern_entry.grid(row=0, column=3, sticky=W, padx=(0, 10))

        # Exclude patterns entry
        exclude_label = tb.Label(detect_frame, text="Exclude:")
        exclude_label.grid(row=0, column=4, sticky=W, padx=(0, 5))
        
        self.exclude_var = tb.StringVar(value=", ".join(self.detection_config["exclude_patterns"]))
        exclude_entry = tb.Entry(detect_frame, textvariable=self.exclude_var, width=20)
        exclude_entry.grid(row=0, column=5, sticky=W, padx=(0, 10))

        # Auto-detect button
        self.detect_btn = tb.Button(
            master=detect_frame, 
            text="🔍 Auto-Detect Configs", 
            command=self.auto_detect_configs, 
            bootstyle=(INFO, OUTLINE)
        )
        self.detect_btn.grid(row=0, column=6, sticky=E, padx=5)

        # --- File List (Treeview) ---
        tree_cols = ("path",)
        self.file_tree = tb.Treeview(
            master=main_frame,
            columns=tree_cols,
            show="headings",
            bootstyle=INFO
        )
        self.file_tree.grid(row=2, column=0, sticky=NSEW)
        self.file_tree.heading("path", text="Config File Path")
        self.file_tree.column("path", width=750, stretch=True)

        scrollbar = tb.Scrollbar(main_frame, orient=VERTICAL, command=self.file_tree.yview, bootstyle=ROUND)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky=NS)

        # --- Status Bar ---
        self.status_var = tb.StringVar(value="Ready. Add configs or use Auto-Detect.")
        status_bar = tb.Label(self, textvariable=self.status_var, bootstyle=INVERSE, padding=5, anchor=W)
        status_bar.pack(side=BOTTOM, fill=X)

        # Populate loaded files in tree
        for file_id, path in self.managed_files.items():
            self.file_tree.insert(parent="", index=END, iid=file_id, values=(path,))
        # Start watcher for each file
        for file_id, path in self.managed_files.items():
            self.ensure_watcher_for_file(path)

        self.protocol("WM_DELETE_WINDOW", self.on_quit)

    def _get_default_search_dirs(self):
        """Returns platform-specific config directories to search"""
        system = platform.system()
        dirs = []
        
        if system == "Windows":
            # Common Windows config locations
            appdata = os.getenv('APPDATA', '')
            localappdata = os.getenv('LOCALAPPDATA', '')
            programdata = os.getenv('PROGRAMDATA', '')
            
            dirs.extend([
                appdata,
                localappdata,
                programdata,
                os.path.join(os.path.expanduser('~'), 'Documents'),
            ])
        elif system == "Linux":
            # Common Linux config locations
            home = os.path.expanduser('~')
            dirs.extend([
                os.path.join(home, '.config'),
                os.path.join(home, '.local', 'share'),
                '/etc',
                home,
            ])
        elif system == "Darwin":  # macOS
            home = os.path.expanduser('~')
            dirs.extend([
                os.path.join(home, 'Library', 'Application Support'),
                os.path.join(home, 'Library', 'Preferences'),
                os.path.join(home, '.config'),
            ])
        
        return [d for d in dirs if d and os.path.isdir(d)]

    def auto_detect_configs(self):
        """Automatically detect config files based on current settings"""
        # Update detection config from UI
        self.detection_config["app_name"] = self.app_name_var.get().strip()
        self.detection_config["file_patterns"] = [p.strip() for p in self.pattern_var.get().split(',') if p.strip()]
        self.detection_config["exclude_patterns"] = [p.strip().lower() for p in self.exclude_var.get().split(',') if p.strip()]
        
        if not self.detection_config["app_name"]:
            messagebox.showwarning("App Name Required", "Please enter an application name to search for.")
            return
        
        self.status_var.set(f"Scanning for {self.detection_config['app_name']} configs...")
        self.update_idletasks()
        
        found_files = []
        app_name = self.detection_config["app_name"]
        
        for base_dir in self.detection_config["search_dirs"]:
            try:
                # Look for directories matching the app name
                for root, dirs, files in os.walk(base_dir, topdown=True):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if not any(
                        excl in d.lower() for excl in self.detection_config["exclude_patterns"]
                    )]
                    
                    # Check if current directory contains app_name/subdirectory pattern
                    path_lower = root.lower()
                    valid_paths = [os.path.join(app_name, subdir).lower() 
                                for subdir in self.detection_config["subdirectories"]]
                    if not any(valid_path in path_lower for valid_path in valid_paths):
                        # Don't search too deep if pattern isn't in path
                        if root.count(os.sep) - base_dir.count(os.sep) > 3:
                            dirs[:] = []
                        continue
                    
                    # Check files against patterns
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        
                        # Check if file matches any pattern
                        if any(Path(filename).match(pattern) for pattern in self.detection_config["file_patterns"]):
                            # Check if not already managed
                            if filepath not in self.managed_files.values():
                                found_files.append(filepath)
                    
                    # Limit search depth in app directories
                    if root.count(os.sep) - base_dir.count(os.sep) > 5:
                        dirs[:] = []
                        
            except (PermissionError, OSError) as e:
                # Skip directories we can't access
                continue
        
        if not found_files:
            self.status_var.set(f"No new {app_name} configs found.")
            messagebox.showinfo("Auto-Detect Complete", f"No new config files found for {app_name}.")
            return
        
        # Show selection dialog
        self._show_detection_results(found_files)

    def _show_detection_results(self, found_files):
        """Display detected files and let user select which to add"""
        dialog = tb.Toplevel(self)
        dialog.title("Detected Config Files")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.grab_set()
        
        # Instructions
        info_label = tb.Label(
            dialog, 
            text=f"Found {len(found_files)} config file(s). Select files to manage:",
            padding=10
        )
        info_label.pack(fill=X)
        
        # Listbox with checkboxes (using Treeview)
        list_frame = tb.Frame(dialog, padding=10)
        list_frame.pack(fill=BOTH, expand=YES)
        
        tree = tb.Treeview(
            list_frame,
            columns=("path",),
            show="tree headings",
            selectmode="extended",
            bootstyle=INFO
        )
        tree.pack(side=LEFT, fill=BOTH, expand=YES)
        tree.heading("#0", text="Select")
        tree.heading("path", text="File Path")
        tree.column("#0", width=50)
        tree.column("path", width=600)
        
        scroll = tb.Scrollbar(list_frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=RIGHT, fill=Y)
        
        # Add files to tree
        selected_items = {}
        for idx, filepath in enumerate(found_files):
            item_id = f"item_{idx}"
            tree.insert("", END, iid=item_id, text="☐", values=(filepath,))
            selected_items[item_id] = {"path": filepath, "selected": False}
        
        def toggle_selection(event):
            item = tree.focus()
            if item and item in selected_items:
                selected_items[item]["selected"] = not selected_items[item]["selected"]
                text = "☑" if selected_items[item]["selected"] else "☐"
                tree.item(item, text=text)
        
        tree.bind("<Button-1>", toggle_selection)
        tree.bind("<space>", toggle_selection)
        
        # Buttons
        btn_frame = tb.Frame(dialog, padding=10)
        btn_frame.pack(fill=X)
        
        def select_all():
            for item_id in selected_items:
                selected_items[item_id]["selected"] = True
                tree.item(item_id, text="☑")
        
        def deselect_all():
            for item_id in selected_items:
                selected_items[item_id]["selected"] = False
                tree.item(item_id, text="☐")
        
        def add_selected():
            added = 0
            for item_data in selected_items.values():
                if item_data["selected"]:
                    filepath = item_data["path"]
                    file_id = f"file_{self.file_counter}"
                    self.file_counter += 1
                    self.managed_files[file_id] = filepath
                    self.file_tree.insert(parent="", index=END, iid=file_id, values=(filepath,))
                    self.ensure_watcher_for_file(filepath)
                    added += 1
            
            self.status_var.set(f"Added {added} config file(s).")
            self.save_data()
            dialog.destroy()
        
        tb.Button(btn_frame, text="Select All", command=select_all, bootstyle=INFO).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Deselect All", command=deselect_all, bootstyle=WARNING).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Add Selected", command=add_selected, bootstyle=SUCCESS).pack(side=RIGHT, padx=5)
        tb.Button(btn_frame, text="Cancel", command=dialog.destroy, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

    # --- Persistence ---
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                self.managed_files = {str(k): v for k, v in data.get("managed_files", {}).items()}
                self.file_counter = data.get("file_counter", len(self.managed_files))
                self.backup_dir = data.get("backup_dir", "")
                self.auto_backup_enabled = data.get("auto_backup_enabled", True)
                
                # Load detection config if available
                if "detection_config" in data:
                    self.detection_config.update(data["detection_config"])
            except Exception:
                self.managed_files, self.backup_dir, self.auto_backup_enabled = {}, "", True

    def save_data(self):
        data = {
            "managed_files": self.managed_files,
            "file_counter": self.file_counter,
            "backup_dir": self.backup_dir,
            "auto_backup_enabled": self.auto_backup_enabled,
            "detection_config": self.detection_config,
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # --- File Management ---
    def add_file(self):
        filepath = filedialog.askopenfilename(title="Select config file")
        if not filepath:
            return
        if filepath in self.managed_files.values():
            messagebox.showwarning("Duplicate File", "This file is already managed.")
            return
        file_id = f"file_{self.file_counter}"
        self.file_counter += 1
        self.managed_files[file_id] = filepath
        self.file_tree.insert(parent="", index=END, iid=file_id, values=(filepath,))
        self.ensure_watcher_for_file(filepath)
        self.status_var.set(f"Added: {os.path.basename(filepath)}")
        self.save_data()

    def remove_file(self):
        selected_id = self.file_tree.focus()
        if not selected_id:
            messagebox.showwarning("No Selection", "Select a file to remove.")
            return
        filepath = self.managed_files.get(selected_id)
        if messagebox.askyesno("Confirm Removal", f"Stop managing this file?\n\n{filepath}"):
            del self.managed_files[selected_id]
            self.file_tree.delete(selected_id)
            self.status_var.set(f"Removed: {os.path.basename(filepath)}")
            self.save_data()

    def choose_backup_dir(self):
        dir_selected = filedialog.askdirectory(title="Select a backup root directory")
        if dir_selected:
            self.backup_dir = dir_selected
            self.status_var.set(f"Backup folder set: {self.backup_dir}")
            self.save_data()

    # --- Backup & Restore ---
    def backup_all(self):
        self._backup_files(self.managed_files.values())

    def backup_single(self, path):
        self._backup_files([path])

    def _backup_files(self, files):
        if not files:
            messagebox.showinfo("No Files", "No files to backup.")
            return
        if not self.backup_dir:
            if not messagebox.askyesno("Backup Folder Not Set", "Backup folder isn't set. Set now?"):
                return
            self.choose_backup_dir()
            if not self.backup_dir:
                return
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target = os.path.join(self.backup_dir, f"ConfigBackup_{timestamp}")
        try:
            os.makedirs(target, exist_ok=True)
            copied_count = 0
            for path in files:
                if os.path.exists(path):
                    fname = os.path.basename(path)
                    tgtfile = os.path.join(target, fname)
                    self.file_handler.copy_file(path, tgtfile, overwrite=True)
                    copied_count += 1
            self.status_var.set(f"Backup complete: {copied_count} files in {os.path.basename(target)}")
            messagebox.showinfo("Backup Done", f"Backed up {copied_count} files:\n{target}")
        except Exception as e:
            self.status_var.set(f"Backup error: {e}")
            messagebox.showerror("Backup Failed", str(e))

    def restore_files(self):
        if not self.backup_dir or not os.path.isdir(self.backup_dir):
            messagebox.showwarning("Backup Location", "No backup folder set.")
            return

        candidates = [d for d in os.listdir(self.backup_dir) if d.startswith("ConfigBackup_")]
        if not candidates:
            messagebox.showinfo("No Backups", "No backups found in the backup folder.")
            return

        import tkinter.simpledialog as sd
        selected = sd.askstring(
            "Restore Which Backup?",
            "Enter backup folder name. Suggestions:\n" + "\n".join(candidates) + "\n\n(Copy from above)",
            initialvalue=candidates[-1] if candidates else ""
        )
        if not selected or selected not in candidates:
            self.status_var.set("Restore cancelled.")
            return
        restore_folder = os.path.join(self.backup_dir, selected)

        files_to_restore = os.listdir(restore_folder)
        ok = messagebox.askyesno(
            "Confirm Restore",
            f"Restore these files to their original locations?\n\n" +
            "\n".join(files_to_restore) + "\n\n(This overwrites files without undo!)"
        )
        if not ok:
            return
        
        name_to_id = {os.path.basename(path): file_id for file_id, path in self.managed_files.items()}
        restored = 0
        for fname in files_to_restore:
            if fname in name_to_id:
                dest_path = self.managed_files[name_to_id[fname]]
                src_path = os.path.join(restore_folder, fname)
                try:
                    self.file_handler.copy_file(src_path, dest_path, overwrite=True)
                    restored += 1
                except Exception as e:
                    messagebox.showerror("Restore Problem", f"Could not restore {fname}: {e}")
        self.status_var.set(f"Restored {restored} files from backup.")
        messagebox.showinfo("Restore Complete", f"Restored {restored} files.")

    # --- Auto-Backup (Watchdog) ---
    def ensure_watcher_for_file(self, file_path):
        parent_dir = os.path.dirname(file_path)
        if parent_dir in self.file_watchdogs:
            return
        def on_event(event):
            if not self.auto_backup_enabled:
                return
            for tracked_path in self.managed_files.values():
                if event.src_path == tracked_path:
                    self.status_var.set(f"Auto-backup: {os.path.basename(tracked_path)} changed")
                    self.backup_single(tracked_path)
        try:
            wdog = create_watchdog(parent_dir, on_modified=on_event, recursive=False)
            wdog.start()
            self.file_watchdogs[parent_dir] = wdog
        except Exception as e:
            print("Watchdog error:", e)

    def toggle_auto_backup(self):
        self.auto_backup_enabled = self.auto_backup_var.get()
        self.status_var.set("Auto-backup " + ("Enabled" if self.auto_backup_enabled else "Disabled"))
        self.save_data()

    def on_quit(self):
        for wdog in self.file_watchdogs.values():
            try:
                wdog.stop()
            except Exception:
                pass
        self.save_data()
        self.destroy()

# --- Entrypoint ---
if __name__ == "__main__":
    try:
        app = OrcaSlicerConfigManager(theme='darkly')
        app.mainloop()
    except (KeyboardInterrupt, SystemExit):
        print("Application exited.")