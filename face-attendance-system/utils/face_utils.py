"""
Face Recognition Utilities Module
Handles face encoding, recognition, and persistence using pickle.

EUCLIDEAN DISTANCE EXPLANATION (For Viva):
==========================================
The face_recognition library uses a deep learning model (ResNet)
to generate 128-dimensional face embeddings (encodings).

To compare two faces:
1. Calculate Euclidean distance between their 128-d vectors:
   
   distance = √Σ(encoding1[i] - encoding2[i])² for i=0 to 127

2. Apply threshold:
   - distance < 0.6  → Same person (match found)
   - distance >= 0.6 → Different person (no match)

3. Why 128 dimensions?
   Each dimension captures different facial features like:
   - Eye distance and shape
   - Nose bridge curve
   - Jawline angle
   - Face symmetry

4. Optimization:
   We resize frames to 0.25 (25%) for processing.
   This gives 16x speedup (4× width × 4× height) while
   maintaining recognition accuracy.
"""

import os
import pickle
import cv2
import face_recognition
import numpy as np
from PIL import Image


class FaceEncoder:
    """
    Manages face encoding, storage, and recognition.
    
    Uses pickle for persistent storage of face encodings,
    enabling instant startup without re-processing images.
    
    Attributes:
        encodings_path: Path to pickle file storing encodings
        known_encodings: List of 128-d face encodings
        known_names: List of names corresponding to encodings
    """
    
    def __init__(self, encodings_path='data/encodings.pkl'):
        """
        Initialize FaceEncoder and load existing encodings.
        
        Args:
            encodings_path: Path to pickle file for persistence
        """
        self.encodings_path = encodings_path
        self.known_encodings = []
        self.known_names = []
        
        # Load existing encodings on startup (instant load)
        self.load_encodings()
    
    def load_encodings(self):
        """
        Load pre-computed face encodings from pickle file.
        
        This enables instant startup because we don't need to:
        - Scan the /images folder
        - Load and process each image
        - Compute face encodings
        
        All that work is done once during registration and saved to disk.
        """
        if os.path.exists(self.encodings_path):
            try:
                with open(self.encodings_path, 'rb') as f:
                    data = pickle.load(f)
                    self.known_encodings = data['encodings']
                    self.known_names = data['names']
                print(f"✅ Loaded {len(self.known_names)} face encodings from {self.encodings_path}")
            except Exception as e:
                print(f"⚠️  Error loading encodings: {e}")
                self.known_encodings = []
                self.known_names = []
        else:
            print(f"ℹ️  No existing encodings file found. Starting fresh.")
            self.known_encodings = []
            self.known_names = []
    
    def save_encodings(self):
        """
        Serialize face encodings to pickle file.
        
        Pickle format stores Python objects as binary data:
        - Fast to write and read
        - Preserves data types exactly
        - More efficient than JSON for NumPy arrays
        """
        data = {
            'encodings': self.known_encodings,
            'names': self.known_names
        }
        
        try:
            with open(self.encodings_path, 'wb') as f:
                pickle.dump(data, f)
            print(f"💾 Saved {len(self.known_names)} encodings to {self.encodings_path}")
        except Exception as e:
            print(f"❌ Error saving encodings: {e}")
    
    def add_face(self, image, name):
        """
        Encode a new face and add to database.
        
        Process:
        1. Detect face locations in image
        2. Compute 128-d face encoding
        3. Save image to /images folder
        4. Add encoding and name to database
        5. Persist to pickle file
        
        Args:
            image: numpy array (BGR format from OpenCV)
            name: String name of the person
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Convert BGR (OpenCV) to RGB (face_recognition)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_image)
        
        if len(face_locations) == 0:
            return False, "No face detected in image"
        
        if len(face_locations) > 1:
            return False, "Multiple faces detected. Please capture with only one person."
        
        # Get face encoding (128-dimensional vector)
        face_encoding = face_recognition.face_encodings(rgb_image, face_locations)[0]
        
        # Check if person already exists
        if name in self.known_names:
            # Update existing encoding
            index = self.known_names.index(name)
            self.known_encodings[index] = face_encoding
            message = f"Updated face data for {name}"
        else:
            # Add new person
            self.known_names.append(name)
            self.known_encodings.append(face_encoding)
            message = f"Added new person: {name}"
        
        # Save image to disk (for reference)
        image_path = f"images/{name.replace(' ', '_')}.jpg"
        cv2.imwrite(image_path, image)
        
        # Persist encodings
        self.save_encodings()
        
        return True, message
    
    def recognize_faces(self, frame, tolerance=0.6):
        """
        Recognize faces in a video frame using optimized processing.
        
        OPTIMIZATION TECHNIQUE:
        =======================
        1. Resize frame to 0.25 (25% of original size)
           - Original: 1920×1080 = 2,073,600 pixels
           - Resized:  480×270  =   129,600 pixels (16× smaller!)
           
        2. Face detection runs on small image (fast)
           
        3. Face encodings computed on small image (fast)
           
        4. Results scaled back to original coordinates for display
        
        This maintains accuracy because face_recognition's HOG/CNN
        models work well at lower resolutions, and the 128-d embeddings
        are normalized and robust to scale changes.
        
        Args:
            frame: numpy array (BGR format)
            tolerance: Matching threshold (default 0.6)
            
        Returns:
            list: Tuples of (name, face_location, confidence)
                  face_location is (top, right, bottom, left)
                  confidence is match distance (lower = better match)
        """
        # Resize frame to 0.25 for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        
        # Convert BGR to RGB
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Detect all face locations
        face_locations = face_recognition.face_locations(rgb_small_frame)
        
        # Compute face encodings for all detected faces
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        results = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare with all known faces
            name = "Unknown"
            confidence = 1.0
            
            if len(self.known_encodings) > 0:
                # Calculate Euclidean distance to all known faces
                # face_distance returns array of distances (0.0 to 1.0+)
                distances = face_recognition.face_distance(
                    self.known_encodings, 
                    face_encoding
                )
                
                # Find best match (minimum distance)
                best_match_index = np.argmin(distances)
                best_distance = distances[best_match_index]
                
                # Check if within tolerance
                if best_distance <= tolerance:
                    name = self.known_names[best_match_index]
                    confidence = best_distance
            
            # Scale face location back to original frame size
            # (multiply by 4 because we divided by 4 with 0.25 resize)
            top, right, bottom, left = face_location
            scaled_location = (
                top * 4,
                right * 4,
                bottom * 4,
                left * 4
            )
            
            results.append((name, scaled_location, confidence))
        
        return results
    
    def get_registered_count(self):
        """Return number of registered faces."""
        return len(self.known_names)
    
    def get_registered_names(self):
        """Return list of registered names."""
        return self.known_names.copy()
