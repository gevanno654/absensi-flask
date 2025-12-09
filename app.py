from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import json
import traceback
import threading
import queue
import time

from database import Database
from face_recognizer import FaceRecognizer

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize components with thread safety
db = None
face_recognizer = None
init_lock = threading.Lock()

# Request queue for face recognition to prevent overload
recognition_queue = queue.Queue(maxsize=10)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def initialize_components():
    """Initialize database and face recognizer with thread safety"""
    global db, face_recognizer
    
    with init_lock:
        if db is None:
            try:
                db = Database()
                print("✅ Database initialized")
            except Exception as e:
                print(f"❌ Database initialization failed: {e}")
                db = None
        
        if face_recognizer is None:
            try:
                face_recognizer = FaceRecognizer()
                print("✅ Face Recognizer initialized")
            except Exception as e:
                print(f"❌ Face Recognizer initialization failed: {e}")
                face_recognizer = None

# Initialize on startup
initialize_components()

def check_components():
    """Check if components are initialized and working"""
    if db is None or face_recognizer is None:
        initialize_components()
    
    # Test database connection
    if db and not db.test_connection():
        print("⚠️ Database connection lost, reinitializing...")
        initialize_components()
    
    return db is not None and face_recognizer is not None

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    components_ok = check_components()
    
    if components_ok:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": "connected",
                "face_recognizer": "initialized"
            }
        }), 200
    else:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": "disconnected" if db is None else "connected",
                "face_recognizer": "uninitialized" if face_recognizer is None else "initialized"
            }
        }), 503

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/attendance')
def attendance_page():
    return render_template('attendance.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/view_data')
def view_data_page():
    return render_template('view_data.html')

@app.route('/camera_test')
def camera_test_page():
    return render_template('camera_test.html')

@app.route('/api/register', methods=['POST'])
def register_student():
    """API untuk mendaftarkan mahasiswa baru"""
    if not check_components():
        return jsonify({
            "success": False,
            "message": "System components not available"
        }), 503
    
    try:
        data = request.json
        nim = data.get('nim', '').strip()
        name = data.get('name', '').strip()
        image_data = data.get('image', '')
        
        if not nim or not name or not image_data:
            return jsonify({
                "success": False,
                "message": "NIM, name, and image are required"
            }), 400
        
        # Register face
        result = face_recognizer.register_face_from_image(image_data, nim, name)
        
        if result['success']:
            # Save to database
            face_id = result['face_id']
            db.add_student(nim, name, face_id)
            
            # Log activity
            db.log_activity(f"New student registered: {name}", 
                           f"NIM: {nim}, Face ID: {face_id}")
            
            return jsonify({
                "success": True,
                "message": f"Student {name} registered successfully!",
                "face_id": face_id,
                "nim": nim
            })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Registration error: {str(e)}"
        }), 500

def process_recognition(image_data):
    """Process face recognition in a controlled manner"""
    try:
        # Recognize face
        result = face_recognizer.recognize_face_from_image(image_data)
        
        if not result['success']:
            return result
        
        # Process recognition results
        if result['results']:
            recognition = result['results'][0]
            
            if recognition['recognized']:
                # Get student from database
                student = db.get_student_by_face_id(recognition['face_id'])
                
                if student:
                    # Record attendance
                    attendance_result = db.record_attendance(
                        student['id'],
                        student['nim'],
                        student['name'],
                        recognition['confidence'],
                        recognition['lighting']
                    )
                    
                    recognition['attendance'] = attendance_result
                    recognition['db_student'] = student
        
        return result
        
    except Exception as e:
        print(f"❌ Recognition processing error: {e}")
        return {
            "success": False,
            "message": f"Recognition processing error: {str(e)}"
        }

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    """API untuk mengenali wajah dan mengambil absensi dengan rate limiting"""
    if not check_components():
        return jsonify({
            "success": False,
            "message": "System components not available"
        }), 503
    
    try:
        data = request.json
        image_data = data.get('image', '')
        
        if not image_data:
            return jsonify({
                "success": False,
                "message": "Image is required"
            }), 400
        
        # Rate limiting: check if queue is full
        if recognition_queue.full():
            return jsonify({
                "success": False,
                "message": "System is busy, please try again in a moment",
                "queue_size": recognition_queue.qsize()
            }), 429  # Too Many Requests
        
        # Add to queue and process
        recognition_queue.put(image_data)
        
        try:
            result = process_recognition(image_data)
            recognition_queue.get()  # Remove from queue after processing
            return jsonify(result)
        except Exception as e:
            recognition_queue.get()  # Still remove from queue on error
            raise e
        
    except Exception as e:
        print(f"❌ Recognition error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Recognition error: {str(e)}"
        }), 500

@app.route('/api/students', methods=['GET'])
def get_students():
    """API untuk mendapatkan data mahasiswa"""
    if not check_components():
        return jsonify({
            "success": False,
            "message": "System components not available"
        }), 503
    
    try:
        students = db.get_students()
        return jsonify({
            "success": True,
            "count": len(students),
            "students": students
        })
    except Exception as e:
        print(f"❌ Get students error: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/attendance/today', methods=['GET'])
def get_today_attendance():
    """API untuk mendapatkan absensi hari ini"""
    if not check_components():
        return jsonify({
            "success": False,
            "message": "System components not available"
        }), 503
    
    try:
        attendance = db.get_today_attendance()
        stats = db.get_attendance_stats()
        
        return jsonify({
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "count": len(attendance),
            "attendance": attendance,
            "stats": stats[0] if stats else {}
        })
    except Exception as e:
        print(f"❌ Get today attendance error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/attendance/date/<date>', methods=['GET'])
def get_attendance_by_date(date):
    """API untuk mendapatkan absensi berdasarkan tanggal"""
    if not check_components():
        return jsonify({
            "success": False,
            "message": "System components not available"
        }), 503
    
    try:
        attendance = db.get_attendance_by_date(date)
        return jsonify({
            "success": True,
            "date": date,
            "count": len(attendance),
            "attendance": attendance
        })
    except Exception as e:
        print(f"❌ Get attendance by date error: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """API untuk mendapatkan statistik"""
    if not check_components():
        return jsonify({
            "success": False,
            "message": "System components not available"
        }), 503
    
    try:
        stats = db.get_attendance_stats()
        recent_logs = db.get_recent_logs(5)
        
        return jsonify({
            "success": True,
            "stats": stats[0] if stats else {},
            "recent_logs": recent_logs
        })
    except Exception as e:
        print(f"❌ Get statistics error: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """API untuk mengecek status sistem"""
    try:
        components_ok = check_components()
        model_status = face_recognizer is not None and hasattr(face_recognizer, 'students')
        
        return jsonify({
            "success": components_ok,
            "database": "connected" if db and db.test_connection() else "disconnected",
            "face_model": "loaded" if model_status else "not_found",
            "students_count": len(face_recognizer.students) if face_recognizer else 0,
            "recognition_queue": recognition_queue.qsize(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        print(f"❌ System status error: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/system/optimize', methods=['POST'])
def optimize_system():
    """API untuk mengoptimalkan sistem"""
    try:
        # Optimize database tables
        if db:
            db.optimize_tables()
        
        return jsonify({
            "success": True,
            "message": "System optimization completed"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

# Static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "success": False,
        "message": "Resource not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"❌ Internal server error: {error}")
    traceback.print_exc()
    return jsonify({
        "success": False,
        "message": "Internal server error"
    }), 500

@app.errorhandler(429)
def ratelimit_error(error):
    return jsonify({
        "success": False,
        "message": "Too many requests, please slow down"
    }), 429

# Database maintenance thread
def database_maintenance():
    """Background thread for database maintenance"""
    while True:
        try:
            time.sleep(3600)  # Run every hour
            
            if db:
                # Clean up old data (older than 90 days)
                db.cleanup_old_data(days=90)
                
                # Optimize tables
                db.optimize_tables()
                
                print("✅ Database maintenance completed")
                
        except Exception as e:
            print(f"❌ Database maintenance error: {e}")

# Start maintenance thread
maintenance_thread = threading.Thread(target=database_maintenance, daemon=True)
maintenance_thread.start()

if __name__ == '__main__':
    print("🚀 Starting Face Attendance System...")
    print(f"📊 Database: {db.database if db else 'Not initialized'}")
    print(f"🤖 Face Model: {'Loaded' if face_recognizer else 'Not found'}")
    print(f"👨‍🎓 Registered Students: {len(face_recognizer.students) if face_recognizer else 0}")
    print(f"🌐 Server running on: http://localhost:5000")
    print(f"🏥 Health check: http://localhost:5000/health")
    
    app.run(
        host='192.168.1.3', 
        port=5000, 
        debug=False,  # Set to False for production
        threaded=True,
        processes=1
    )