from PIL import Image
import customtkinter
from bin.util import *
import keyring
import configparser
import subprocess
from platformdirs import *
import logging
import platform
import dateparser
from tkinter import messagebox,filedialog
import os
import threading
import aiohttp
from pypdl import Pypdl  # Ensure this import is at the top
import tkinter as tk


appname = 'Smoke Launcher'
settings_file_name = 'settings.ini'
settings_location = user_data_dir(appname)
settings_file = os.path.join(settings_location, settings_file_name)
window_size="1280x800"


# Ensure settings directory exists
os.makedirs(settings_location, exist_ok=True)

# Check if settings file exists
if not os.path.exists(settings_file):
    # Create ConfigParser instance
    config = configparser.ConfigParser()

    # Set default values
    config['SETTINGS'] = {
        'username': '',
        'install_location': '',
        'url': '',
        'apperance': 'System',
        'theme': 'blue',
        'debug': 'False'
    }

    # Write the default configuration to the file
    with open(settings_file, 'w') as configfile:
        config.write(configfile)
else:
    # Read configuration from file
    config = configparser.ConfigParser()
    config.read(settings_file)

if config['SETTINGS'].get('debug') == 'True':
    logging.basicConfig(level=logging.DEBUG)
    # customtkinter.deactivate_automatic_dpi_awareness()  # Disable DPI awareness for debugging

# Get values from config
username = config['SETTINGS'].get('username')
password = keyring.get_password("Smoke-Launcher", username)
install_location = config['SETTINGS'].get('install_location')
url = config['SETTINGS'].get('url')



# Set appearance mode and default color theme
customtkinter.set_appearance_mode(config['SETTINGS'].get('apperance'))  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme(config['SETTINGS'].get('theme'))  # Themes: "blue" (standard), "green", "dark-blue"


class InstallWizard(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry(window_size)
        # self.resizable(False, False)  # Disallow resizing both horizontally and vertically
        self.title("Smoke Launcher - Setup")

        image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bin/img")
        # Create a frame to contain the widgets
        frame = customtkinter.CTkFrame(self,fg_color="transparent")
        frame.pack(padx=20, pady=20)

        # Image
        self.logo_image = customtkinter.CTkImage(light_image=Image.open(os.path.join(image_path, "GV-dark.png")), size=(200, 25), dark_image=Image.open(os.path.join(image_path, "GV-light.png")))
        self.logo_label = customtkinter.CTkLabel(frame, image=self.logo_image, text="")
        self.logo_label.grid(row=0, columnspan=2, pady=20)

        def validate_url():
            url = self.GV_URL.get()
            if url:
                is_valid = check_url_health(url)
                if is_valid:
                    self.GV_URL.configure(fg_color='green')  # Change text color to green for valid URL
                else:
                    self.GV_URL.configure(fg_color='red')    # Change text color to red for invalid URL
                return is_valid
            return False

        # GameVault URL Entry
        stored_url = config['SETTINGS'].get('url', '')  # Get URL or default to None
        self.GV_URL = customtkinter.CTkEntry(frame, placeholder_text="GameVault URL IE: http://127.0.0.1:8080", validate="focusout", validatecommand=validate_url, width=350)
        
        if stored_url: 
            self.GV_URL.insert(0, stored_url)  # Insert stored_url if it's not None
            logging.debug("Stored URL is not none")
        self.GV_URL.grid(row=1, columnspan=2, pady=10, sticky="ew")

        # Username Entry
        stored_username = config['SETTINGS'].get('username', 'Username')  # Get username or default to an empty string
        self.username = customtkinter.CTkEntry(frame, placeholder_text="Username")
        if stored_username:
            logging.debug("Stored username is not none")
            self.username.insert(0, stored_username)
        self.username.grid(row=3, columnspan=2, pady=10)

        # Password Entry
        self.password = customtkinter.CTkEntry(frame, show="*", placeholder_text="Password")
        self.password.grid(row=4, columnspan=2, pady=10)

        # Install Location Entry
        stored_install_location = config['SETTINGS'].get('install_location', '')  # Get install location or default to an empty string
        self.install_location = customtkinter.CTkEntry(frame, placeholder_text="Install Location", width=300)
        if stored_install_location:
            logging.debug("Stored install location is not none")
            self.install_location.insert(0, stored_install_location)
        self.install_location.grid(row=5, column=0, pady=10, sticky='ew')

        # Select Folder Button
        self.select_location_button = customtkinter.CTkButton(frame, text='📁', command=self.select_install_location,width=30)
        self.select_location_button.grid(row=5, column=1, padx=(10, 0), pady=10,sticky='w')

        # Submit Button
        self.submit_il = customtkinter.CTkButton(frame, text='Submit', command=self.submit_credentials)
        self.submit_il.grid(row=6, columnspan=2, pady=10)

        self.close_label = customtkinter.CTkLabel(frame, text="")
        self.close_label.grid(row=7, columnspan=2, pady=10)
    
    def select_install_location(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.install_location.delete(0, 'end')
            self.install_location.insert(0, folder_selected)
            

    def submit_credentials(self):
        username = self.username.get()
        password = self.password.get()
        installoc = self.install_location.get()
        url = self.GV_URL.get()

        keyring.set_password("Smoke-Launcher", username, password)

        config = configparser.ConfigParser()
        config.read(settings_file)
        config.set('SETTINGS', 'username', username)
        config.set('SETTINGS', 'install_location', installoc)
        config.set('SETTINGS', 'url', url)

        # Write to the correct settings file location
        with open(settings_file, 'w') as configfile:
            config.write(configfile)

        self.close_label.configure(text="Settings saved! Close and reopen to launch GameVault-Snake Edition.")


class Main(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("1200x600")  # Set window size
        self.title("Smoke Launcher")

        self.topbar = customtkinter.CTkFrame(self, fg_color=("grey","black"))
        self.topbar.pack(padx=0, pady=0, fill="x")

        self.refresh_button = customtkinter.CTkButton(self.topbar, text="Refresh", command=self.refresh_ui)
        self.refresh_button.pack(side="right", padx=10, pady=10)

        self.username_label = customtkinter.CTkLabel(self.topbar, text=f"Logged in as: {username}", anchor="w")
        self.username_label.pack(side="left", padx=10, pady=10)

        self.appearance_mode_label = customtkinter.CTkLabel(self.topbar, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.pack(side="left", padx=10, pady=10)

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.topbar, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.pack(side="left", padx=10, pady=10)
        self.appearance_mode_optionemenu.set(config['SETTINGS'].get('apperance'))

        self.frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        self.frame.pack(padx=0, pady=0, fill="both", expand=True)

        # Centering inner content frame
        self.inner_frame = customtkinter.CTkFrame(self.frame, fg_color="transparent")
        self.inner_frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)

        self.frame2 = customtkinter.CTkFrame(self, fg_color="transparent")
        self.frame2.pack(padx=0, pady=0, fill="both", expand=False)
        self.frame2.grid_columnconfigure(1, weight=1)

        # Progress Bar
        self.progress_bar = customtkinter.CTkProgressBar(self.frame2)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)  # Initialize progress at 0%

        # Progress Label
        self.progress_label = customtkinter.CTkLabel(self.frame2, text="Start a Download")
        self.progress_label.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # Cancel Button (Initially disabled)
        self.cancel_button = customtkinter.CTkButton(self.frame2, text="🛑", command=self.cancel_download, state="disabled")
        self.cancel_button.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")

        # Ensure widgets expand evenly
        # self.frame2.grid_columnconfigure(0, weight=1)
        self.frame2.grid_columnconfigure(1, weight=1)
        # self.frame2.grid_columnconfigure(2, weight=1)

        # Download manager instance
        self.download_manager = DownloadManager(self.progress_bar, self.progress_label, self.cancel_button, self.refresh_ui)
        # Initialize UI
        self.refresh_ui()

    def refresh_ui(self):
        """Clear and refresh the game list UI."""
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        game_list = fetch_game_titles(username, password)
        row_num = 0
        col_num = 0

        for game in game_list:
            game_title = game['title']
            game_id = game['id']
            game_box_art_location = get_box_art(game_id)

            self.game_frame = customtkinter.CTkFrame(self.inner_frame)
            self.game_frame.grid(row=row_num, column=col_num, padx=10, pady=5, sticky="ns")
            self.game_frame.grid_columnconfigure(0, weight=1)
            self.game_frame.grid_columnconfigure(1, weight=1)
            self.game_frame.grid_columnconfigure(2, weight=1)

            game_box_art = customtkinter.CTkImage(light_image=Image.open(game_box_art_location), size=(176, 235), dark_image=Image.open(game_box_art_location))
            game_box_art_label = customtkinter.CTkLabel(self.game_frame, image=game_box_art, text="")
            game_box_art_label.grid(row=0, column=0, padx=10, pady=5, sticky="nsew",columnspan=3)
            game_label = customtkinter.CTkLabel(self.game_frame, text=game_title, wraplength=176)
            game_label.grid(row=1, column=0, padx=10, pady=5, sticky="nsew",columnspan=3)


            button_size = 20
            download_button = customtkinter.CTkButton(self.game_frame, text="DL", command=lambda gid=game_id: self.start_download(gid), width=button_size, height=button_size, corner_radius=button_size // 2)
            download_button.grid(row=2, column=0, padx=2, pady=2)
            dl_tooltip = ToolTip(download_button, "Download Game")
            if is_game_downloaded(game_id):
                download_button.configure(state="disabled")


            if is_game_installed(game_id):
                exe_list = get_exes(game_id) or []
                exe_selection_dropdown = customtkinter.CTkComboBox(
                    self.game_frame,
                    values=["Select an EXE"] + exe_list
                )
                add_to_library_button = customtkinter.CTkButton(
                    self.game_frame, 
                    text="+S", 
                    command=lambda gid=game_id, dropdown=exe_selection_dropdown: real_add_non_steam_game(gid, dropdown.get()), 
                    width=button_size, 
                    height=button_size, 
                    corner_radius=button_size // 2) 
                add_to_library_button.grid(row=2, column=1, padx=2, pady=2)  # Moved to column 1
                steam_tooltip = ToolTip(add_to_library_button, "Add this game to your Steam library")



                exe_selection_dropdown.set(get_selected_exe(game_id) or "Select an EXE")
                exe_selection_dropdown.grid(row=3, column=0, columnspan=3, padx=2, pady=5, sticky="nsew")

                uninstall_button = customtkinter.CTkButton(self.game_frame, text="U/I", command=lambda gid=game_id: self.delete_download_and_refresh(gid), width=button_size, height=button_size, corner_radius=button_size // 2)
                uninstall_button.grid(row=2, column=2, padx=2, pady=2)  # Moved to column 2
                uninstall_button_tooltip = ToolTip(uninstall_button, "Uninstall Game")


            elif is_game_downloaded(game_id) and not is_game_installed(game_id):
                unpack_button = customtkinter.CTkButton(self.game_frame, text="U/P", command=lambda gid=game_id: self.unpack_and_refresh(gid), width=button_size, height=button_size, corner_radius=button_size // 2)
                unpack_button.grid(row=2, column=0, padx=2, pady=2)
                unpack_button_tooltip = ToolTip(unpack_button, "Unpack Game")


                delete_button = customtkinter.CTkButton(self.game_frame, text="DEL/DL", command=lambda gid=game_id: self.uninstall_and_refresh(gid), width=button_size, height=button_size, corner_radius=button_size // 2)
                delete_button.grid(row=2, column=1, padx=2, pady=2)  # Moved to column 1
                delete_button_tooltip = ToolTip(delete_button, "Delete Download")



            col_num += 1
            if col_num > 4:
                col_num = 0
                row_num += 5

        # Ensure the columns are evenly distributed
        for i in range(5):
            self.inner_frame.grid_columnconfigure(i, weight=1)

 
    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)
        #write to settings
        config = configparser.ConfigParser()
        config.read(settings_file)
        config.set('SETTINGS', 'apperance', new_appearance_mode)
        with open(settings_file, 'w') as configfile:
            config.write(configfile)

    def unpack_and_refresh(self, gid):
        """Start unpacking in a separate thread and refresh UI after completion."""
        thread = threading.Thread(target=self.unpack_game_thread, args=(gid,))
        thread.start()

    def unpack_game_thread(self, gid):
        """Threaded function to handle unpacking without blocking the UI."""
        unpack_game(gid)  # Run unpacking
        self.after(0, self.refresh_ui)  # Schedule UI update on the main thread
    
    def delete_download_and_refresh(self, gid):
        """Start deletion in a separate thread and refresh UI after completion."""
        thread = threading.Thread(target=self.delete_game_thread, args=(gid,))
        thread.start()
    
    def delete_game_thread(self, gid):
        """Threaded function to handle deletion without blocking the UI."""
        uninstall_game(gid)
        self.after(0, self.refresh_ui)  # Schedule UI update on the main thread

    def uninstall_and_refresh(self, gid):
        """Start deletion in a separate thread and refresh UI after completion."""
        thread = threading.Thread(target=self.uninstall_and_refresh_download_thread, args=(gid,))
        thread.start()

    def uninstall_and_refresh_download_thread(self, gid):
        """Threaded function to handle deletion without blocking the UI."""
        delete_download(gid)
        self.after(0, self.refresh_ui)
    def add_to_library( gid):
        fetch_game_info(username, password, gid)
        
        # add_non_steam_game(exe_path, game_name=None, start_dir=None, icon_path=None, launch_options=None, tags=None, compatibility_tool=None)





    def start_download(self,gid):
        """Start game download when button is clicked."""
        # gid = "1"  # Replace with actual game ID
        if not username or not password:
            messagebox.showerror("Error", "Username or password missing.")
            return

        self.download_manager.download_game_files(username, password, gid)

    def cancel_download(self):
        """Cancel an ongoing download."""
        self.download_manager.cancel_download()


class DownloadManager:
    def __init__(self, progress_bar, progress_label, cancel_button, refresh_callback):
        self.progress_bar = progress_bar
        self.progress_label = progress_label
        self.cancel_button = cancel_button
        self.current_download = None
        self.cancel_requested = False  
        self.download_name = ""  # Store the name of the download
        self.refresh_callback = refresh_callback  # Store the UI refresh function

    def update_progress(self):
        """Periodically update the progress bar during the download."""
        if self.current_download and not self.current_download.completed:
            if self.cancel_requested:
                self.current_download.stop()  # Stop the download
                self._update_ui(f"{self.download_name}: Download Cancelled", 0, disable_button=True)
                return

            progress = self.current_download.progress or 0
            normalized_progress = max(0, min(progress / 100, 1))

            # Get the download speed in MB/s
            speed = self.current_download.speed or 0  # Speed in MB/s

            # Get the ETA (in seconds)
            eta = self.current_download.eta or 0  # ETA in seconds
            eta_minutes, eta_seconds = divmod(int(eta), 60)  # Convert to minutes and seconds

            self._update_ui(f"{self.download_name}: Progress: {int(progress)}% | Speed: {speed:.2f} MB/s | ETA: {eta_minutes}m {eta_seconds}s", 
                            normalized_progress)
            self.progress_bar.after(500, self.update_progress)  # Keep checking progress
        else:
            self._update_ui(f"{self.download_name}: Download Complete!", 1.0, disable_button=True)
            self.refresh_callback()

    def _update_ui(self, label_text, progress_value, disable_button=False):
        """Safely update UI elements from the main thread."""
        self.progress_label.after(0, lambda: self.progress_label.configure(text=label_text))
        self.progress_bar.after(0, lambda: self.progress_bar.set(progress_value))
        if disable_button:
            self.cancel_button.after(0, lambda: self.cancel_button.configure(state="disabled"))

    def download_file(self, url, file_path, auth, download_name):
        """Handles the file download with authentication and progress tracking."""
        self.current_download = Pypdl()
        self.cancel_requested = False  
        self.download_name = download_name  # Set the download name

        if isinstance(auth, tuple) and len(auth) == 2:
            username, password = auth
        elif isinstance(auth, str) and ":" in auth:
            username, password = auth.split(":", 1)
        else:
            raise ValueError("Invalid auth format. Expected a tuple (username, password) or 'username:password' string.")

        auth_string = f"{username}:{password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        headers = {"Authorization": f"Basic {encoded_auth}"}

        try:
            self.current_download.start(
                url,
                file_path=file_path,
                segments=10,
                display=True,
                multisegment=True,
                block=False,
                retries=0,
                overwrite=False,
                headers=headers
            )

            self.progress_bar.after(0, self.update_progress)  # Schedule UI updates in main thread

        except Exception as e:
            logging.error(f"Download failed: {e}")
            self._update_ui(f"{self.download_name}: Download Error", 0, disable_button=True)

    def download_game_files(self, username, password, gid):
        """Prepare file paths and start the download."""
        game_info = fetch_game_info(username, password, gid)
        if not game_info:
            logging.error("Failed to fetch game information.")
            return

        auth = (username, password)  
        download_url = config["SETTINGS"].get("url") + f"/api/games/{gid}/download"
        game_name = game_info['title']
        install_location = config['SETTINGS'].get('install_location')
        filetype = game_info['file_path'].split(".")[-1]
        download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.{filetype}")

        os.makedirs(os.path.dirname(download_path), exist_ok=True)

        self.cancel_button.configure(state="normal")

        self.cancel_requested = False
        threading.Thread(target=self.download_file, args=(download_url, download_path, auth, game_name), daemon=True).start()

    def cancel_download(self):
        """Request to cancel the download."""
        if self.current_download:  # Check if there's an active download
            self.cancel_requested = True
            self.current_download.stop()  # Stop the download immediately
            self._update_ui(f"{self.download_name}: Download Cancelled", 0, disable_button=True)
            print("Download cancellation requested.")
        else:
            print("No active download to cancel.")


class ToolTip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def schedule_tooltip(self, event):
        # Schedule the tooltip to show after the delay
        self.tooltip_after = self.widget.after(self.delay, self.show_tooltip, event)

    def show_tooltip(self, event):
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 25}")
        label = tk.Label(self.tooltip, text=self.text, relief="solid", borderwidth=0)  # No background
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
        if hasattr(self, 'tooltip_after'):
            self.widget.after_cancel(self.tooltip_after)  # Cancel the tooltip display if mouse leaves early



if __name__ == "__main__":
    if not check_config(settings_file):
        logging.debug("Config file not valid running installer")
        InstallWizard().mainloop()
    else:
        logging.debug("Config file is valid running main program")
        Main().mainloop()




