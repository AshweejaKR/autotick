import socket
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Any, List, Optional


class DebugServer:
    """
    Socket server running in app_main.py to handle debug requests
    """
    def __init__(self, globals_dict: Dict[str, Any], port: int = 44444):
        self.globals_dict = globals_dict
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the debug server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(1)
            self.running = True
            print(f"Debug server started on port {self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
                except socket.error:
                    break
        except Exception as e:
            print(f"Error starting debug server: {e}")
    
    def handle_client(self, client_socket):
        """Handle debug requests from client"""
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                try:
                    request = json.loads(data)
                    response = self.process_request(request)
                    client_socket.send(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    error_response = {"error": "Invalid JSON format"}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
                except Exception as e:
                    error_response = {"error": str(e)}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
        except Exception:
            pass
        finally:
            client_socket.close()
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process debug requests"""
        command = request.get('command')
        
        if command == 'list_globals':
            return self.list_global_variables()
        elif command == 'get_variable':
            var_name = request.get('variable')
            return self.get_variable_value(var_name)
        elif command == 'set_variable':
            var_name = request.get('variable')
            value = request.get('value')
            return self.set_variable_value(var_name, value)
        elif command == 'delete_variable':
            var_name = request.get('variable')
            return self.delete_variable(var_name)
        elif command == 'monitor_variable':
            var_name = request.get('variable')
            return self.monitor_variable(var_name)
        else:
            return {"error": "Unknown command"}
    
    def list_global_variables(self) -> Dict[str, Any]:
        """Get list of all global variables"""
        variables = {}
        for name, value in self.globals_dict.items():
            if not name.startswith('_') and not callable(value):
                variables[name] = {
                    'type': type(value).__name__,
                    'value': str(value)
                }
        return {"variables": variables}
    
    def get_variable_value(self, var_name: str) -> Dict[str, Any]:
        """Get value of a specific variable"""
        if var_name in self.globals_dict:
            value = self.globals_dict[var_name]
            return {
                "variable": var_name,
                "value": value,
                "type": type(value).__name__
            }
        else:
            return {"error": f"Variable '{var_name}' not found"}
    
    def set_variable_value(self, var_name: str, value: Any) -> Dict[str, Any]:
        """Set value of a specific variable"""
        if var_name in self.globals_dict:
            old_value = self.globals_dict[var_name]
            old_type = type(old_value).__name__
            
            # Try to convert value to the same type as the original
            try:
                if isinstance(old_value, bool):
                    new_value = bool(value) if not isinstance(value, str) else value.lower() in ['true', '1', 'yes']
                elif isinstance(old_value, int):
                    new_value = int(value)
                elif isinstance(old_value, float):
                    new_value = float(value)
                elif isinstance(old_value, str):
                    new_value = str(value)
                elif isinstance(old_value, list):
                    new_value = list(value) if isinstance(value, (list, tuple)) else [value]
                elif isinstance(old_value, dict):
                    new_value = dict(value) if isinstance(value, dict) else {str(value): value}
                else:
                    new_value = value
                
                self.globals_dict[var_name] = new_value
                return {
                    "success": True,
                    "variable": var_name,
                    "old_value": old_value,
                    "new_value": new_value,
                    "old_type": old_type,
                    "new_type": type(new_value).__name__
                }
            except ValueError as e:
                return {"error": f"Cannot convert value: {e}"}
        else:
            return {"error": f"Variable '{var_name}' not found"}
    
    def delete_variable(self, var_name: str) -> Dict[str, Any]:
        """Delete a specific variable"""
        if var_name in self.globals_dict:
            if var_name in ['__name__', '__file__', '__builtins__']:
                return {"error": f"Cannot delete built-in variable '{var_name}'"}
            
            old_value = self.globals_dict[var_name]
            del self.globals_dict[var_name]
            return {
                "success": True,
                "variable": var_name,
                "deleted_value": old_value
            }
        else:
            return {"error": f"Variable '{var_name}' not found"}
    
    def monitor_variable(self, var_name: str) -> Dict[str, Any]:
        """Monitor a variable (get its current value and type)"""
        return self.get_variable_value(var_name)
    
    def stop(self):
        """Stop the debug server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


class DebugClient:
    """
    Socket client to communicate with app_main.py debug server
    """
    def __init__(self, host: str = 'localhost', port: int = 44444):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self) -> bool:
        """Connect to the debug server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Failed to connect to debug server: {e}")
            return False
    
    def send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the debug server"""
        try:
            # Always try to establish a fresh connection for each request
            if self.socket:
                self.socket.close()
                self.socket = None
            
            if not self.connect():
                return None
            
            # Send request
            request_data = json.dumps(request).encode('utf-8')
            self.socket.send(request_data)
            
            # Receive response
            response_data = self.socket.recv(4096).decode('utf-8')
            response = json.loads(response_data)
            
            # Close connection after each request to avoid connection issues
            self.socket.close()
            self.socket = None
            
            return response
        except Exception as e:
            print(f"Error sending request: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return None
    
    def close(self):
        """Close the connection"""
        if self.socket:
            self.socket.close()
            self.socket = None


class DebugManager:
    """
    Debug manager that communicates with app_main.py via sockets
    """
    def __init__(self):
        self.debug_server = None
        self.debug_client = DebugClient()
    
    def start_debug_server(self, globals_dict: Dict[str, Any]):
        """Start the debug server in app_main.py"""
        self.debug_server = DebugServer(globals_dict)
        server_thread = threading.Thread(target=self.debug_server.start, daemon=True)
        server_thread.start()
        time.sleep(0.1)  # Give server time to start
        
        # Create client with the same port as server
        self.debug_client = DebugClient(port=self.debug_server.port)
    
    def list_global_variables(self) -> None:
        """1. Get the list of global variables present in app_main.py"""
        if not self.debug_client:
            print("Error: Debug client not initialized. Call start_debug_server() first.")
            return
            
        request = {"command": "list_globals"}
        response = self.debug_client.send_request(request)
        
        if response and "variables" in response:
            print("\n=== Global Variables ===")
            for var_name, var_info in response["variables"].items():
                print(f"{var_name}: {var_info['type']} = {var_info['value']}")
        elif response and "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("Failed to get variable list")
    
    def monitor_variable(self, var_name: str) -> None:
        """2. Monitor the selected variable with value and type"""
        if not self.debug_client:
            print("Error: Debug client not initialized. Call start_debug_server() first.")
            return
            
        request = {"command": "monitor_variable", "variable": var_name}
        response = self.debug_client.send_request(request)
        
        if response and "variable" in response:
            print(f"\n=== Monitoring Variable: {var_name} ===")
            print(f"Value: {response['value']}")
            print(f"Type: {response['type']}")
        elif response and "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("Failed to monitor variable")
    
    def get_variable_value(self, var_name: str) -> None:
        """3. GET the selected variable value and print"""
        if not self.debug_client:
            print("Error: Debug client not initialized. Call start_debug_server() first.")
            return
            
        request = {"command": "get_variable", "variable": var_name}
        response = self.debug_client.send_request(request)
        
        if response and "variable" in response:
            print(f"\n=== Variable Value ===")
            print(f"{var_name} = {response['value']} ({response['type']})")
        elif response and "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("Failed to get variable value")
    
    def set_variable_value(self, var_name: str, value: Any) -> None:
        """4. SET the value to the selected variable"""
        if not self.debug_client:
            print("Error: Debug client not initialized. Call start_debug_server() first.")
            return
            
        request = {"command": "set_variable", "variable": var_name, "value": value}
        response = self.debug_client.send_request(request)
        
        if response and "success" in response:
            print(f"\n=== Variable Updated ===")
            print(f"{var_name}: {response['old_value']} ({response['old_type']}) -> {response['new_value']} ({response['new_type']})")
        elif response and "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("Failed to set variable value")
    
    def delete_variable(self, var_name: str) -> None:
        """5. Delete the selected variable"""
        if not self.debug_client:
            print("Error: Debug client not initialized. Call start_debug_server() first.")
            return
            
        request = {"command": "delete_variable", "variable": var_name}
        response = self.debug_client.send_request(request)
        
        if response and "success" in response:
            print(f"\n=== Variable Deleted ===")
            print(f"Deleted {var_name} (was: {response['deleted_value']})")
        elif response and "error" in response:
            print(f"Error: {response['error']}")
        else:
            print("Failed to delete variable")
    
    def interactive_debug_menu(self):
        """Interactive menu for debugging operations"""
        print("\n=== Debug Manager ===")
        print("1. List all global variables")
        print("2. Monitor a variable")
        print("3. Get variable value")
        print("4. Set variable value")
        print("5. Delete variable")
        print("6. Exit")
        
        while True:
            try:
                choice = input("\nEnter your choice (1-6): ").strip()
                
                if choice == '1':
                    self.list_global_variables()
                elif choice == '2':
                    var_name = input("Enter variable name to monitor: ").strip()
                    self.monitor_variable(var_name)
                elif choice == '3':
                    var_name = input("Enter variable name to get: ").strip()
                    self.get_variable_value(var_name)
                elif choice == '4':
                    var_name = input("Enter variable name to set: ").strip()
                    value = input("Enter new value: ").strip()
                    # Try to evaluate the value as Python literal
                    try:
                        value = eval(value)
                    except:
                        pass  # Keep as string if evaluation fails
                    self.set_variable_value(var_name, value)
                elif choice == '5':
                    var_name = input("Enter variable name to delete: ").strip()
                    self.delete_variable(var_name)
                elif choice == '6':
                    print("Exiting debug manager...")
                    break
                else:
                    print("Invalid choice. Please enter 1-6.")
            except KeyboardInterrupt:
                print("\nExiting debug manager...")
                break
            except Exception as e:
                print(f"Error: {e}")
        
        self.debug_client.close()


class VariableMonitorWindow:
    """
    Separate window for monitoring a specific variable in real-time
    """
    def __init__(self, parent, debug_manager, var_name):
        self.parent = parent
        self.debug_manager = debug_manager
        self.var_name = var_name
        self.monitoring = False
        self.monitor_timer = None
        self.change_count = 0
        self.start_time = time.time()
        self.last_value = None
        self.last_type = None
        
        # Create the monitor window
        self.window = tk.Toplevel(parent.root)
        self.window.title(f"Monitor: {var_name}")
        self.window.geometry("500x400")
        self.window.configure(bg='#2b2b2b')
        
        # Make window stay on top
        self.window.attributes('-topmost', True)
        
        self.setup_window()
        self.start_monitoring()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_window(self):
        """Setup the monitor window layout"""
        # Title frame
        title_frame = tk.Frame(self.window, bg='#2b2b2b')
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = tk.Label(title_frame, text=f"Monitoring Variable: {self.var_name}", 
                              font=('Arial', 14, 'bold'), bg='#2b2b2b', fg='white')
        title_label.pack()
        
        # Current value frame
        value_frame = tk.LabelFrame(self.window, text="Current Value", 
                                   bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        value_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.value_label = tk.Label(value_frame, text="Loading...", 
                                   font=('Consolas', 12), bg='#2b2b2b', fg='#00ff00',
                                   wraplength=450, justify=tk.LEFT)
        self.value_label.pack(padx=10, pady=10)
        
        self.type_label = tk.Label(value_frame, text="Type: Loading...", 
                                  font=('Consolas', 10), bg='#2b2b2b', fg='#17a2b8')
        self.type_label.pack(padx=10, pady=(0, 10))
        
        # Statistics frame
        stats_frame = tk.LabelFrame(self.window, text="Statistics", 
                                   bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_label = tk.Label(stats_frame, text="Changes: 0 | Duration: 0s", 
                                   font=('Arial', 10), bg='#2b2b2b', fg='#ffc107')
        self.stats_label.pack(padx=10, pady=10)
        
        # Control frame
        control_frame = tk.Frame(self.window, bg='#2b2b2b')
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_stop_btn = tk.Button(control_frame, text="Stop Monitoring", 
                                       command=self.toggle_monitoring,
                                       bg='#dc3545', fg='white', font=('Arial', 10, 'bold'))
        self.start_stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        refresh_btn = tk.Button(control_frame, text="Refresh Now", 
                               command=self.refresh_value,
                               bg='#28a745', fg='white', font=('Arial', 10, 'bold'))
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.interval_var = tk.IntVar(value=1)
        tk.Label(control_frame, text="Interval (s):", bg='#2b2b2b', fg='white').pack(side=tk.LEFT, padx=(10, 5))
        interval_spinbox = tk.Spinbox(control_frame, from_=1, to=10, width=5,
                                     textvariable=self.interval_var,
                                     command=self.update_interval)
        interval_spinbox.pack(side=tk.LEFT)
        
        # Monitor log frame
        log_frame = tk.LabelFrame(self.window, text="Monitor Log", 
                                 bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, bg='#1e1e1e', fg='#ffff00',
                               font=('Consolas', 9), wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status bar
        self.status_label = tk.Label(self.window, text="Initializing...", 
                                    bg='#2b2b2b', fg='#28a745', font=('Arial', 9))
        self.status_label.pack(fill=tk.X, padx=10, pady=(0, 5))
    
    def log_message(self, message):
        """Add message to the monitor log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        # Keep only last 50 lines to prevent memory issues
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 50:
            self.log_text.delete("1.0", f"{len(lines) - 50}.0")
        
        self.window.update()
    
    def start_monitoring(self):
        """Start monitoring the variable"""
        self.monitoring = True
        self.log_message(f"Started monitoring variable: {self.var_name}")
        self.status_label.config(text="Monitoring active", fg='#28a745')
        self.start_stop_btn.config(text="Stop Monitoring", bg='#dc3545')
        self.monitor_loop()
    
    def stop_monitoring(self):
        """Stop monitoring the variable"""
        self.monitoring = False
        if self.monitor_timer:
            self.window.after_cancel(self.monitor_timer)
            self.monitor_timer = None
        
        duration = int(time.time() - self.start_time)
        self.log_message(f"Stopped monitoring. Total changes: {self.change_count}, Duration: {duration}s")
        self.status_label.config(text="Monitoring stopped", fg='#6c757d')
        self.start_stop_btn.config(text="Start Monitoring", bg='#28a745')
    
    def toggle_monitoring(self):
        """Toggle monitoring on/off"""
        if self.monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def update_interval(self):
        """Update monitoring interval"""
        if self.monitoring:
            self.log_message(f"Updated monitoring interval to {self.interval_var.get()}s")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        if not self.monitoring:
            return
        
        try:
            request = {"command": "get_variable", "variable": self.var_name}
            response = self.debug_manager.debug_client.send_request(request)
            
            if response and "variable" in response:
                current_value = response['value']
                current_type = response['type']
                
                # Update display
                self.value_label.config(text=str(current_value))
                self.type_label.config(text=f"Type: {current_type}")
                
                # Check for changes
                if self.last_value is not None:
                    if current_value != self.last_value or current_type != self.last_type:
                        self.change_count += 1
                        self.log_message(f"CHANGED: {self.last_value} ({self.last_type}) → {current_value} ({current_type})")
                        
                        # Flash the value label to indicate change
                        original_bg = self.value_label.cget('bg')
                        self.value_label.config(bg='#ff6b6b')
                        self.window.after(200, lambda: self.value_label.config(bg=original_bg))
                
                # Update stored values
                self.last_value = current_value
                self.last_type = current_type
                
                # Update statistics
                duration = int(time.time() - self.start_time)
                self.stats_label.config(text=f"Changes: {self.change_count} | Duration: {duration}s")
                
                self.status_label.config(text=f"Last update: {time.strftime('%H:%M:%S')}", fg='#28a745')
                
            elif response and "error" in response:
                if "not found" in response['error'].lower():
                    self.log_message(f"ERROR: Variable '{self.var_name}' was deleted from main application")
                    self.value_label.config(text="VARIABLE DELETED", fg='#dc3545')
                    self.type_label.config(text="Type: N/A")
                    self.status_label.config(text="Variable no longer exists", fg='#dc3545')
                else:
                    self.log_message(f"ERROR: {response['error']}")
                    self.status_label.config(text="Error occurred", fg='#dc3545')
            else:
                self.log_message("ERROR: Failed to get variable value")
                self.status_label.config(text="Connection error", fg='#dc3545')
        
        except Exception as e:
            self.log_message(f"ERROR: {str(e)}")
            self.status_label.config(text="Exception occurred", fg='#dc3545')
        
        # Schedule next update
        if self.monitoring:
            interval = self.interval_var.get() * 1000  # Convert to milliseconds
            self.monitor_timer = self.window.after(interval, self.monitor_loop)
    
    def refresh_value(self):
        """Manually refresh the variable value"""
        self.log_message("Manual refresh requested")
        if not self.monitoring:
            # If not monitoring, do a one-time refresh
            try:
                request = {"command": "get_variable", "variable": self.var_name}
                response = self.debug_manager.debug_client.send_request(request)
                
                if response and "variable" in response:
                    self.value_label.config(text=str(response['value']))
                    self.type_label.config(text=f"Type: {response['type']}")
                    self.status_label.config(text=f"Refreshed: {time.strftime('%H:%M:%S')}", fg='#28a745')
                    self.log_message(f"Manual refresh: {response['value']} ({response['type']})")
                elif response and "error" in response:
                    self.log_message(f"Refresh error: {response['error']}")
            except Exception as e:
                self.log_message(f"Refresh exception: {str(e)}")
    
    def on_closing(self):
        """Handle window closing"""
        self.stop_monitoring()
        
        # Remove from parent's monitor windows dict
        if self.var_name in self.parent.monitor_windows:
            del self.parent.monitor_windows[self.var_name]
        
        self.window.destroy()


class DebugManagerGUI:
    """
    GUI interface for the Debug Manager using tkinter
    """
    def __init__(self):
        self.debug_manager = DebugManager()
        # Try to connect to the running main.py on common ports (44444, 44445, etc.)
        self.debug_manager.debug_client = self._connect_to_debug_server()
        
        self.root = tk.Tk()
        self.root.title("Debug Manager - Variable Inspector")
        self.root.geometry("800x600")
        self.root.configure(bg='#2b2b2b')
        
        # Variables for GUI
        self.selected_variable = tk.StringVar()
        self.auto_refresh = tk.BooleanVar(value=False)
        self.refresh_interval = tk.IntVar(value=2)
        self.monitor_windows = {}  # Dict to store monitor windows
        
        self.setup_gui()
        self.refresh_variables()
        
    def _connect_to_debug_server(self):
        """Try to connect to debug server on common ports"""
        ports_to_try = [44444, 44445, 44446, 44447, 44448]
        
        for port in ports_to_try:
            try:
                client = DebugClient(port=port)
                if client.connect():
                    print(f"Connected to debug server on port {port}")
                    client.close()  # Close test connection
                    return DebugClient(port=port)  # Return new client instance
            except Exception:
                continue
        
        print("Warning: Could not connect to any debug server. Make sure main.py is running.")
        return None
        
    def setup_gui(self):
        """Setup the GUI layout"""
        # Main frame
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="Debug Manager - Variable Inspector", 
                              font=('Arial', 16, 'bold'), bg='#2b2b2b', fg='white')
        title_label.pack(pady=(0, 10))
        
        # Top control frame
        control_frame = tk.Frame(main_frame, bg='#2b2b2b')
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Refresh button
        refresh_btn = tk.Button(control_frame, text="Refresh Variables", 
                               command=self.refresh_variables,
                               bg='#4a9eff', fg='white', font=('Arial', 10, 'bold'))
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-refresh checkbox
        auto_refresh_cb = tk.Checkbutton(control_frame, text="Auto Refresh", 
                                        variable=self.auto_refresh,
                                        command=self.toggle_auto_refresh,
                                        bg='#2b2b2b', fg='white', selectcolor='#4a9eff')
        auto_refresh_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh interval
        tk.Label(control_frame, text="Interval (s):", bg='#2b2b2b', fg='white').pack(side=tk.LEFT)
        interval_spinbox = tk.Spinbox(control_frame, from_=1, to=10, width=5,
                                     textvariable=self.refresh_interval)
        interval_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Variables list frame
        list_frame = tk.LabelFrame(main_frame, text="Global Variables", 
                                  bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for variables
        columns = ('Variable', 'Type', 'Value')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configure column headings
        self.tree.heading('Variable', text='Variable Name')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Value', text='Value')
        
        # Configure column widths
        self.tree.column('Variable', width=200)
        self.tree.column('Type', width=100)
        self.tree.column('Value', width=400)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click event
        self.tree.bind('<Double-1>', self.on_variable_select)
        
        # Action buttons frame
        button_frame = tk.Frame(main_frame, bg='#2b2b2b')
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Action buttons
        monitor_btn = tk.Button(button_frame, text="Monitor Variable", 
                               command=self.monitor_selected_variable,
                               bg='#28a745', fg='white', font=('Arial', 10, 'bold'))
        monitor_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        get_btn = tk.Button(button_frame, text="Get Value", 
                           command=self.get_selected_variable_value,
                           bg='#17a2b8', fg='white', font=('Arial', 10, 'bold'))
        get_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        set_btn = tk.Button(button_frame, text="Set Value", 
                           command=self.set_selected_variable,
                           bg='#ffc107', fg='black', font=('Arial', 10, 'bold'))
        set_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        delete_btn = tk.Button(button_frame, text="Delete Variable", 
                              command=self.delete_selected_variable,
                              bg='#dc3545', fg='white', font=('Arial', 10, 'bold'))
        delete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        close_monitors_btn = tk.Button(button_frame, text="Close All Monitors", 
                                      command=self.close_all_monitors,
                                      bg='#6c757d', fg='white', font=('Arial', 10, 'bold'))
        close_monitors_btn.pack(side=tk.LEFT)
        
        # Status frame
        status_frame = tk.Frame(main_frame, bg='#2b2b2b')
        status_frame.pack(fill=tk.X)
        
        # Status label
        self.status_label = tk.Label(status_frame, text="Ready", 
                                    bg='#2b2b2b', fg='#28a745', font=('Arial', 10))
        self.status_label.pack(anchor=tk.W)
        
        # Output text area
        output_frame = tk.LabelFrame(main_frame, text="Debug Output", 
                                    bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.output_text = tk.Text(output_frame, height=8, bg='#1e1e1e', fg='#00ff00',
                                  font=('Consolas', 10), wrap=tk.WORD)
        output_scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, 
                                        command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Auto-refresh timer
        self.auto_refresh_timer = None
        
    def log_output(self, message: str):
        """Add message to output text area"""
        timestamp = time.strftime("%H:%M:%S")
        self.output_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.output_text.see(tk.END)
        self.root.update()
        
    def update_status(self, message: str, color: str = '#28a745'):
        """Update status label"""
        self.status_label.config(text=message, fg=color)
        self.root.update()
        
    def refresh_variables(self):
        """Refresh the variables list"""
        try:
            self.update_status("Refreshing variables...", '#ffc107')
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Check if debug client is initialized
            if not self.debug_manager.debug_client:
                self.update_status("Debug client not connected", '#dc3545')
                self.log_output("Error: Debug client not initialized. Try connecting to main.py first.")
                return
            
            # Get variables from debug manager
            request = {"command": "list_globals"}
            response = self.debug_manager.debug_client.send_request(request)
            
            if response and "variables" in response:
                for var_name, var_info in response["variables"].items():
                    # Add monitor indicator if window is open
                    display_name = var_name
                    if var_name in self.monitor_windows:
                        display_name = f"📊 {var_name}"  # Add monitor icon
                    
                    self.tree.insert('', tk.END, values=(display_name, var_info['type'], var_info['value']))
                
                self.update_status(f"Found {len(response['variables'])} variables")
                
                # Update status with monitor count
                if self.monitor_windows:
                    monitor_count = len(self.monitor_windows)
                    self.log_output(f"Refreshed {len(response['variables'])} variables ({monitor_count} monitored)")
                else:
                    self.log_output(f"Refreshed {len(response['variables'])} global variables")
            elif response and "error" in response:
                self.update_status(f"Error: {response['error']}", '#dc3545')
                self.log_output(f"Error: {response['error']}")
            else:
                self.update_status("Failed to connect to debug server", '#dc3545')
                self.log_output("Failed to connect to debug server. Make sure app_main.py is running.")
                
        except Exception as e:
            self.update_status(f"Error: {str(e)}", '#dc3545')
            self.log_output(f"Error refreshing variables: {str(e)}")
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality"""
        if self.auto_refresh.get():
            self.start_auto_refresh()
            self.log_output("Auto-refresh enabled")
        else:
            self.stop_auto_refresh()
            self.log_output("Auto-refresh disabled")
    
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.auto_refresh_timer:
            self.root.after_cancel(self.auto_refresh_timer)
        
        def auto_refresh_loop():
            if self.auto_refresh.get():
                self.refresh_variables()
                self.auto_refresh_timer = self.root.after(self.refresh_interval.get() * 1000, auto_refresh_loop)
        
        auto_refresh_loop()
    
    def stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        if self.auto_refresh_timer:
            self.root.after_cancel(self.auto_refresh_timer)
            self.auto_refresh_timer = None
    
    def get_selected_variable(self):
        """Get the currently selected variable name"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a variable from the list.")
            return None
        
        item = self.tree.item(selection[0])
        if item['values']:
            var_name = item['values'][0]
            # Remove monitor indicator if present
            if var_name.startswith('📊 '):
                var_name = var_name[2:]  # Remove the emoji and space
            return var_name
        return None
    
    def on_variable_select(self, event):
        """Handle double-click on variable"""
        var_name = self.get_selected_variable()
        if var_name:
            self.monitor_variable_by_name(var_name)
    
    def monitor_selected_variable(self):
        """Monitor the selected variable"""
        var_name = self.get_selected_variable()
        if var_name:
            self.monitor_variable_by_name(var_name)
    
    def monitor_variable_by_name(self, var_name: str):
        """Create a monitor window for the specified variable"""
        if not self.debug_manager.debug_client:
            self.log_output("Error: Debug client not connected. Cannot monitor variable.")
            self.update_status("Debug client not connected", '#dc3545')
            return
            
        # Check if variable exists first
        try:
            request = {"command": "monitor_variable", "variable": var_name}
            response = self.debug_manager.debug_client.send_request(request)
            
            if response and "variable" in response:
                # Check if already monitoring this variable
                if var_name in self.monitor_windows:
                    # Bring existing window to front
                    self.monitor_windows[var_name].window.lift()
                    self.monitor_windows[var_name].window.focus_force()
                    self.log_output(f"Monitor window for '{var_name}' already exists - brought to front")
                    return
                
                # Create new monitor window
                monitor_window = VariableMonitorWindow(self, self.debug_manager, var_name)
                self.monitor_windows[var_name] = monitor_window
                
                self.log_output(f"Created monitor window for variable: {var_name}")
                self.update_status(f"Monitoring: {var_name}")
                
            elif response and "error" in response:
                self.log_output(f"Error creating monitor for {var_name}: {response['error']}")
                self.update_status(f"Error: {response['error']}", '#dc3545')
                messagebox.showerror("Error", f"Cannot monitor variable '{var_name}':\n{response['error']}")
                
        except Exception as e:
            error_msg = f"Error creating monitor window: {str(e)}"
            self.log_output(error_msg)
            self.update_status("Monitor error", '#dc3545')
            messagebox.showerror("Error", error_msg)
    
    def close_all_monitors(self):
        """Close all monitor windows"""
        if not self.monitor_windows:
            messagebox.showinfo("No Monitors", "No monitor windows are currently open.")
            return
        
        count = len(self.monitor_windows)
        monitor_names = list(self.monitor_windows.keys())
        
        # Close all monitor windows
        for monitor_window in list(self.monitor_windows.values()):
            monitor_window.on_closing()
        
        self.log_output(f"Closed {count} monitor windows: {', '.join(monitor_names)}")
        messagebox.showinfo("Monitors Closed", f"Closed {count} monitor window(s).")
    
    def get_selected_variable_value(self):
        """Get the value of the selected variable"""
        var_name = self.get_selected_variable()
        if var_name:
            if not self.debug_manager.debug_client:
                self.log_output("Error: Debug client not connected. Cannot get variable value.")
                self.update_status("Debug client not connected", '#dc3545')
                return
                
            try:
                request = {"command": "get_variable", "variable": var_name}
                response = self.debug_manager.debug_client.send_request(request)
                
                if response and "variable" in response:
                    message = f"Got {var_name}: {response['value']} ({response['type']})"
                    self.log_output(message)
                    self.update_status(f"Retrieved: {var_name}")
                    
                    # Show value in popup
                    info = f"Variable: {var_name}\nType: {response['type']}\nValue: {response['value']}"
                    messagebox.showinfo("Variable Value", info)
                    
                elif response and "error" in response:
                    self.log_output(f"Error getting {var_name}: {response['error']}")
                    messagebox.showerror("Error", response['error'])
                    
            except Exception as e:
                error_msg = f"Error getting variable value: {str(e)}"
                self.log_output(error_msg)
                messagebox.showerror("Error", error_msg)
    
    def set_selected_variable(self):
        """Set the value of the selected variable"""
        var_name = self.get_selected_variable()
        if var_name:
            if not self.debug_manager.debug_client:
                self.log_output("Error: Debug client not connected. Cannot set variable value.")
                self.update_status("Debug client not connected", '#dc3545')
                return
                
            # Get new value from user
            new_value = simpledialog.askstring("Set Variable Value", 
                                              f"Enter new value for '{var_name}':")
            
            if new_value is not None:
                try:
                    # Try to evaluate as Python literal
                    try:
                        evaluated_value = eval(new_value)
                    except:
                        evaluated_value = new_value  # Keep as string if evaluation fails
                    
                    request = {"command": "set_variable", "variable": var_name, "value": evaluated_value}
                    response = self.debug_manager.debug_client.send_request(request)
                    
                    if response and "success" in response:
                        message = f"Set {var_name}: {response['old_value']} -> {response['new_value']}"
                        self.log_output(message)
                        self.update_status(f"Updated: {var_name}")
                        
                        # Refresh the variables list
                        self.refresh_variables()
                        
                        # Show success message
                        info = f"Variable: {var_name}\nOld: {response['old_value']} ({response['old_type']})\nNew: {response['new_value']} ({response['new_type']})"
                        messagebox.showinfo("Variable Updated", info)
                        
                    elif response and "error" in response:
                        self.log_output(f"Error setting {var_name}: {response['error']}")
                        messagebox.showerror("Error", response['error'])
                        
                except Exception as e:
                    error_msg = f"Error setting variable value: {str(e)}"
                    self.log_output(error_msg)
                    messagebox.showerror("Error", error_msg)
    
    def delete_selected_variable(self):
        """Delete the selected variable"""
        var_name = self.get_selected_variable()
        if var_name:
            if not self.debug_manager.debug_client:
                self.log_output("Error: Debug client not connected. Cannot delete variable.")
                self.update_status("Debug client not connected", '#dc3545')
                return
                
            # Confirm deletion
            if messagebox.askyesno("Confirm Deletion", 
                                  f"Are you sure you want to delete variable '{var_name}'?"):
                try:
                    request = {"command": "delete_variable", "variable": var_name}
                    response = self.debug_manager.debug_client.send_request(request)
                    
                    if response and "success" in response:
                        message = f"Deleted {var_name} (was: {response['deleted_value']})"
                        self.log_output(message)
                        self.update_status(f"Deleted: {var_name}")
                        
                        # Refresh the variables list
                        self.refresh_variables()
                        
                        messagebox.showinfo("Variable Deleted", f"Variable '{var_name}' has been deleted.")
                        
                    elif response and "error" in response:
                        self.log_output(f"Error deleting {var_name}: {response['error']}")
                        messagebox.showerror("Error", response['error'])
                        
                except Exception as e:
                    error_msg = f"Error deleting variable: {str(e)}"
                    self.log_output(error_msg)
                    messagebox.showerror("Error", error_msg)
    
    def run(self):
        """Start the GUI application"""
        self.log_output("Debug Manager GUI started")
        self.log_output("Make sure app_main.py is running for debugging to work")
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
    
    def on_closing(self):
        """Handle application closing"""
        self.stop_auto_refresh()
        
        # Close all monitor windows
        for monitor_window in list(self.monitor_windows.values()):
            monitor_window.on_closing()
        
        # Safely close debug client if it exists
        if self.debug_manager.debug_client:
            self.debug_manager.debug_client.close()
        
        self.root.destroy()


# Example usage when running debug_mngr.py directly
if __name__ == "__main__":
    import sys
    
    print("Debug Manager - Choose Interface:")
    print("1. GUI Interface (default)")
    print("2. Command Line Interface")
    
    choice = input("Enter choice (1-3) or press Enter for GUI: ").strip()
    
    if choice == '2':
        # Command Line Interface
        print("\nStarting Debug Manager Command Line Client...")
        print("Make sure app_main.py is running first!")
        
        time.sleep(2)  # Wait for server to be ready
        
        debug_manager = DebugManager()
        debug_manager.interactive_debug_menu()
        
    elif choice == '3':
        # Programmatic example
        print("\nStarting Programmatic Debug Example...")
        print("Make sure app_main.py is running first!")
        
        time.sleep(2)  # Wait for server to be ready
        #TODO: Need to update for test
        
    else:
        # GUI Interface (default)
        print("\nStarting Debug Manager GUI...")
        print("Make sure app_main.py is running first!")
        
        try:
            gui = DebugManagerGUI()
            gui.run()
        except ImportError:
            print("Error: tkinter not available. Falling back to command line interface.")
            time.sleep(2)
            debug_manager = DebugManager()
            debug_manager.interactive_debug_menu()
        except Exception as e:
            print(f"Error starting GUI: {e}")
            print("Falling back to command line interface.")
            time.sleep(2)
            debug_manager = DebugManager()
            debug_manager.interactive_debug_menu()

# # Usage for this debug_mngr
# from debug_mngr import DebugManager
# import threading
# debug_mngr = DebugManager()
# debug_mngr.start_debug_server(globals())