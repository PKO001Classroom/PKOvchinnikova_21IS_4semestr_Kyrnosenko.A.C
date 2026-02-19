from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import sqlite3
import os
import shutil
import json
import hashlib
from pathlib import Path
import jwt
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr

# Security
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Простое хеширование паролей (для тестирования)
def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

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
    
    # Create tables - Упрощенная версия
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            full_name TEXT,
            hashed_password TEXT,
            role TEXT DEFAULT 'student',
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
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_students (
            course_id INTEGER,
            student_id INTEGER,
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
            FOREIGN KEY (assignment_id) REFERENCES assignments (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER,
            grader_id INTEGER,
            scores TEXT,
            total_score FLOAT,
            feedback TEXT,
            graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES submissions (id),
            FOREIGN KEY (grader_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Pydantic schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: str = "student"

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

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

class AssignmentOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str]
    max_score: float
    criteria: List[Dict]
    deadline: datetime

class GradeCreate(BaseModel):
    submission_id: int
    scores: Dict[str, float]
    feedback: str

# App initialization
app = FastAPI(title="EduGrader")

# CORS - разрешаем все источники для тестирования
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security functions
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

# Routes
@app.post("/api/auth/register", response_model=UserOut)
def register(user: UserCreate, request: Request = None):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                  (user.username, user.email))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create user - без group_name
    cursor.execute('''
        INSERT INTO users (email, username, full_name, hashed_password, role)
        VALUES (?, ?, ?, ?, ?)
    ''', (user.email, user.username, user.full_name, 
          get_password_hash(user.password), user.role))
    
    conn.commit()
    user_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    new_user = cursor.fetchone()
    conn.close()
    
    return dict(new_user)

@app.post("/api/auth/login", response_model=Token)
def login(request: LoginRequest):
    user = get_user_by_username(request.username)
    
    if not user or not verify_password(request.password, user['hashed_password']):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user['username'], "id": user['id']})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=UserOut)
def get_current_user_info(token: str):
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

@app.get("/api/courses", response_model=list[CourseOut])
def get_courses(token: str):
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
        cursor.execute("SELECT COUNT(*) as count FROM course_students WHERE course_id = ?", 
                      (course['id'],))
        count = cursor.fetchone()['count']
        
        course_dict = dict(course)
        course_dict['students_count'] = count
        result.append(course_dict)
    
    conn.close()
    return result

@app.post("/api/courses", response_model=CourseOut)
def create_course(course: CourseCreate, token: str):
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
    
    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    new_course = cursor.fetchone()
    conn.close()
    
    result = dict(new_course)
    result['students_count'] = 0
    return result

@app.post("/api/courses/{course_id}/enroll")
def enroll_course(course_id: int, token: str):
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
    
    conn.close()
    return {"message": "Enrolled successfully"}

# Остальные роуты (assignments, submissions, grades) можно добавить позже

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)