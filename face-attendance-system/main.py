"""
Face Recognition Attendance System - Main Application

A modern GUI-based attendance system using:
- OpenCV for video capture
- face_recognition for face detection and matching
- CustomTkinter for modern dark theme UI
- Pickle for fast face encoding persistence
- CSV for human-readable attendance logs

VIVA NOTES:
===========
1. Face Recognition Algorithm:
   - Uses 128-dimensional face embeddings (ResNet-based)
   - Euclidean distance for face matching
   - Threshold: 0.6 (lower = more similar)

2. Performance Optimization:
   - Frame resize to 0.25 (16x speedup)
   - Pickle persistence for instant startup
   - Separate processing and display threads

3. Anti-Spam Mechanism:
   - CSV duplicate checking per day
   - One entry per person per day
   - Real-time status feedback

Author: College Project
Platform: macOS (with camera fallback support)
"""

import os
import sys
import cv2
import threading
import time
from datetime import datetime
from PIL import Image, ImageTk

import customtkinter as ctk
from tkinter import messagebox

# Import our utility modules
from utils.camera import CameraHandler
from utils.face_utils import FaceEncoder
from utils.database import AttendanceDB


class AttendanceApp(ctk.CTk):
    """
    Main application class using CustomTkinter.
    
    Features:
    - Tab-based interface (Dashboard, Registration)
    - Live webcam feed with face overlay
    - Real-time face recognition
    - Employee registration with capture
    - Anti-spam attendance tracking
    - Status bar with system state
    
    Attributes:
        scanning: Boolean indicating if face scanning is active
        video_running: Boolean for video loop control
        last_attendance_time: Timestamp of last attendance (anti-spam cooldown)
        cooldown_seconds: Minimum seconds between duplicate warnings
    """
    
    def __init__(self):
        """Initialize the application and all components."""
        super().__init__()
        
        # Window configuration
        self.title("Face Recognition Attendance System")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # CustomTkinter theme settings
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize state variables
        self.scanning = False
        self.video_running = True
        self.last_attendance_time = {}
        self.cooldown_seconds = 5  # Seconds between duplicate warnings
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = time.time()
        
        # Initialize backend components
        print("🔧 Initializing components...")
        
        # Create directories if needed
        os.makedirs('images', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        # Initialize face encoder (loads from pickle)
        self.face_encoder = FaceEncoder()
        
        # Initialize camera (with fallback)
        self.camera = CameraHandler()
        if not self.camera.is_connected:
            print("❌ Cannot start without camera")
            sys.exit(1)
        
        # Initialize database
        self.attendance_db = AttendanceDB()
        
        # Build UI
        print("🎨 Building interface...")
        self.create_ui()
        
        # Start video loop
        print("▶️  Starting video feed...")
        self.update_video_frame()
        
        # Update status periodically
        self.update_status_bar()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("✅ Application ready!")
    
    def create_ui(self):
        """Create the complete user interface."""
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Create tabs
        self.dashboard_tab = self.tabview.add("📹 Dashboard")
        self.registration_tab = self.tabview.add("➕ Registration")
        self.records_tab = self.tabview.add("📊 Records")
        
        # Build each tab
        self.create_dashboard_tab()
        self.create_registration_tab()
        self.create_records_tab()
        
        # Status bar at bottom
        self.create_status_bar()
    
    def create_dashboard_tab(self):
        """
        Create the Dashboard tab with video feed and controls.
        
        Layout:
        - Left: Video feed (640x480 or larger)
        - Right: Controls and today's stats
        """
        # Configure grid
        self.dashboard_tab.grid_columnconfigure(0, weight=3)
        self.dashboard_tab.grid_columnconfigure(1, weight=1)
        self.dashboard_tab.grid_rowconfigure(0, weight=1)
        
        # ===== VIDEO FRAME (Left Side) =====
        video_frame = ctk.CTkFrame(self.dashboard_tab, corner_radius=10)
        video_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Video label (where frames will be displayed)
        self.video_label = ctk.CTkLabel(
            video_frame, 
            text="Starting camera...",
            font=ctk.CTkFont(size=16)
        )
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)
        
        # ===== CONTROL PANEL (Right Side) =====
        control_frame = ctk.CTkFrame(self.dashboard_tab, corner_radius=10)
        control_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Title
        ctk.CTkLabel(
            control_frame,
            text="Control Panel",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=20)
        
        # Scanning toggle button
        self.scan_button = ctk.CTkButton(
            control_frame,
            text="▶️  Start Scanning",
            font=ctk.CTkFont(size=14),
            height=40,
            command=self.toggle_scanning,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.scan_button.pack(pady=10, padx=20, fill="x")
        
        # Separator
        ctk.CTkFrame(control_frame, height=2, fg_color="gray").pack(
            fill="x", padx=20, pady=20
        )
        
        # Today's Stats
        ctk.CTkLabel(
            control_frame,
            text="Today's Attendance",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        self.stats_label = ctk.CTkLabel(
            control_frame,
            text="Count: 0",
            font=ctk.CTkFont(size=14)
        )
        self.stats_label.pack(pady=5)
        
        # Registered employees count
        self.registered_label = ctk.CTkLabel(
            control_frame,
            text=f"Registered: {self.face_encoder.get_registered_count()}",
            font=ctk.CTkFont(size=14)
        )
        self.registered_label.pack(pady=5)
        
        # Separator
        ctk.CTkFrame(control_frame, height=2, fg_color="gray").pack(
            fill="x", padx=20, pady=20
        )
        
        # Current time display
        self.time_label = ctk.CTkLabel(
            control_frame,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            font=ctk.CTkFont(size=14)
        )
        self.time_label.pack(pady=10)
        
        # FPS display
        self.fps_label = ctk.CTkLabel(
            control_frame,
            text="FPS: --",
            font=ctk.CTkFont(size=12)
        )
        self.fps_label.pack(pady=5)
    
    def create_registration_tab(self):
        """
        Create the Registration tab for adding new employees.
        
        Features:
        - Name input field
        - Live preview for capture
        - Capture button
        - Success/error feedback
        """
        # Configure grid
        self.registration_tab.grid_columnconfigure(0, weight=1)
        self.registration_tab.grid_columnconfigure(1, weight=1)
        self.registration_tab.grid_rowconfigure(0, weight=1)
        
        # ===== PREVIEW FRAME (Left) =====
        preview_frame = ctk.CTkFrame(self.registration_tab, corner_radius=10)
        preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(
            preview_frame,
            text="Live Preview",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # Preview label
        self.preview_label = ctk.CTkLabel(
            preview_frame,
            text="Camera preview will appear here",
            font=ctk.CTkFont(size=14)
        )
        self.preview_label.pack(expand=True, fill="both", padx=20, pady=10)
        
        # Preview instruction
        self.preview_instruction = ctk.CTkLabel(
            preview_frame,
            text="Position your face in the frame",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.preview_instruction.pack(pady=10)
        
        # ===== FORM FRAME (Right) =====
        form_frame = ctk.CTkFrame(self.registration_tab, corner_radius=10)
        form_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(
            form_frame,
            text="Employee Registration",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # Name input
        ctk.CTkLabel(
            form_frame,
            text="Employee Name:",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 5), padx=20, anchor="w")
        
        self.name_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Enter full name...",
            font=ctk.CTkFont(size=14),
            height=35
        )
        self.name_entry.pack(pady=5, padx=20, fill="x")
        
        # Instructions
        instructions_text = (
            "Instructions:\n"
            "1. Enter the employee's full name\n"
            "2. Position face in the preview window\n"
            "3. Click 'Capture Face'\n"
            "4. Wait for confirmation"
        )
        
        ctk.CTkLabel(
            form_frame,
            text=instructions_text,
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=300
        ).pack(pady=20, padx=20)
        
        # Capture button
        self.capture_button = ctk.CTkButton(
            form_frame,
            text="📷 Capture Face",
            font=ctk.CTkFont(size=14),
            height=40,
            command=self.capture_face
        )
        self.capture_button.pack(pady=20, padx=20, fill="x")
        
        # Status label for registration feedback
        self.registration_status = ctk.CTkLabel(
            form_frame,
            text="",
            font=ctk.CTkFont(size=12),
            wraplength=300
        )
        self.registration_status.pack(pady=10)
    
    def create_records_tab(self):
        """
        Create the Records tab for viewing attendance history.
        
        Features:
        - List of today's attendance
        - Total count display
        - Export functionality
        """
        # Configure grid
        self.records_tab.grid_columnconfigure(0, weight=1)
        self.records_tab.grid_rowconfigure(1, weight=1)
        
        # Title
        ctk.CTkLabel(
            self.records_tab,
            text="Attendance Records",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, pady=20)
        
        # Records text box
        self.records_text = ctk.CTkTextbox(
            self.records_tab,
            font=ctk.CTkFont(size=12),
            wrap="none"
        )
        self.records_text.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Refresh button
        ctk.CTkButton(
            self.records_tab,
            text="🔄 Refresh",
            command=self.refresh_records
        ).grid(row=2, column=0, pady=10)
    
    def create_status_bar(self):
        """
        Create the status bar at the bottom.
        
        Shows:
        - Current system state (Scanning, Face Detected, etc.)
        - Today's attendance count
        - Error messages
        """
        self.status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self.status_frame.grid_columnconfigure(0, weight=1)
        
        # Status label (left)
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="⏳ System Ready",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=5, sticky="w")
        
        # Info label (right)
        self.info_label = ctk.CTkLabel(
            self.status_frame,
            text=f"📊 Today: {self.attendance_db.get_registered_today_count()} | 👥 Registered: {self.face_encoder.get_registered_count()}",
            font=ctk.CTkFont(size=12),
            anchor="e"
        )
        self.info_label.grid(row=0, column=1, padx=20, pady=5, sticky="e")
    
    def update_video_frame(self):
        """
        Main video processing loop.
        
        Runs continuously at ~30 FPS:
        1. Capture frame from camera
        2. If scanning: detect and recognize faces
        3. Draw overlays (rectangles, names)
        4. Convert to Tkinter-compatible format
        5. Update label
        6. Handle attendance marking
        7. Schedule next frame
        
        PERFORMANCE NOTE:
        - Face detection runs on 0.25x resized frame (16x faster)
        - Display uses full resolution for clarity
        - Separate processing for Dashboard and Registration tabs
        """
        if not self.video_running or not self.camera.is_connected:
            return
        
        # Capture frame
        frame = self.camera.get_frame()
        
        if frame is None:
            self.after(10, self.update_video_frame)
            return
        
        # Calculate FPS
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = current_time
            self.fps_label.configure(text=f"FPS: {self.fps}")
        
        # Get active tab
        current_tab = self.tabview.get()
        
        # Process based on active tab
        if current_tab == "📹 Dashboard":
            self.process_dashboard_frame(frame)
        elif current_tab == "➕ Registration":
            self.process_registration_frame(frame)
        
        # Update time display
        self.time_label.configure(
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Schedule next frame
        self.after(10, self.update_video_frame)  # ~100 FPS max, actual ~30 FPS
    
    def process_dashboard_frame(self, frame):
        """
        Process frame for Dashboard tab.
        
        - Resize frame for display
        - Detect faces if scanning
        - Draw overlays
        - Mark attendance if recognized
        - Update video label
        """
        display_frame = frame.copy()
        
        # Face recognition if scanning
        if self.scanning and self.face_encoder.get_registered_count() > 0:
            # Get recognition results (with optimization)
            results = self.face_encoder.recognize_faces(frame)
            
            # Draw overlays and handle attendance
            face_detected = False
            
            for name, face_location, confidence in results:
                top, right, bottom, left = face_location
                face_detected = True
                
                # Determine color based on recognition
                if name != "Unknown":
                    # Green for known faces
                    color = (0, 255, 0)
                    label = f"{name} ({confidence:.2f})"
                    
                    # Mark attendance (with anti-spam)
                    self.handle_attendance(name)
                else:
                    # Red for unknown faces
                    color = (0, 0, 255)
                    label = "Unknown"
                
                # Draw rectangle
                cv2.rectangle(
                    display_frame,
                    (left, top),
                    (right, bottom),
                    color,
                    2
                )
                
                # Draw label background
                label_size, _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                cv2.rectangle(
                    display_frame,
                    (left, top - label_size[1] - 10),
                    (left + label_size[0], top),
                    color,
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    display_frame,
                    label,
                    (left, top - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
            
            # Update status
            if face_detected:
                self.set_status("👤 Face Detected")
            else:
                self.set_status("🔍 Scanning...")
        
        # Convert to RGB for display
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        
        # Resize for display (fit in window)
        height, width = rgb_frame.shape[:2]
        max_width = 640
        scale = max_width / width
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        rgb_frame = cv2.resize(rgb_frame, (new_width, new_height))
        
        # Convert to PIL Image
        image = Image.fromarray(rgb_frame)
        
        # Convert to CTkImage
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(new_width, new_height)
        )
        
        # Update label
        self.video_label.configure(image=ctk_image, text="")
        self.video_label.image = ctk_image  # Keep reference
    
    def process_registration_frame(self, frame):
        """
        Process frame for Registration tab (preview only).
        
        - Simple preview without overlays
        - Smaller size for form layout
        """
        # Resize for preview
        height, width = frame.shape[:2]
        max_width = 400
        scale = max_width / width
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        display_frame = cv2.resize(frame, (new_width, new_height))
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL and CTkImage
        image = Image.fromarray(rgb_frame)
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(new_width, new_height)
        )
        
        # Update preview
        self.preview_label.configure(image=ctk_image, text="")
        self.preview_label.image = ctk_image
    
    def handle_attendance(self, name):
        """
        Handle attendance marking with anti-spam protection.
        
        Anti-Spam Logic:
        1. Check if already marked today (from CSV)
        2. If new: Mark attendance, show success
        3. If duplicate: Check cooldown, show warning if needed
        
        Args:
            name: Recognized person's name
        """
        current_time = time.time()
        
        # Check if already marked today
        is_marked = self.attendance_db.is_already_marked(name)
        
        if is_marked:
            # Check cooldown to avoid spamming warnings
            last_warning = self.last_attendance_time.get(name, 0)
            
            if current_time - last_warning > self.cooldown_seconds:
                # Show duplicate warning (throttled)
                self.set_status(f"⚠️ {name} already marked today")
                self.last_attendance_time[name] = current_time
        else:
            # Mark new attendance
            success, message = self.attendance_db.mark_attendance(name)
            
            if success:
                self.set_status(f"✅ Attendance marked: {name}")
                self.last_attendance_time[name] = current_time
                
                # Update stats
                self.update_stats()
                
                # Refresh records tab if visible
                self.refresh_records()
    
    def toggle_scanning(self):
        """Toggle face scanning on/off."""
        self.scanning = not self.scanning
        
        if self.scanning:
            self.scan_button.configure(
                text="⏹️  Stop Scanning",
                fg_color="red",
                hover_color="darkred"
            )
            self.set_status("🔍 Scanning started...")
            
            # Check if any faces registered
            if self.face_encoder.get_registered_count() == 0:
                messagebox.showwarning(
                    "No Registered Faces",
                    "No employees registered yet. Please register at least one face first."
                )
        else:
            self.scan_button.configure(
                text="▶️  Start Scanning",
                fg_color="green",
                hover_color="darkgreen"
            )
            self.set_status("⏳ Ready")
    
    def capture_face(self):
        """
        Capture face from current frame for registration.
        
        Process:
        1. Validate name input
        2. Get current frame
        3. Add face to encoder
        4. Show success/error message
        5. Clear input
        """
        name = self.name_entry.get().strip()
        
        if not name:
            self.registration_status.configure(
                text="❌ Please enter a name",
                text_color="red"
            )
            return
        
        # Get current frame
        frame = self.camera.get_frame()
        
        if frame is None:
            self.registration_status.configure(
                text="❌ Camera error. Please try again.",
                text_color="red"
            )
            return
        
        # Add face to encoder
        success, message = self.face_encoder.add_face(frame, name)
        
        if success:
            self.registration_status.configure(
                text=f"✅ {message}",
                text_color="green"
            )
            
            # Clear input
            self.name_entry.delete(0, 'end')
            
            # Update stats
            self.update_stats()
            
            # Show success dialog
            messagebox.showinfo("Success", message)
        else:
            self.registration_status.configure(
                text=f"❌ {message}",
                text_color="red"
            )
    
    def refresh_records(self):
        """Refresh the records display."""
        # Get today's records
        records = self.attendance_db.get_all_records(date=self.attendance_db.today)
        
        # Clear and rebuild
        self.records_text.delete("0.0", "end")
        
        if not records:
            self.records_text.insert("0.0", "No attendance records for today.")
            return
        
        # Header
        header = f"{'Name':<20} {'Date':<12} {'Time':<10} {'Status':<10}\n"
        self.records_text.insert("0.0", header)
        self.records_text.insert("end", "=" * 55 + "\n")
        
        # Records
        for record in records:
            line = f"{record['Name']:<20} {record['Date']:<12} {record['Time']:<10} {record['Status']:<10}\n"
            self.records_text.insert("end", line)
    
    def set_status(self, message):
        """Update status bar message."""
        self.status_label.configure(text=message)
    
    def update_stats(self):
        """Update statistics displays."""
        today_count = self.attendance_db.get_registered_today_count()
        registered_count = self.face_encoder.get_registered_count()
        
        self.stats_label.configure(text=f"Count: {today_count}")
        self.registered_label.configure(text=f"Registered: {registered_count}")
        self.info_label.configure(
            text=f"📊 Today: {today_count} | 👥 Registered: {registered_count}"
        )
    
    def update_status_bar(self):
        """Periodic status bar updates."""
        self.update_stats()
        self.after(5000, self.update_status_bar)  # Update every 5 seconds
    
    def on_closing(self):
        """Handle window close event."""
        print("\n🛑 Shutting down...")
        
        # Stop video loop
        self.video_running = False
        
        # Release camera
        self.camera.release()
        
        # Close window
        self.destroy()
        
        print("✅ Application closed")


def main():
    """Main entry point."""
    print("=" * 50)
    print("Face Recognition Attendance System")
    print("=" * 50)
    
    # Create and run app
    app = AttendanceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
