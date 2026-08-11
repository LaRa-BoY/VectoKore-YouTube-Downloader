import customtkinter as ctk
import yt_dlp
import requests
import threading
import time
import os
import subprocess
import io
from PIL import Image
from tkinter import messagebox, filedialog
import sys
import urllib.request
import uuid
import hashlib

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a PyInstaller exe, use the normal current directory
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- NEW: Define Software Version ---
APP_VERSION = "1.0.2"
GITHUB_REPO = "LaRa-BoY/VectoKore-YouTube-Downloader"  # Used for OTA GitHub Release Updates

# --- Analytics Configuration ---
GA4_MEASUREMENT_ID = "G-VJR7YQ0G1X" # Replace with your actual Measurement ID
GA4_API_SECRET = "mfxt9jIeT-qbVWwyZTorng"  # Replace with your actual API Secret


class VectoKoreApp(ctk.CTk):

  def __init__(self):
    super().__init__()

    # --- Window Configuration ---
    self.title("VectoKore YouTube Downloader")
    try:
        self.iconbitmap(resource_path("assets/icon.ico"))
    except Exception:
        pass
    self.configure(fg_color="#13151e")

    # Set window dimensions
    window_width = 1200
    window_height = 700

    # Get screen width and height
    screen_width = self.winfo_screenwidth()
    screen_height = self.winfo_screenheight()

    # Calculate the starting X and Y coordinates to center the window
    x = int((screen_width / 2) - (window_width / 2))
    y = int((screen_height / 2) - (window_height / 2))

    # Apply the geometry with the coordinates
    self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Root Layout: 3 Columns (Left Nav, Center Dashboard, Right Queue)
    self.grid_columnconfigure(0, weight=0)  # Left Sidebar (Fixed)
    self.grid_columnconfigure(1, weight=1)  # Main Dashboard (Expandable)
    self.grid_columnconfigure(2, weight=0)  # Right Sidebar (Fixed)
    self.grid_rowconfigure(0, weight=1)

    # Load Assets
    self.load_images()

    # Set default download path to the Windows 'Downloads' folder
    self.download_path = os.path.join(os.path.expanduser('~'), 'Downloads')

    # Build Interface Sections
    self.build_left_sidebar()
    self.build_center_dashboard()
    self.build_right_sidebar()
    self.build_history_dashboard()   # <-- Renamed
    self.build_settings_dashboard()  
    
    # Set default view to Home
    self.navigate("Home")

    # Initialize Analytics
    self.client_id = self._get_client_id()
    self.send_analytics_event("app_open", {"version": APP_VERSION})

    # Run Remote Features Check
    self.check_remote_features()

    # Detect clipboard URLs when window gains focus
    self.bind("<FocusIn>", self.check_clipboard_for_url)
  # ==========================================
  # 1. ASSET INITIALIZATION
  # ==========================================
  def load_images(self):
    """Loads platform logo icons for cards."""
    try:
      # Wrap the string path in resource_path()
      yt_path = resource_path("assets/youtube.png")
      tk_path = resource_path("assets/tiktok.png")
      fb_path = resource_path("assets/facebook.png")
      ig_path = resource_path("assets/instagram.png")
      logo_path = resource_path("assets/icon2.png")

      self.yt_icon = ctk.CTkImage(Image.open(yt_path), size=(72, 72))
      self.tk_icon = ctk.CTkImage(Image.open(tk_path), size=(72, 72))
      self.fb_icon = ctk.CTkImage(Image.open(fb_path), size=(72, 72))
      self.ig_icon = ctk.CTkImage(Image.open(ig_path), size=(72, 72))
      self.app_logo = ctk.CTkImage(Image.open(logo_path), size=(100, 100))
    except Exception as e:
      print(f"Error loading icons: {e}")
      self.yt_icon = self.tk_icon = self.fb_icon = self.ig_icon = self.app_logo = None

  # ==========================================
  # 2. LEFT NAVIGATION SIDEBAR
  # ==========================================
  def build_left_sidebar(self):
    self.left_sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#191b28")
    self.left_sidebar.grid(row=0, column=0, sticky="nsew")
    self.left_sidebar.grid_rowconfigure(6, weight=1)

    self.logo_label = ctk.CTkLabel(
        self.left_sidebar, text="", image=getattr(self, "app_logo", None)
    )
    self.logo_label.grid(row=0, column=0, pady=(30, 30))

    # Navigation Buttons with Commands (Downloads removed)
    nav_items = ["Home", "History", "Queue", "Settings"]
    self.nav_buttons = {} 

    for idx, item in enumerate(nav_items, start=1):
      btn = ctk.CTkButton(
          self.left_sidebar,
          text=f"  {item}",
          anchor="w",
          font=ctk.CTkFont(size=14),
          fg_color="#24273a" if item == "Home" else "transparent",
          hover_color="#24273a",
          text_color="#ffffff" if item == "Home" else "#8b92a5",
          height=40,
          command=lambda nav=item: self.navigate(nav) # <-- Adds the click action
      )
      btn.grid(row=idx, column=0, padx=15, pady=5, sticky="ew")
      self.nav_buttons[item] = btn

    # --- NEW: Software Version Label at the bottom ---
    self.version_label = ctk.CTkLabel(
        self.left_sidebar,
        text=f"Version {APP_VERSION}",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="#8b92a5",
        cursor="hand2"
    )
    # Sticky "s" means South (bottom of the grid cell)
    self.version_label.grid(row=7, column=0, pady=(0, 20), sticky="s")
    self.version_label.bind("<Button-1>", self.show_about_popup)

  def show_about_popup(self, event=None):
    about_window = ctk.CTkToplevel(self)
    about_window.title("About")
    try:
        about_window.after(200, lambda: about_window.iconbitmap(resource_path("assets/icon.ico")))
    except Exception:
        pass
    about_window.geometry("400x250")
    about_window.resizable(False, False)
    about_window.attributes("-topmost", True)
    
    # Center the popup relative to the main window
    x = self.winfo_x() + (self.winfo_width() // 2) - 200
    y = self.winfo_y() + (self.winfo_height() // 2) - 125
    about_window.geometry(f"+{x}+{y}")
    
    title_label = ctk.CTkLabel(about_window, text="VectoKore YouTube Downloader", font=ctk.CTkFont(size=18, weight="bold"))
    title_label.pack(pady=(25, 5))
    
    version_label = ctk.CTkLabel(about_window, text=f"Version {APP_VERSION}", font=ctk.CTkFont(size=12))
    version_label.pack(pady=(0, 10))
    
    desc_label = ctk.CTkLabel(about_window, text="A high-performance media downloader.\nBuilt with CustomTkinter.", font=ctk.CTkFont(size=12))
    desc_label.pack(pady=5)
    
    company_label = ctk.CTkLabel(about_window, text="© 2026 VectoKore Developers.\nAll rights reserved.", font=ctk.CTkFont(size=11), text_color="#8b92a5")
    company_label.pack(pady=10)
    
    close_btn = ctk.CTkButton(about_window, text="Close", command=about_window.destroy, width=100)
    close_btn.pack(pady=(5, 20))

  # ==========================================
  # 3. CENTRAL DASHBOARD
  # ==========================================
  def build_center_dashboard(self):
    # Base container frame
    self.center_base = ctk.CTkFrame(self, fg_color="#13151e", corner_radius=0)
    self.center_base.grid(row=0, column=1, sticky="nsew")
    self.center_base.grid_rowconfigure(0, weight=1)
    self.center_base.grid_columnconfigure(0, weight=1)

    # LAYER 1: Background Label (Master Container)
    self.bg_label = ctk.CTkLabel(self.center_base, text="")
    self.bg_label.grid(row=0, column=0, sticky="nsew")

    # LAYER 2: UI Panel (Sits inside the background label so transparency sees the image)
    self.center_frame = ctk.CTkFrame(self.bg_label, fg_color="transparent", bg_color="transparent")
    self.center_frame.place(relwidth=1, relheight=1)

    self.center_frame.grid_rowconfigure(2, weight=1)
    self.center_frame.grid_columnconfigure(0, weight=1)

    # Header
    self.header = ctk.CTkLabel(
        self.center_frame, text="VIDEO DOWNLOADER HUB", font=ctk.CTkFont(size=26, weight="bold")
    )
    self.header.grid(row=0, column=0, sticky="w", padx=25, pady=(25, 15))

    # URL Input Container
    self.url_container = ctk.CTkFrame(
        self.center_frame, height=48, corner_radius=25, border_color="#ff7e5f", border_width=1,
        fg_color="#1c1f2e", bg_color="transparent"
    )
    self.url_container.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 20))
    self.url_container.grid_columnconfigure(0, weight=1)
    
    self.url_entry = ctk.CTkEntry(
        self.url_container, placeholder_text="PASTE VIDEO URL HERE (YouTube, TikTok, FB, Insta)...",
        height=40, border_width=0, fg_color="transparent", bg_color="transparent", font=ctk.CTkFont(size=13)
    )
    self.url_entry.grid(row=0, column=0, sticky="ew", padx=(15, 0), pady=4)
    self.url_entry.bind("<Return>", self.trigger_metadata_fetch)
    self.url_entry.bind("<FocusOut>", self.trigger_metadata_fetch)
    
    self.paste_btn = ctk.CTkButton(
        self.url_container, text="📋", width=30, height=30, fg_color="transparent", 
        hover_color="#2a2d3e", text_color="#8b92a5", command=self.paste_url
    )
    self.paste_btn.grid(row=0, column=1, padx=(5, 5))
    
    self.clear_btn = ctk.CTkButton(
        self.url_container, text="✖", width=30, height=30, fg_color="transparent", 
        hover_color="#2a2d3e", text_color="#8b92a5", command=self.clear_url
    )
    self.clear_btn.grid(row=0, column=2, padx=(0, 15))

    # Split Panel
    self.split_panel = ctk.CTkFrame(self.center_frame, fg_color="transparent", bg_color="transparent")
    self.split_panel.grid(row=2, column=0, sticky="nsew", padx=25, pady=(0, 25))
    self.split_panel.grid_columnconfigure(0, weight=1)
    self.split_panel.grid_columnconfigure(1, weight=1)
    self.split_panel.grid_rowconfigure(0, weight=1)

    # Subpanel 1: 2x2 Platform Cards
    self.platform_grid = ctk.CTkFrame(self.split_panel, fg_color="transparent", bg_color="transparent")
    self.platform_grid.grid(row=0, column=0, sticky="new", padx=(0, 15))
    self.platform_grid.grid_columnconfigure((0, 1), weight=1)

    platforms = [
        ("YOUTUBE\nYouTube", "#ff0000", self.yt_icon, 0, 0),
        ("TIKTOK\nTikTok", "#00f2fe", self.tk_icon, 0, 1),
        ("FACEBOOK\nFacebook", "#1877f2", self.fb_icon, 1, 0),
        ("INSTAGRAM\nInstagram", "#e1306c", self.ig_icon, 1, 1),
    ]
    for text, color, icon, r, c in platforms:
        btn = ctk.CTkButton(
            self.platform_grid, text="", image=icon, fg_color="#1c1f2e", hover_color=color, 
            border_width=0, corner_radius=15, height=140
        )
        btn.grid(row=r, column=c, padx=8, pady=8, sticky="ew")

    # Subpanel 2: Control Panel
    self.control_panel = ctk.CTkFrame(self.split_panel, fg_color="#1c1f2e", corner_radius=15)
    self.control_panel.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

    self.thumb_label = ctk.CTkLabel(self.control_panel, text="No Video Loaded", fg_color="#2a2d3e", corner_radius=10, height=180)
    self.thumb_label.pack(fill="x", padx=15, pady=15)

    self.v_title = ctk.CTkLabel(self.control_panel, text="Ready to Download", font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
    self.v_title.pack(fill="x", padx=15, pady=(0, 5))

    self.v_meta = ctk.CTkLabel(self.control_panel, text="Paste a valid video URL and press Enter", font=ctk.CTkFont(size=12), text_color="#8b92a5", anchor="w")
    self.v_meta.pack(fill="x", padx=15, pady=(0, 15))

    self.quality_label = ctk.CTkLabel(self.control_panel, text="SELECT QUALITY & FORMAT", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8b92a5", anchor="w")
    self.quality_label.pack(fill="x", padx=15, pady=(0, 5))

    self.quality_var = ctk.StringVar(value="1080p Video")
    self.quality_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
    self.quality_frame.pack(fill="x", padx=15, pady=(0, 15))
    self.quality_frame.grid_columnconfigure((0, 1, 2), weight=1)

    qualities = [("360p", 0, 0), ("480p", 0, 1), ("720p", 0, 2), ("1080p", 1, 0), ("2K", 1, 1), ("4K", 1, 2), ("MP3 Audio", 2, 0)]
    self.quality_buttons = []
    for q_text, r, c in qualities:
        col_span = 3 if q_text == "MP3 Audio" else 1
        btn = ctk.CTkButton(
            self.quality_frame, text=q_text, height=45, font=ctk.CTkFont(size=12, weight="bold"), 
            fg_color="#ff7e5f" if q_text == "1080p" else "#24273a", hover_color="#e6683c" if q_text == "1080p" else "#2a2d3e", 
            text_color="#ffffff" if q_text == "1080p" else "#8b92a5", command=lambda val=q_text: self.set_quality(val)
        )
        btn.grid(row=r, column=c, columnspan=col_span, padx=3, pady=3, sticky="ew")
        self.quality_buttons.append((btn, q_text))

    self.download_btn = ctk.CTkButton(self.control_panel, text="DOWNLOAD NOW", height=45, font=ctk.CTkFont(size=15, weight="bold"), fg_color="#ff7e5f", hover_color="#e6683c", corner_radius=10, command=self.start_download_thread)
    self.download_btn.pack(fill="x", padx=15, pady=(5, 15))

  # ==========================================
  # 3.5 DOWNLOADS PAGE & NAVIGATION
  # ==========================================
  def navigate(self, nav_item):
    """Switches between the Home, History, and Settings dashboards."""
    for name, btn in self.nav_buttons.items():
        if name == nav_item:
            btn.configure(fg_color="#24273a", text_color="#ffffff")
        else:
            btn.configure(fg_color="transparent", text_color="#8b92a5")

    # Hide all frames first
    if hasattr(self, 'center_base'): self.center_base.grid_forget()    # <-- Updated
    if hasattr(self, 'history_frame'): self.history_frame.grid_forget()
    if hasattr(self, 'settings_frame'): self.settings_frame.grid_forget()

    # Show the requested frame
    if nav_item == "Home":
        self.center_base.grid(row=0, column=1, sticky="nsew")          # <-- Updated
    elif nav_item == "History":
        self.history_frame.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.refresh_history_list()
    elif nav_item == "Settings":
        self.settings_frame.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)

  # ==========================================
  # 3.5 HISTORY PAGE LOGIC
  # ==========================================
  def build_history_dashboard(self):
    """Creates the layout for the History tab."""
    self.history_frame = ctk.CTkFrame(self, fg_color="transparent")
    self.history_frame.grid_rowconfigure(1, weight=1)
    self.history_frame.grid_columnconfigure(0, weight=1)

    self.hist_header = ctk.CTkLabel(
        self.history_frame, text="DOWNLOAD HISTORY", font=ctk.CTkFont(size=26, weight="bold")
    )
    self.hist_header.grid(row=0, column=0, sticky="w", pady=(0, 15))

    self.history_list = ctk.CTkScrollableFrame(self.history_frame, fg_color="#1c1f2e", corner_radius=15)
    self.history_list.grid(row=1, column=0, sticky="nsew")

  def build_settings_dashboard(self):
    """Creates the layout for the Settings tab."""
    self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
    self.settings_frame.grid_rowconfigure(1, weight=1)
    self.settings_frame.grid_columnconfigure(0, weight=1)

    header = ctk.CTkLabel(
        self.settings_frame, text="SETTINGS", font=ctk.CTkFont(size=26, weight="bold")
    )
    header.grid(row=0, column=0, sticky="w", pady=(0, 15))

    # Settings Container Panel
    container = ctk.CTkFrame(self.settings_frame, fg_color="#1c1f2e", corner_radius=15)
    container.grid(row=1, column=0, sticky="nsew")

    # Download Location Section
    loc_label = ctk.CTkLabel(
        container, text="Default Download Location", font=ctk.CTkFont(size=16, weight="bold")
    )
    loc_label.pack(anchor="w", padx=20, pady=(30, 5))

    self.path_label = ctk.CTkLabel(
        container, text=self.download_path, text_color="#8b92a5", font=ctk.CTkFont(size=13)
    )
    self.path_label.pack(anchor="w", padx=20, pady=(0, 15))

    change_btn = ctk.CTkButton(
        container, text="Change Folder", width=120, height=35,
        font=ctk.CTkFont(weight="bold"), fg_color="#ff7e5f", hover_color="#e6683c",
        command=self.change_download_location
    )
    change_btn.pack(anchor="w", padx=20)

  def change_download_location(self):
    """Opens a Windows folder selection dialog to change the save path."""
    new_path = filedialog.askdirectory(initialdir=self.download_path, title="Select Download Folder")
    if new_path:
        self.download_path = os.path.normpath(new_path)
        self.path_label.configure(text=self.download_path)

  def refresh_history_list(self):
    """Scans the folder using the ledger to show ONLY VectoKore downloads."""
    for widget in self.history_list.winfo_children():
        widget.destroy()
        
    if not os.path.exists(self.download_path):
        return
        
    # Load history and verify the files still exist in the folder
    tracked_files = self.load_history()
    valid_files = []
    
    for f in tracked_files:
        if os.path.exists(os.path.join(self.download_path, f)):
            valid_files.append(f)
    
    if not valid_files:
        empty_lbl = ctk.CTkLabel(self.history_list, text="No VectoKore downloads found in history.", text_color="#8b92a5")
        empty_lbl.pack(pady=30)
        return

    for file in valid_files:
        item_frame = ctk.CTkFrame(self.history_list, fg_color="#2a2d3e", corner_radius=8, height=70)
        item_frame.pack(fill="x", pady=8, padx=10)
        
        # --- THUMBNAIL LOGIC ---
        base_name = os.path.splitext(file)[0]
        thumb_path = None
        
        for ext in ['.webp', '.jpg', '.png', '.jpeg']:
            potential_path = os.path.join(self.download_path, base_name + ext)
            if os.path.exists(potential_path):
                thumb_path = potential_path
                break
                
        if thumb_path:
            try:
                img = Image.open(thumb_path)
                img_ratio = img.width / img.height
                t_width = 90  
                t_height = int(t_width / img_ratio)
                
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(t_width, t_height))
                thumb_lbl = ctk.CTkLabel(item_frame, text="", image=ctk_img)
                thumb_lbl.pack(side="left", padx=(10, 5), pady=10)
            except Exception:
                pass
        else:
            placeholder = ctk.CTkFrame(item_frame, width=90, height=50, fg_color="#1c1f2e")
            placeholder.pack(side="left", padx=(10, 5), pady=10)
            
        # --- TEXT AND BUTTONS ---
        display_name = file[:50] + ("..." if len(file) > 50 else "")
        lbl = ctk.CTkLabel(item_frame, text=display_name, font=ctk.CTkFont(size=13, weight="bold"))
        lbl.pack(side="left", padx=15, pady=10)
        
        play_btn = ctk.CTkButton(
            item_frame, text="Play Media", width=80, fg_color="#ff7e5f", hover_color="#e6683c",
            command=lambda f=file: self.play_specific_media(f)
        )
        play_btn.pack(side="right", padx=(5, 15), pady=10)
        
        folder_btn = ctk.CTkButton(
            item_frame, text="Open Folder", width=80, fg_color="#1877f2", hover_color="#145dbf",
            command=lambda f=file: self.open_specific_folder(f)
        )
        folder_btn.pack(side="right", padx=5, pady=10)

  def play_specific_media(self, filename):
    file_path = os.path.abspath(os.path.join(self.download_path, filename))
    if os.path.exists(file_path):
        os.startfile(file_path)

  def open_specific_folder(self, filename):
    file_path = os.path.abspath(os.path.join(self.download_path, filename))
    if os.path.exists(file_path):
        subprocess.Popen(f'explorer /select,"{file_path}"')

  # ==========================================
  # 4. RIGHT SIDEBAR (DOWNLOAD QUEUE)
  # ==========================================
  def build_right_sidebar(self):
    self.right_sidebar = ctk.CTkFrame(
        self, width=280, corner_radius=0, fg_color="#191b28"
    )
    self.right_sidebar.grid(row=0, column=2, sticky="nsew")

    self.queue_header = ctk.CTkLabel(
        self.right_sidebar,
        text="ACTIVE DOWNLOADS",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#8b92a5",
    )
    self.queue_header.pack(anchor="w", padx=20, pady=(25, 20))

    # Active Item Card
    self.item_card = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
    self.item_card.pack(fill="x", padx=20)

    self.download_title = ctk.CTkLabel(
        self.item_card,
        text="No Active Download",
        font=ctk.CTkFont(size=13, weight="bold"),
        anchor="w",
    )
    self.download_title.pack(fill="x")

    self.status_label = ctk.CTkLabel(
        self.item_card,
        text="Idle",
        font=ctk.CTkFont(size=12),
        text_color="#ff7e5f",
        anchor="w",
    )
    self.status_label.pack(fill="x", pady=(2, 8))

    self.progress_bar = ctk.CTkProgressBar(
        self.item_card,
        progress_color="#ff7e5f",
        fg_color="#2a2d3e",
        height=8,
    )
    self.progress_bar.pack(fill="x")
    self.progress_bar.set(0)

  # ==========================================
  # NEW METADATA & UI HELPER FUNCTIONS
  # ==========================================
  def format_bytes(self, size):
    """Converts bytes to a readable MB or GB format."""
    if not size: return ""
    size = float(size)
    if size < 1024 * 1024:
        return f"~{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"~{size / (1024 * 1024):.1f} MB"
    else:
        return f"~{size / (1024 * 1024 * 1024):.2f} GB"

  def _estimate_sizes(self, info):
    """Calculates the estimated file size for each resolution."""
    sizes = {
        "360p": "", "480p": "", "720p": "",
        "1080p": "", "2K": "", "4K": "", "MP3 Audio": ""
    }
    
    audio_size = 0
    # Find best audio stream size
    for f in info.get('formats', []):
        if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
            size = f.get('filesize') or f.get('filesize_approx') or 0
            if size > audio_size:
                audio_size = size
                
    if audio_size > 0:
        sizes["MP3 Audio"] = self.format_bytes(audio_size)

    # Find best video stream sizes
    height_map = {360: "360p", 480: "480p", 720: "720p", 1080: "1080p", 1440: "2K", 2160: "4K"}
    best_video_sizes = {360: 0, 480: 0, 720: 0, 1080: 0, 1440: 0, 2160: 0}
    
    for f in info.get('formats', []):
        h = f.get('height')
        if h in best_video_sizes and f.get('vcodec') != 'none':
            size = f.get('filesize') or f.get('filesize_approx') or 0
            if size > best_video_sizes[h]:
                best_video_sizes[h] = size
                
    # Total size = Video + Audio
    for h, label in height_map.items():
        if best_video_sizes[h] > 0:
            total_size = best_video_sizes[h] + audio_size
            sizes[label] = self.format_bytes(total_size)
            
    return sizes

  def set_quality(self, selected_quality):
    """Updates the selected quality variable and changes button colors."""
    self.quality_var.set(selected_quality)
    
    # Update button visuals so only the active one is highlighted orange
    for btn, q_text in self.quality_buttons:
        if q_text == selected_quality:
            btn.configure(fg_color="#ff7e5f", hover_color="#e6683c", text_color="#ffffff")
        else:
            btn.configure(fg_color="#24273a", hover_color="#2a2d3e", text_color="#8b92a5")

  def paste_url(self):
    """Pastes clipboard text into the URL entry and triggers metadata fetch."""
    try:
        self.url_entry.delete(0, 'end')
        self.url_entry.insert(0, self.clipboard_get())
        self.trigger_metadata_fetch()
    except Exception:
        pass

  def clear_url(self):
    """Clears the text in the URL entry."""
    self.url_entry.delete(0, 'end')

  def check_clipboard_for_url(self, event=None):
    """Checks the clipboard for a supported video URL and prompts the user."""
    # To prevent spamming on every internal widget focus change, ensure it's the main window
    if event and getattr(event, 'widget', None) != self:
        return
        
    try:
        clipboard_content = self.clipboard_get().strip()
    except Exception:
        return
        
    if not clipboard_content.startswith("http"):
        return
        
    supported = ["youtube.com", "youtu.be", "tiktok.com", "facebook.com", "fb.watch", "instagram.com"]
    if not any(domain in clipboard_content.lower() for domain in supported):
        return
        
    # Ignore if we already prompted for this URL or if it's currently in the entry
    if clipboard_content == getattr(self, "last_prompted_url", "") or clipboard_content == self.url_entry.get().strip():
        return
        
    self.last_prompted_url = clipboard_content
        
    if messagebox.askyesno("Clipboard Detected", "A supported video URL was found in your clipboard.\n\nWould you like to load it?"):
        self.url_entry.delete(0, 'end')
        self.url_entry.insert(0, clipboard_content)
        self.trigger_metadata_fetch()

  def trigger_metadata_fetch(self, event=None):
    """Fires when the user hits Enter or clicks out of the URL box."""
    url = self.url_entry.get().strip()
    # Ensure it looks like a valid link and hasn't already been scanned
    if not url.startswith("http") or url == getattr(self, "last_scanned_url", ""):
        return
        
    self.last_scanned_url = url
    self.v_title.configure(text="Fetching video info...")
    self.v_meta.configure(text="Please wait...")
    
    # Run in background so the UI doesn't freeze
    threading.Thread(target=self._fetch_metadata_thread, args=(url,), daemon=True).start()

  def _fetch_metadata_thread(self, url):
    """Downloads the thumbnail and metadata invisibly."""
    try:
        ydl_opts = {'quiet': True, 'nocheckcertificate': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # download=False means it only grabs data, not the video
            info = ydl.extract_info(url, download=False)
            
            title = info.get("title", "Unknown Title")
            uploader = info.get("uploader", "Unknown Channel")
            duration_str = info.get("duration_string", "0:00")
            thumb_url = info.get("thumbnail", "")

            # Truncate title if it's too long for the UI
            display_title = title[:45] + ("..." if len(title) > 45 else "")

            # Download and process the thumbnail image
            if thumb_url:
                response = requests.get(thumb_url)
                img_data = response.content
                img = Image.open(io.BytesIO(img_data))
                
                # Resize image to fit within a maximum bounding box without stretching the UI
                max_width = 320
                max_height = 180
                
                img_ratio = img.width / img.height
                if img_ratio >= max_width / max_height:
                    target_width = max_width
                    target_height = int(target_width / img_ratio)
                else:
                    target_height = max_height
                    target_width = int(target_height * img_ratio)
                
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_width, target_height))
                
                # Apply the image and remove the placeholder text. Use max_height to keep the UI fixed
                self.thumb_label.configure(image=ctk_img, text="", height=max_height)

            # Update text metadata on the UI
            self.v_title.configure(text=display_title)
            self.v_meta.configure(text=f"{uploader} • {duration_str}")
            
            # --- NEW: Calculate and display file sizes on the buttons ---
            estimated_sizes = self._estimate_sizes(info)
            for btn, q_text in self.quality_buttons:
                size_str = estimated_sizes.get(q_text, "")
                if size_str:
                    btn.configure(text=f"{q_text}\n{size_str}")
                else:
                    btn.configure(text=f"{q_text}\nN/A")

    except Exception:
        self.v_title.configure(text="Error loading video info")
        self.v_meta.configure(text="Ready to download anyway")

  # ==========================================
  # 5. BACKEND LOGIC & ENGINE
  # ==========================================
  def _get_client_id(self):
    """Generates a consistent, anonymous identifier based on the machine's MAC address."""
    mac = uuid.getnode()
    return hashlib.md5(str(mac).encode()).hexdigest()

  def send_analytics_event(self, event_name, params=None):
    """Sends a raw event to Google Analytics 4 via Measurement Protocol."""
    if GA4_MEASUREMENT_ID == "G-XXXXXXXXXX" or GA4_API_SECRET == "YOUR_API_SECRET":
        return # Analytics not configured
        
    def _send():
        try:
            url = f"https://www.google-analytics.com/mp/collect?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}"
            payload = {
                "client_id": self.client_id,
                "events": [{
                    "name": event_name,
                    "params": params or {}
                }]
            }
            requests.post(url, json=payload, timeout=3)
        except Exception:
            pass # Fail silently so the app never crashes from a failed ping
            
    threading.Thread(target=_send, daemon=True).start()

  def apply_background_image(self, img_data, opacity=150):
    """Applies the downloaded image with a dark glass tint directly to the background layer."""
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        
        # Force a fixed high-resolution size for the dashboard area to prevent 1px render bugs
        img = img.resize((1000, 700), Image.Resampling.LANCZOS)
        
        # Apply a dark overlay so your text stays readable, opacity controlled remotely
        overlay = Image.new("RGBA", img.size, (19, 21, 30, int(opacity)))
        tinted_img = Image.alpha_composite(img, overlay).convert("RGB")
        
        # Save a hard reference so Python does not delete the image from memory
        self.persistent_bg_image = ctk.CTkImage(light_image=tinted_img, dark_image=tinted_img, size=(1000, 700))
        
        if hasattr(self, 'bg_label'):
            self.bg_label.configure(image=self.persistent_bg_image, text="")
            
    except Exception as e:
        print(f"Failed to process background image: {e}")

  def perform_silent_update(self, update_url):
    """Downloads the new update in the background and seamlessly restarts the app."""
    try:
        # Download the new file to a temporary location
        temp_file = "update_temp.tmp"
        urllib.request.urlretrieve(update_url, temp_file)
        
        # Determine the target file to overwrite
        is_compiled = getattr(sys, 'frozen', False)
        target_file = sys.executable if is_compiled else os.path.abspath(sys.argv[0])

        # Create a batch script to replace the file and restart
        bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
move /y "{temp_file}" "{target_file}"
start "" "{target_file}"
del "%~f0"
"""
        bat_path = "update_script.bat"
        with open(bat_path, "w") as f:
            f.write(bat_content)
            
        # Run the batch script completely hidden
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=CREATE_NO_WINDOW)
        
        # Exit immediately so the file is freed and can be overwritten
        os._exit(0)
        
    except Exception as e:
        print(f"Silent update failed: {e}")

  def check_github_updates(self):
    """Checks GitHub Releases for new versions and silently applies them OTA."""
    def _fetch():
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {'User-Agent': 'VectoKore-OTA-Updater'}
            response = requests.get(api_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                # Helper to parse version strings like "1.0.2" into tuples like (1, 0, 2)
                def parse_version(v):
                    return tuple(map(int, v.split(".")))
                
                # Compare versions semantically (only update if GitHub version is higher)
                if latest_version and parse_version(latest_version) > parse_version(APP_VERSION):
                    update_url = ""
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            update_url = asset.get("browser_download_url")
                            break
                            
                    if update_url:
                        self.perform_silent_update(update_url)
                    else:
                        update_msg = f"A new version (v{latest_version}) is available!\n\nPlease visit GitHub to download it."
                        messagebox.showinfo("Update Available", update_msg)
        except Exception as e:
            print(f"GitHub OTA update check failed: {e}")

    threading.Thread(target=_fetch, daemon=True).start()

  def check_remote_features(self):
    """Checks GitHub Gist for version updates, popups, and remote backgrounds."""

    def _fetch():
      try:
        base_url = "https://gist.githubusercontent.com/LaRa-BoY/eeee3de0bdb1966c27ce8f60f63f2310/raw/8af66423c4c720e5c740b7ee20749717b861205e/vectokore_config.json"
        config_url = f"{base_url}?t={time.time()}"
        
        # User-Agent header prevents image servers from blocking Python requests
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(config_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
          data = response.json()
          
          # 1. Trigger GitHub OTA Updater
          self.check_github_updates()
          
          # 2. Check for standard popups
          if data.get("popup", {}).get("show"):
            messagebox.showinfo(
                data["popup"].get("title", "Notification"),
                data["popup"].get("message", ""),
            )

          # 3. Check for Remote Background Image
          bg_url = data.get("background_url", "")
          bg_opacity = data.get("background_opacity", 150)
          if bg_url:
              img_response = requests.get(bg_url, headers=headers, timeout=10)
              if img_response.status_code == 200:
                  img_data = img_response.content
                  self.after(0, lambda: self.apply_background_image(img_data, opacity=bg_opacity))
              else:
                  print(f"Background image request failed with status: {img_response.status_code}")

      except Exception as e:
        print(f"Remote check error: {e}")

    threading.Thread(target=_fetch, daemon=True).start()

  def update_progress(self, d):
    """Updates progress bar from yt-dlp execution thread."""
    if d["status"] == "downloading":
      percent_str = (
          d.get("_percent_str", "0%")
          .strip("\x1b[0;94m")
          .strip("\x1b[0m")
          .strip("%")
      )
      try:
        percent = float(percent_str) / 100
        self.progress_bar.set(percent)
        self.status_label.configure(text=f"Downloading {percent_str}")
      except ValueError:
        pass
        
    elif d["status"] == "finished":
      # The internet download is done, but FFmpeg is now extracting/merging in the background.
      self.progress_bar.set(1)
      self.status_label.configure(text="Processing file (Please wait)...")
      # DO NOT re-enable the download button here!

  def download_video(self, url):
    quality_choice = self.quality_var.get()
    ydl_opts = {
        # Combine the selected folder path with the filename
        "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
        "progress_hooks": [self.update_progress],
        "quiet": True,
        "nocheckcertificate": True,
        "ffmpeg_location": ".",
        "writethumbnail": True
    }

    if quality_choice == "MP3 Audio":
      ydl_opts["format"] = "bestaudio/best"
      ydl_opts["postprocessors"] = [{
          "key": "FFmpegExtractAudio",
          "preferredcodec": "mp3",
          "preferredquality": "192",
      }]
      # --- NEW: Force the engine to delete the original .webm file ---
      ydl_opts["keepvideo"] = False 
      ext = ".mp3"
    else:
      height_map = {
          "360p Video": 360,
          "480p Video": 480,
          "720p Video": 720,
          "1080p Video": 1080,
          "2K Video": 1440,
          "4K Video": 2160,
      }
      h = height_map.get(quality_choice, 1080)
      ydl_opts["format"] = (
          f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
      )
      ydl_opts["merge_output_format"] = "mp4"
      ext = ".mp4"
    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        self.download_title.configure(text=info.get("title", "Downloading..."))
        
        base_filename = ydl.prepare_filename(info)
        self.last_downloaded_file = os.path.splitext(base_filename)[0] + ext
        
        # This line pauses the code until BOTH the download AND FFmpeg processing are 100% finished
        ydl.download([url])
        
      # --- Code below here only runs when the final MP4/MP3 is fully created ---
      final_filename = os.path.basename(self.last_downloaded_file)
      if hasattr(self, 'save_to_history'):
          self.save_to_history(final_filename)
        
      self.status_label.configure(text="Complete!")
      self.progress_bar.set(1)
      self.download_btn.configure(state="normal", text="DOWNLOAD NOW")
      
      if hasattr(self, 'open_folder_btn'):
          self.open_folder_btn.configure(state="normal", fg_color="#1877f2")
      if hasattr(self, 'play_media_btn'):
          self.play_media_btn.configure(state="normal", fg_color="#ff7e5f", text="Play Audio" if ext == ".mp3" else "Play Video")

    except Exception as e:
      self.status_label.configure(text=f"Error: {e}")
      self.download_btn.configure(state="normal", text="DOWNLOAD NOW")

  def start_download_thread(self):
    url = self.url_entry.get().strip()
    if not url:
      self.status_label.configure(text="Please paste a URL")
      return

    self.download_btn.configure(state="disabled", text="DOWNLOADING...")
    self.progress_bar.set(0)
    self.status_label.configure(text="Starting...")

    thread = threading.Thread(
        target=self.download_video, args=(url,), daemon=True
    )
    thread.start()


if __name__ == "__main__":
  app = VectoKoreApp()
  
  # Close the PyInstaller splash screen once the UI is fully loaded
  try:
      import pyi_splash
      pyi_splash.close()
  except ImportError:
      pass # Ignored if running in your code editor
      
  app.mainloop()