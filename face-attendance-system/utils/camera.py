"""
Camera Handler Module
Handles webcam capture with automatic fallback between camera indices.
Optimized for macOS where camera 0 might be unavailable.
"""

import sys
import time
import cv2
import tkinter as tk
from tkinter import messagebox

# Detect if running on macOS
IS_MACOS = sys.platform == 'darwin'


class CameraHandler:
    """
    Manages webcam connection with automatic index fallback.
    
    On macOS, the default camera might not always be at index 0,
    especially with external webcams or virtual cameras.
    This handler tries index 0 first, then falls back to index 1.
    
    Attributes:
        cap: OpenCV VideoCapture object
        current_index: Currently active camera index (0 or 1)
        is_connected: Boolean indicating successful connection
    """
    
    def __init__(self):
        """Initialize camera handler and attempt connection."""
        self.cap = None
        self.current_index = 0
        self.is_connected = False
        self.connect()
    
    def connect(self):
        """
        Attempt to connect to camera with fallback.
        
        On macOS: Uses AVFOUNDATION backend (better permission handling)
        On Linux/Windows: Uses default V4L2/DShow backends
        
        Tries camera index 0 first (default camera).
        If that fails, tries index 1 (external/webcam).
        
        Raises:
            Shows error dialog if no camera is found.
        """
        # On macOS, use AVFOUNDATION backend for better permission handling
        # This prevents the GIL/threading crash when permission dialog appears
        backend = cv2.CAP_AVFOUNDATION if IS_MACOS else cv2.CAP_ANY
        
        # Try camera index 0 (default)
        print("📷 Attempting to connect to camera...")
        if IS_MACOS:
            print("   (macOS detected - using AVFOUNDATION backend)")
            # On macOS, give system a moment to handle permission dialog
            # without blocking Python's GIL
            self.cap = cv2.VideoCapture(0, backend)
            time.sleep(0.5)  # Allow permission dialog to process
        else:
            self.cap = cv2.VideoCapture(0, backend)
        
        if self.cap.isOpened():
            self.current_index = 0
            self.is_connected = True
            print(f"✅ Camera connected at index 0")
            return
        
        # Fallback to camera index 1
        if IS_MACOS:
            self.cap = cv2.VideoCapture(1, backend)
            time.sleep(0.5)
        else:
            self.cap = cv2.VideoCapture(1, backend)
        
        if self.cap.isOpened():
            self.current_index = 1
            self.is_connected = True
            print(f"✅ Camera connected at index 1 (fallback)")
            return
        
        # No camera found
        self.is_connected = False
        error_msg = (
            "No camera found or permission denied!\n\n"
            "On macOS:\n"
            "1. Go to System Settings > Privacy & Security > Camera\n"
            "2. Enable camera access for Terminal/IDE\n"
            "3. Restart the application\n\n"
            "Also check:\n"
            "• Camera is connected\n"
            "• No other app is using the camera"
        )
        print(f"❌ {error_msg}")
        
        # Show error dialog (deferred to avoid threading issues)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Camera Error", error_msg)
            root.destroy()
        except Exception as e:
            print(f"Could not show dialog: {e}")
    
    def get_frame(self):
        """
        Capture a single frame from the camera.
        
        Returns:
            numpy.ndarray: Frame in BGR format, or None if capture failed
        """
        if not self.is_connected or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            print("⚠️  Warning: Failed to capture frame")
            return None
        
        return frame
    
    def release(self):
        """Release camera resources. Should be called on app exit."""
        if self.cap is not None:
            self.cap.release()
            self.is_connected = False
            print("📷 Camera released")
    
    def __del__(self):
        """Destructor to ensure camera is released."""
        self.release()
