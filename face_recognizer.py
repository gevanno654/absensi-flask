import cv2
import numpy as np
import os
import pickle
from datetime import datetime
import base64
import io
from PIL import Image
import warnings
import threading
warnings.filterwarnings('ignore')

class FaceRecognizer:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, model_dir="models"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FaceRecognizer, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_dir="models"):
        if not self._initialized:
            self.model_dir = model_dir
            os.makedirs(model_dir, exist_ok=True)
            
            # Path untuk file model
            self.cascade_path = os.path.join(model_dir, "haarcascade_frontalface_default.xml")
            self.model_path = os.path.join(model_dir, "face_trainer.yml")
            self.students_path = os.path.join(model_dir, "students_data.pkl")
            
            # Download cascade file jika belum ada
            if not os.path.exists(self.cascade_path):
                print("Downloading haarcascade...")
                import urllib.request
                url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
                urllib.request.urlretrieve(url, self.cascade_path)
            
            # Initialize with locks for thread safety
            self.face_cascade = None
            self.recognizer = None
            self.students = {}
            self.next_face_id = 0
            self.model_lock = threading.Lock()
            self.students_lock = threading.Lock()
            
            # Load existing data
            self._load_data()
            
            self._initialized = True
    
    def _load_data(self):
        """Load trained model and student data with thread safety"""
        try:
            # Load face detector
            self.face_cascade = cv2.CascadeClassifier(self.cascade_path)
            
            # Initialize recognizer
            self.recognizer = cv2.face.LBPHFaceRecognizer_create(
                radius=2,
                neighbors=16,
                grid_x=8,
                grid_y=8
            )
            
            # Load trained model
            if os.path.exists(self.model_path):
                with self.model_lock:
                    self.recognizer.read(self.model_path)
                print("✅ Model loaded successfully")
            
            # Load student data
            if os.path.exists(self.students_path):
                with self.students_lock:
                    with open(self.students_path, 'rb') as f:
                        self.students = pickle.load(f)
                
                # Determine next available face_id
                if self.students:
                    self.next_face_id = max(self.students.keys()) + 1
                else:
                    self.next_face_id = 0
                    
                print(f"✅ {len(self.students)} students data loaded")
            else:
                print("ℹ️ No existing student data found")
                
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
            raise
    
    def _save_data(self):
        """Save model and student data with thread safety"""
        try:
            with self.model_lock:
                self.recognizer.write(self.model_path)
            
            with self.students_lock:
                with open(self.students_path, 'wb') as f:
                    pickle.dump(self.students, f)
                    
            print("✅ Data saved successfully")
            
        except Exception as e:
            print(f"❌ Failed to save data: {e}")
            raise
    
    def preprocess_face(self, face_image):
        """Preprocess face for better recognition"""
        try:
            # Resize to consistent size
            face_image = cv2.resize(face_image, (200, 200))
            
            # Apply CLAHE for contrast normalization
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            face_image = clahe.apply(face_image)
            
            # Gaussian blur for noise reduction
            face_image = cv2.GaussianBlur(face_image, (5, 5), 0)
            
            return face_image
        except Exception as e:
            print(f"❌ Preprocessing error: {e}")
            return cv2.resize(face_image, (200, 200))
    
    def register_face_from_image(self, image_base64, nim, name):
        """Register a new face from base64 image with thread safety"""
        try:
            # Check if NIM already exists
            with self.students_lock:
                for student_id, student_data in self.students.items():
                    if student_data['nim'] == nim:
                        return {"success": False, "message": "NIM already registered"}
            
            # Decode base64 image
            image_data = base64.b64decode(image_base64.split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5,
                minSize=(100, 100)
            )
            
            if len(faces) == 0:
                return {"success": False, "message": "No face detected"}
            
            # Take the largest face
            faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
            x, y, w, h = faces[0]
            
            # Extract and preprocess face
            face_roi = gray[y:y+h, x:x+w]
            processed_face = self.preprocess_face(face_roi)
            
            # Assign face_id
            with self.students_lock:
                face_id = self.next_face_id
                
                # Add to students dictionary
                self.students[face_id] = {
                    "nim": nim,
                    "name": name,
                    "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                self.next_face_id += 1
            
            # Training recognizer with lock
            with self.model_lock:
                faces_for_training = []
                labels_for_training = []
                
                # Add multiple augmented versions for better training
                for i in range(3):  # Create 3 augmented versions
                    augmented_face = self.augment_face(processed_face, i)
                    faces_for_training.append(augmented_face)
                    labels_for_training.append(face_id)
                
                # Train the model
                if os.path.exists(self.model_path):
                    # Update existing model
                    self.recognizer.update(faces_for_training, np.array(labels_for_training))
                else:
                    # Train new model
                    self.recognizer.train(faces_for_training, np.array(labels_for_training))
            
            # Save everything
            self._save_data()
            
            return {
                "success": True,
                "face_id": face_id,
                "message": f"Student {name} registered successfully",
                "face_size": f"{w}x{h}"
            }
            
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def augment_face(self, face_image, variation):
        """Create augmented versions of face for training"""
        try:
            if variation == 0:
                return face_image  # Original
            elif variation == 1:
                # Brighten
                return cv2.convertScaleAbs(face_image, alpha=1.2, beta=10)
            elif variation == 2:
                # Darken
                return cv2.convertScaleAbs(face_image, alpha=0.8, beta=-10)
            elif variation == 3:
                # Add slight blur
                return cv2.GaussianBlur(face_image, (3, 3), 0)
            else:
                return face_image
        except:
            return face_image
    
    def recognize_face_from_image(self, image_base64):
        """Recognize face from base64 image with thread safety"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64.split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )
            
            if len(faces) == 0:
                return {
                    "success": False,
                    "message": "No face detected",
                    "faces_count": 0
                }
            
            results = []
            # Take only the largest face (main face)
            faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
            x, y, w, h = faces[0]
            
            # Extract and preprocess face
            face_roi = gray[y:y+h, x:x+w]
            processed_face = self.preprocess_face(face_roi)
            
            # Predict with lock
            with self.model_lock:
                face_id, confidence = self.recognizer.predict(processed_face)
            
            # Adjust confidence (lower is better in LBPH)
            confidence = 100 - confidence if confidence < 100 else 0
            
            # Analyze lighting condition
            brightness = np.mean(gray)
            if brightness < 50:
                lighting = "Dark"
            elif brightness < 100:
                lighting = "Dim"
            elif brightness < 150:
                lighting = "Normal"
            else:
                lighting = "Bright"
            
            # Check if recognized
            with self.students_lock:
                if face_id in self.students and confidence > 65:  # Threshold 65%
                    student = self.students[face_id]
                    results.append({
                        "face_id": face_id,
                        "nim": student['nim'],
                        "name": student['name'],
                        "confidence": round(confidence, 2),
                        "bounding_box": {
                            "x": int(x),
                            "y": int(y),
                            "width": int(w),
                            "height": int(h)
                        },
                        "lighting": lighting,
                        "recognized": True
                    })
                else:
                    results.append({
                        "face_id": None,
                        "nim": None,
                        "name": "Unknown",
                        "confidence": round(confidence, 2),
                        "bounding_box": {
                            "x": int(x),
                            "y": int(y),
                            "width": int(w),
                            "height": int(h)
                        },
                        "lighting": lighting,
                        "recognized": False
                    })
            
            return {
                "success": True,
                "faces_detected": len(faces),
                "results": results,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"❌ Recognition error: {e}")
            return {
                "success": False,
                "message": f"Recognition error: {str(e)}"
            }