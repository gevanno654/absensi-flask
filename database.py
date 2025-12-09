import mysql.connector
from mysql.connector import Error, pooling
import json
from datetime import datetime, timedelta
import threading
import time

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.host = "localhost"
            self.user = "root"
            self.password = ""  # Default XAMPP kosong
            self.database = "face_attendance_db"
            self.pool = None
            self.pool_size = 10
            self.max_overflow = 20
            self._initialized = True
            self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize database connection pool"""
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="face_attendance_pool",
                pool_size=self.pool_size,
                pool_reset_session=True,
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
                buffered=True,
                connection_timeout=30,
                use_pure=True
            )
            print(f"✅ Database connection pool created (size: {self.pool_size})")
            
            # Test connection
            conn = self.pool.get_connection()
            if conn.is_connected():
                print("✅ Database connected successfully")
                conn.close()
            else:
                print("❌ Database connection failed")
                
        except Error as e:
            print(f"❌ Database pool initialization failed: {e}")
            self.pool = None
    
    def get_connection(self):
        """Get a connection from the pool with retry logic"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not self.pool:
                    self._initialize_pool()
                
                conn = self.pool.get_connection()
                
                # Test connection
                if not conn.is_connected():
                    conn.reconnect(attempts=3, delay=1)
                
                return conn
                
            except Error as e:
                print(f"❌ Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e
    
    def _serialize_row(self, row):
        """Convert datetime and timedelta objects to strings for JSON serialization"""
        if row is None:
            return None
        
        if isinstance(row, dict):
            result = {}
            for key, value in row.items():
                if isinstance(value, (datetime, timedelta)):
                    result[key] = str(value)
                elif isinstance(value, bytes):
                    result[key] = value.decode('utf-8', errors='ignore')
                else:
                    result[key] = value
            return result
        elif isinstance(row, list):
            return [self._serialize_row(item) for item in row]
        else:
            return row
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute query with automatic connection management"""
        conn = None
        cursor = None
        
        try:
            # Get connection from pool
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            # Execute query
            cursor.execute(query, params or ())
            
            if fetch:
                rows = cursor.fetchall()
                # Serialize rows for JSON compatibility
                result = [self._serialize_row(row) for row in rows]
            else:
                conn.commit()
                result = cursor.lastrowid
            
            return result
            
        except Error as e:
            print(f"❌ Query error: {e}")
            print(f"   Query: {query}")
            print(f"   Params: {params}")
            
            # Try to reconnect and retry once
            try:
                if conn and not conn.is_connected():
                    conn.reconnect()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(query, params or ())
                    
                    if fetch:
                        rows = cursor.fetchall()
                        result = [self._serialize_row(row) for row in rows]
                    else:
                        conn.commit()
                        result = cursor.lastrowid
                    
                    return result
            except Error as retry_error:
                print(f"❌ Retry also failed: {retry_error}")
            
            return None
            
        finally:
            # Always close cursor and return connection to pool
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def execute_many(self, query, params_list):
        """Execute multiple queries in batch"""
        conn = None
        cursor = None
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.executemany(query, params_list)
            conn.commit()
            
            return cursor.rowcount
            
        except Error as e:
            print(f"❌ Batch query error: {e}")
            if conn:
                conn.rollback()
            return 0
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def test_connection(self):
        """Test database connection"""
        try:
            conn = self.get_connection()
            if conn.is_connected():
                conn.close()
                return True
            return False
        except:
            return False
    
    # CRUD Operations for Students
    def add_student(self, nim, name, face_id):
        query = """
        INSERT INTO students (nim, name, face_id) 
        VALUES (%s, %s, %s)
        """
        return self.execute_query(query, (nim, name, face_id))
    
    def get_students(self):
        query = "SELECT * FROM students ORDER BY name"
        return self.execute_query(query, fetch=True)
    
    def get_student_by_nim(self, nim):
        query = "SELECT * FROM students WHERE nim = %s"
        result = self.execute_query(query, (nim,), fetch=True)
        return result[0] if result else None
    
    def get_student_by_face_id(self, face_id):
        query = "SELECT * FROM students WHERE face_id = %s"
        result = self.execute_query(query, (face_id,), fetch=True)
        return result[0] if result else None
    
    # Attendance Operations with transaction
    def record_attendance(self, student_id, nim, name, confidence, lighting):
        today = datetime.now().date()
        current_time = datetime.now().time().strftime('%H:%M:%S')  # Convert to string
        
        conn = None
        cursor = None
        
        try:
            # Get connection
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Start transaction
            conn.start_transaction()
            
            # Cek apakah sudah absen hari ini
            check_query = """
            SELECT * FROM attendance 
            WHERE student_id = %s AND date = %s
            """
            cursor.execute(check_query, (student_id, today))
            existing = cursor.fetchall()
            
            if existing:
                conn.rollback()
                return {"status": "already", "record": existing[0]}
            
            # Tambah absensi baru
            query = """
            INSERT INTO attendance 
            (student_id, nim, name, date, time, confidence, lighting_condition) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (student_id, nim, name, today, current_time, confidence, lighting)
            
            cursor.execute(query, params)
            attendance_id = cursor.lastrowid
            
            # Commit transaction
            conn.commit()
            
            # Log activity
            self.log_activity(f"Attendance recorded for {name}", 
                            f"NIM: {nim}, Confidence: {confidence:.1f}")
            
            return {"status": "success", "attendance_id": attendance_id}
            
        except Error as e:
            print(f"❌ Attendance recording error: {e}")
            if conn:
                conn.rollback()
            return {"status": "error", "message": str(e)}
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_today_attendance(self):
        today = datetime.now().date()
        query = """
        SELECT a.*, s.face_id 
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.id
        WHERE a.date = %s
        ORDER BY a.time DESC
        """
        return self.execute_query(query, (today,), fetch=True)
    
    def get_attendance_by_date(self, date):
        query = """
        SELECT a.*, s.face_id 
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.id
        WHERE a.date = %s
        ORDER BY a.time DESC
        """
        return self.execute_query(query, (date,), fetch=True)
    
    def get_attendance_stats(self):
        query = """
        SELECT 
            COUNT(DISTINCT student_id) as total_students,
            COUNT(CASE WHEN date = CURDATE() THEN 1 END) as today_attendance,
            (SELECT COUNT(*) FROM students) as registered_students
        FROM attendance
        """
        result = self.execute_query(query, fetch=True)
        return result[0] if result else {}
    
    # System Logs
    def log_activity(self, activity, details=""):
        query = """
        INSERT INTO system_logs (activity, details) 
        VALUES (%s, %s)
        """
        self.execute_query(query, (activity, details))
    
    def get_recent_logs(self, limit=10):
        query = """
        SELECT * FROM system_logs 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        return self.execute_query(query, (limit,), fetch=True)
    
    # Database maintenance
    def optimize_tables(self):
        """Optimize database tables for performance"""
        tables = ['students', 'attendance', 'system_logs']
        for table in tables:
            try:
                self.execute_query(f"OPTIMIZE TABLE {table}")
                print(f"✅ Table {table} optimized")
            except Error as e:
                print(f"❌ Failed to optimize {table}: {e}")
    
    def cleanup_old_data(self, days=30):
        """Clean up old attendance data"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()
            query = "DELETE FROM attendance WHERE date < %s"
            result = self.execute_query(query, (cutoff_date,))
            print(f"✅ Cleaned up {result} old attendance records")
            return result
        except Error as e:
            print(f"❌ Cleanup failed: {e}")
            return 0