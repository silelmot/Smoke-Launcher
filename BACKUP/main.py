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
    logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
    # customtkinter.deactivate_automatic_dpi_awareness()  # Disable DPI awareness for debugging

# Get values from config
username = config['SETTINGS'].get('username')
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


# class Main(customtkinter.CTk):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.geometry("1200x600")  # Set window size
#         self.title("Smoke Launcher")

#         # Frame for UI elements
#         frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent", bg_color="red")
#         frame.pack(padx=0, pady=3, fill="both", expand=True)
#         game_list = fetch_game_titles(username, keyring.get_password("Smoke-Launcher", username))
#         row_num = 0
#         for game in game_list:
#             # Game Title Label
#             game_title = game['title']
#             game_id = game['id']
#             game_label = customtkinter.CTkLabel(frame, text=game_title)
#             game_label.grid(row=row_num, column=0, padx=10, pady=5, sticky="ew")

#             # Download Button
#             download_button = customtkinter.CTkButton(frame, text="⬇️", command=lambda gid=game_id: self.start_download(gid))
#             download_button.grid(row=row_num, column=1, padx=10, pady=5, sticky="ew")

#             #unpack button

#             if is_game_installed(game_id):
#                 add_to_library_button = customtkinter.CTkButton(frame, text="📚", command=lambda gid=game_id: self.add_to_library(gid))
#                 add_to_library_button.grid(row=row_num, column=2, padx=10, pady=5, sticky="ew")
#                 uninstall_button = customtkinter.CTkButton(frame, text="🗑️", command=lambda gid=game_id: self.uninstall_game(gid))
#                 uninstall_button.grid(row=row_num, column=3, padx=10, pady=5, sticky="ew")
#             elif is_game_downloaded(game_id):
#                 unpack_button = customtkinter.CTkButton(frame, text="📦", command=lambda gid=game_id: unpack_game(gid))
#                 unpack_button.grid(row=row_num, column=2, padx=10, pady=5, sticky="ew")

#             row_num += 1
#         frame2 = customtkinter.CTkFrame(self, fg_color="transparent",bg_color="blue")
#         frame2.pack(padx=5, pady=0, fill="both", expand=False)
#         # Progress Bar
#         self.progress_bar = customtkinter.CTkProgressBar(frame2)
#         self.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
#         self.progress_bar.set(0)  # Initialize progress at 0%
#         # Progress Label
#         self.progress_label = customtkinter.CTkLabel(frame2, text="Progress: 0%")
#         self.progress_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
#         frame2.grid_columnconfigure(1, weight=1)
#         # Cancel Button (Initially disabled)
#         self.cancel_button = customtkinter.CTkButton(frame2, text="🛑", command=self.cancel_download, state="disabled")
#         self.cancel_button.grid(row=0, column=2, padx=10, pady=5)
#         # Download manager instance
#         self.download_manager = DownloadManager(self.progress_bar, self.progress_label, self.cancel_button)


class Main(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("1200x600")  # Set window size
        self.title("Smoke Launcher")

        self.frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent", bg_color="red")
        self.frame.pack(padx=0, pady=3, fill="both", expand=True)

        self.frame2 = customtkinter.CTkFrame(self, fg_color="transparent", bg_color="blue")
        self.frame2.pack(padx=5, pady=0, fill="both", expand=False)

        # Progress Bar
        self.progress_bar = customtkinter.CTkProgressBar(self.frame2)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)  # Initialize progress at 0%

        # Progress Label
        self.progress_label = customtkinter.CTkLabel(self.frame2, text="Progress: 0%")
        self.progress_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.frame2.grid_columnconfigure(1, weight=1)

        # Cancel Button (Initially disabled)
        self.cancel_button = customtkinter.CTkButton(self.frame2, text="🛑", command=self.cancel_download, state="disabled")
        self.cancel_button.grid(row=0, column=2, padx=10, pady=5)

        # Download manager instance
        self.download_manager = DownloadManager(self.progress_bar, self.progress_label, self.cancel_button)

        # Initialize UI
        self.refresh_ui()

    def refresh_ui(self):
        """Clear and refresh the game list UI."""
        # Clear the existing UI elements in the scrollable frame
        for widget in self.frame.winfo_children():
            widget.destroy()

        game_list = fetch_game_titles(username, keyring.get_password("Smoke-Launcher", username))
        row_num = 0
        for game in game_list:
            game_title = game['title']
            game_id = game['id']
            game_label = customtkinter.CTkLabel(self.frame, text=game_title)
            game_label.grid(row=row_num, column=0, padx=10, pady=5, sticky="ew")

            download_button = customtkinter.CTkButton(self.frame, text="⬇️", command=lambda gid=game_id: self.start_download(gid))
            download_button.grid(row=row_num, column=1, padx=10, pady=5, sticky="ew")

            if is_game_installed(game_id):
                add_to_library_button = customtkinter.CTkButton(self.frame, text="📚", command=lambda gid=game_id: self.add_to_library(gid))
                add_to_library_button.grid(row=row_num, column=2, padx=10, pady=5, sticky="ew")

                uninstall_button = customtkinter.CTkButton(self.frame, text="🗑️", command=lambda gid=game_id: self.uninstall_game(gid))
                uninstall_button.grid(row=row_num, column=3, padx=10, pady=5, sticky="ew")
            elif is_game_downloaded(game_id):
                unpack_button = customtkinter.CTkButton(self.frame, text="📦", command=lambda gid=game_id: self.unpack_and_refresh(gid))
                unpack_button.grid(row=row_num, column=2, padx=10, pady=5, sticky="ew")
            row_num += 1

    def unpack_and_refresh(self, gid):
        """Unpack the game and refresh UI afterward."""
        unpack_game(gid)
        self.refresh_ui()  # Refresh UI after unpacking






    def start_download(self,gid):
        """Start game download when button is clicked."""
        username = config["SETTINGS"].get("username")
        password = keyring.get_password("Smoke-Launcher", username)
        # gid = "1"  # Replace with actual game ID

        if not username or not password:
            messagebox.showerror("Error", "Username or password missing.")
            return

        self.download_manager.download_game_files(username, password, gid)

    def cancel_download(self):
        """Cancel an ongoing download."""
        self.download_manager.cancel_download()


class DownloadManager:
    def __init__(self, progress_bar, progress_label, cancel_button):
        self.progress_bar = progress_bar
        self.progress_label = progress_label
        self.cancel_button = cancel_button
        self.current_download = None
        self.cancel_requested = False  

    def update_progress(self):
        """Periodically update the progress bar during the download."""
        if self.current_download and not self.current_download.completed:
            if self.cancel_requested:
                self.current_download.stop()  # Stop the download
                self._update_ui("Download Cancelled", 0, disable_button=True)
                return

            progress = self.current_download.progress or 0
            normalized_progress = max(0, min(progress / 100, 1))

            # Get the download speed in MB/s
            speed = self.current_download.speed or 0  # Speed in MB/s

            # Get the ETA (in seconds)
            eta = self.current_download.eta or 0  # ETA in seconds
            eta_minutes, eta_seconds = divmod(int(eta), 60)  # Convert to minutes and seconds
            

            self._update_ui(f"Progress: {int(progress)}% | Speed: {speed:.2f} MB/s | ETA: {eta_minutes}m {eta_seconds}s", 
                            normalized_progress)
            self.progress_bar.after(500, self.update_progress)  # Keep checking progress
        else:
            self._update_ui("Download Complete!", 1.0, disable_button=True)

    def _update_ui(self, label_text, progress_value, disable_button=False):
        """Safely update UI elements from the main thread."""
        self.progress_label.after(0, lambda: self.progress_label.configure(text=label_text))
        self.progress_bar.after(0, lambda: self.progress_bar.set(progress_value))
        if disable_button:
            self.cancel_button.after(0, lambda: self.cancel_button.configure(state="disabled"))

    def download_file(self, url, file_path, auth):
        """Handles the file download with authentication and progress tracking."""
        self.current_download = Pypdl()
        self.cancel_requested = False  

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
            self._update_ui("Download Error", 0, disable_button=True)

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
        threading.Thread(target=self.download_file, args=(download_url, download_path, auth), daemon=True).start()

    def cancel_download(self):
        """Request to cancel the download."""
        if self.current_download:  # Check if there's an active download
            self.cancel_requested = True
            self.current_download.stop()  # Stop the download immediately
            self._update_ui("Download Cancelled", 0, disable_button=True)
            print("Download cancellation requested.")
        else:
            print("No active download to cancel.")


if __name__ == "__main__":
    if not check_config(settings_file):
        logging.debug("Config file not valid running installer")
        InstallWizard().mainloop()
    else:
        logging.debug("Config file is valid running main program")
        Main().mainloop()




