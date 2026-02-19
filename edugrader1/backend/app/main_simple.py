from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import sqlite3
import os
import shutil
import json
import random
import string
import csv
import io
import time
from collections import defaultdict
from pathlib import Path
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from fastapi.responses import FileResponse, StreamingResponse

# Security
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting
rate_limit_store = defaultdict(list)

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Database setup
DB_PATH = "edugrader.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            full_name TEXT,
            hashed_password TEXT,
            role TEXT DEFAULT 'student',
            group_name TEXT,
            reset_token TEXT,
            reset_token_expires TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT UNIQUE,
            description TEXT,
            teacher_id INTEGER,
            academic_year TEXT,
            semester INTEGER,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_students (
            course_id INTEGER,
            student_id INTEGER,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (student_id) REFERENCES users (id),
            PRIMARY KEY (course_id, student_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            title TEXT,
            description TEXT,
            max_score FLOAT DEFAULT 100,
            criteria TEXT,
            deadline TIMESTAMP,
            allow_resubmit BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            student_id INTEGER,
            file_path TEXT,
            file_name TEXT,
            comment TEXT,
            status TEXT DEFAULT 'submitted',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_draft BOOLEAN DEFAULT 0,
            FOREIGN KEY (assignment_id) REFERENCES assignments (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER UNIQUE,
            grader_id INTEGER,
            scores TEXT,
            total_score FLOAT,
            feedback TEXT,
            graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES submissions (id),
            FOREIGN KEY (grader_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            comment_text TEXT,
            is_template BOOLEAN DEFAULT 0,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT,
            type TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            entity_type TEXT,
            entity_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Добавляем шаблоны комментариев для преподавателей
    cursor.execute('''
        INSERT OR IGNORE INTO comments (user_id, comment_text, is_template, category) VALUES
        (1, 'Отличная работа! Все требования выполнены.', 1, 'positive'),
        (1, 'Хорошая работа, но есть небольшие недочеты.', 1, 'neutral'),
        (1, 'Требуется доработка. Обратите внимание на комментарии.', 1, 'negative'),
        (1, 'Оригинальный подход к решению задачи.', 1, 'positive'),
        (1, 'Есть ошибки в расчетах, проверьте формулы.', 1, 'negative')
    ''')
    
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# Rate limiting middleware
async def rate_limit_middleware(request: Request, call_next, max_requests: int = 10, window_seconds: int = 60):
    client_ip = request.client.host
    now = time.time()
    
    # Clean old requests
    rate_limit_store[client_ip] = [t for t in rate_limit_store[client_ip] 
                                  if now - t < window_seconds]
    
    # Check for auth endpoints specifically
    if request.url.path in ["/api/auth/login", "/api/auth/register", "/api/auth/reset-password-request"]:
        if len(rate_limit_store[client_ip]) >= 5:  # Stricter limit for auth
            raise HTTPException(status_code=429, detail="Too many authentication attempts. Please try again later.")
    
    # General rate limit
    if len(rate_limit_store[client_ip]) >= max_requests:
        raise HTTPException(status_code=429, detail=f"Too many requests. Limit: {max_requests} per {window_seconds} seconds")
    
    rate_limit_store[client_ip].append(now)
    response = await call_next(request)
    return response

# Pydantic schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: str = "student"
    group: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    group: Optional[str]
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class CourseCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    academic_year: str
    semester: int

class CourseOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]
    teacher_id: int
    academic_year: str
    semester: int
    students_count: int = 0
    is_active: bool

class Criteria(BaseModel):
    name: str
    max_score: float

class AssignmentCreate(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = None
    max_score: float = 100
    criteria: List[Criteria]
    deadline: datetime
    allow_resubmit: bool = False

class AssignmentOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str]
    max_score: float
    criteria: List[Dict]
    deadline: datetime
    allow_resubmit: bool

class GradeCreate(BaseModel):
    submission_id: int
    scores: Dict[str, float]
    feedback: str

class GradeOut(BaseModel):
    id: int
    submission_id: int
    total_score: float
    feedback: str
    graded_at: datetime

class CommentTemplateCreate(BaseModel):
    comment_text: str
    category: str = "general"

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

class AuditLogOut(BaseModel):
    id: int
    user_id: int
    action: str
    entity_type: str
    created_at: datetime

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    group: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class BulkUserCreate(BaseModel):
    users: List[UserCreate]

# App initialization
app = FastAPI(title="EduGrader")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware_wrapper(request: Request, call_next):
    return await rate_limit_middleware(request, call_next, max_requests=30, window_seconds=60)

# Security functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_user_by_username(username: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_email(email: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def generate_reset_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def create_notification(user_id: int, title: str, message: str, type: str = "info"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, ?, ?, ?)
    ''', (user_id, title, message, type))
    conn.commit()
    conn.close()

def create_audit_log(user_id: int, action: str, entity_type: str, entity_id: int = None, 
                     old_value: str = None, new_value: str = None, ip: str = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value, new_value, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, action, entity_type, entity_id, old_value, new_value, ip))
    conn.commit()
    conn.close()

# Routes
@app.post("/api/auth/register", response_model=UserOut)
async def register(user: UserCreate, request: Request):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                  (user.username, user.email))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create user
    cursor.execute('''
        INSERT INTO users (email, username, full_name, hashed_password, role, group_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user.email, user.username, user.full_name, 
          get_password_hash(user.password), user.role, user.group))
    
    conn.commit()
    user_id = cursor.lastrowid
    
    # Create audit log
    client_ip = request.client.host
    create_audit_log(user_id, "REGISTER", "user", user_id, ip=client_ip)
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    new_user = cursor.fetchone()
    conn.close()
    
    return dict(new_user)

@app.post("/api/auth/login", response_model=Token)
async def login(request: Request, login_req: LoginRequest):
    user = get_user_by_username(login_req.username)
    
    if not user or not verify_password(login_req.password, user['hashed_password']):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if not user['is_active']:
        raise HTTPException(status_code=403, detail="Account is blocked")
    
    access_token = create_access_token(data={"sub": user['username'], "id": user['id']})
    
    # Create audit log
    create_audit_log(user['id'], "LOGIN", "user", user['id'], ip=request.client.host)
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/reset-password-request")
async def reset_password_request(reset_req: PasswordResetRequest, request: Request):
    user = get_user_by_email(reset_req.email)
    if not user:
        # Don't reveal that user doesn't exist
        return {"message": "If email exists, reset link will be sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    expires = datetime.utcnow() + timedelta(hours=24)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET reset_token = ?, reset_token_expires = ?
        WHERE id = ?
    ''', (reset_token, expires, user['id']))
    conn.commit()
    conn.close()
    
    # In real app, send email here
    print(f"Reset token for {user['email']}: {reset_token}")
    
    # Create audit log
    create_audit_log(user['id'], "PASSWORD_RESET_REQUEST", "user", user['id'], ip=request.client.host)
    
    return {"message": "Reset link sent to email"}

@app.post("/api/auth/reset-password-confirm")
async def reset_password_confirm(confirm: PasswordResetConfirm, request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users WHERE reset_token = ? AND reset_token_expires > ?
    ''', (confirm.token, datetime.utcnow()))
    
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Update password
    cursor.execute('''
        UPDATE users SET hashed_password = ?, reset_token = NULL, reset_token_expires = NULL
        WHERE id = ?
    ''', (get_password_hash(confirm.new_password), user['id']))
    
    conn.commit()
    conn.close()
    
    # Create audit log
    create_audit_log(user['id'], "PASSWORD_RESET_CONFIRM", "user", user['id'], ip=request.client.host)
    
    return {"message": "Password updated successfully"}

@app.get("/api/users/me", response_model=UserOut)
async def get_current_user_info(token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

@app.get("/api/users", response_model=List[UserOut])
async def get_users(token: str, search: str = None, request: Request = None):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(payload.get("sub"))
    if not user or user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_db()
    cursor = conn.cursor()
    
    if search:
        cursor.execute('''
            SELECT * FROM users 
            WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ?
        ''', (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("SELECT * FROM users")
    
    users = cursor.fetchall()
    conn.close()
    
    return [dict(u) for u in users]

@app.put("/api/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, user_update: UserUpdate, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    admin = get_user_by_username(payload.get("sub"))
    if not admin or admin['role'] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get old values for audit
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    old_user = cursor.fetchone()
    if not old_user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user
    updates = []
    params = []
    if user_update.full_name is not None:
        updates.append("full_name = ?")
        params.append(user_update.full_name)
    if user_update.email is not None:
        updates.append("email = ?")
        params.append(user_update.email)
    if user_update.group is not None:
        updates.append("group_name = ?")
        params.append(user_update.group)
    if user_update.role is not None:
        updates.append("role = ?")
        params.append(user_update.role)
    if user_update.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if user_update.is_active else 0)
    
    if updates:
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        
        # Create audit log
        create_audit_log(admin['id'], "UPDATE_USER", "user", user_id, 
                        json.dumps(dict(old_user)), json.dumps(user_update.dict()),
                        ip=request.client.host)
    
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    updated_user = cursor.fetchone()
    conn.close()
    
    return dict(updated_user)

@app.post("/api/users/import-csv")
async def import_users_csv(
    file: UploadFile = File(...), 
    token: str = Form(...),
    request: Request = None
):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    admin = get_user_by_username(payload.get("sub"))
    if not admin or admin['role'] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Read CSV file
    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    csv_reader = csv.DictReader(csv_file)
    
    conn = get_db()
    cursor = conn.cursor()
    imported = 0
    errors = []
    
    for row in csv_reader:
        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                          (row.get('username'), row.get('email')))
            if cursor.fetchone():
                errors.append(f"User {row.get('username')} already exists")
                continue
            
            # Create user
            cursor.execute('''
                INSERT INTO users (email, username, full_name, hashed_password, role, group_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row.get('email'),
                row.get('username'),
                row.get('full_name'),
                get_password_hash(row.get('password', 'Default123!')),
                row.get('role', 'student'),
                row.get('group')
            ))
            imported += 1
        except Exception as e:
            errors.append(f"Error importing {row.get('username')}: {str(e)}")
    
    conn.commit()
    conn.close()
    
    # Create audit log
    create_audit_log(admin['id'], "IMPORT_USERS", "user", None, 
                    ip=request.client.host if request else "unknown")
    
    return {"imported": imported, "errors": errors}

@app.get("/api/courses", response_model=list[CourseOut])
async def get_courses(token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    
    if user['role'] == "teacher":
        cursor.execute("SELECT * FROM courses WHERE teacher_id = ?", (user['id'],))
    elif user['role'] == "student":
        cursor.execute('''
            SELECT c.* FROM courses c
            JOIN course_students cs ON c.id = cs.course_id
            WHERE cs.student_id = ?
        ''', (user['id'],))
    else:
        cursor.execute("SELECT * FROM courses")
    
    courses = cursor.fetchall()
    result = []
    
    for course in courses:
        # Get students count
        cursor.execute("SELECT COUNT(*) as count FROM course_students WHERE course_id = ?", 
                      (course['id'],))
        count = cursor.fetchone()['count']
        
        course_dict = dict(course)
        course_dict['students_count'] = count
        result.append(course_dict)
    
    conn.close()
    return result

@app.post("/api/courses", response_model=CourseOut)
async def create_course(course: CourseCreate, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO courses (name, code, description, teacher_id, academic_year, semester)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (course.name, course.code, course.description, 
          user['id'], course.academic_year, course.semester))
    
    conn.commit()
    course_id = cursor.lastrowid
    
    # Create audit log
    create_audit_log(user['id'], "CREATE_COURSE", "course", course_id, 
                    ip=request.client.host)
    
    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    new_course = cursor.fetchone()
    conn.close()
    
    result = dict(new_course)
    result['students_count'] = 0
    return result

@app.post("/api/courses/{course_id}/enroll")
async def enroll_course(course_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] != "student":
        raise HTTPException(status_code=403, detail="Only students can enroll")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if already enrolled
    cursor.execute('''
        SELECT * FROM course_students 
        WHERE course_id = ? AND student_id = ?
    ''', (course_id, user['id']))
    
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO course_students (course_id, student_id)
            VALUES (?, ?)
        ''', (course_id, user['id']))
        conn.commit()
        
        # Create notification
        cursor.execute("SELECT name FROM courses WHERE id = ?", (course_id,))
        course = cursor.fetchone()
        create_notification(user['id'], "Course Enrollment", 
                           f"You have been enrolled in {course['name']}", "success")
        
        # Create audit log
        create_audit_log(user['id'], "ENROLL_COURSE", "course", course_id,
                        ip=request.client.host)
    
    conn.close()
    return {"message": "Enrolled successfully"}

@app.get("/api/assignments/course/{course_id}", response_model=list[AssignmentOut])
async def get_course_assignments(course_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments WHERE course_id = ? ORDER BY deadline", (course_id,))
    assignments = cursor.fetchall()
    
    result = []
    for assignment in assignments:
        assignment_dict = dict(assignment)
        if assignment_dict['criteria']:
            assignment_dict['criteria'] = json.loads(assignment_dict['criteria'])
        else:
            assignment_dict['criteria'] = []
        result.append(assignment_dict)
    
    conn.close()
    return result

@app.post("/api/assignments", response_model=AssignmentOut)
async def create_assignment(assignment: AssignmentCreate, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check course ownership
    cursor.execute("SELECT * FROM courses WHERE id = ? AND teacher_id = ?", 
                  (assignment.course_id, user['id']))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cursor.execute('''
        INSERT INTO assignments (course_id, title, description, max_score, criteria, deadline, allow_resubmit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (assignment.course_id, assignment.title, assignment.description,
          assignment.max_score, json.dumps([c.dict() for c in assignment.criteria]), 
          assignment.deadline, assignment.allow_resubmit))
    
    conn.commit()
    assignment_id = cursor.lastrowid
    
    # Create audit log
    create_audit_log(user['id'], "CREATE_ASSIGNMENT", "assignment", assignment_id,
                    ip=request.client.host)
    
    # Notify all students in course
    cursor.execute("SELECT student_id FROM course_students WHERE course_id = ?", 
                  (assignment.course_id,))
    students = cursor.fetchall()
    for student in students:
        create_notification(student['student_id'], "New Assignment", 
                           f"New assignment: {assignment.title}", "info")
    
    cursor.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,))
    new_assignment = cursor.fetchone()
    conn.close()
    
    result = dict(new_assignment)
    result['criteria'] = json.loads(result['criteria'])
    return result

@app.post("/api/submissions/draft")
async def save_draft(
    assignment_id: int = Form(...),
    comment: str = Form(None),
    token: str = Form(...),
    request: Request = None
):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] != "student":
        raise HTTPException(status_code=403, detail="Only students can save drafts")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if draft exists
    cursor.execute('''
        SELECT id FROM submissions 
        WHERE assignment_id = ? AND student_id = ? AND is_draft = 1
    ''', (assignment_id, user['id']))
    
    draft = cursor.fetchone()
    
    if draft:
        # Update existing draft
        cursor.execute('''
            UPDATE submissions SET comment = ? WHERE id = ?
        ''', (comment, draft['id']))
    else:
        # Create new draft
        cursor.execute('''
            INSERT INTO submissions (assignment_id, student_id, comment, is_draft, status)
            VALUES (?, ?, ?, 1, 'draft')
        ''', (assignment_id, user['id'], comment))
    
    conn.commit()
    conn.close()
    
    return {"message": "Draft saved successfully"}

@app.post("/api/submissions")
async def upload_submission(
    assignment_id: int = Form(...),
    comment: str = Form(None),
    file: UploadFile = File(...),
    token: str = Form(...),
    request: Request = None
):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")
    
    # Check file size (max 50MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size: 50MB")
    
    # Save file
    file_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if there's a draft and delete it
    cursor.execute('''
        DELETE FROM submissions 
        WHERE assignment_id = ? AND student_id = ? AND is_draft = 1
    ''', (assignment_id, user['id']))
    
    # Create submission
    cursor.execute('''
        INSERT INTO submissions (assignment_id, student_id, file_path, file_name, comment)
        VALUES (?, ?, ?, ?, ?)
    ''', (assignment_id, user['id'], str(file_path), file.filename, comment))
    
    conn.commit()
    submission_id = cursor.lastrowid
    
    # Create audit log
    create_audit_log(user['id'], "SUBMIT_WORK", "submission", submission_id,
                    ip=request.client.host if request else "unknown")
    
    # Notify teacher
    cursor.execute('''
        SELECT c.teacher_id FROM assignments a
        JOIN courses c ON a.course_id = c.id
        WHERE a.id = ?
    ''', (assignment_id,))
    teacher = cursor.fetchone()
    if teacher:
        create_notification(teacher['teacher_id'], "New Submission", 
                           f"Student {user['full_name']} submitted work", "info")
    
    conn.close()
    
    return {"message": "File uploaded successfully", "id": submission_id}

@app.get("/api/submissions/assignment/{assignment_id}")
async def get_submissions(assignment_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT s.*, u.full_name as student_name, u.username as student_username,
               u.group_name as student_group
        FROM submissions s 
        JOIN users u ON s.student_id = u.id 
        WHERE s.assignment_id = ? AND s.is_draft = 0
    """
    params = [assignment_id]
    
    if user['role'] == "student":
        query += " AND s.student_id = ?"
        params.append(user['id'])
    
    cursor.execute(query, params)
    submissions = cursor.fetchall()
    
    result = []
    for sub in submissions:
        sub_dict = dict(sub)
        cursor.execute("SELECT * FROM grades WHERE submission_id = ?", (sub['id'],))
        grade = cursor.fetchone()
        if grade:
            sub_dict['grade'] = grade['total_score']
            sub_dict['feedback'] = grade['feedback']
            sub_dict['scores'] = json.loads(grade['scores']) if grade['scores'] else {}
            sub_dict['graded_at'] = grade['graded_at']
        
        # Get assignment info for comparison
        if user['role'] == "student":
            cursor.execute('''
                SELECT AVG(total_score) as avg_score, COUNT(*) as graded_count
                FROM grades g
                JOIN submissions s ON g.submission_id = s.id
                WHERE s.assignment_id = ?
            ''', (assignment_id,))
            stats = cursor.fetchone()
            sub_dict['class_avg'] = stats['avg_score'] if stats else None
            sub_dict['graded_count'] = stats['graded_count'] if stats else 0
        
        result.append(sub_dict)
    
    conn.close()
    return result

@app.post("/api/grades")
async def create_grade(grade_data: GradeCreate, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if already graded
    cursor.execute("SELECT id FROM grades WHERE submission_id = ?", (grade_data.submission_id,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Submission already graded")
    
    total_score = sum(grade_data.scores.values())
    
    cursor.execute('''
        INSERT INTO grades (submission_id, grader_id, scores, total_score, feedback)
        VALUES (?, ?, ?, ?, ?)
    ''', (grade_data.submission_id, user['id'], 
          json.dumps(grade_data.scores), total_score, grade_data.feedback))
    
    cursor.execute("UPDATE submissions SET status = 'graded' WHERE id = ?", 
                  (grade_data.submission_id,))
    
    # Create audit log
    create_audit_log(user['id'], "CREATE_GRADE", "grade", grade_data.submission_id,
                    ip=request.client.host)
    
    # Get student id for notification
    cursor.execute("SELECT student_id FROM submissions WHERE id = ?", (grade_data.submission_id,))
    submission = cursor.fetchone()
    if submission:
        create_notification(submission['student_id'], "Work Graded", 
                           f"Your work has been graded. Score: {total_score}", "success")
    
    conn.commit()
    conn.close()
    
    return {"message": "Grade saved", "total_score": total_score}

@app.get("/api/grades/student/{student_id}")
async def get_student_grades(student_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check permissions
    if user['role'] == "student" and user['id'] != student_id:
        raise HTTPException(status_code=403, detail="Can only view own grades")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            g.id, g.total_score, g.feedback, g.graded_at,
            a.title as assignment_title,
            c.name as course_name,
            c.id as course_id,
            (SELECT AVG(total_score) FROM grades g2 
             JOIN submissions s2 ON g2.submission_id = s2.id
             WHERE s2.assignment_id = a.id) as class_avg
        FROM grades g
        JOIN submissions s ON g.submission_id = s.id
        JOIN assignments a ON s.assignment_id = a.id
        JOIN courses c ON a.course_id = c.id
        WHERE s.student_id = ?
        ORDER BY g.graded_at DESC
    ''', (student_id,))
    
    grades = cursor.fetchall()
    conn.close()
    
    result = []
    for grade in grades:
        grade_dict = dict(grade)
        # Calculate percentile if class avg exists
        if grade_dict['class_avg'] and grade_dict['total_score']:
            if grade_dict['total_score'] > grade_dict['class_avg']:
                grade_dict['comparison'] = "above"
            elif grade_dict['total_score'] < grade_dict['class_avg']:
                grade_dict['comparison'] = "below"
            else:
                grade_dict['comparison'] = "average"
        result.append(grade_dict)
    
    return result

@app.get("/api/grades/student/{student_id}/summary")
async def get_student_summary(student_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Overall average
    cursor.execute('''
        SELECT AVG(g.total_score) as overall_avg,
               COUNT(g.id) as total_grades
        FROM grades g
        JOIN submissions s ON g.submission_id = s.id
        WHERE s.student_id = ?
    ''', (student_id,))
    
    overall = cursor.fetchone()
    
    # Average by course
    cursor.execute('''
        SELECT 
            c.id, c.name,
            AVG(g.total_score) as course_avg,
            COUNT(g.id) as grades_count
        FROM grades g
        JOIN submissions s ON g.submission_id = s.id
        JOIN assignments a ON s.assignment_id = a.id
        JOIN courses c ON a.course_id = c.id
        WHERE s.student_id = ?
        GROUP BY c.id, c.name
    ''', (student_id,))
    
    by_course = cursor.fetchall()
    conn.close()
    
    return {
        "overall_average": overall['overall_avg'] if overall else 0,
        "total_grades": overall['total_grades'] if overall else 0,
        "by_course": [dict(c) for c in by_course]
    }

@app.get("/api/comments/templates")
async def get_comment_templates(token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM comments WHERE is_template = 1 ORDER BY category")
    templates = cursor.fetchall()
    conn.close()
    
    return [dict(t) for t in templates]

@app.post("/api/comments/templates")
async def create_comment_template(template: CommentTemplateCreate, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can create templates")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO comments (user_id, comment_text, is_template, category)
        VALUES (?, ?, 1, ?)
    ''', (user['id'], template.comment_text, template.category))
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    
    # Create audit log
    create_audit_log(user['id'], "CREATE_COMMENT_TEMPLATE", "comment", template_id,
                    ip=request.client.host)
    
    return {"id": template_id, "message": "Template created"}

@app.get("/api/notifications", response_model=List[NotificationOut])
async def get_notifications(token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 50
    ''', (user['id'],))
    notifications = cursor.fetchall()
    conn.close()
    
    return [dict(n) for n in notifications]

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE notifications SET is_read = 1 
        WHERE id = ? AND user_id = ?
    ''', (notification_id, user['id']))
    conn.commit()
    conn.close()
    
    return {"message": "Notification marked as read"}

@app.get("/api/audit-logs", response_model=List[AuditLogOut])
async def get_audit_logs(token: str, limit: int = 100, request: Request = None):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM audit_logs 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    logs = cursor.fetchall()
    conn.close()
    
    return [dict(l) for l in logs]

@app.get("/api/analytics/course/{course_id}")
async def get_course_analytics(course_id: int, token: str, request: Request):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Course info
    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    if not course:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Overall statistics
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT s.student_id) as total_students,
            AVG(g.total_score) as average_grade,
            COUNT(DISTINCT a.id) as total_assignments,
            SUM(CASE WHEN g.id IS NOT NULL THEN 1 ELSE 0 END) as graded_submissions,
            COUNT(s.id) as total_submissions
        FROM courses c
        LEFT JOIN assignments a ON c.id = a.course_id
        LEFT JOIN submissions s ON a.id = s.assignment_id
        LEFT JOIN grades g ON s.id = g.submission_id
        WHERE c.id = ?
    ''', (course_id,))
    
    stats = cursor.fetchone()
    
    # Grade distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN g.total_score >= 90 THEN 'A'
                WHEN g.total_score >= 75 THEN 'B'
                WHEN g.total_score >= 60 THEN 'C'
                WHEN g.total_score >= 50 THEN 'D'
                ELSE 'F'
            END as grade,
            COUNT(*) as count
        FROM grades g
        JOIN submissions s ON g.submission_id = s.id
        JOIN assignments a ON s.assignment_id = a.id
        WHERE a.course_id = ?
        GROUP BY grade
    ''', (course_id,))
    
    distribution = cursor.fetchall()
    
    # Assignment difficulty
    cursor.execute('''
        SELECT 
            a.title,
            AVG(g.total_score) as avg_score,
            a.max_score,
            COUNT(s.id) as submissions_count
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id
        LEFT JOIN grades g ON s.id = g.submission_id
        WHERE a.course_id = ?
        GROUP BY a.id
        ORDER BY avg_score ASC
    ''', (course_id,))
    
    assignments = cursor.fetchall()
    
    conn.close()
    
    # Create audit log
    create_audit_log(user['id'], "VIEW_ANALYTICS", "course", course_id,
                    ip=request.client.host)
    
    return {
        "course": dict(course),
        "statistics": dict(stats),
        "grade_distribution": [dict(d) for d in distribution],
        "assignments_difficulty": [dict(a) for a in assignments]
    }

@app.get("/api/export/grades/{course_id}")
async def export_grades(course_id: int, token: str, format: str = "csv", request: Request = None):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_username(username)
    if not user or user['role'] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all grades for course
    cursor.execute('''
        SELECT 
            u.full_name as student_name,
            u.username,
            u.group_name,
            a.title as assignment_title,
            g.total_score as grade,
            g.feedback,
            g.graded_at
        FROM grades g
        JOIN submissions s ON g.submission_id = s.id
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.student_id = u.id
        WHERE a.course_id = ?
        ORDER BY u.full_name, a.title
    ''', (course_id,))
    
    grades = cursor.fetchall()
    conn.close()
    
    # Create audit log
    create_audit_log(user['id'], "EXPORT_GRADES", "course", course_id,
                    ip=request.client.host if request else "unknown")
    
    if format == "csv":
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Name', 'Username', 'Group', 'Assignment', 'Grade', 'Feedback', 'Date'])
        
        for grade in grades:
            writer.writerow([
                grade['student_name'],
                grade['username'],
                grade['group_name'] or '',
                grade['assignment_title'],
                grade['grade'],
                grade['feedback'] or '',
                grade['graded_at']
            ])
        
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=grades_course_{course_id}.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

@app.get("/")
async def root():
    return {"message": "EduGrader API is running", "version": "1.0"}

@app.get("/test")
async def test():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)