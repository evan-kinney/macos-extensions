#!/usr/bin/env python3
"""
Copy to Server Workflow Script
Copies selected files to a remote server via SCP with GUI for server selection
and destination path completion.
"""

import os
import sys
import subprocess
import re
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading


class SSHConfigParser:
    """Parse SSH config file to extract host configurations."""
    
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.expanduser("~/.ssh/config")
        self.config_path = config_path
        self.hosts = []
        
    def parse(self):
        """Parse SSH config and return list of host configurations."""
        if not os.path.exists(self.config_path):
            return []
        
        current_host = None
        
        with open(self.config_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Match Host directive
                if line.startswith('Host '):
                    if current_host:
                        self.hosts.append(current_host)
                    
                    host_name = line.split('Host ', 1)[1].strip()
                    # Remove surrounding quotes if present
                    if (host_name.startswith('"') and host_name.endswith('"')) or \
                       (host_name.startswith("'") and host_name.endswith("'")):
                        host_name = host_name[1:-1]
                    # Skip wildcard hosts
                    if '*' not in host_name and '?' not in host_name:
                        current_host = {
                            'name': host_name,
                            'hostname': None,
                            'user': None,
                            'identity_file': None
                        }
                    else:
                        current_host = None
                
                elif current_host:
                    # Parse HostName
                    if line.startswith('HostName '):
                        current_host['hostname'] = line.split('HostName ', 1)[1].strip()
                    
                    # Parse User
                    elif line.startswith('User '):
                        current_host['user'] = line.split('User ', 1)[1].strip()
                    
                    # Parse IdentityFile
                    elif line.startswith('IdentityFile '):
                        identity_file = line.split('IdentityFile ', 1)[1].strip()
                        # Expand ~ in path
                        current_host['identity_file'] = os.path.expanduser(identity_file)
        
        # Add the last host
        if current_host:
            self.hosts.append(current_host)
        
        return self.hosts


class ServerCopyDialog:
    """Custom dialog for selecting server and destination path."""
    
    def __init__(self, hosts, file_count):
        self.result = None
        self.hosts = hosts
        self.file_count = file_count
        self.file_paths = []
        self.selected_host = None
        self.destination_paths = []
        self.password_visible = False
        self.remote_home = None  # Store the remote server's home directory
        
        self.root = tk.Tk()
        self.root.title("Copy to Server")
        
        # Set Aqua theme for macOS native look
        style = ttk.Style()
        style.theme_use('aqua')
        
        # Set window properties - will be adjusted dynamically
        self.root.resizable(False, False)
        
        # Bring window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Create main frame with native background
        main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Source files display
        source_label = ttk.Label(
            main_frame,
            text="Source:",
            font=("Helvetica", 11)
        )
        source_label.pack(fill=tk.X, pady=(0, 4))
        
        # Text widget to display files
        source_frame = ttk.Frame(main_frame)
        source_frame.pack(fill=tk.X, pady=(0, 12))
        
        # Create pinned icon column (non-scrolling)
        self.icon_tree = ttk.Treeview(
            source_frame,
            columns=(),
            show='tree',
            selectmode='none',
            height=min(3, max(1, file_count)),
            takefocus=False
        )
        self.icon_tree.column('#0', width=35, stretch=False)
        self.icon_tree.grid(row=0, column=0, sticky='ns')
        
        # Create scrollable path column
        self.source_tree = ttk.Treeview(
            source_frame,
            columns=('path',),
            show='tree',  # Hide headers
            selectmode='none',
            height=min(3, max(1, file_count)),
            takefocus=False
        )
        self.source_tree.column('#0', width=0, stretch=False)  # Hide tree column
        self.source_tree.column('path', anchor=tk.W, width=1000, stretch=False)
        self.source_tree.grid(row=0, column=1, sticky='nsew')
        
        # Store if scrolling should be enabled
        self.scrolling_enabled = file_count > 3
        
        # Add vertical scrollbar if needed - control both trees
        if self.scrolling_enabled:
            v_scrollbar = ttk.Scrollbar(source_frame, orient='vertical')
            v_scrollbar.grid(row=0, column=2, sticky='ns')
            
            # Configure both trees to use the same scrollbar
            def on_scroll(*args):
                self.icon_tree.yview(*args)
                self.source_tree.yview(*args)
            
            v_scrollbar.config(command=on_scroll)
            
            # Update scrollbar when either tree scrolls
            def update_scrollbar(*args):
                v_scrollbar.set(*args)
                
            self.icon_tree.config(yscrollcommand=update_scrollbar)
            self.source_tree.config(yscrollcommand=update_scrollbar)
            
            # Bind mouse wheel to both trees for macOS
            def on_mousewheel(event):
                # macOS uses event.delta directly
                self.icon_tree.yview_scroll(-1 * int(event.delta), "units")
                self.source_tree.yview_scroll(-1 * int(event.delta), "units")
                return "break"
            
            # Bind to both source_tree and icon_tree
            self.icon_tree.bind("<MouseWheel>", on_mousewheel)
            self.source_tree.bind("<MouseWheel>", on_mousewheel)
            
            # Also bind to the frame to catch events when hovering over either
            source_frame.bind("<MouseWheel>", on_mousewheel)
        else:
            # Even without scrollbar, bind mouse wheel to prevent default behavior
            def no_scroll(event):
                return "break"
            self.icon_tree.bind("<MouseWheel>", no_scroll)
            self.source_tree.bind("<MouseWheel>", no_scroll)
        
        # Add horizontal scrollbar for path column only
        self.h_scrollbar = ttk.Scrollbar(source_frame, orient='horizontal', command=self.source_tree.xview)
        self.source_tree.config(xscrollcommand=self.h_scrollbar.set)
        # Will be shown/hidden based on content length
        
        # Store reference to source_frame for later scrollbar management
        self.source_frame = source_frame
        
        # Configure grid weights
        source_frame.grid_rowconfigure(0, weight=1)
        source_frame.grid_columnconfigure(1, weight=1)
        
        # Summary label for file/directory count
        self.summary_label = ttk.Label(
            main_frame,
            text="",
            font=("Helvetica", 10),
            foreground="gray"
        )
        self.summary_label.pack(fill=tk.X, pady=(0, 8))
        
        # Server selection
        server_frame = ttk.Frame(main_frame)
        server_frame.pack(fill=tk.X, pady=8)
        
        server_label = ttk.Label(
            server_frame,
            text="Server:",
            width=12,
            font=("Helvetica", 11)
        )
        server_label.pack(side=tk.LEFT)
        
        self.server_var = tk.StringVar()
        self.server_combo = ttk.Combobox(
            server_frame,
            textvariable=self.server_var,
            state='readonly'
        )
        self.server_combo['values'] = [h['name'] for h in hosts]
        if hosts:
            self.server_combo.current(0)
        self.server_combo.bind('<<ComboboxSelected>>', self.on_server_selected)
        self.server_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Password field (initially hidden) - positioned between server and destination
        self.password_frame = ttk.Frame(main_frame)
        
        password_label = ttk.Label(
            self.password_frame,
            text="Password:",
            width=12,
            font=("Helvetica", 11)
        )
        password_label.pack(side=tk.LEFT)
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            self.password_frame,
            textvariable=self.password_var,
            show='•'
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Destination path with autocomplete - positioned after password field
        self.dest_frame = ttk.Frame(main_frame)
        self.dest_frame.pack(fill=tk.X, pady=8)
        
        dest_label = ttk.Label(
            self.dest_frame,
            text="Destination:",
            width=12,
            font=("Helvetica", 11)
        )
        dest_label.pack(side=tk.LEFT)
        
        self.dest_var = tk.StringVar()
        self.dest_combo = ttk.Combobox(
            self.dest_frame,
            textvariable=self.dest_var
        )
        self.dest_combo['values'] = []
        self.dest_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.dest_combo.bind('<KeyRelease>', self.on_dest_typing)
        self.dest_combo.bind('<FocusIn>', self.on_dest_focus)
        self.dest_combo.bind('<<ComboboxSelected>>', self.on_dest_selected)
        
        # Create destination checkbox
        self.create_dest_var = tk.BooleanVar(value=True)
        create_dest_check = ttk.Checkbutton(
            main_frame,
            text="Create destination if it doesn't exist",
            variable=self.create_dest_var
        )
        create_dest_check.pack(fill=tk.X, pady=(0, 8))
        
        # Buttons - always at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(16, 0))
        
        # Right-align buttons within button_frame
        copy_btn = ttk.Button(
            button_frame,
            text="Copy",
            command=self.copy,
            default="active",
            padding=(10, 2)
        )
        copy_btn.pack(side=tk.RIGHT, padx=8)
        
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel,
            padding=(10, 2)
        )
        cancel_btn.pack(side=tk.RIGHT, padx=8)
        
        # Keyboard bindings
        self.root.bind('<Return>', lambda e: self.copy())
        self.root.bind('<Escape>', lambda e: self.cancel())
        
        # Initialize server selection
        if hosts:
            self.on_server_selected(None)
        
        # Set initial window size after content is loaded
        self.update_window_size()
    
    def fetch_remote_home(self):
        """Fetch the home directory from the remote server."""
        if not self.selected_host:
            return None
        
        hostname = self.selected_host['hostname'] or self.selected_host['name']
        user = self.selected_host['user']
        identity_file = self.selected_host['identity_file']
        
        # Build SSH command
        ssh_cmd = ['ssh']
        
        if identity_file and os.path.exists(identity_file):
            ssh_cmd.extend(['-i', identity_file])
        
        # Add connection options
        ssh_cmd.extend([
            '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=no'
        ])
        
        if user:
            ssh_cmd.append(f'{user}@{hostname}')
        else:
            ssh_cmd.append(hostname)
        
        # Get home directory
        ssh_cmd.append('echo $HOME')
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception as e:
            print(f"Failed to fetch remote home directory: {e}")
        
        return None
    
    def on_server_selected(self, event):
        """Handle server selection change."""
        selected_name = self.server_var.get()
        self.selected_host = next((h for h in self.hosts if h['name'] == selected_name), None)
        
        if self.selected_host:
            # Show password field only if no identity file exists
            needs_password = not (self.selected_host['identity_file'] and 
                                 os.path.exists(self.selected_host['identity_file']))
            
            if needs_password and not self.password_visible:
                self.password_frame.pack(fill=tk.X, pady=8, before=self.dest_frame)
                self.password_visible = True
                self.update_window_size()
            elif not needs_password and self.password_visible:
                self.password_frame.pack_forget()
                self.password_visible = False
                self.update_window_size()
            
            # Fetch remote home directory asynchronously
            threading.Thread(target=self.fetch_and_store_home, daemon=True).start()
            
            # Load initial destination suggestions
            self.load_destination_suggestions()
    
    def fetch_and_store_home(self):
        """Fetch and store the remote home directory."""
        self.remote_home = self.fetch_remote_home()
        
        # After getting home directory, refresh destination values to apply tilde replacement
        if self.remote_home and self.destination_paths:
            self.root.after(0, self.apply_home_replacement_to_paths)
    
    def on_dest_focus(self, event):
        """Load suggestions when destination field gets focus."""
        if not self.destination_paths:
            self.load_destination_suggestions()
    
    def on_dest_selected(self, event):
        """Handle selection from dropdown - load subdirectories of selected path."""
        selected_path = self.dest_var.get()
        
        if selected_path:
            # Ensure path ends with /
            if not selected_path.endswith('/'):
                selected_path += '/'
                self.dest_var.set(selected_path)
            
            # Fetch subdirectories of the selected path
            threading.Thread(
                target=self.fetch_remote_paths,
                args=(selected_path,),
                daemon=True
            ).start()
    
    def on_dest_typing(self, event):
        """Handle typing in destination field for autocomplete."""
        current_text = self.dest_var.get()
        
        # Ignore certain keys that don't change the text
        if event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 
                            'Alt_L', 'Alt_R', 'Meta_L', 'Meta_R', 'Super_L', 'Super_R',
                            'Caps_Lock', 'Escape', 'Return', 'Tab'):
            return
        
        # Fetch completions whenever text changes
        if current_text:
            # Get the directory path to search
            if '/' in current_text:
                # Extract the directory part
                last_slash = current_text.rfind('/')
                dir_path = current_text[:last_slash + 1]
                prefix = current_text[last_slash + 1:]
            else:
                # No slash, search from home
                dir_path = '~/'
                prefix = current_text
            
            # Fetch paths asynchronously
            threading.Thread(
                target=self.fetch_and_filter_paths, 
                args=(dir_path, prefix), 
                daemon=True
            ).start()
    
    def fetch_and_filter_paths(self, dir_path, prefix):
        """Fetch remote paths and filter based on prefix."""
        if not self.selected_host:
            return
        
        hostname = self.selected_host['hostname'] or self.selected_host['name']
        user = self.selected_host['user']
        identity_file = self.selected_host['identity_file']
        
        # Build SSH command
        ssh_cmd = ['ssh']
        
        if identity_file and os.path.exists(identity_file):
            ssh_cmd.extend(['-i', identity_file])
        
        # Add connection options
        ssh_cmd.extend([
            '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=no'
        ])
        
        if user:
            ssh_cmd.append(f'{user}@{hostname}')
        else:
            ssh_cmd.append(hostname)
        
        # Detect if user typed path starting with ~/
        using_tilde = self.dest_var.get().startswith('~/')
        
        # Command to list directories matching prefix (without trailing slashes)
        if prefix:
            cmd = f'ls -1d {dir_path}{prefix}*/ 2>/dev/null | head -30'
        else:
            cmd = f'ls -1d {dir_path}*/ 2>/dev/null | head -30'
        
        ssh_cmd.append(cmd)
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Process paths: remove all trailing slashes and replace home dir if needed
                paths = []
                for p in result.stdout.strip().split('\n'):
                    # Remove all trailing slashes
                    p = p.strip().rstrip('/')
                    
                    # If using tilde paths and we have the remote home, replace it with ~
                    if using_tilde and p and self.remote_home:
                        if p.startswith(self.remote_home):
                            p = '~' + p[len(self.remote_home):]
                    
                    if p:  # Only add non-empty paths
                        paths.append(p + '/')  # Re-add trailing slash
                
                # Update the combo box values in the main thread
                if paths:
                    self.root.after(0, self.update_and_show_dropdown, paths)
        except Exception as e:
            print(f"Failed to fetch remote paths: {e}")
    
    def load_destination_suggestions(self):
        """Load initial destination path suggestions from remote server."""
        if not self.selected_host:
            return
        
        # Start with common directories
        self.destination_paths = ['~/']
        self.dest_combo['values'] = self.destination_paths
        self.dest_var.set('~/')
        
        # Asynchronously load actual home directory contents
        threading.Thread(target=self.fetch_remote_paths, args=('~/',), daemon=True).start()
    
    def fetch_remote_paths(self, remote_path):
        """Fetch directory listings from remote server via SSH."""
        if not self.selected_host:
            return
        
        # Track if user is using tilde paths
        using_tilde = remote_path.startswith('~/')
        
        hostname = self.selected_host['hostname'] or self.selected_host['name']
        user = self.selected_host['user']
        identity_file = self.selected_host['identity_file']
        
        # Build SSH command
        ssh_cmd = ['ssh']
        
        if identity_file and os.path.exists(identity_file):
            ssh_cmd.extend(['-i', identity_file])
        
        # Add connection options
        ssh_cmd.extend([
            '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=no'
        ])
        
        if user:
            ssh_cmd.append(f'{user}@{hostname}')
        else:
            ssh_cmd.append(hostname)
        
        # Command to list directories (only directories, not files)
        ssh_cmd.append(f'ls -1dp {remote_path}*/ 2>/dev/null | head -20')
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Process paths: remove trailing slashes and replace home dir if needed
                paths = []
                for p in result.stdout.strip().split('\n'):
                    # Remove trailing slashes
                    p = p.strip().rstrip('/')
                    
                    # If using tilde paths and we have the remote home, replace it with ~
                    if using_tilde and p and self.remote_home and p.startswith(self.remote_home):
                        p = '~' + p[len(self.remote_home):]
                    
                    if p:  # Only add non-empty paths
                        paths.append(p + '/')  # Re-add trailing slash
                
                # Update the combo box values in the main thread
                self.root.after(0, self.update_destination_values, paths)
        except Exception as e:
            print(f"Failed to fetch remote paths: {e}")
    
    def update_and_show_dropdown(self, paths):
        """Update destination combobox values and open dropdown (must be called from main thread)."""
        if paths:
            # Store cursor position before update
            cursor_pos = self.dest_combo.index(tk.INSERT)
            
            self.destination_paths = paths
            self.dest_combo['values'] = paths
            
            # Restore cursor position
            self.dest_combo.icursor(cursor_pos)
            
            # Don't auto-open dropdown - just update values
            # User can see them by clicking arrow or pressing Down key
    
    def update_destination_values(self, paths):
        """Update destination combobox values (must be called from main thread)."""
        if paths:
            self.destination_paths = paths
            self.dest_combo['values'] = paths
    
    def apply_home_replacement_to_paths(self):
        """Apply home directory replacement to existing destination paths."""
        if not self.remote_home or not self.destination_paths:
            return
        
        updated_paths = []
        for p in self.destination_paths:
            # Remove trailing slash for processing
            p = p.rstrip('/')
            
            # Skip paths that already use tilde
            if p.startswith('~'):
                updated_paths.append(p + '/')
                continue
            
            # Replace home directory with tilde
            if p.startswith(self.remote_home):
                p = '~' + p[len(self.remote_home):]
            
            updated_paths.append(p + '/')
        
        # Update the combo box with replaced paths
        self.destination_paths = updated_paths
        self.dest_combo['values'] = updated_paths
        
        # If current value needs replacement, update it too
        current = self.dest_var.get()
        if current and not current.startswith('~') and current.startswith(self.remote_home):
            new_value = '~' + current[len(self.remote_home):]
            self.dest_var.set(new_value)
    
    def update_window_size(self):
        """Update window size based on visible elements."""
        self.root.update_idletasks()
        
        # Base height for source files display, server, destination, and buttons
        # Calculate based on number of source files shown (up to 3 lines)
        source_lines = min(3, max(1, self.file_count))
        base_height = 230 + (source_lines * 17)
        
        # Add height for horizontal scrollbar (always present)
        base_height += 16
        
        # Add height for summary label
        base_height += 20
        
        # Add height for create destination checkbox
        base_height += 25
        
        # Add height for password field if visible
        if self.password_visible:
            base_height += 40
        
        self.root.geometry(f"500x{base_height}")
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def copy(self):
        """Handle copy button click."""
        if not self.server_var.get():
            messagebox.showerror("Error", "Please select a server")
            return
        
        if not self.dest_var.get():
            messagebox.showerror("Error", "Please enter a destination path")
            return
        
        self.result = {
            'host': self.selected_host,
            'destination': self.dest_var.get(),
            'password': self.password_var.get() if self.password_var.get() else None,
            'create_destination': self.create_dest_var.get()
        }
        self.root.quit()
        self.root.destroy()
    
    def cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def show(self):
        """Show dialog and return result."""
        self.root.mainloop()
        return self.result
    
    def set_file_paths(self, file_paths):
        """Set the file paths to display in the source tree."""
        self.file_paths = file_paths
        
        # Get local home directory
        local_home = os.path.expanduser('~')
        
        # Clear existing items from both trees
        for item in self.icon_tree.get_children():
            self.icon_tree.delete(item)
        for item in self.source_tree.get_children():
            self.source_tree.delete(item)
        
        # Count files and directories
        file_count = 0
        dir_count = 0
        
        # Add file paths to tree and calculate max width
        max_width = 400  # Minimum width
        max_display_length = 0  # Track longest display path
        font = ("Helvetica", 10)
        
        for idx, path in enumerate(file_paths):
            # Count files vs directories
            is_dir = os.path.isdir(path)
            if is_dir:
                dir_count += 1
                icon = '􀈕'  # Folder character
            else:
                file_count += 1
                icon = '􀈷'  # Document character
            
            # Replace local home directory with ~
            display_path = path
            if path.startswith(local_home):
                display_path = '~' + path[len(local_home):]
            
            # Track longest display path
            max_display_length = max(max_display_length, len(display_path))
            
            # Insert icon into pinned column
            self.icon_tree.insert('', 'end', text=icon)
            
            # Insert path into scrollable column
            self.source_tree.insert('', 'end', values=(display_path,))
            
            # Estimate width based on character count (rough approximation)
            estimated_width = len(display_path) * 7  # ~7 pixels per character
            max_width = max(max_width, estimated_width)
        
        # Set column width to accommodate longest path, capped at reasonable max
        self.source_tree.column('path', width=min(max_width, 2000), stretch=False)
        
        # Show or hide horizontal scrollbar based on longest path
        if max_display_length > 63:
            self.h_scrollbar.grid(row=1, column=1, sticky='ew')
        else:
            self.h_scrollbar.grid_forget()
        
        # Update summary label
        summary_parts = []
        if file_count > 0:
            summary_parts.append(f"{file_count} file" + ("s" if file_count != 1 else ""))
        if dir_count > 0:
            summary_parts.append(f"{dir_count} director" + ("ies" if dir_count != 1 else "y"))
        
        self.summary_label.config(text=", ".join(summary_parts))


def copy_files_to_server(file_paths, config):
    """Copy files to remote server using SCP."""
    host = config['host']
    destination = config['destination']
    password = config['password']
    create_destination = config.get('create_destination', False)
    
    hostname = host['hostname'] or host['name']
    user = host['user']
    identity_file = host['identity_file']
    
    # Create destination directory if requested
    if create_destination:
        # Build SSH command to create directory
        ssh_cmd = ['ssh']
        
        if identity_file and os.path.exists(identity_file):
            ssh_cmd.extend(['-i', identity_file])
        
        ssh_cmd.extend([
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10'
        ])
        
        if user:
            ssh_cmd.append(f'{user}@{hostname}')
        else:
            ssh_cmd.append(hostname)
        
        # Create directory with parent directories
        ssh_cmd.append(f'mkdir -p {destination}')
        
        try:
            if password and (not identity_file or not os.path.exists(identity_file)):
                # Use sshpass for password authentication
                sshpass_check = subprocess.run(['which', 'sshpass'], capture_output=True)
                if sshpass_check.returncode == 0:
                    ssh_cmd = ['sshpass', '-p', password] + ssh_cmd
            
            subprocess.run(ssh_cmd, capture_output=True, timeout=10, check=True)
        except Exception as e:
            print(f"Warning: Failed to create destination directory: {e}")
    
    # Build remote destination
    if user:
        remote_dest = f"{user}@{hostname}:{destination}"
    else:
        remote_dest = f"{hostname}:{destination}"
    
    # Build SCP command
    scp_cmd = ['scp', '-r']
    
    # Add identity file if available
    if identity_file and os.path.exists(identity_file):
        scp_cmd.extend(['-i', identity_file])
    
    # Add connection options
    scp_cmd.extend([
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10'
    ])
    
    # Add files
    scp_cmd.extend(file_paths)
    
    # Add destination
    scp_cmd.append(remote_dest)
    
    try:
        # If password is provided and no identity file, we need to handle password authentication
        # This is tricky with scp - we'll use expect or handle via subprocess with input
        if password and (not identity_file or not os.path.exists(identity_file)):
            # Use sshpass if available (needs to be installed)
            # Check if sshpass is available
            sshpass_check = subprocess.run(['which', 'sshpass'], capture_output=True)
            
            if sshpass_check.returncode == 0:
                # Use sshpass
                scp_cmd = ['sshpass', '-p', password] + scp_cmd
            else:
                # sshpass not available, show error
                raise Exception("Password authentication requires 'sshpass' to be installed.\n"
                              "Install with: brew install sshpass\n"
                              "Alternatively, use SSH key authentication.")
        
        # Execute SCP command
        result = subprocess.run(
            scp_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"SCP failed: {result.stderr}")
        
        return True, "Files copied successfully!"
    
    except Exception as e:
        return False, str(e)


def main():
    """Main entry point for the workflow."""
    file_paths = sys.argv[1:]

    if not file_paths:
        messagebox.showerror("Error", "No files selected")
        return
    
    # Parse SSH config
    parser = SSHConfigParser()
    hosts = parser.parse()
    
    if not hosts:
        messagebox.showerror(
            "Error",
            "No SSH hosts found in ~/.ssh/config\n\n"
            "Please configure your SSH hosts first."
        )
        return
    
    # Show dialog
    dialog = ServerCopyDialog(hosts, len(file_paths))
    dialog.set_file_paths(file_paths)
    config = dialog.show()
    
    if not config:
        print("Copy cancelled by user")
        return
    
    # Copy files
    print(f"Copying {len(file_paths)} file(s) to {config['host']['name']}:{config['destination']}")
    
    success, message = copy_files_to_server(file_paths, config)
    
    if success:
        messagebox.showinfo("Success", message)
    else:
        messagebox.showerror("Error", f"Copy failed:\n{message}")


if __name__ == "__main__":
    main()
