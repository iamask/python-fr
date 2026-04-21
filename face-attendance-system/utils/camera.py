"""
Camera Handler Module
Handles webcam capture with automatic fallback between camera indices.
Optimized for macOS where camera 0 might be unavailable.
"""

import cv2
import tkinter as tk
from tkinter import messagebox


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
        
        Tries camera index 0 first (default camera).
        If that fails, tries index 1 (external/webcam).
        
        Raises:
            Shows error dialog if no camera is found.
        """
        # Try camera index 0 (default)
        self.cap = cv2.VideoCapture(0)
        
        if self.cap.isOpened():
            self.current_index = 0
            self.is_connected = True
            print(f"✅ Camera connected at index 0")
            return
        
        # Fallback to camera index 1
        self.cap = cv2.VideoCapture(1)
        
        if self.cap.isOpened():
            self.current_index = 1
            self.is_connected = True
            print(f"✅ Camera connected at index 1 (fallback)")
            return
        
        # No camera found
        self.is_connected = False
        error_msg = (
            "No camera found!\n\n"
            "Please check:\n"
            "• Camera is connected\n"
            "• Camera permissions are granted in System Preferences > Security & Privacy\n"
            "• No other app is using the camera"
        )
        print(f"❌ {error_msg}")
        
        # Show error dialog
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Camera Error", error_msg)
        root.destroy()
    
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
