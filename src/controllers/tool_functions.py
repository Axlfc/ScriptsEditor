import json
import multiprocessing
import os
import queue
import re
import subprocess
import threading
import math
import cmath
from tkinter import (colorchooser, END, Toplevel, Label, Entry, Button, scrolledtext, IntVar, Menu, StringVar, \
    messagebox, OptionMenu, Checkbutton, Scrollbar, Canvas, Frame, font, filedialog, Listbox, simpledialog, Text, \
                     DISABLED, NORMAL, SUNKEN, W, BOTH, LEFT, SINGLE, X, RAISED, WORD, RIGHT, Y, BooleanVar, VERTICAL, \
                     BOTTOM)

import webview  # pywebview
from datetime import datetime

from tkinter.ttk import Separator, Treeview, Notebook, Combobox
import markdown
from PIL import ImageTk
from PIL.Image import Image
from tkhtmlview import HTMLLabel

from src.controllers.parameters import read_config_parameter, write_config_parameter
from src.views.tk_utils import text, script_text, root, style, current_session
from src.controllers.utility_functions import make_tag
from src.views.ui_elements import Tooltip, ScrollableFrame

from src.models.ai_assistant import find_gguf_file
from src.views.edit_operations import cut, copy, paste, duplicate

from lib.git import git_icons


# Global variable to hold the Git Console window instance
git_console_instance = None


def load_themes_from_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get('themes', [])
    except FileNotFoundError:
        messagebox.showerror("Error", "Themes file not found.")
        return []
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Error decoding themes file.")
        return []


def change_color():
    """
        Changes the text color in the application's text widget.

        This function opens a color chooser dialog, allowing the user to select a new color for the text.
        It then applies this color to the text within the text widget.

        Parameters:
        None

        Returns:
        None
    """
    color = colorchooser.askcolor(initialcolor='#ff0000')
    color_name = color[1]
    global fontColor
    fontColor = color_name
    current_tags = text.tag_names()
    if "font_color_change" in current_tags:
        # first char is bold, so unbold the range
        text.tag_delete("font_color_change", 1.0, END)
    else:
        # first char is normal, so bold the whole selection
        text.tag_add("font_color_change", 1.0, END)
    make_tag()


def colorize_text():
    """
        Applies color to the text in the script text widget.

        This function retrieves the current content of the script text widget, deletes it, and reinserts it,
        applying the currently selected color.

        Parameters:
        None

        Returns:
        None
    """
    script_content = script_text.get("1.0", "end")
    script_text.delete("1.0", "end")
    script_text.insert("1.0", script_content)


def check(value):
    """
        Highlights all occurrences of a specified value in the script text widget.

        This function searches for the given value in the script text widget and applies a 'found' tag with a
        yellow background to each occurrence.

        Parameters:
        value (str): The string to be searched for in the text widget.

        Returns:
        None
    """
    script_text.tag_remove('found', '1.0', END)

    if value:
        script_text.tag_config('found', background='yellow')
        idx = '1.0'
        while idx:
            idx = script_text.search(value, idx, nocase=1, stopindex=END)
            if idx:
                lastidx = f"{idx}+{len(value)}c"
                script_text.tag_add('found', idx, lastidx)
                idx = lastidx


def search_and_replace(search_text, replace_text):
    """
        Replaces all occurrences of a specified search text with a replacement text in the script text widget.

        This function finds each occurrence of the search text and replaces it with the provided replacement text.

        Parameters:
        search_text (str): The text to be replaced.
        replace_text (str): The text to replace the search text.

        Returns:
        None
    """
    if search_text:
        start_index = '1.0'
        while True:
            start_index = script_text.search(search_text, start_index, nocase=1, stopindex=END)
            if not start_index:
                break
            end_index = f"{start_index}+{len(search_text)}c"
            script_text.delete(start_index, end_index)
            script_text.insert(start_index, replace_text)
            start_index = end_index


def find_text(event=None):
    """
        Opens a dialog for finding text within the script text widget.

        This function creates a new window with an entry field where the user can input a text string
        to find in the script text widget.

        Parameters:
        event (Event, optional): The event that triggered this function.

        Returns:
        None
    """
    search_toplevel = Toplevel(root)
    search_toplevel.title('Find Text')
    search_toplevel.transient(root)
    search_toplevel.resizable(False, False)
    Label(search_toplevel, text="Find All:").grid(row=0, column=0, sticky='e')
    search_entry_widget = Entry(search_toplevel, width=25)
    search_entry_widget.grid(row=0, column=1, padx=2, pady=2, sticky='we')
    search_entry_widget.focus_set()
    Button(search_toplevel,
           text="Ok",
           underline=0,
           command=lambda: check(search_entry_widget.get())).grid(row=0,
                                                                  column=2,
                                                                  sticky='e' + 'w',
                                                                  padx=2,
                                                                  pady=5
                                                                  )
    Button(search_toplevel,
           text="Cancel",
           underline=0,
           command=lambda: find_text_cancel_button(search_toplevel)).grid(row=0,
                                                                          column=4,
                                                                          sticky='e' + 'w',
                                                                          padx=2,
                                                                          pady=2
                                                                          )


# remove search tags and destroys the search box
def find_text_cancel_button(search_toplevel):
    """
        Removes search highlights and closes the search dialog.

        This function is called to close the search dialog and remove any search highlights
        from the text widget.

        Parameters:
        search_toplevel (Toplevel): The top-level widget of the search dialog.

        Returns:
        None
    """
    text.tag_remove('found', '1.0', END)
    search_toplevel.destroy()
    return "break"


def open_search_replace_dialog():
    """
        Opens a dialog for searching and replacing text within the script text widget.

        This function creates a new window with fields for inputting the search and replace texts
        and a button to execute the replacement.

        Parameters:
        None

        Returns:
        None
    """
    search_replace_toplevel = Toplevel(root)
    search_replace_toplevel.title('Search and Replace')
    search_replace_toplevel.transient(root)
    search_replace_toplevel.resizable(False, False)

    # Campo de búsqueda
    Label(search_replace_toplevel, text="Find:").grid(row=0, column=0, sticky='e')
    search_entry_widget = Entry(search_replace_toplevel, width=25)
    search_entry_widget.grid(row=0, column=1, padx=2, pady=2, sticky='we')

    # Campo de reemplazo
    Label(search_replace_toplevel, text="Replace:").grid(row=1, column=0, sticky='e')
    replace_entry_widget = Entry(search_replace_toplevel, width=25)
    replace_entry_widget.grid(row=1, column=1, padx=2, pady=2, sticky='we')

    # Botones
    Button(
        search_replace_toplevel,
        text="Replace All",
        command=lambda: search_and_replace(search_entry_widget.get(),
                                           replace_entry_widget.get())).grid(row=2,
                                                                             column=1,
                                                                             sticky='e' + 'w',
                                                                             padx=2,
                                                                             pady=5
                                                                             )


def open_ipynb_window():
    print("OPEN IPYTHON TERMINAL")


def create_settings_window():
    settings_window = Toplevel()
    settings_window.title("ScriptsEditor Settings")
    settings_window.geometry("800x600")

    default_config_file = "data/config.json"
    user_config_file = "data/user_config.json"

    if os.path.exists(user_config_file):
        config_file_to_use = user_config_file
    else:
        config_file_to_use = default_config_file

    try:
        with open(config_file_to_use, 'r') as config_file:
            config_data = json.load(config_file)
    except FileNotFoundError:
        messagebox.showerror("Error", f"Config file ({config_file_to_use}) not found.")
        return
    except json.JSONDecodeError:
        messagebox.showerror("Error", f"Error decoding config file ({config_file_to_use}).")
        return

    # Main frame
    main_frame = Frame(settings_window)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Notebook
    notebook = Notebook(main_frame)
    notebook.pack(fill=BOTH, expand=True)

    # Bottom frame for buttons
    bottom_frame = Frame(settings_window)
    bottom_frame.pack(fill=X, side=BOTTOM, padx=10, pady=10)

    setting_entries = {}

    for section, options in config_data['options'].items():
        # Create a frame for each section
        section_frame = Frame(notebook)
        notebook.add(section_frame, text=section.capitalize())

        # Create a scrollable frame
        scrollable_frame = ScrollableFrame(section_frame)
        scrollable_frame.pack(fill=BOTH, expand=True)

        # Populate the scrollable frame with settings
        for row, (option_name, default_value) in enumerate(options.items()):
            label = Label(scrollable_frame.scrollable_frame, text=option_name.replace('_', ' ').capitalize())
            label.grid(row=row, column=0, padx=5, pady=5, sticky="w")

            if option_name.lower() == 'font_family':
                font_families = font.families()
                default_font = default_value if default_value in font_families else 'Courier New'
                var = StringVar(value=default_font)
                widget = Combobox(scrollable_frame.scrollable_frame, textvariable=var, values=font_families)
            elif option_name.lower() == 'theme':
                # Load themes
                themes = load_themes_from_json("data/themes.json")
                default_theme = default_value if default_value in themes else themes[0]
                var = StringVar(value=default_theme)
                widget = Combobox(scrollable_frame.scrollable_frame, textvariable=var, values=themes)
            elif isinstance(default_value, bool):
                var = BooleanVar(value=default_value)
                widget = Checkbutton(scrollable_frame.scrollable_frame, variable=var)
            elif isinstance(default_value, (str, int)):
                var = StringVar(value=str(default_value))
                widget = Entry(scrollable_frame.scrollable_frame, textvariable=var)
            else:
                continue  # Skip unsupported types

            widget.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
            scrollable_frame.scrollable_frame.grid_columnconfigure(1, weight=1)
            setting_entries[(section, option_name)] = var

    def save_settings():
        print("Save Settings Button Pressed")
        global style  # Ensure style is accessible
        updated_config_data = {'options': {}}
        for (section, option_name), var in setting_entries.items():
            value = var.get()
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            updated_config_data['options'].setdefault(section, {})[option_name] = value

        with open(user_config_file, 'w') as user_config:
            json.dump(updated_config_data, user_config, indent=4)

        # Apply the theme if it was changed
        theme = updated_config_data['options'].get('theme_appearance', {}).get('theme', None)
        if theme:
            try:
                style.theme_use(theme)
            except Exception as e:
                messagebox.showerror("Theme Error", f"The theme '{theme}' is not available. ({e})")

        messagebox.showinfo("Settings Saved", "Settings saved successfully!")

        # TO-DO: Reload main app GUI

    def reset_settings():
        global style  # Ensure style is accessible
        for (section, option_name), var in setting_entries.items():
            default_value = config_data['options'][section][option_name]
            if isinstance(var, BooleanVar):
                var.set(default_value)
            elif isinstance(var, StringVar):
                var.set(str(default_value))

        if os.path.exists(user_config_file):
            os.remove(user_config_file)

        # Reset theme to default
        default_theme = config_data['options'].get('theme_appearance', {}).get('theme', 'default')
        print("DEFAULT THEME:\t", default_theme)
        try:
            style.theme_use(default_theme)
        except Exception as e:
            messagebox.showerror("Theme Error", f"The default theme '{default_theme}' is not available. ({e}")

        messagebox.showinfo("Reset Settings", "Settings reset to defaults. User configuration file deleted.")

    # Save and Reset buttons
    save_button = Button(bottom_frame, text="Save Settings", command=save_settings)
    save_button.pack(side=LEFT, padx=5)

    reset_button = Button(bottom_frame, text="Reset Settings", command=reset_settings)
    reset_button.pack(side=LEFT, padx=5)

    return settings_window


def open_system_info_window():
    # Create the main window
    system_info_window = Toplevel()
    system_info_window.title("System Information Viewer")
    system_info_window.geometry("800x600")

    # Create a notebook (tabbed interface)
    notebook = Notebook(system_info_window)
    notebook.pack(expand=True, fill='both', padx=10, pady=10)

    # Function to execute PowerShell commands and fetch results
    def run_command(command, result_queue, label):
        try:
            powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            full_command = f'"{powershell_path}" -Command "{command}"'
            result = subprocess.run(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode == 0:
                output = result.stdout.strip()
            else:
                output = f"Error: {result.stderr.strip()}"
        except Exception as e:
            output = f"Error: {str(e)}"

        # Put the result in the queue with the associated label
        result_queue.put((label, output))

    # Worker thread function
    def worker(commands, result_queue):
        for label, cmd in commands.items():
            run_command(cmd, result_queue, label)

    # Function to create a frame with a treeview
    def create_info_frame(parent, commands):
        frame = Frame(parent)
        frame.pack(fill='both', expand=True)

        # Create a treeview
        tree = Treeview(frame, columns=('Value',), show='tree')
        tree.heading('#0', text='Property')
        tree.column('#0', width=250)
        tree.heading('Value', text='Value')
        tree.column('Value', width=500)
        tree.pack(side='left', fill='both', expand=True)

        # Add a scrollbar
        scrollbar = Scrollbar(frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)

        # Initialize the queue and start the worker thread
        result_queue = queue.Queue()
        thread = threading.Thread(target=worker, args=(commands, result_queue))
        thread.daemon = True  # Daemonize thread
        thread.start()

        # Dictionary to hold tree items for quick access
        tree_items = {}

        # Function to process the queue and update the treeview
        def process_queue():
            while not result_queue.empty():
                label, result = result_queue.get()
                # Handle multi-line outputs
                if '\n' in result:
                    if label not in tree_items:
                        parent_item = tree.insert('', 'end', text=label)
                        tree_items[label] = parent_item
                    else:
                        parent_item = tree_items[label]
                        tree.delete(*tree.get_children(parent_item))
                    for line in result.splitlines():
                        tree.insert(parent_item, 'end', text='', values=(line,))
                else:
                    if label in tree_items:
                        tree.item(tree_items[label], values=(result,))
                    else:
                        item_id = tree.insert('', 'end', text=label, values=(result,))
                        tree_items[label] = item_id
            # Schedule the next queue check
            frame.after(100, process_queue)  # Check every 100 milliseconds

        # Start processing the queue
        process_queue()

        return frame

    # System Information commands
    system_commands = {
        "Hostname": "$env:COMPUTERNAME",
        "Operating System": "(Get-CimInstance Win32_OperatingSystem).Caption",
        "OS Version": "(Get-CimInstance Win32_OperatingSystem).Version",
        "Build Number": "(Get-CimInstance Win32_OperatingSystem).BuildNumber",
        "System Architecture": "(Get-CimInstance Win32_OperatingSystem).OSArchitecture",
        "Manufacturer": "(Get-CimInstance Win32_ComputerSystem).Manufacturer",
        "Model": "(Get-CimInstance Win32_ComputerSystem).Model",
        "Serial Number": "(Get-CimInstance Win32_BIOS).SerialNumber",
        "BIOS Version": "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion",
        "System Uptime": "(New-TimeSpan -Start (Get-CimInstance "
                         "Win32_OperatingSystem).LastBootUpTime).ToString()",
        "Current System Time": "Get-Date",
        "Timezone": "(Get-TimeZone).DisplayName",
    }

    # Hardware Information commands
    hardware_commands = {
        # CPU Information
        "CPU Model": "(Get-CimInstance Win32_Processor).Name",
        "CPU Manufacturer": "(Get-CimInstance Win32_Processor).Manufacturer",
        "CPU Clock Speed (MHz)": "(Get-CimInstance Win32_Processor).MaxClockSpeed",
        "CPU Cores": "(Get-CimInstance Win32_Processor).NumberOfCores",
        "CPU Logical Processors": "(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors",
        "L2 Cache Size (KB)": "(Get-CimInstance Win32_Processor).L2CacheSize",
        "L3 Cache Size (KB)": "(Get-CimInstance Win32_Processor).L3CacheSize",
        # Memory Information
        "Total Installed Memory (GB)": "('{0:N2}' -f ((Get-CimInstance "
                                       "Win32_ComputerSystem).TotalPhysicalMemory / 1GB))",
        "Available Memory (GB)": "('{0:N2}' -f ((Get-CimInstance "
                                  "Win32_OperatingSystem).FreePhysicalMemory / 1MB / 1024))",
        "Memory Type and Speed": "Get-CimInstance Win32_PhysicalMemory | "
                                 "Select-Object MemoryType, Speed | Format-Table -AutoSize",
        "Memory Slots Used": "(Get-CimInstance Win32_PhysicalMemory).Count",
        "Total Memory Slots": "(Get-CimInstance Win32_PhysicalMemoryArray).MemoryDevices",
        # Storage Devices
        "Disk Drives": "Get-CimInstance Win32_DiskDrive | Select-Object Model, MediaType, "
                       "Size | Format-Table -AutoSize",
        "Logical Drives": "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, "
                          "FileSystem, Size, FreeSpace | Format-Table -AutoSize",
        # GPU Information
        "GPU Model": "(Get-CimInstance Win32_VideoController).Name",
        "GPU Adapter RAM": "(Get-CimInstance Win32_VideoController).AdapterRAM",
        "GPU Driver Version": "(Get-CimInstance Win32_VideoController).DriverVersion",
        # Motherboard
        "Motherboard Manufacturer": "(Get-CimInstance Win32_BaseBoard).Manufacturer",
        "Motherboard Model": "(Get-CimInstance Win32_BaseBoard).Product",
        # Network Interfaces
        "Network Adapters": "Get-NetAdapter | Select-Object Name, InterfaceDescription, "
                            "MacAddress, Status | Format-Table -AutoSize",
        # Peripherals
        "Audio Devices": "Get-CimInstance Win32_SoundDevice | Select-Object Name, "
                         "Manufacturer | Format-Table -AutoSize",
        "Input Devices": "Get-PnpDevice -Class Keyboard, Mouse | Where-Object "
                         "{ $_.Status -eq 'OK' } | Select-Object FriendlyName | "
                         "Format-Table -AutoSize",
        # Displays
        '''"Connected Monitors": "Get-CimInstance -Namespace root\\wmi -Class WmiMonitorID | "
                              "ForEach-Object { $name = ($_.UserFriendlyName -notmatch 0 | "
                              "ForEach-Object { [char]$_ }) -join ''; $name }",'''
        '''"Display Resolutions": "Add-Type -AssemblyName System.Windows.Forms; "
                               "[System.Windows.Forms.Screen]::AllScreens | ForEach-Object "
                               "{ \"$($_.DeviceName): $($_.Bounds.Width)x$($_.Bounds.Height)\" }",'''
        # Battery (for laptops)
        "Battery Status": "Get-CimInstance Win32_Battery | Select-Object Name, "
                          "EstimatedChargeRemaining, BatteryStatus | Format-Table -AutoSize",
    }

    # Network Information commands
    network_commands = {
        "Public IP Address": "(Invoke-WebRequest -Uri 'http://ifconfig.me/ip').Content.Trim()",
        "Private IP Addresses": "Get-NetIPAddress -AddressFamily IPv4 | Where-Object "
                                "{ $_.InterfaceAlias -ne 'Loopback Pseudo-Interface 1' } | "
                                "Select-Object IPAddress | Format-Table -AutoSize",
        "Subnet Masks": "Get-NetIPConfiguration | Select-Object InterfaceAlias, "
                        "IPv4SubnetMask | Format-Table -AutoSize",
        "Default Gateway": "Get-NetIPConfiguration | Select-Object InterfaceAlias, "
                           "IPv4DefaultGateway | Format-Table -AutoSize",
        "DNS Servers": "Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object "
                       "InterfaceAlias, ServerAddresses | Format-Table -AutoSize",
        "DHCP Information": "Get-NetIPConfiguration | Select-Object InterfaceAlias, "
                            "DhcpServer, DhcpLeaseObtainedTime, DhcpLeaseExpires | "
                            "Format-Table -AutoSize",
        "Active Network Connections": "Get-NetTCPConnection | Where-Object "
                                      "{ $_.State -eq 'Established' } | Select-Object "
                                      "LocalAddress, LocalPort, RemoteAddress, RemotePort | "
                                      "Format-Table -AutoSize",
        "VPN Connections": "Get-VpnConnection | Select-Object Name, ConnectionStatus | Format-Table -AutoSize",
        "Proxy Settings": "Get-ItemProperty -Path "
                          "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' "
                          "| Select-Object ProxyServer, ProxyEnable | Format-Table -AutoSize",
        "Firewall Status": "Get-NetFirewallProfile | Select-Object Name, Enabled | "
                           "Format-Table -AutoSize",
    }

    # Software Information commands
    software_commands = {
        "Installed Applications": "Get-ItemProperty @('HKLM:\\Software\\Microsoft\\Windows\\"
                                  "CurrentVersion\\Uninstall\\*','HKLM:\\Software\\Wow6432Node\\"
                                  "Microsoft\\Windows\\CurrentVersion\\Uninstall\\*') | "
                                  "Where-Object { $_.DisplayName } | Select-Object DisplayName, "
                                  "DisplayVersion, InstallDate | Sort-Object DisplayName | "
                                  "Format-Table -AutoSize",
        "Running Processes": "Get-Process | Select-Object ProcessName, Id, CPU, WorkingSet | "
                             "Format-Table -AutoSize",
        "Startup Programs": "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, "
                            "Location | Format-Table -AutoSize"
    }

    # Security Information commands
    security_commands = {
        "User Accounts": "Get-LocalUser | Select-Object Name, Enabled | Format-Table -AutoSize",
        '''"Group Memberships": "Get-LocalGroupMember -Group 'Administrators' | Select-Object Name, "
                             "ObjectClass | Format-Table -AutoSize",'''
        "Antivirus Software": "Get-CimInstance -Namespace 'root\\SecurityCenter2' -ClassName "
                              "AntiVirusProduct | Select-Object displayName, productState | "
                              "Format-Table -AutoSize",
        "Firewall Configuration": "Get-NetFirewallProfile | Select-Object Name, Enabled | "
                                  "Format-Table -AutoSize",
        "Disk Encryption Status": "Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus | "
                                  "Format-Table -AutoSize",
    }

    # Performance Metrics commands
    '''performance_commands = {
        "CPU Usage (%)": "(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples."
                         "CookedValue",
        "Available Memory (MB)": "(Get-Counter '\\Memory\\Available MBytes').CounterSamples."
                                 "CookedValue",
        "Disk Read/Write Speeds": "Get-Counter -Counter '\\PhysicalDisk(_Total)\\Disk Read "
                                  "Bytes/sec','\\PhysicalDisk(_Total)\\Disk Write Bytes/sec' | "
                                  "Format-Table -AutoSize",
    }'''

    # Development Environment commands
    development_commands = {
        "Version Control Systems": "Get-Command git, svn -ErrorAction SilentlyContinue | "
                                   "Select-Object Name, Version | Format-Table -AutoSize",
        "Programming Languages": "Get-Command python, java -ErrorAction SilentlyContinue | "
                                 "Select-Object Name, Version | Format-Table -AutoSize",
        "Environment Variables": "[Environment]::GetEnvironmentVariables() | "
                                 "Format-Table -AutoSize",
    }

    # Miscellaneous Information commands
    miscellaneous_commands = {
        "Locale and Language Settings": "Get-Culture | Select-Object Name, DisplayName",
        "Installed Fonts": "Get-ChildItem -Path $env:windir\\Fonts -Include *.ttf,*.otf -Recurse "
                           "| Select-Object Name | Format-Table -AutoSize",
        "Recent Application Events": "Get-EventLog -LogName Application -Newest 10 | "
                                     "Format-Table -AutoSize",
    }

    # User-Specific Information commands
    user_commands = {
        "Home Directory Contents": "Get-ChildItem -Path $env:USERPROFILE | Select-Object Name | "
                                   "Format-Table -AutoSize",
        "Installed Browsers": "Get-ItemProperty 'HKLM:\\Software\\Clients\\StartMenuInternet\\*' | "
                              "Select-Object '(default)' | Format-Table -AutoSize",
    }

    # Create tabs
    system_tab = create_info_frame(notebook, system_commands)
    hardware_tab = create_info_frame(notebook, hardware_commands)
    network_tab = create_info_frame(notebook, network_commands)
    software_tab = create_info_frame(notebook, software_commands)
    security_tab = create_info_frame(notebook, security_commands)
    # performance_tab = create_info_frame(notebook, performance_commands)
    development_tab = create_info_frame(notebook, development_commands)
    miscellaneous_tab = create_info_frame(notebook, miscellaneous_commands)
    user_tab = create_info_frame(notebook, user_commands)

    # Add tabs to the notebook
    notebook.add(system_tab, text='System')
    notebook.add(hardware_tab, text='Hardware')
    notebook.add(network_tab, text='Network')
    notebook.add(software_tab, text='Software')
    notebook.add(security_tab, text='Security')
    # notebook.add(performance_tab, text='Performance')
    notebook.add(development_tab, text='Development')
    notebook.add(miscellaneous_tab, text='Miscellaneous')
    notebook.add(user_tab, text='User')

    # Refresh button
    def refresh_all():
        tabs_and_commands = [
            (system_tab, system_commands),
            (hardware_tab, hardware_commands),
            (network_tab, network_commands),
            (software_tab, software_commands),
            (security_tab, security_commands),
            # (performance_tab, performance_commands),
            (development_tab, development_commands),
            (miscellaneous_tab, miscellaneous_commands),
            (user_tab, user_commands),
        ]
        for tab, commands in tabs_and_commands:
            # Clear existing items in the treeview
            tree = tab.winfo_children()[0]
            tree.delete(*tree.get_children())
            # Start a new worker thread
            result_queue = queue.Queue()
            thread = threading.Thread(target=worker, args=(commands, result_queue))
            thread.daemon = True
            thread.start()
            # Dictionary to hold tree items
            tree_items = {}

            # Set up processing queue
            def process_queue():
                while not result_queue.empty():
                    label, result = result_queue.get()
                    # Handle multi-line outputs
                    if '\n' in result:
                        if label not in tree_items:
                            parent_item = tree.insert('', 'end', text=label)
                            tree_items[label] = parent_item
                        else:
                            parent_item = tree_items[label]
                            tree.delete(*tree.get_children(parent_item))
                        for line in result.splitlines():
                            tree.insert(parent_item, 'end', text='', values=(line,))
                    else:
                        if label in tree_items:
                            tree.item(tree_items[label], values=(result,))
                        else:
                            item_id = tree.insert('', 'end', text=label, values=(result,))
                            tree_items[label] = item_id
                tree.after(100, process_queue)

            process_queue()

    refresh_button = Button(system_info_window, text="Refresh All", command=refresh_all)
    refresh_button.pack(pady=10)


def open_winget_window():
    # Helper function to execute Winget commands
    def run_command(command):
        try:
            # Append flags to suppress progress indicators
            command += ' --disable-interactivity'
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr as well
                text=True,
                encoding='utf-8',
                shell=True
            )
            output = result.stdout
            # Filter out lines that contain only spinner characters
            spinner_chars = {'\\', '-', '|', '/', '█', '▒'}
            filtered_output = '\n'.join(
                line for line in output.splitlines()
                if not set(line.strip()).issubset(spinner_chars) and line.strip() != ''
            )
            return filtered_output
        except Exception as e:
            return f"Error: {str(e)}"

    def list_programs():
        # TODO: Open in a new window so we can right click over a program (that has to be an item of a listbox) and know the description
        output = run_command('winget search --exact')
        insert_output(output)

    # Function to display installed programs as a list
    def list_installed():
        output = run_command('winget list --source "winget"')
        installed_listbox.delete(0, END)  # Clear previous items
        # Split the output into lines and extract relevant program info
        lines = output.splitlines()
        for line in lines[1:]:  # Skip the first two lines of headers
            program_info = ' '.join(line.split()).strip()  # Clean up spaces
            if program_info:
                installed_listbox.insert(END, program_info)

    # Function to display upgradable programs
    def list_upgradable():
        output = run_command('winget upgrade --include-unknown')
        removed_text = "winget"

        for widget in upgrade_checkboxes_frame.winfo_children():
            widget.destroy()  # Clear previous checkboxes
        upgrade_vars.clear()  # Clear previous variables

        version_pattern = re.compile(r'(\d+[\.-]\d+[\.-]?\d*)')

        lines = output.splitlines()[1:]  # Skip header lines
        for i, line in enumerate(lines):
            from_version = "Unknown"
            to_version = "Unknown"
            if line.strip():  # Check if the line is not empty
                match = version_pattern.search(line)
                if match:
                    try:
                        # The rest of the information (version details and description)
                        program_info = line[match.start():].strip().replace(removed_text, "")
                        to_version = program_info[::-1].split()[0][::-1]
                        from_version = program_info[::-1].split()[1][::-1]

                        new_to_version = "Unknown"
                        new_from_version = "Unknown"

                        if "(" in program_info and ")" in program_info:
                            new_line = line.replace(removed_text, "")

                            new_to_version = new_line[::-1].split()[0]
                            if "(" in new_to_version and ")" in new_to_version:
                                new_new_line = new_line.split()[::-1]
                                new_to_version = new_new_line[1] + " " + new_new_line[0]
                                new_line = new_line.replace(new_to_version, "").strip()
                                to_version = new_to_version
                            if "(" in new_to_version and ")" in new_to_version and new_to_version != "Unknown":
                                new_new_line = new_line.split()[::-1]
                                new_from_version = new_new_line[1] + " " + new_new_line[0]
                                from_version = new_from_version

                        line = line.replace(to_version, "").replace(from_version, "").replace(removed_text, "")
                    except Exception as e:
                        pass

                # Reverse String, get the first element and reverse back to get the program id
                program_id = line[::-1].split()[0][::-1]

                if program_id == "winget":
                    try:
                        removed_text = "winget"
                        # The rest of the information (version details and description)
                        new_line = line.replace(removed_text, "")
                        to_version = new_line[::-1].split()[0][::-1]
                        from_version = new_line[::-1].split()[1][::-1]
                        new_line = line.replace(from_version, "").replace(to_version, "").replace(removed_text, "")
                        program_id = new_line[::-1].split()[0][::-1]
                    except Exception as e:
                        pass

                if from_version != "Unknown" and to_version != "Unknown" and program_id != "()":
                    # Create tabulated display
                    display_text = f"{program_id:<40} {from_version:<15} {to_version:<15}"
                    var = BooleanVar()
                    checkbox = Checkbutton(upgrade_checkboxes_frame, text=display_text, variable=var, anchor='w',
                                           justify=LEFT, font=("Courier", 10))
                    checkbox.grid(row=i, column=0, sticky="w")
                    upgrade_vars.append((var, program_id))

        # Update the scrollregion of the canvas
        upgrade_checkboxes_frame.update_idletasks()
        upgrade_checkboxes_canvas.configure(scrollregion=upgrade_checkboxes_canvas.bbox("all"))

    def update_output(output):
        output_text.insert(END, output + "\n")
        output_text.see(END)

    # Function to upgrade selected programs
    def upgrade_selected():
        # Disable buttons during the upgrade process
        disable_upgrade_buttons()

        # Run the upgrade process in a separate thread to avoid blocking the UI
        def upgrade_thread():
            selected_programs = [info for var, info in upgrade_vars if var.get()]
            if not selected_programs:
                messagebox.showinfo("No Selection", "Please select programs to upgrade.")
                enable_upgrade_buttons()
                return

            successfully_upgraded = []
            for program_info in selected_programs:
                program_id = program_info.split()[0]  # Assuming the ID is the first word
                update_output(f"\nUpgrading {program_id}...")
                output = run_command(f'winget upgrade --include-unknown --id "{program_id}"')
                update_output(output)
                successfully_upgraded.append(program_id)

            # Refresh the upgradable programs list
            list_upgradable()

            # Show summary message after upgrading
            summary = f"Programs {', '.join(successfully_upgraded)} successfully upgraded."
            update_output(summary)

            # Re-enable buttons after the upgrade process
            enable_upgrade_buttons()

        # Start the upgrade process in a new thread
        threading.Thread(target=upgrade_thread).start()

    # Function to disable all buttons during an ongoing operation
    def disable_upgrade_buttons():
        select_all_button.config(state=DISABLED)
        deselect_all_button.config(state=DISABLED)
        upgrade_selected_button.config(state=DISABLED)

        # Disable all checkboxes
        for widget in upgrade_checkboxes_frame.winfo_children():
            if isinstance(widget, Checkbutton):
                widget.config(state=DISABLED)

    # Function to enable all buttons after an operation is finished
    def enable_upgrade_buttons():
        select_all_button.config(state=NORMAL)
        deselect_all_button.config(state=NORMAL)
        upgrade_selected_button.config(state=NORMAL)

        # Enable all checkboxes
        for widget in upgrade_checkboxes_frame.winfo_children():
            if isinstance(widget, Checkbutton):
                widget.config(state=NORMAL)

    # Function to select all upgradable programs
    def select_all():
        for var, _ in upgrade_vars:  # Only use 'var', which is the BooleanVar
            var.set(True)  # Set all checkboxes to True (selected)

    # Function to deselect all upgradable programs
    def deselect_all():
        for var, _ in upgrade_vars:  # Only use 'var', which is the BooleanVar
            var.set(False)  # Set all checkboxes to False (deselected)

    # Function to search for installable programs
    def search_program():
        search_term = simpledialog.askstring("Search", "Enter program name to search:")
        if search_term:
            output = run_command(f'winget search --exact "{search_term}"')
            insert_output(output)

    # Function to install a program
    def install_program():
        program_id = simpledialog.askstring("Install", "Enter program ID to install:")
        if program_id:
            output = run_command(f'winget install -s "winget" "{program_id}"')
            insert_output(f"Installing {program_id}...\n{output}")
            list_installed()  # Refresh the installed programs list
            list_upgradable()  # Refresh the upgradable programs list

    # Function to uninstall a program
    def uninstall_program():
        program_id = simpledialog.askstring("Uninstall", "Enter program ID to uninstall:")
        if program_id:
            output = run_command(f'winget uninstall "{program_id}"')
            insert_output(f"Uninstalling {program_id}...\n{output}")
            list_installed()  # Refresh the installed programs list
            list_upgradable()  # Refresh the upgradable programs list

    def get_program_description(program_id):
        # Function to extract the program description
        return run_command(f'winget show "{program_id}"')

    def program_description():
        program_id = simpledialog.askstring("Description of Program", "Enter program ID to get its description:")
        if program_id:
            output = get_program_description(program_id)
            insert_output(output)
            list_installed()  # Refresh the installed programs list

    # Function to display output in the text area
    def insert_output(output):
        output_text.delete(1.0, END)  # Clear previous results
        output_text.insert(END, output)

    # Create the Winget window
    winget_window = Toplevel()
    winget_window.title("WinGet Package Manager")
    winget_window.geometry("1000x700")

    # Create main frame
    main_frame = Frame(winget_window)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Create left frame for installed programs
    left_frame = Frame(main_frame)
    left_frame.pack(side=LEFT, fill=BOTH, expand=True)

    installed_label = Label(left_frame, text="Installed Programs")
    installed_label.pack()

    installed_listbox = Listbox(left_frame, height=20, width=50)
    installed_listbox.pack(side=LEFT, fill=BOTH, expand=True)

    installed_scrollbar = Scrollbar(left_frame)
    installed_scrollbar.pack(side=RIGHT, fill=Y)

    installed_listbox.config(yscrollcommand=installed_scrollbar.set)
    installed_scrollbar.config(command=installed_listbox.yview)

    # Create right frame for upgradable programs
    right_frame = Frame(main_frame)
    right_frame.pack(side=RIGHT, fill=BOTH, expand=True)

    upgradable_label = Label(right_frame, text="Upgradable Programs")
    upgradable_label.pack()

    # Create a canvas and scrollbar for the checkboxes
    upgrade_checkboxes_canvas = Canvas(right_frame)
    upgrade_checkboxes_canvas.pack(side=LEFT, fill=BOTH, expand=True)

    upgrade_checkboxes_scrollbar = Scrollbar(right_frame, orient=VERTICAL, command=upgrade_checkboxes_canvas.yview)
    upgrade_checkboxes_scrollbar.pack(side=RIGHT, fill=Y)

    upgrade_checkboxes_canvas.configure(yscrollcommand=upgrade_checkboxes_scrollbar.set)

    upgrade_checkboxes_frame = Frame(upgrade_checkboxes_canvas)
    upgrade_checkboxes_canvas.create_window((0, 0), window=upgrade_checkboxes_frame, anchor='nw')

    # Add mouse wheel scrolling functionality
    def on_mousewheel(event):
        upgrade_checkboxes_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_mousewheel(event):
        upgrade_checkboxes_canvas.bind_all("<MouseWheel>", on_mousewheel)

    def unbind_mousewheel(event):
        upgrade_checkboxes_canvas.unbind_all("<MouseWheel>")

    upgrade_checkboxes_canvas.bind('<Enter>', bind_mousewheel)
    upgrade_checkboxes_canvas.bind('<Leave>', unbind_mousewheel)

    upgrade_vars = []

    # Create the text widget to display the output from Winget commands
    output_text = scrolledtext.ScrolledText(winget_window, wrap=WORD, height=10, width=120)
    output_text.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Create button frame
    button_frame = Frame(winget_window)
    button_frame.pack(fill=X, padx=10, pady=10)

    # Create buttons
    list_all_programs_button = Button(button_frame, text="List All Programs", command=list_programs)
    list_all_programs_button.pack(side=LEFT, padx=5)

    search_button = Button(button_frame, text="Search Program", command=search_program)
    search_button.pack(side=LEFT, padx=5)

    program_description_button = Button(button_frame, text="Program Description", command=program_description)
    program_description_button.pack(side=LEFT, padx=5)

    install_button = Button(button_frame, text="Install Program", command=install_program)
    install_button.pack(side=LEFT, padx=5)

    uninstall_button = Button(button_frame, text="Uninstall Program", command=uninstall_program)
    uninstall_button.pack(side=LEFT, padx=5)

    select_all_button = Button(button_frame, text="Select All", command=select_all)
    select_all_button.pack(side=LEFT, padx=5)

    deselect_all_button = Button(button_frame, text="Deselect All", command=deselect_all)
    deselect_all_button.pack(side=LEFT, padx=5)

    upgrade_selected_button = Button(button_frame, text="Upgrade Selected", command=upgrade_selected)
    upgrade_selected_button.pack(side=LEFT, padx=5)

    # Initialize the window with installed programs
    list_installed()
    list_upgradable()

    # Insert welcome message in the output area
    insert_output("Welcome to WinGet Package Manager.\nUse the buttons to perform WinGet operations.")


def open_git_window(repo_dir=None):
    global git_console_instance
    command_history = []

    def execute_command(command):
        if command.strip():
            command_history.append(command)
            history_pointer[0] = len(command_history)

            directory = repo_dir or os.getcwd()
            git_command = f'git -C "{directory}" {command}'

            try:
                if command == "status --porcelain -u":
                    update_output_text(output_text)
                else:
                    output = subprocess.check_output(git_command, stderr=subprocess.STDOUT, shell=True, text=True)
                    insert_ansi_text(output_text, f"{git_command}\n{output}\n")
            except subprocess.CalledProcessError as e:
                insert_ansi_text(output_text, f"Error: {e.output}\n", "error")
            entry.delete(0, END)
            output_text.see(END)
        # update_status()

    def populate_branch_menu():
        branch_menu.delete(0, END)
        try:
            branches_output = subprocess.check_output(['git', 'branch', '--all'], text=True)
            branches = list(filter(None, [branch.strip() for branch in branches_output.split('\n')]))
            active_branch = next((branch[2:] for branch in branches if branch.startswith('*')), None)
            for branch in branches:
                is_active = branch.startswith('*')
                branch_name = branch[2:] if is_active else branch
                display_name = f"✓ {branch_name}" if is_active else branch_name
                branch_menu.add_command(label=display_name, command=lambda b=branch_name: checkout_branch(b))
        except subprocess.CalledProcessError as e:
            insert_ansi_text(output_text, f"Error fetching branches: {e.output}\n", "error")

    def update_commit_list(commit_list):
        command = 'git log --no-merges --color --graph --pretty=format:"%h %d %s - <%an (%cr)>" --abbrev-commit --branches'
        output = subprocess.check_output(command, shell=True, text=True)
        commit_list.delete(0, END)

        apply_visual_styles(commit_list)

        current_commit = get_current_checkout_commit()
        short_hash_number_commit = current_commit[:7]

        # Iterate through each line of the git log output
        for line in output.split('\n'):
            #print("THE LINE IS:\t", line)
            line = line[2:]
            # Check if the line contains the short hash of the current commit
            if short_hash_number_commit in line:
                # Prepend an asterisk if it's the current commit
                commit_list.insert(END, f"* {line}")
            else:
                # Otherwise, insert the line without modification
                commit_list.insert(END, line)

        # Apply the visual styles after updating the list
        apply_visual_styles(commit_list)

    def apply_visual_styles(commit_list):
        current_commit = get_current_checkout_commit()
        for i in range(commit_list.size()):
            item = commit_list.get(i)
            if current_commit in item:
                commit_list.itemconfig(i, {'bg': 'yellow'})  # Highlight with a different background
            elif item.startswith('*'):
                commit_list.itemconfig(i, {'fg': 'green'})
            else:
                commit_list.itemconfig(i, {'fg': 'gray'})

    def commit_list_context_menu(event):
        context_menu = Menu(commit_list, tearoff=0)
        context_menu.add_command(label="Checkout",
                                 command=lambda: checkout_commit(commit_list.get(commit_list.curselection())))
        context_menu.add_command(label="View Details",
                                 command=lambda: view_commit_details(commit_list.get(commit_list.curselection())))
        context_menu.post(event.x_root, event.y_root)

    def checkout_commit(commit_info):
        # Extract commit hash from the selected commit
        # Assuming the commit info is formatted like: '<commit_hash> - <author> <details>'
        commit_hash = commit_info.split(' ')[0]

        # Run the git checkout command for the commit hash
        try:
            execute_command(f'checkout {commit_hash}')
            update_status(commit_hash)
            update_commit_list(commit_list)
        except subprocess.CalledProcessError as e:
            insert_ansi_text(output_text, f"Error checking out commit: {e.output}\n", "error")

        # Apply the visual styles after updating the list
        apply_visual_styles(commit_list)

    def view_commit_details(commit_hash):
        try:
            commit_hash_number = commit_hash[:7]
            # Execute the git show command and capture colored output
            output = subprocess.check_output(['git', 'show', '--color=always', commit_hash_number], text=True)
            # print("This is the output:\n", output)

            details_window = Toplevel()
            details_window.title(f"{commit_hash}")
            text_widget = scrolledtext.ScrolledText(details_window)

            define_ansi_tags(text_widget)
            apply_ansi_styles(text_widget, output)
            text_widget.config(state=DISABLED)
            text_widget.pack(fill='both', expand=True)

        except subprocess.CalledProcessError as e:
            # Handle errors by showing an error message in a new window
            error_window = Toplevel()
            error_window.title("Error")
            Label(error_window, text=f"Failed to fetch commit details: {e.output}").pack(pady=20, padx=20)

    def get_current_checkout_commit():
        current_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        update_status()
        return current_commit

    def checkout_branch(branch):
        execute_command(f'checkout {branch}')
        populate_branch_menu()
        update_commit_list(commit_list)
        update_status()
        # apply_visual_styles(commit_list)

    def define_ansi_tags(text_widget):
        # Ensure all tags used in 'insert_ansi_text' are defined here
        text_widget.tag_configure('added', background='light green', foreground='black')
        text_widget.tag_configure('removed', background='light coral', foreground='black')
        text_widget.tag_configure("changed", foreground="cyan")
        text_widget.tag_configure('commit', foreground='yellow')
        text_widget.tag_configure('author', foreground='green')
        text_widget.tag_configure('date', foreground='magenta')
        text_widget.tag_configure('error', foreground='red')

        text_widget.tag_configure('green', foreground='green')
        text_widget.tag_configure('yellow', foreground='yellow')
        text_widget.tag_configure('blue', foreground='blue')
        text_widget.tag_configure('magenta', foreground='magenta')
        text_widget.tag_configure('cyan', foreground='cyan')

        text_widget.tag_configure('modified', foreground='orange')
        text_widget.tag_configure('modified_multiple', foreground='dark orange')
        text_widget.tag_configure('untracked', foreground='red')
        text_widget.tag_configure('added', foreground='green')
        text_widget.tag_configure('deleted', foreground='red')
        text_widget.tag_configure('renamed', foreground='blue')
        text_widget.tag_configure('copied', foreground='purple')
        text_widget.tag_configure('unmerged', foreground='yellow')
        text_widget.tag_configure('ignored', foreground='gray')

        text_widget.tag_configure("addition", foreground="green")
        text_widget.tag_configure("deletion", foreground="red")
        text_widget.tag_configure("info", foreground="blue")  # For context lines and file names

    def apply_ansi_styles(text_widget, text):
        ansi_escape = re.compile(r'\x1B\[([0-9;]*[mK])')
        pos = 0

        # Split the text into lines for individual processing
        lines = text.splitlines()
        for line in lines:
            # Remove ANSI escape codes
            cleaned_line = ansi_escape.sub('', line)
            # Print the cleaned line into the text widget with the correct tag
            if cleaned_line.startswith('commit '):
                text_widget.insert('end', 'commit ', 'commit')
                text_widget.insert('end', cleaned_line[7:] + '\n')
            elif cleaned_line.startswith('Author: '):
                text_widget.insert('end', 'Author: ', 'author')
                text_widget.insert('end', cleaned_line[8:] + '\n')
            elif cleaned_line.startswith('Date: '):
                text_widget.insert('end', 'Date: ', 'date')
                text_widget.insert('end', cleaned_line[6:] + '\n')
            elif cleaned_line.startswith('+ ') or cleaned_line.startswith('+') and not cleaned_line.startswith('+++'):
                text_widget.insert('end', cleaned_line + '\n', 'added')
            elif cleaned_line.startswith('- ') or cleaned_line.startswith('-') and not cleaned_line.startswith('---'):
                text_widget.insert('end', cleaned_line + '\n', 'removed')
            elif cleaned_line.startswith('@@ '):
                # Split the line at '@@' characters
                parts = cleaned_line.split('@@')
                if len(parts) >= 3:
                    # Insert the part before the first '@@'
                    text_widget.insert('end', parts[0])
                    # Insert the middle part (between '@@') with 'changed' tag
                    text_widget.insert('end', '@@' + parts[1] + '@@', 'changed')
                    # Insert the part after the second '@@' and the newline
                    text_widget.insert('end', ''.join(parts[2:]) + '\n')
                else:
                    # If there aren't two '@@', insert the whole line
                    text_widget.insert('end', cleaned_line + '\n')
            else:
                text_widget.insert('end', cleaned_line + '\n')

    def insert_ansi_text(widget, text, tag=""):
        ansi_escape = re.compile(r'\x1B\[(?P<code>\d+(;\d+)*)m')
        segments = ansi_escape.split(text)

        tag = None
        for i, segment in enumerate(segments):
            if i % 2 == 0:
                widget.insert(END, segment, tag)
            else:
                codes = list(map(int, segment.split(';')))
                tag = get_ansi_tag(codes)
                if tag:
                    widget.tag_configure(tag, **get_ansi_style(tag))

    def get_ansi_tag(codes):
        fg_map = {
            30: 'black', 31: 'red', 32: 'green', 33: 'yellow',
            34: 'blue', 35: 'magenta', 36: 'cyan', 37: 'white',
            90: 'bright_black', 91: 'bright_red', 92: 'bright_green', 93: 'bright_yellow',
            94: 'bright_blue', 95: 'bright_magenta', 96: 'bright_cyan', 97: 'bright_white',
        }
        bg_map = {
            40: 'bg_black', 41: 'bg_red', 42: 'bg_green', 43: 'bg_yellow',
            44: 'bg_blue', 45: 'bg_magenta', 46: 'bg_cyan', 47: 'bg_white',
            100: 'bg_bright_black', 101: 'bg_bright_red', 102: 'bg_bright_green', 103: 'bg_bright_yellow',
            104: 'bg_bright_blue', 105: 'bg_bright_magenta', 106: 'bg_bright_cyan', 107: 'bg_bright_white',
        }
        styles = []
        for code in codes:
            if code in fg_map:
                styles.append(fg_map[code])
            elif code in bg_map:
                styles.append(bg_map[code])
            elif code == 1:
                styles.append('bold')
            elif code == 4:
                styles.append('underline')

        return '_'.join(styles) if styles else None

    def get_ansi_style(tag):
        styles = {
            'black': {'foreground': 'black'},
            'red': {'foreground': 'red'},
            'green': {'foreground': 'green'},
            'yellow': {'foreground': 'yellow'},
            'blue': {'foreground': 'blue'},
            'magenta': {'foreground': 'magenta'},
            'cyan': {'foreground': 'cyan'},
            'white': {'foreground': 'white'},
            'bright_black': {'foreground': 'gray'},
            'bright_red': {'foreground': 'lightcoral'},
            'bright_green': {'foreground': 'lightgreen'},
            'bright_yellow': {'foreground': 'lightyellow'},
            'bright_blue': {'foreground': 'lightblue'},
            'bright_magenta': {'foreground': 'violet'},
            'bright_cyan': {'foreground': 'lightcyan'},
            'bright_white': {'foreground': 'white'},
            'bg_black': {'background': 'black'},
            'bg_red': {'background': 'red'},
            'bg_green': {'background': 'green'},
            'bg_yellow': {'background': 'yellow'},
            'bg_blue': {'background': 'blue'},
            'bg_magenta': {'background': 'magenta'},
            'bg_cyan': {'background': 'cyan'},
            'bg_white': {'background': 'white'},
            'bg_bright_black': {'background': 'gray'},
            'bg_bright_red': {'background': 'lightcoral'},
            'bg_bright_green': {'background': 'lightgreen'},
            'bg_bright_yellow': {'background': 'lightyellow'},
            'bg_bright_blue': {'background': 'lightblue'},
            'bg_bright_magenta': {'background': 'violet'},
            'bg_bright_cyan': {'background': 'lightcyan'},
            'bg_bright_white': {'background': 'white'},
            'bold': {'font': ('TkDefaultFont', 10, 'bold')},
            'underline': {'font': ('TkDefaultFont', 10, 'underline')},
        }
        style = {}
        for part in tag.split('_'):
            if part in styles:
                style.update(styles[part])
        return style

    terminal_window = Toplevel()
    terminal_window.title("Git Console")
    terminal_window.geometry("600x512")

    # Create a top-level menu
    menubar = Menu(terminal_window)
    terminal_window.config(menu=menubar)

    # Create a Git menu
    git_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Git", menu=git_menu)

    # Add Git commands to the menu
    for command, icon in git_icons.items():
        git_menu.add_command(label=f"{icon} {command.capitalize()}", command=lambda c=command: execute_command(c))

    # Create a Branch menu
    branch_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Branch", menu=branch_menu)

    populate_branch_menu()  # Populate the Branch menu with branches

    # Create a ScrolledText widget to display terminal output
    output_text = scrolledtext.ScrolledText(terminal_window, height=20, width=80)
    output_text.pack(fill='both', expand=True)

    # Status bar to display current branch
    status_bar = Label(terminal_window, text="Checking branch...", bd=1, relief=SUNKEN, anchor=W)
    status_bar.pack(side='top', fill='x')

    # Function to update status bar
    def update_status(commit_hash="HEAD"):
        try:
            # First, check if the hash is a branch
            branch_name = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', commit_hash], text=True).strip()
            if branch_name != "HEAD":
                status_bar.config(text=f"Current branch: {branch_name}")
            else:
                # If not a branch, then it is a commit
                commit_short_hash = subprocess.check_output(['git', 'rev-parse', '--short', commit_hash],
                                                            text=True).strip()
                status_bar.config(text=f"Current commit: {commit_short_hash}")
        except subprocess.CalledProcessError:
            status_bar.config(text="Error: Invalid identifier")

    # Call update_status to initialize
    update_status()

    # Initialize a list to store command history
    command_history = []
    # Initialize a pointer to the current position in the command history
    history_pointer = [0]

    # Function to navigate the command history
    def navigate_history(event):
        if command_history:
            # UP arrow key pressed
            if event.keysym == 'Up':
                history_pointer[0] = max(0, history_pointer[0] - 1)
            # DOWN arrow key pressed
            elif event.keysym == 'Down':
                history_pointer[0] = min(len(command_history), history_pointer[0] + 1)
            # Get the command from history
            command = command_history[history_pointer[0]] if history_pointer[0] < len(command_history) else ''
            # Set the command to the entry widget
            entry.delete(0, END)
            entry.insert(0, command)

    # Function to add selected text to Git staging
    def add_selected_text_to_git_staging():
        selected_text = output_text.get("sel.first", "sel.last")
        if selected_text:
            execute_command(f"add -f {selected_text}")

    # Function to unstage selected text
    def unstage_selected_text():
        selected_text = output_text.get("sel.first", "sel.last")
        if selected_text:
            execute_command(f"reset -- {selected_text}")

    def get_git_status():
        return subprocess.check_output(['git', 'status', '--porcelain', '-u'], text=True)

    def show_git_diff():
        git_diff_command = 'git diff --color'
        try:
            output = subprocess.check_output(git_diff_command, shell=True, stderr=subprocess.STDOUT)
            output = output.decode('utf-8', errors='replace')

            # Create a new window for the diff output
            diff_window = Toplevel(terminal_window)
            diff_window.title("Git Diff")
            diff_window.geometry("800x600")

            # Create a Text widget to display the diff output
            diff_text = Text(diff_window, height=20, width=80)
            diff_text.pack(fill='both', expand=True)

            # Configure tags for syntax highlighting
            define_ansi_tags(diff_text)

            # Parse the diff output and apply syntax highlighting
            ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
            for line in output.split('\n'):
                line_clean = ansi_escape.sub('', line)  # Remove ANSI escape sequences
                if line.startswith('+'):
                    diff_text.insert(END, line_clean + '\n', "addition")
                elif line.startswith('-'):
                    diff_text.insert(END, line_clean + '\n', "deletion")
                elif line.startswith('@'):
                    diff_text.insert(END, line_clean + '\n', "info")
                else:
                    diff_text.insert(END, line_clean + '\n')

            diff_text.config(state="disabled")  # Make the text widget read-only

        except subprocess.CalledProcessError as e:
            output_text.insert(END, f"Error: {e.output}\n", "error")

    def update_output_text(output_text_widget):
        git_status = get_git_status()
        define_ansi_tags(output_text_widget)

        if git_status == "":
            output_text_widget.insert('end', 'Your branch is up to date.\n\n')
        else:

            # Parse the diff output and apply syntax highlighting
            for line in git_status.split('\n'):

                status = line[:2]
                filename = line[3:]

                if status in [' M', 'M ']:
                    output_text_widget.insert('end', status, 'modified')
                    output_text_widget.insert('end', ' <' + filename + '>\n')
                elif status == 'MM':
                    output_text_widget.insert('end', status, 'modified_multiple')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status == '??':
                    output_text_widget.insert('end', status, 'untracked')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status == 'A ':
                    output_text_widget.insert('end', status, 'added')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status in [' D', 'D ']:
                    output_text_widget.insert('end', status, 'deleted')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status == 'R ':
                    output_text_widget.insert('end', status, 'renamed')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status == 'C ':
                    output_text_widget.insert('end', status, 'copied')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status == 'U ':
                    output_text_widget.insert('end', status, 'unmerged')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                elif status == '!!':
                    output_text_widget.insert('end', status, 'ignored')
                    output_text_widget.insert('end', ' ' + filename + '\n')
                else:
                    output_text_widget.insert('end', status)  # No special formatting for unknown status
                    output_text_widget.insert('end', ' ' + filename + '\n')

                try:
                    if status in [' M', 'M ']:
                        git_diff_command = f'git diff --color {filename}'
                        diff_output = subprocess.check_output(git_diff_command, shell=True, stderr=subprocess.STDOUT)
                        diff_output = diff_output.decode('utf-8', errors='replace')

                        # Parse the diff output and apply syntax highlighting
                        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
                        for diff_line in diff_output.split('\n')[1:]:
                            line_clean = ansi_escape.sub('', diff_line)  # Remove ANSI escape sequences
                            apply_ansi_styles(output_text, line_clean)

                        output_text_widget.insert('end', ' </' + filename + '>\n\n')

                except subprocess.CalledProcessError as e:
                    output_text.insert(END, f"Error: {e.output}\n", "error")

    # Create a context menu for the text widget
    context_menu = Menu(output_text)
    output_text.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))

    context_menu.add_command(label="Git Add", command=add_selected_text_to_git_staging)
    context_menu.add_command(label="Git Status", command=lambda: execute_command("status"))
    context_menu.add_command(label="Git Unstage", command=unstage_selected_text)
    context_menu.add_command(label="Git Diff", command=show_git_diff)

    # Set up the horizontal split
    top_frame = Frame(terminal_window)
    top_frame.pack(fill='both', expand=True)

    # Create a scrollbar for the commit list
    commit_scrollbar = Scrollbar(top_frame)
    commit_scrollbar.pack(side='right', fill='y')

    # Commit history list with attached scrollbar
    commit_list = Listbox(top_frame, yscrollcommand=commit_scrollbar.set)
    commit_list.pack(side='left', fill='both', expand=True)

    # Attach scrollbar to the listbox
    commit_scrollbar.config(command=commit_list.yview)

    commit_list.bind("<Button-3>", commit_list_context_menu)  # Bind right-click event

    # Populate the commit list
    update_commit_list(commit_list)

    # Create a frame for buttons
    button_frame = Frame(terminal_window)
    button_frame.pack(fill='both', expand=False)

    # Create buttons for common git commands
    common_commands = ["commit", "push", "pull", "fetch"]
    for command in common_commands:
        button = Button(button_frame, text=f"{git_icons[command]} {command.capitalize()}", command=lambda c=command: execute_command(c))
        button.pack(side='left')

    # Create an Entry widget for typing commands
    entry = Entry(button_frame, width=80)
    entry.pack(side='left', fill='x', expand=True)

    entry.focus()
    entry.bind("<Return>", lambda event: execute_command(entry.get()))
    # Bind the UP and DOWN arrow keys to navigate the command history
    entry.bind("<Up>", navigate_history)
    entry.bind("<Down>", navigate_history)

    execute_command("status --porcelain -u")


def open_kanban_window():
    # Global variables
    global kanban_data, columns_frame, drag_label

    # Initialize data
    kanban_data = {
        'columns': ['To Do', 'In Progress', 'Testing', 'Done', 'Continuous Improvement'],
        'tasks': [
            {'title': 'Task 1', 'description': 'Description 1', 'priority': 'High', 'column': 'To Do'},
            {'title': 'Task 2', 'description': 'Description 2', 'priority': 'Medium', 'column': 'In Progress'}
        ],
        'wip_limits': {'To Do': 10, 'In Progress': 5, 'Testing': 5, 'Done': float('inf'), 'Continuous Improvement': 5}
    }

    drag_label = None

    def load_kanban_data():
        global kanban_data
        try:
            with open('data/kanban_tasks.json', 'r') as f:
                kanban_data = json.load(f)
        except FileNotFoundError:
            save_kanban_data()

    def save_kanban_data():
        with open('data/kanban_tasks.json', 'w') as f:
            json.dump(kanban_data, f, indent=4)

    def on_drag_start(event):
        global drag_label
        widget = event.widget
        index = widget.nearest(event.y)
        _, y, _, height = widget.bbox(index)

        if y <= event.y < y + height:
            widget.drag_data = widget.get(index)
            widget.selection_clear(0, END)
            widget.selection_set(index)
            widget.itemconfig(index, {'bg': 'lightblue'})  # Highlight selected item

            # Create floating label
            drag_label = Label(kanban_window, text=widget.drag_data, relief=RAISED)
            drag_label.place(x=event.x_root, y=event.y_root, anchor="center")

    def on_drag_motion(event):
        global drag_label
        widget = event.widget
        if hasattr(widget, 'drag_data') and drag_label:
            x, y = kanban_window.winfo_pointerxy()
            drag_label.place(x=x, y=y, anchor="center")

            # Highlight target column
            target = widget.winfo_containing(x, y)
            if isinstance(target, Listbox):
                for child in columns_frame.winfo_children():
                    if isinstance(child, Frame):
                        child.config(bg='SystemButtonFace')  # Reset background
                target.master.config(bg='lightgreen')  # Highlight target column

    def on_drop(event):
        global drag_label
        widget = event.widget
        if hasattr(widget, 'drag_data'):
            x, y = widget.winfo_pointerxy()
            target = widget.winfo_containing(x, y)
            if isinstance(target, Listbox) and target != widget:
                item = widget.drag_data
                origin_column = widget.column
                target_column = target.column

                # Update kanban_data
                for task in kanban_data['tasks']:
                    if task['title'] == item:
                        task['column'] = target_column
                        break

                save_kanban_data()
                refresh_kanban_board()

            # Reset highlights and remove floating label
            for child in columns_frame.winfo_children():
                if isinstance(child, Frame):
                    child.config(bg='SystemButtonFace')
            if drag_label:
                drag_label.destroy()
                drag_label = None
            delattr(widget, 'drag_data')

    def setup_drag_and_drop(listbox, column):
        listbox.column = column
        listbox.bind("<ButtonPress-1>", on_drag_start)
        listbox.bind("<B1-Motion>", on_drag_motion)
        listbox.bind("<ButtonRelease-1>", on_drop)

    def add_task(event, column):
        task_title = event.widget.get()
        if task_title:
            new_task = {'title': task_title, 'description': '', 'priority': 'Medium', 'column': column}
            kanban_data['tasks'].append(new_task)
            save_kanban_data()
            refresh_kanban_board()

    def create_column(column_name):
        column_frame = Frame(columns_frame, borderwidth=2, relief='raised')
        column_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        label = Label(column_frame, text=f"{column_name} (Limit: {kanban_data['wip_limits'][column_name]})")
        label.pack(pady=5)

        task_list = Listbox(column_frame, selectmode=SINGLE)
        task_list.pack(fill=BOTH, expand=True, padx=5, pady=5)

        for task in [t for t in kanban_data['tasks'] if t['column'] == column_name]:
            task_list.insert(END, task['title'])

        setup_drag_and_drop(task_list, column_name)

        entry = Entry(column_frame)
        entry.pack(fill=X, padx=5, pady=5)
        entry.bind("<Return>", lambda event, col=column_name: add_task(event, col))

    def refresh_kanban_board():
        for widget in columns_frame.winfo_children():
            widget.destroy()
        for column in kanban_data['columns']:
            create_column(column)

        # Clear all entry widgets after refreshing the board
        for column_frame in columns_frame.winfo_children():
            entry_widget = column_frame.winfo_children()[-1]  # The entry widget is the last child
            if isinstance(entry_widget, Entry):
                entry_widget.delete(0, END)

    # Create main window
    kanban_window = Toplevel()
    kanban_window.title("Kanban Board")
    kanban_window.geometry("1280x720")

    # Create main frame
    columns_frame = Frame(kanban_window)
    columns_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Load data and create initial board
    load_kanban_data()
    refresh_kanban_board()

    kanban_window.protocol("WM_DELETE_WINDOW", lambda: (save_kanban_data(), kanban_window.destroy()))


def open_calculator_window():
    calculator_window = Toplevel()
    calculator_window.title("Advanced Scientific Calculator")
    calculator_window.geometry("500x600")

    expression_entry = Entry(calculator_window, width=30, font=('Arial', 18), borderwidth=2, relief='solid',
                             justify='right')
    expression_entry.grid(row=0, column=0, columnspan=5, padx=10, pady=10, sticky='nsew')

    result_label = Label(calculator_window, text="", font=('Arial', 14))
    result_label.grid(row=1, column=0, columnspan=5, padx=10, pady=5, sticky='nsew')

    original_states = {}  # Dictionary to store the original state of buttons

    def button_click(value):
        current = expression_entry.get()
        if current in ("Error", "Invalid Input"):
            expression_entry.delete(0, END)
        expression_entry.insert(END, value)

    def clear_entry():
        expression_entry.delete(0, END)
        result_label.config(text="")

    def backspace():
        current = expression_entry.get()
        expression_entry.delete(len(current) - 1, END)

    def toggle_scientific_calculator_buttons():
        # Dictionary mapping standard buttons to their scientific counterparts
        toggle_map = {
            "x²": ("x³", lambda: button_click("**3")),
            "xʸ": ("x⁽¹/ʸ⁾", lambda: button_click("**(1/y)")),
            "sin": ("asin", lambda: scientific_function_click("asin")),
            "cos": ("acos", lambda: scientific_function_click("acos")),
            "tan": ("atan", lambda: scientific_function_click("atan")),
            "√": ("¹/ₓ", lambda: button_click("1/")),
            "10ˣ": ("eˣ", lambda: button_click("math.e**")),
            "log": ("ln", lambda: scientific_function_click("ln")),
            "Exp": ("dms", lambda: button_click("dms(")),
            "Mod": ("deg", lambda: button_click("deg("))
        }

        for btn in calculator_buttons:
            current_text = btn["text"]

            # Toggle to scientific function
            if current_text in toggle_map:
                if btn not in original_states:
                    # Save the original text and command
                    original_states[btn] = (current_text, btn["command"])

                new_text, new_command = toggle_map[current_text]
                btn.config(text=new_text, command=new_command)

            # Reverse toggle to original function
            elif any(current_text == pair[0] for pair in toggle_map.values()):
                reverse_map = {v[0]: (k, v[1]) for k, v in toggle_map.items()}  # Reverse the mapping
                original_text, original_command = reverse_map[current_text]

                # Restore original state if it exists
                if btn in original_states:
                    original_text, original_command = original_states[btn]
                    btn.config(text=original_text, command=original_command)

    def balance_parentheses(expr):
        open_count = expr.count('(')
        close_count = expr.count(')')
        return expr + ')' * (open_count - close_count)

    def evaluate_expression():
        try:
            expression = expression_entry.get().strip()
            if not expression:
                result_label.config(text="Error: Empty expression")
                return

            expression = balance_parentheses(expression)

            # Replace operators and functions
            replacements = {
                'sin': 'sin', 'cos': 'cos', 'tan': 'tan',
                'log': 'log', 'ln': 'ln', 'sqrt': 'sqrt',
                'abs': 'abs', 'π': 'math.pi', 'e': 'math.e', '**': '**',
                '^': '**', '√': 'sqrt', 'asin': 'math.asin', 'acos': 'math.acos', 'atan': 'math.atan',
            }

            for old, new in replacements.items():
                expression = expression.replace(old, new)

            expression = re.sub(r'(\d+)!', r'factorial(\1)', expression)

            expression = expression.replace('+', ' + ').replace('-', ' - ').replace('*', ' * ').replace('/', ' / ')

            safe_dict = {
                'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                'sqrt': math.sqrt, 'abs': abs, 'log': math.log,
                'ln': math.log, 'factorial': math.factorial, 'math': math
            }

            result = eval(expression, {"__builtins__": None}, safe_dict)

            if isinstance(result, (int, float)):
                formatted_result = f"{result:.8g}"
            elif isinstance(result, complex):
                formatted_result = f"{result.real:.8g} + {result.imag:.8g}j" if result.imag != 0 else f"{result.real:.8g}"
            else:
                formatted_result = str(result)

            result_label.config(text=formatted_result)

        except Exception as e:
            result_label.config(text=f"Error: {str(e)}")

    def scientific_function_click(func_name):
        expression_entry.insert(END, f"{func_name}(")

    button_texts = [
        ('x²', 1, 0), ('xʸ', 1, 1), ('sin', 1, 2), ('cos', 1, 3), ('tan', 1, 4),
        ('√', 2, 0), ('10ˣ', 2, 1), ('log', 2, 2), ('Exp', 2, 3), ('Mod', 2, 4),
        ('↑', 3, 0), ('CE', 3, 1), ('C', 3, 2), ('←', 3, 3), ('/', 3, 4),
        ('π', 4, 0), ('7', 4, 1), ('8', 4, 2), ('9', 4, 3), ('*', 4, 4),
        ('e', 5, 0), ('4', 5, 1), ('5', 5, 2), ('6', 5, 3), ('-', 5, 4),
        ('x!', 6, 0), ('1', 6, 1), ('2', 6, 2), ('3', 6, 3), ('+', 6, 4),
        ('(', 7, 0), (')', 7, 1), ('0', 7, 2), ('.', 7, 3), ('=', 7, 4)
    ]

    calculator_buttons = []

    for (text, row, col) in button_texts:
        if text == '=':
            btn = Button(calculator_window, text=text, width=8, height=2, command=evaluate_expression)
        elif text == 'C':
            btn = Button(calculator_window, text=text, width=8, height=2, command=clear_entry)
        elif text == '10ˣ':
            btn = Button(calculator_window, text=text, width=8, height=2, command=lambda: button_click('10**'))
        elif text in ('sin', 'cos', 'tan', 'log', 'ln', 'abs', 'asin', 'acos', 'atan', '√'):
            btn = Button(calculator_window, text=text, width=8, height=2,
                         command=lambda t=text: scientific_function_click(t))
        elif text in ('π', 'e', 'j'):
            btn = Button(calculator_window, text=text, width=8, height=2, command=lambda t=text: button_click(t))
        elif text == 'x!':
            btn = Button(calculator_window, text=text, width=8, height=2, command=lambda: button_click('factorial('))
        elif text == '←':
            btn = Button(calculator_window, text='←', width=8, height=2, command=backspace)
        elif text == '↑':
            btn = Button(calculator_window, text='↑', width=8, height=2, command=toggle_scientific_calculator_buttons)
        else:
            btn = Button(calculator_window, text=text, width=8, height=2, command=lambda t=text: button_click(t))

        calculator_buttons.append(btn)
        btn.grid(row=row + 1, column=col, padx=2, pady=2)

    for i in range(9):
        calculator_window.grid_rowconfigure(i, weight=1)
    for i in range(5):
        calculator_window.grid_columnconfigure(i, weight=1)

    calculator_window.bind('<Return>', lambda event: evaluate_expression())
    calculator_window.bind('<Escape>', lambda event: clear_entry())

    calculator_window.mainloop()


def open_terminal_window():
    """
        Opens a new window functioning as a terminal within the application.

        This function creates a top-level window that simulates a terminal, allowing users to
        enter and execute commands with output displayed in the window.

        Parameters:
        None

        Returns:
        None
    """
    terminal_window = Toplevel()
    terminal_window.title("Terminal")
    terminal_window.geometry("600x400")

    # Create a ScrolledText widget to display terminal output
    output_text = scrolledtext.ScrolledText(terminal_window, height=20, width=80)
    output_text.pack(fill='both', expand=True)

    # Initialize a list to store command history
    command_history = []
    # Initialize a pointer to the current position in the command history
    history_pointer = [0]

    # Function to execute the command from the entry widget
    def execute_command(event=None):
        # Get the command from entry widget
        command = entry.get()
        if command.strip():
            # Add command to history and reset history pointer
            command_history.append(command)
            history_pointer[0] = len(command_history)

            try:
                # Run the command and get the output
                output = subprocess.check_output(command,
                                                 stderr=subprocess.STDOUT,
                                                 shell=True,
                                                 text=True,
                                                 cwd=os.getcwd())
                output_text.insert(END, f"{command}\n{output}\n")
            except subprocess.CalledProcessError as e:
                # If there's an error, print it to the output widget
                output_text.insert(END, f"Error: {e.output}", "error")
            # Clear the entry widget
            entry.delete(0, END)
            output_text.see(END)  # Auto-scroll to the bottom

    # Function to navigate the command history
    def navigate_history(event):
        if command_history:
            # UP arrow key pressed
            if event.keysym == 'Up':
                history_pointer[0] = max(0, history_pointer[0] - 1)
            # DOWN arrow key pressed
            elif event.keysym == 'Down':
                history_pointer[0] = min(len(command_history), history_pointer[0] + 1)
            # Get the command from history
            command = command_history[history_pointer[0]] if history_pointer[0] < len(command_history) else ''
            # Set the command to the entry widget
            entry.delete(0, END)
            entry.insert(0, command)

    # Create an Entry widget for typing commands
    entry = Entry(terminal_window, width=80)
    entry.pack(side='bottom', fill='x')
    entry.focus()
    entry.bind("<Return>", execute_command)
    # Bind the UP and DOWN arrow keys to navigate the command history
    entry.bind("<Up>", navigate_history)
    entry.bind("<Down>", navigate_history)


def open_audio_generation_window():
    def generate_audio():
        model_path = model_path_entry.get()
        prompt = prompt_entry.get()
        start_time = start_time_entry.get()
        duration = duration_entry.get()
        output_path = output_path_entry.get()

        if not model_path or not prompt or not start_time or not duration or not output_path:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        status_label.config(text="Starting audio generation...")
        generate_button.config(state=DISABLED)

        # Create a queue to capture the output
        output_queue = queue.Queue()

        # Run the audio generation in a separate thread
        threading.Thread(target=run_audio_generation, args=(model_path, prompt, start_time, duration, output_path, output_queue)).start()

        # Periodically check the queue for updates
        generation_window.after(100, lambda: update_progress(output_queue))

    def run_audio_generation(model_path, prompt, start_time, duration, output_path, output_queue):
        try:
            # Execute the command to generate the audio and capture the output
            process = subprocess.Popen([
                ".\\venv\\Scripts\\python.exe",
                ".\\lib\\stableAudioCpp.py",
                "--model_path", model_path,
                "--prompt", prompt,
                "--start", start_time,
                "--total", duration,
                "--out-dir", output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            for line in process.stdout:
                output_queue.put(line.strip())

            process.wait()

            if process.returncode == 0:
                output_queue.put("Audio generation completed successfully.")
                output_queue.put(f"LOAD_AUDIO:{output_path}")
                output_queue.put(f"AUDIO GENERATED AT {output_path}")
            else:
                output_queue.put(f"Audio generation failed: {process.stderr.read()}")

        except subprocess.CalledProcessError as e:
            output_queue.put(f"Audio generation failed: {e}")
            return

        output_queue.put("DONE")

    def update_progress(output_queue):
        try:
            while not output_queue.empty():
                line = output_queue.get_nowait()
                if line.startswith("LOAD_AUDIO:"):
                    load_audio(line.split(":", 1)[1])
                elif line.startswith("AUDIO GENERATED AT"):
                    status_label.config(text=line)
                else:
                    status_label.config(text=f"Progress: {line}")
        except queue.Empty:
            pass
        finally:
            # Continue checking the queue
            if not "AUDIO GENERATED AT" in status_label.cget("text") and not "failed" in status_label.cget("text"):
                generation_window.after(100, lambda: update_progress(output_queue))
            else:
                generate_button.config(state=NORMAL)

    def load_audio(audio_path):
        try:
            # Implement the logic to load and preview audio
            status_label.config(text=f"Audio generated at {audio_path}")
        except Exception as e:
            messagebox.showerror("Audio Error", f"Could not load audio: {e}")

    def select_model_path():
        path = filedialog.askopenfilename(filetypes=[("Checkpoint Files", "*.ckpt")])
        model_path_entry.delete(0, END)
        model_path_entry.insert(0, path)

    def select_output_path():
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Files", "*.wav")])
        output_path_entry.delete(0, END)
        output_path_entry.insert(0, path)

    generation_window = Toplevel()
    generation_window.title("Audio Generation")
    generation_window.geometry("480x580")

    Label(generation_window, text="Model Path:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
    model_path_entry = Entry(generation_window, width=30)
    model_path_entry.grid(row=0, column=1, padx=10, pady=5)
    Button(generation_window, text="Browse", command=select_model_path).grid(row=0, column=2, padx=10, pady=5)

    Label(generation_window, text="Prompt:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    prompt_entry = Entry(generation_window, width=30)
    prompt_entry.grid(row=1, column=1, padx=10, pady=5)

    Label(generation_window, text="Start Time:").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    start_time_entry = Entry(generation_window, width=30)
    start_time_entry.grid(row=2, column=1, padx=10, pady=5)

    Label(generation_window, text="Duration:").grid(row=3, column=0, padx=10, pady=5, sticky='e')
    duration_entry = Entry(generation_window, width=30)
    duration_entry.grid(row=3, column=1, padx=10, pady=5)

    Label(generation_window, text="Output Path:").grid(row=4, column=0, padx=10, pady=5, sticky='e')
    output_path_entry = Entry(generation_window, width=30)
    output_path_entry.grid(row=4, column=1, padx=10, pady=5)
    Button(generation_window, text="Save As", command=select_output_path).grid(row=4, column=2, padx=10, pady=5)

    generate_button = Button(generation_window, text="Generate Audio", command=generate_audio)
    generate_button.grid(row=5, column=0, columnspan=3, pady=10)

    status_label = Label(generation_window, text="Status: Waiting to start...", width=60, anchor='w')
    status_label.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

    Label(generation_window, text="Audio Preview:").grid(row=7, column=0, columnspan=3, pady=10)
    audio_label = Label(generation_window, text="No audio generated yet", width=40, height=20, relief="sunken")
    audio_label.grid(row=8, column=0, columnspan=3, padx=10, pady=10)

 
def open_music_generation_window():
    pass


def open_image_generation_window():
    def generate_image():
        model_path = model_path_entry.get()
        prompt = prompt_entry.get()
        output_path = output_path_entry.get()

        if not model_path or not prompt or not output_path:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        status_label.config(text="Starting image generation...")
        generate_button.config(state=DISABLED)

        # Create a queue to capture the output
        output_queue = queue.Queue()

        # Run the image generation in a separate thread
        threading.Thread(target=run_image_generation, args=(model_path, prompt, output_path, output_queue)).start()

        # Periodically check the queue for updates
        generation_window.after(100, lambda: update_progress(output_queue))

    def run_image_generation(model_path, prompt, output_path, output_queue):
        try:
            # Execute the command to generate the image and capture the output
            process = subprocess.Popen([
                ".\\venv\\Scripts\\python.exe",
                ".\\lib\\stableDiffusionCpp.py",
                "--model_path", model_path,
                "--prompt", prompt,
                "--output_path", output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            for line in process.stdout:
                output_queue.put(line.strip())

            process.wait()

            if process.returncode == 0:
                output_queue.put("Image generation completed successfully.")
                output_queue.put(f"LOAD_IMAGE:{output_path}")
                output_queue.put(f"IMAGE GENERATED AT {output_path}")
            else:
                output_queue.put(f"Image generation failed: {process.stderr.read()}")

        except subprocess.CalledProcessError as e:
            output_queue.put(f"Image generation failed: {e}")

        output_queue.put("DONE")

    def update_progress(output_queue):
        try:
            while not output_queue.empty():
                line = output_queue.get_nowait()
                if line.startswith("LOAD_IMAGE:"):
                    load_image(line.split(":", 1)[1])
                elif line.startswith("IMAGE GENERATED AT"):
                    status_label.config(text=line)
                else:
                    status_label.config(text=f"Progress: {line}")
        except queue.Empty:
            pass
        finally:
            # Continue checking the queue
            if not "IMAGE GENERATED AT" in status_label.cget("text") and not "failed" in status_label.cget("text"):
                generation_window.after(100, lambda: update_progress(output_queue))
            else:
                generate_button.config(state=NORMAL)

    def load_image(image_path):
        try:
            img = Image.open(image_path)
            img = img.resize((250, 250), Image.ANTIALIAS)
            img_tk = ImageTk.PhotoImage(img)
            image_label.config(image=img_tk)
            image_label.image = img_tk
        except Exception as e:
            messagebox.showerror("Image Error", f"Could not load image: {e}")

    def select_model_path():
        path = filedialog.askopenfilename(filetypes=[("Checkpoint Files", "*.ckpt")])
        model_path_entry.delete(0, END)
        model_path_entry.insert(0, path)

    def select_output_path():
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Files", "*.png")])
        output_path_entry.delete(0, END)
        output_path_entry.insert(0, path)

    generation_window = Toplevel()
    generation_window.title("Image Generation")
    generation_window.geometry("480x580")

    Label(generation_window, text="Model Path:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
    model_path_entry = Entry(generation_window, width=30)
    model_path_entry.grid(row=0, column=1, padx=10, pady=5)
    Button(generation_window, text="Browse", command=select_model_path).grid(row=0, column=2, padx=10, pady=5)

    Label(generation_window, text="Prompt:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    prompt_entry = Entry(generation_window, width=30)
    prompt_entry.grid(row=1, column=1, padx=10, pady=5)

    Label(generation_window, text="Output Path:").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    output_path_entry = Entry(generation_window, width=30)
    output_path_entry.grid(row=2, column=1, padx=10, pady=5)
    Button(generation_window, text="Save As", command=select_output_path).grid(row=2, column=2, padx=10, pady=5)

    generate_button = Button(generation_window, text="Generate Image", command=generate_image)
    generate_button.grid(row=3, column=0, columnspan=3, pady=10)

    status_label = Label(generation_window, text="Status: Waiting to start...", width=60, anchor='w')
    status_label.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

    Label(generation_window, text="Image Preview:").grid(row=5, column=0, columnspan=3, pady=10)
    image_label = Label(generation_window, text="No image generated yet", width=40, height=20, relief="sunken")
    image_label.grid(row=6, column=0, columnspan=3, padx=10, pady=10)


def add_current_main_opened_script(include_main_script):
    global include_main_script_in_command
    include_main_script_in_command = include_main_script


def add_current_selected_text(include_selected_text):
    global include_selected_text_in_command
    include_selected_text_in_command = include_selected_text


def open_ai_assistant_window(session_id=None):
    """
    Opens a window for interacting with an AI assistant.

    This function creates a new window where users can input commands or queries, and the AI assistant
    processes and displays the results. It also provides options for rendering Markdown to HTML.

    Parameters:
    None

    Returns:
    None
    """
    global original_md_content, markdown_render_enabled, rendered_html_content, session_data, url_data

    def start_llama_cpp_python_server():
        file_path = find_gguf_file()
        print("THE PATH TO THE MODEL IS:\t", file_path)
        #  subprocess.run(["python", "-m", "llama_cpp.server", "--port", "8004", "--model",
        #  ".\\src\\models\\model\\llama-2-7b-chat.Q4_K_M.gguf"])

    def open_ai_server_settings_window():
        def toggle_display(selected_server):
            server_info = server_details.get(selected_server, {})
            server_url = server_info.get("server_url", "")
            api_key = server_info.get("api_key", "")

            server_url_entry.delete(0, END)
            server_url_entry.insert(0, server_url)
            api_key_entry.delete(0, END)
            api_key_entry.insert(0, api_key)

            if selected_server in ["lmstudio", "ollama", "openai", "llama-cpp-python", "claude"]:
                server_url_entry.grid()
                server_url_label.grid()
            else:
                server_url_entry.grid_remove()
                server_url_label.grid_remove()

            if selected_server == "openai" or selected_server == "claude":
                api_key_entry.grid()
                api_key_label.grid()
            else:
                api_key_entry.grid_remove()
                api_key_label.grid_remove()

        def load_server_details():
            try:
                with open("data/llm_server_providers.json", 'r') as server_file:
                    return json.load(server_file)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                messagebox.showerror("Error", f"Failed to load server details: {str(e)}")
                return {}

        def save_ai_server_settings():
            selected = selected_server.get()
            server_url = server_url_entry.get()
            api_key = api_key_entry.get()

            write_config_parameter("options.network_settings.last_selected_llm_server_provider", selected)
            write_config_parameter("options.network_settings.server_url", server_url)
            write_config_parameter("options.network_settings.api_key", api_key)

            messagebox.showinfo("AI Server Settings", "Settings saved successfully!")
            settings_window.destroy()

        server_details = load_server_details()

        settings_window = Toplevel()
        settings_window.title("AI Server Settings")
        settings_window.geometry("400x300")

        Label(settings_window, text="Select Server:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        selected_server = StringVar(settings_window)
        last_selected = read_config_parameter("options.network_settings.last_selected_llm_server_provider")
        selected_server.set(last_selected if last_selected in server_details else next(iter(server_details), ""))

        server_options = list(server_details.keys())
        server_dropdown = OptionMenu(settings_window, selected_server, *server_options)
        server_dropdown.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        server_url_label = Label(settings_window, text="Server URL:")
        server_url_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        server_url_entry = Entry(settings_window, width=25)
        server_url_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        api_key_label = Label(settings_window, text="API Key:")
        api_key_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        api_key_entry = Entry(settings_window, width=25, show="*")
        api_key_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        Button(settings_window, text="Save", command=save_ai_server_settings).grid(row=3, column=0, columnspan=2,
                                                                                   pady=10)

        selected_server.trace("w", lambda *args: toggle_display(selected_server.get()))
        toggle_display(selected_server.get())

        settings_window.columnconfigure(1, weight=1)
        settings_window.mainloop()

    def open_ai_server_agent_settings_window():
        def load_agents():
            """
            Load agents from the JSON file located at ScriptsEditor/data/agents.json.

            Returns:
            agents (list): A list of agents loaded from the JSON file.
            """
            # Get the directory of the current script (tool_functions.py)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Construct the path to the JSON file relative to the current script
            json_file_path = os.path.join(current_dir, '..', '..', 'data', 'agents.json')

            # Normalize the path to handle different operating systems
            json_file_path = os.path.normpath(json_file_path)

            # Print the JSON path for debugging
            print("JSON PATH:", json_file_path)

            try:
                with open(json_file_path, "r") as file:
                    agents = json.load(file)
                return agents
            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {json_file_path}")
                return []
            except json.JSONDecodeError:
                messagebox.showerror("Error", f"Error decoding JSON from file: {json_file_path}")
                return []

        def update_instructions(selected_agent):
            global selected_agent_var
            selected_agent_var = selected_agent
            for agent in agents:
                if agent["name"] == selected_agent:
                    instructions_text.delete("1.0", "end")
                    instructions_text.insert("1.0", agent["instructions"])
                    # Update the temperature entry with the corresponding temperature
                    temperature_entry.delete(0, "end")  # Clear the content of the Entry widget
                    temperature_entry.insert(0, agent["temperature"])  # Insert the temperature
                    break

        def save_agent_settings():
            global selected_agent_var
            # Save selected agent and temperature to user_config.json
            selected_agent = selected_agent_var
            print("SAVE_AGENT_SETTINTS!!!\n", selected_agent, "\n", "* " * 25)
            selected_agent_var = selected_agent
            temperature = temperature_entry.get()
            # Pass selected_agent_var to execute_ai_assistant_command
            execute_ai_assistant_command(add_current_main_opened_script_var, add_current_selected_text_var, entry.get())
            # Update the status label with the name of the selected agent
            status_label_var.set(selected_agent)
            messagebox.showinfo("Agent Settings", "Settings saved successfully!")
            settings_window.destroy()

        agents = load_agents()
        if not agents:
            return

        settings_window = Toplevel()
        settings_window.title("AI Server Agent Settings")

        Label(settings_window, text="Select Agent:").grid(row=0, column=0)
        selected_agent_var = StringVar(settings_window)
        selected_agent_var.set(agents[0]["name"])  # Set default selection

        agent_options = [agent["name"] for agent in agents]
        agent_dropdown = OptionMenu(settings_window, selected_agent_var, *agent_options, command=update_instructions)
        agent_dropdown.grid(row=0, column=1)

        Label(settings_window, text="Instructions:").grid(row=1, column=0)
        instructions_text = scrolledtext.ScrolledText(settings_window, height=7, width=50)
        instructions_text.grid(row=1, column=1, columnspan=2)

        agent_temperature = [agent["temperature"] for agent in agents]
        Label(settings_window, text="Temperature:").grid(row=2, column=0)
        temperature_entry = Entry(settings_window)
        temperature_entry.grid(row=2, column=1)

        # Add Persistent Agent Selection checkbox
        persistent_agent_selection_checkbox = Checkbutton(settings_window, text="Persistent Agent Selection", variable=persistent_agent_selection_var)
        persistent_agent_selection_checkbox.grid(row=3, columnspan=2)

        Button(settings_window, text="Save", command=lambda: save_agent_settings()).grid(row=4, column=0)
        Button(settings_window, text="Cancel", command=settings_window.destroy).grid(row=4, column=1)

        # Initial update of instructions
        update_instructions(selected_agent_var.get())

    original_md_content = ""
    rendered_html_content = ""
    markdown_render_enabled = False
    session_data = []
    url_data = []

    ai_assistant_window = Toplevel()
    ai_assistant_window.title("AI Assistant")
    ai_assistant_window.geometry("800x600")

    # Create a Menu Bar
    menu_bar = Menu(ai_assistant_window)
    ai_assistant_window.config(menu=menu_bar)

    # Create a 'Settings' Menu
    settings_menu = Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Settings", menu=settings_menu)
    menu_bar.add_command(label="AI Server Settings", command=open_ai_server_settings_window)
    menu_bar.add_command(label="Agent Options", command=open_ai_server_agent_settings_window)
    render_markdown_var = IntVar()
    settings_menu.add_checkbutton(
        label="Toggle Markdown-to-HTML Rendering",
        onvalue=1,
        offvalue=0,
        variable=render_markdown_var,
        command=lambda: toggle_render_markdown(render_markdown_var.get())
    )

    add_current_main_opened_script_var = IntVar()
    settings_menu.add_checkbutton(
        label="Include Main Script in AI Context",
        onvalue=1,
        offvalue=0,
        variable=add_current_main_opened_script_var,
        command=lambda: add_current_main_opened_script(add_current_main_opened_script_var.get())
    )

    add_current_selected_text_var = IntVar()
    settings_menu.add_checkbutton(
        label="Include Selected Text from Script",
        onvalue=1,
        offvalue=0,
        variable=add_current_selected_text_var,
        command=lambda: add_current_selected_text(add_current_selected_text_var.get())
    )

    persistent_agent_selection_var = IntVar()
    '''settings_menu.add_checkbutton(
        label="Persistent Agent Selection",
        onvalue=1,
        offvalue=0,
        variable=persistent_agent_selection_var,
        #command=lambda: add_current_selected_text(add_current_selected_text_var.get())
    )'''

    # --- Session List with Sessions and Documents Sections ---

    session_list_frame = Frame(ai_assistant_window)  # Frame to hold the entire session_list structure
    session_list_frame.pack(side="left", fill="y")

    # --- Sessions Section ---
    Label(session_list_frame, text="SESSIONS", font=("Helvetica", 10, "bold")).pack(fill="x")

    sessions_list = Listbox(session_list_frame)  # Scrollable list for sessions
    sessions_list.pack(fill="both", expand=True)

    # --- Visual Separator ---
    Separator(session_list_frame, orient="horizontal").pack(fill="x", pady=5)

    # --- Links Section ---
    Label(session_list_frame, text="LINKS", font=("Helvetica", 10, "bold")).pack(fill="x")

    links_frame = Frame(session_list_frame)
    links_frame.pack(fill="both", expand=True)

    links_list = Listbox(links_frame)
    links_list.pack(fill="both", expand=True)

    def refresh_links_list():
        print("Refreshing links list...")
        links_list.delete(0, END)
        for idx, url in enumerate(url_data):
            links_list.insert(END, url)

    def add_new_link():
        print("Adding new link...")
        new_url = simpledialog.askstring("Add New Link", "Enter URL:")
        if new_url:
            url_data.append(new_url)
            refresh_links_list()

    def delete_selected_link():
        print("Deleting selected link...")
        selected_link_index = links_list.curselection()
        if selected_link_index:
            url_data.pop(selected_link_index[0])
            refresh_links_list()

    def edit_selected_link():
        selected_link_index = links_list.curselection()
        if selected_link_index:
            selected_link = links_list.get(selected_link_index)
            new_url = simpledialog.askstring("Edit Link", "Enter new URL:", initialvalue=selected_link)
            if new_url:
                url_data[selected_link_index[0]] = new_url
                refresh_links_list()

    # Create Right-Click Context Menu for Links List
    links_context_menu = Menu(ai_assistant_window, tearoff=0)

    #links_context_menu.add_command(label="Delete Selected Link", command=delete_selected_link)
    #links_context_menu.add_command(label="Add New Link", command=add_new_link)  # Remove all items from the menu if no link is selected

    def show_links_context_menu(event):
        if links_list.size() == 0:  # Check if there are no links in the list
            links_context_menu.delete(0, END)  # Clear all existing menu items
            links_context_menu.add_command(label="Add New Link", command=add_new_link)
        else:
            links_context_menu.delete(0, END)  # Clear all existing menu items
            selected_link_index = links_list.curselection()
            if selected_link_index:
                links_context_menu.add_command(label="Edit Link", command=edit_selected_link)
                links_context_menu.add_command(label="Delete Selected Link", command=delete_selected_link)
            else:
                links_context_menu.add_command(label="Add New Link", command=add_new_link)
        links_context_menu.post(event.x_root, event.y_root)

    links_list.bind("<Button-3>", show_links_context_menu)

    # Populate the links_list initially (you can start with an empty list)
    refresh_links_list()

    # --- Visual Separator ---
    Separator(session_list_frame, orient="horizontal").pack(fill="x", pady=5)

    # --- Documents Section ---
    Label(session_list_frame, text="DOCUMENTS", font=("Helvetica", 10, "bold")).pack(fill="x")

    documents_frame = Frame(session_list_frame)
    documents_frame.pack(fill="both", expand=True)

    # List to store document paths and checkbutton states (no local copies)
    document_paths = []
    document_checkbuttons = []

    def refresh_documents_list():
        print("Refreshing documents list...")
        for widget in documents_frame.winfo_children():
            widget.destroy()
        for idx, doc_path in enumerate(document_paths):
            doc_name = os.path.basename(doc_path)
            var = IntVar()
            checkbutton = Checkbutton(documents_frame, text=doc_name, variable=var)
            checkbutton.pack(anchor="w")
            document_checkbuttons.append((doc_path, var))

    def add_new_document():
        print("Adding new document...")
        file_path = filedialog.askopenfilename(
            initialdir=".",
            title="Select a PDF document",
            filetypes=(("PDF files", "*.pdf"), ("all files", "*.*"))
        )
        if file_path:
            document_paths.append(file_path)
            refresh_documents_list()

    # Populate the documents_list initially (you can start with an empty list)
    refresh_documents_list()

    # Create Right-Click Context Menu for Documents List
    documents_context_menu = Menu(ai_assistant_window, tearoff=0)
    documents_context_menu.add_command(label="Add New Document", command=add_new_document)

    def show_documents_context_menu(event):
        documents_context_menu.post(event.x_root, event.y_root)

    documents_frame.bind("<Button-3>", show_documents_context_menu)

    # Create the output text widget
    output_text = scrolledtext.ScrolledText(ai_assistant_window, height=20, width=80)
    output_text.pack(fill='both', expand=True)

    html_display = HTMLLabel(ai_assistant_window, html="")
    html_display.pack(side='left', fill='both', expand=False)
    html_display.pack_forget()  # Initially hide the HTML display

    entry = Entry(ai_assistant_window, width=30)
    entry.pack(side='bottom', fill='x')
    Tooltip(entry, "Input text prompt")

    status_label_var = StringVar()
    status_label = Label(ai_assistant_window, textvariable=status_label_var)
    status_label.pack(side='bottom')  # This will keep the status label at the bottom
    status_label_var.set("READY")
    output_text.tag_configure("user", foreground="#a84699")
    output_text.tag_configure("ai", foreground="#6a7fd2")
    output_text.tag_configure("error", foreground="red")
    output_text.insert(END, "> ", "ai")

    entry.focus()

    def on_md_content_change(event=None):
        global original_md_content
        original_md_content = script_text.get("1.0", END)
        if markdown_render_enabled:
            update_html_content()

    def update_html_content():
        global rendered_html_content
        rendered_html_content = markdown.markdown(original_md_content)
        html_display.set_html(rendered_html_content)

    def update_html_content_thread():
        global rendered_html_content
        rendered_html_content = markdown.markdown(original_md_content)
        html_display.set_html(rendered_html_content)

    def toggle_render_markdown(is_checked):
        global markdown_render_enabled
        markdown_render_enabled = bool(is_checked)

        if markdown_render_enabled:
            threading.Thread(target=update_html_content_thread).start()
            output_text.pack_forget()
            html_display.pack(fill='both', expand=True)
        else:
            output_text.delete("1.0", "end")
            output_text.insert("1.0", original_md_content)
            html_display.pack_forget()
            output_text.pack(fill='both', expand=True)

    def navigate_history(event):
        if command_history:
            # UP arrow key pressed
            if event.keysym == 'Up':
                history_pointer[0] = max(0, history_pointer[0] - 1)
            # DOWN arrow key pressed
            elif event.keysym == 'Down':
                history_pointer[0] = min(len(command_history), history_pointer[0] + 1)
            # Get the command from history
            command = command_history[history_pointer[0]] if history_pointer[0] < len(command_history) else ''
            # Set the command to the entry widget
            entry.delete(0, END)
            entry.insert(0, command)

    def stream_output(process):
        global current_session
        ai_response_buffer = ""  # Initialize a buffer to collect the AI response incrementally

        try:
            while True:
                char = process.stdout.read(1)  # Read one character at a time
                if char:
                    ai_response_buffer += char  # Append character to the AI response buffer

                    if markdown_render_enabled:
                        update_html_content()
                    else:
                        output_text.insert(END, char, "ai")
                        output_text.see(END)

                    # Optionally: if you want to append to the session on every character, do it here.
                    # This can be resource-intensive, so it's usually better to wait until the response is complete.

                elif process.poll() is not None:
                    break  # Exit the loop if the process has terminated

            # Once the AI response is fully collected, add it to the session file
            if ai_response_buffer:
                current_session.add_message("ai", ai_response_buffer)

        except Exception as e:
            output_text.insert(END, f"Error: {e}\n", "error")
        finally:
            on_processing_complete()

    def on_processing_complete():
        load_selected_agent()
        entry.config(state='normal')  # Re-enable the entry widget
        status_label_var.set("READY")  # Update label to show AI is processing

    # Add a function to store the selected agent for persistence
    def store_selected_agent(selected_agent):
        # Store the selected agent in a config file for persistence
        with open("data/agent_config.json", "w") as config_file:
            json.dump({"selected_agent": selected_agent}, config_file)

    # Add code to load the selected agent from the config file at startup
    def load_selected_agent():
        try:
            with open("data/config.json", "r") as config_file:
                config_data = json.load(config_file)
                return config_data.get("selected_agent", selected_agent_var)
        except FileNotFoundError:
            pass  # Ignore if the config file doesn't exist

    def execute_ai_assistant_command(opened_script_var, selected_text_var, ai_command):
        global original_md_content, selected_agent_var, current_session

        if not current_session:
            create_session()

        if ai_command.strip():
            script_content = ""
            if selected_text_var.get():
                try:
                    script_content = "```\n" + script_text.get(script_text.tag_ranges("sel")[0],
                                                               script_text.tag_ranges("sel")[1]) + "```\n\n"
                except:
                    messagebox.showerror("Error", "No text selected in main script window.")
                    return
            elif opened_script_var.get():
                script_content = "```\n" + script_text.get("1.0", END) + "```\n\n"

            combined_command = f"{script_content}{ai_command}"

            # Add user message to the session and save
            current_session.add_message("user", combined_command)

            # Insert the user command with a newline and a visual separator
            original_md_content += f"\n{combined_command}\n"
            original_md_content += "-" * 80 + "\n"  # A line of dashes as a separator


            output_text.insert("end", f"You: {combined_command}\n", "user")
            output_text.insert("end", "-" * 80 + "\n")
            entry.delete(0, END)
            entry.config(state='disabled')  # Disable entry while processing
            status_label_var.set("AI is thinking...")  # Update label to show AI is processing

            ai_script_path = 'src/models/ai_assistant.py'

            # Pass the selected agent name to create_ai_command function if provided
            try:
                selected_agent = selected_agent_var
            except Exception as e:
                selected_agent_var = "Assistant"
                selected_agent = selected_agent_var
            if persistent_agent_selection_var.get():
                # Store the selected agent in a config file for persistence
                store_selected_agent(selected_agent)
            command = create_ai_command(ai_script_path, combined_command, selected_agent)

            print("SAVE AI MESSAGE BEFORE")
            process_ai_command(command)
            print("SAVE AI MESSAGE END")
        else:
            entry.config(state='normal')  # Re-enable the entry widget if no command is entered

    def create_ai_command(ai_script_path, user_prompt, agent_name=None):
        if agent_name:
            return ['python', ai_script_path, user_prompt, agent_name]
        else:
            return ['python', ai_script_path, user_prompt]

    def process_ai_command(command):
        global process, selected_agent_var

        try:
            # Terminate existing subprocess if it exists
            if 'process' in globals() and process.poll() is None:
                process.terminate()

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                       encoding='utf-8', bufsize=1)
            threading.Thread(target=stream_output, args=(process,)).start()

        except Exception as e:
            output_text.insert(END, f"Error: {e}\n")
            on_processing_complete()
        finally:
            update_html_content()
            # Update the status label with the name of the selected agent
            status_label_var.set(f"{selected_agent_var} is thinking")  # Update label to show the agent is processing


    def read_ai_command(command_name, user_prompt):
        # Path to commands.json file
        commands_file = "data/commands.json"
        try:
            # Load commands data from commands.json
            with open(commands_file, 'r') as f:
                commands_data = json.load(f)

            # Helper function to find the command in a submenu recursively
            def find_command(commands, command_name):
                for command in commands:
                    if command['name'] == command_name:
                        return command
                    if 'submenu' in command:
                        result = find_command(command['submenu'], command_name)
                        if result:
                            return result
                return None

            # Find the matching command
            matching_command = find_command(commands_data['customCommands'], command_name)

            if matching_command:
                # Extract the original prompt from the matching command
                original_prompt = matching_command.get("prompt", "")

                # Replace '{{{ input }}}' with the user-provided prompt
                formatted_prompt = original_prompt.replace("{{{ input }}}", user_prompt)

                # Return the formatted prompt
                return formatted_prompt
            else:
                return f"Command '{command_name}' not found."

        except FileNotFoundError:
            return f"Error: File '{commands_file}' not found."
        except json.JSONDecodeError:
            return f"Error: Failed to decode JSON from '{commands_file}'."

    def ai_assistant_rightclick_menu(command):
        selected_text = output_text.get("sel.first", "sel.last")
        if selected_text.strip():
            fix_user_prompt = read_ai_command(command, selected_text)
            execute_ai_assistant_command(add_current_main_opened_script_var, add_current_selected_text_var,
                                         fix_user_prompt)

    def nlp_custom():
        selected_text = output_text.get("sel.first", "sel.last")
        if selected_text.strip():
            print(read_ai_command("code-optimize", selected_text))
            #  TODO: Add custom command window

    def show_context_menu(event):
        # Load commands from JSON file
        commands_file = "data/commands.json"

        def load_commands():
            try:
                with open(commands_file, 'r') as f:
                    commands_data = json.load(f)
                return commands_data['customCommands']
            except (FileNotFoundError, json.JSONDecodeError) as e:
                messagebox.showerror("Error", f"Failed to load commands: {e}")
                return []

        def add_commands_to_menu(menu, commands):
            for command in commands:
                if 'submenu' in command:
                    submenu = Menu(menu, tearoff=0)
                    menu.add_cascade(label=command['name'], menu=submenu)
                    add_commands_to_menu(submenu, command['submenu'])
                else:
                    if command['name'] == "---":
                        menu.add_separator()
                    else:
                        menu.add_command(label=command['description'],
                                         command=lambda cmd=command: ai_assistant_rightclick_menu(cmd['name']))
                        if 'description' in command:
                            Tooltip(menu, command['description'])

        # Create the context menu
        context_menu = Menu(root, tearoff=0)
        context_menu.add_command(label="Cut", command=cut)
        context_menu.add_command(label="Copy", command=copy)
        context_menu.add_command(label="Paste", command=paste)
        context_menu.add_command(label="Duplicate", command=duplicate)
        context_menu.add_command(label="Select All", command=duplicate)
        context_menu.add_separator()

        # Load and add custom commands from JSON
        custom_commands = load_commands()
        add_commands_to_menu(context_menu, custom_commands)

        context_menu.add_separator()
        context_menu.add_command(label="Custom AI request", command=nlp_custom)

        # Post the context menu at the cursor location
        context_menu.post(event.x_root, event.y_root)

        # Give focus to the context menu
        context_menu.focus_set()

        def destroy_menu():
            context_menu.unpost()

        # Bind the <Leave> event to destroy the context menu when the mouse cursor leaves it
        context_menu.bind("<Leave>", lambda e: destroy_menu())

        # Bind the <FocusOut> event to destroy the context menu when it loses focus
        context_menu.bind("<FocusOut>", lambda e: destroy_menu())

    output_text.bind("<Button-3>", show_context_menu)

    output_text.bind("<<TextModified>>", on_md_content_change)
    output_text.see(END)

    entry.bind("<Return>", lambda event: execute_ai_assistant_command(
        add_current_main_opened_script_var,
        add_current_selected_text_var,
        entry.get())
               )

    entry.bind("<Up>", navigate_history)
    entry.bind("<Down>", navigate_history)

    # Initialize a list to store command history
    command_history = []
    # Initialize a pointer to the current position in the command history
    history_pointer = [0]

    class Session:
        def __init__(self, name, load_existing=False):
            self.id = datetime.now().strftime("%Y%m%d%H%M%S")
            self.name = name
            self.file_path = os.path.join("data", "conversations", self.id, f"session_{self.id}.json")
            self.messages = []  # Initialize messages list here

            if load_existing and os.path.exists(self.file_path):
                self.load()
            else:
                self.save()  # Save to initialize file

        def add_message(self, role, content):
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            self.messages.append(message)  # Append to messages list
            self.save()  # Save the updated list to file

        def save(self):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            data = {"session_id": self.id, "session_name": self.name, "messages": self.messages}
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        def load(self):
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.messages = data.get("messages", [])  # Load existing messages, if any

    def create_session():
        global current_session, session_data
        session_name = f"Session {len(session_data) + 1}"
        print("CREATING SESSION:\t", session_name)
        current_session = Session(session_name)  # Initialize only once per session
        session_data.append(current_session)
        update_sessions_list()
        select_session(len(session_data) - 1)  # Automatically select the new session

    def update_chat_display():
        if current_session and os.path.exists(current_session.file_path):
            with open(current_session.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                output_text.delete("1.0", END)
                for message in data["messages"]:
                    role_tag = "user" if message["role"] == "user" else "ai"
                    output_text.insert(END, f"{message['role']}: {message['content']}\n", role_tag)
                output_text.see(END)
        else:
            print("Session file not found or no session is currently active.")

    def load_session(session_id):
        global current_session
        for session in session_data:
            if session.id == session_id:
                current_session = session
                break
        update_chat_display()

    def select_session(index):
        sessions_list.selection_clear(0, END)
        sessions_list.selection_set(index)
        sessions_list.activate(index)
        sessions_list.see(index)
        write_config_parameter("options.network_settings.last_selected_session_id", index + 1)
        update_chat_display()

    def update_sessions_list():
        sessions_list.delete(0, END)
        for session in session_data:
            sessions_list.insert(END, session.name)

    def on_session_select(event):
        selected_indices = sessions_list.curselection()
        if selected_indices:
            index = selected_indices[0]
            load_session(session_data[index].id)

    def show_session_context_menu(event, session_index):
        session_context_menu = Menu(ai_assistant_window, tearoff=0)
        session_context_menu.add_command(label="Share Chat", command=lambda: save_session(session_index))
        session_context_menu.add_command(label="Change Name", command=lambda: rename_session(session_index))
        session_context_menu.add_command(label="Archive", command=lambda: archive_session(session_index))
        session_context_menu.add_command(label="Delete", command=lambda: delete_session(session_index))
        session_context_menu.post(event.x_root, event.y_root)

    def save_session(session_index):
        print(f"Saving session {session_index}...")
        session = session_data[session_index]
        with open(f"session_{session['id']}.txt", "w") as f:
            f.write(session["content"])
            messagebox.showinfo("Delete Session", f"Session {session['id']} deleted successfully.")

    def rename_session(session_index):
        print(f"Renaming session {session_index}...")
        session = session_data[session_index]
        new_name = simpledialog.askstring("Rename Session", "Enter new session name:")
        if new_name:
            session["name"] = new_name
            update_sessions_list()

    def archive_session(session_index):
        print(f"Archiving session {session_index}...")
        messagebox.showinfo("Archive Session", f"Session {session_data[session_index]['id']} archived successfully.")

    def delete_session(session_index):
        print(f"Deleting session {session_index}...")
        session = session_data.pop(session_index)
        update_sessions_list()
        messagebox.showinfo("Delete Session", f"Session {session['id']} deleted successfully.")

    def handle_session_click(event):
        session_context_menu = Menu(ai_assistant_window, tearoff=0)
        try:
            session_index = sessions_list.curselection()[0]
            session = session_data[session_index]
            session_context_menu.add_command(label="Share Chat", command=lambda: save_session(session_index))
            session_context_menu.add_command(label="Change Name", command=lambda: rename_session(session_index))
            session_context_menu.add_command(label="Archive", command=lambda: archive_session(session_index))
            session_context_menu.add_command(label="Delete", command=lambda: delete_session(session_index))
            session_context_menu.add_separator()
            session_context_menu.add_command(label="Create New Session", command=create_session)
        except IndexError:
            session_index = 0

        session_context_menu.add_command(label="Create New Session", command=create_session)
        session_context_menu.post(event.x_root, event.y_root)

    sessions_list.bind("<Button-3>", handle_session_click)

    #create_session_button = Button(ai_assistant_window, text="Create New Session", command=create_session)
    #create_session_button.pack(side="left")

    ai_assistant_window.mainloop()


# Define _create_webview_process at the top level
def _create_webview_process(title, url):
    webview.create_window(title, url, width=800, height=600, text_select=True, zoomable=True)
    webview.start(private_mode=True)


def open_webview(title, url):
    webview_process = multiprocessing.Process(target=_create_webview_process, args=(title, url,))
    webview_process.start()


def open_url_in_webview(url):
    webview.create_window("My Web Browser", url, width=800, height=600, text_select=True, zoomable=True,
                          easy_drag=True, confirm_close=True, background_color="#1f1f1f")
    webview.start(private_mode=True)


def on_go_button_clicked(entry, window):
    url = entry.get()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url  # Prepend 'https://' if not present
    on_close(window)
    webview_process = multiprocessing.Process(target=open_url_in_webview, args=(url,))
    webview_process.start()


def create_url_input_window():
    # Change this to Toplevel
    window = Toplevel(root)  # Use the existing root from Tkinter
    window.title("Enter URL")

    entry = Entry(window, width=50)
    entry.insert(0, "https://duckduckgo.com")
    entry.pack(padx=10, pady=10)
    entry.focus()

    go_button = Button(window, text="Go", command=lambda: on_go_button_clicked(entry, window))
    go_button.pack(pady=5)

    window.bind('<Return>', lambda event: on_go_button_clicked(entry, window))


def on_enter(event, entry, window):
    """Event handler to trigger navigation when Enter key is pressed."""
    on_go_button_clicked(entry, window)


def on_close(window):
    # Terminate the subprocesses here if any
    # Clean up resources
    window.destroy()
