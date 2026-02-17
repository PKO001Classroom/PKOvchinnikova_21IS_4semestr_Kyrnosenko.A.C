from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os
import uuid
from typing import Optional

from app.core.database import engine, Base, get_db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.models.user import User, UserRole
from app.models.course import Course, CourseStatus
from app.models.assignment import Assignment, Rubric
from app.models.submission import Submission, SubmissionStatus, Grade
from sqlalchemy.orm import Session

# Создание таблиц в БД
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EduGrader", version="1.0.0")

# Настройка CORS для API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Подключение шаблонов
templates = Jinja2Templates(directory="../frontend/templates")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_current_user_from_cookie(request: Request, db: Session):
    """Получение текущего пользователя из cookie"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except:
        return None

# ==================== СТРАНИЦЫ ====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Главная страница"""
    user = get_current_user_from_cookie(request, db)
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "user": user, "now": datetime.now()}
    )

# ==================== АУТЕНТИФИКАЦИЯ ====================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, db: Session = Depends(get_db)):
    """Страница входа"""
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "auth/login.html", 
        {"request": request, "error": error}
    )

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Обработка входа"""
    # Поиск пользователя
    user = db.query(User).filter(
        (User.email == username) | (User.username == username)
    ).first()
    
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse(
            url="/login?error=Неверный email или пароль",
            status_code=302
        )
    
    if not user.is_active:
        return RedirectResponse(
            url="/login?error=Аккаунт заблокирован",
            status_code=302
        )
    
    # Создание токена
    expires_delta = timedelta(days=30) if remember else timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=expires_delta
    )
    
    # Обновление времени последнего входа
    user.last_login_at = datetime.now()
    db.commit()
    
    # Установка cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=int(expires_delta.total_seconds()),
        secure=False,  # В продакшене должно быть True
        samesite="lax"
    )
    
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None, db: Session = Depends(get_db)):
    """Страница регистрации"""
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "auth/register.html", 
        {"request": request, "error": error}
    )

@app.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    group: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Обработка регистрации"""
    # Проверка пароля
    if password != confirm_password:
        return RedirectResponse(
            url="/register?error=Пароли не совпадают",
            status_code=302
        )
    
    if len(password) < 8:
        return RedirectResponse(
            url="/register?error=Пароль должен быть минимум 8 символов",
            status_code=302
        )
    
    # Проверка существующего пользователя
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse(
            url="/register?error=Пользователь с таким email уже существует",
            status_code=302
        )
    
    # Создание пользователя
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name,
        role=role,
        group=group if role == "student" else None,
        password_hash=get_password_hash(password),
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    
    # Автоматический вход после регистрации
    access_token = create_access_token(data={"sub": str(user.id)})
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,
        secure=False
    )
    
    return response

@app.get("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

# ==================== ДАШБОРД ====================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Дашборд пользователя"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Статистика в зависимости от роли
    if user.role == UserRole.STUDENT:
        # Курсы студента
        courses = user.courses_enrolled
        
        # Статистика
        total_courses = len(courses)
        pending_assignments = db.query(Assignment).join(Course).filter(
            Course.id.in_([c.id for c in courses]),
            Assignment.due_date > datetime.now()
        ).count()
        
        # Последние оценки
        recent_grades = db.query(Grade).filter(
            Grade.student_id == user.id
        ).order_by(Grade.created_at.desc()).limit(5).all()
        
        # Ближайшие дедлайны
        deadlines = db.query(Assignment).join(Course).filter(
            Course.id.in_([c.id for c in courses]),
            Assignment.due_date > datetime.now(),
            Assignment.due_date < datetime.now() + timedelta(days=7)
        ).order_by(Assignment.due_date).limit(5).all()
        
    elif user.role == UserRole.TEACHER:
        # Курсы преподавателя
        courses = user.courses_teaching
        
        # Статистика
        total_courses = len(courses)
        pending_reviews = db.query(Submission).filter(
            Submission.assignment_id.in_(
                db.query(Assignment.id).filter(Assignment.course_id.in_([c.id for c in courses]))
            ),
            Submission.status == SubmissionStatus.SUBMITTED
        ).count()
        
        recent_grades = []
        deadlines = []
    
    else:  # ADMIN
        courses = db.query(Course).all()
        total_courses = len(courses)
        pending_assignments = db.query(Assignment).filter(
            Assignment.due_date > datetime.now()
        ).count()
        pending_reviews = db.query(Submission).filter(
            Submission.status == SubmissionStatus.SUBMITTED
        ).count()
        recent_grades = []
        deadlines = []
    
    return templates.TemplateResponse(
        "dashboard/dashboard.html",
        {
            "request": request,
            "user": user,
            "courses": courses[:5],  # Топ 5 курсов
            "total_courses": total_courses,
            "pending_assignments": pending_assignments if user.role == UserRole.STUDENT else None,
            "pending_reviews": pending_reviews if user.role == UserRole.TEACHER else None,
            "recent_grades": recent_grades if user.role == UserRole.STUDENT else None,
            "deadlines": deadlines if user.role == UserRole.STUDENT else None,
            "now": datetime.now()
        }
    )

# ==================== КУРСЫ ====================

@app.get("/courses", response_class=HTMLResponse)
async def courses_page(
    request: Request,
    page: int = 1,
    search: str = "",
    db: Session = Depends(get_db)
):
    """Страница со списком курсов"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    per_page = 9
    offset = (page - 1) * per_page
    
    # Запрос в зависимости от роли
    query = db.query(Course)
    
    if user.role == UserRole.STUDENT:
        query = query.filter(Course.students.any(id=user.id))
    elif user.role == UserRole.TEACHER:
        query = query.filter(Course.teacher_id == user.id)
    
    if search:
        query = query.filter(
            (Course.name.ilike(f"%{search}%")) | 
            (Course.code.ilike(f"%{search}%"))
        )
    
    total = query.count()
    courses = query.offset(offset).limit(per_page).all()
    
    return templates.TemplateResponse(
        "courses/courses.html",
        {
            "request": request,
            "user": user,
            "courses": courses,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "search": search,
            "now": datetime.now()
        }
    )

@app.get("/courses/create", response_class=HTMLResponse)
async def course_create_page(request: Request, db: Session = Depends(get_db)):
    """Страница создания курса"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        return RedirectResponse(url="/courses", status_code=302)
    
    return templates.TemplateResponse(
        "courses/course_create.html",
        {"request": request, "user": user}
    )

@app.post("/courses/create")
async def course_create(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(None),
    credits: int = Form(3),
    max_students: int = Form(30),
    db: Session = Depends(get_db)
):
    """Создание нового курса"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        return RedirectResponse(url="/courses", status_code=302)
    
    # Проверка уникальности кода
    existing = db.query(Course).filter(Course.code == code).first()
    if existing:
        return templates.TemplateResponse(
            "courses/course_create.html",
            {
                "request": request,
                "user": user,
                "error": "Курс с таким кодом уже существует",
                "code": code,
                "name": name,
                "description": description,
                "credits": credits,
                "max_students": max_students
            }
        )
    
    course = Course(
        id=uuid.uuid4(),
        code=code,
        name=name,
        description=description,
        credits=credits,
        max_students=max_students,
        teacher_id=user.id,
        status=CourseStatus.ACTIVE,
        is_published=False
    )
    
    db.add(course)
    db.commit()
    
    return RedirectResponse(url=f"/courses/{course.id}", status_code=302)

@app.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_detail(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Детальная страница курса"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return RedirectResponse(url="/courses", status_code=302)
    
    # Проверка доступа
    if user.role == UserRole.STUDENT and user not in course.students:
        return RedirectResponse(url="/courses", status_code=302)
    if user.role == UserRole.TEACHER and course.teacher_id != user.id:
        return RedirectResponse(url="/courses", status_code=302)
    
    assignments = db.query(Assignment).filter(
        Assignment.course_id == course.id
    ).order_by(Assignment.due_date).all()
    
    students = course.students
    
    return templates.TemplateResponse(
        "courses/course_detail.html",
        {
            "request": request,
            "user": user,
            "course": course,
            "assignments": assignments,
            "students": students,
            "now": datetime.now()
        }
    )

@app.post("/courses/{course_id}/enroll")
async def course_enroll(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Запись студента на курс"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.STUDENT:
        return RedirectResponse(url="/login", status_code=302)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return RedirectResponse(url="/courses", status_code=302)
    
    if user not in course.students and len(course.students) < course.max_students:
        course.students.append(user)
        db.commit()
    
    return RedirectResponse(url=f"/courses/{course_id}", status_code=302)

# ==================== ЗАДАНИЯ ====================

@app.get("/courses/{course_id}/assignments/create", response_class=HTMLResponse)
async def assignment_create_page(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Страница создания задания"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        return RedirectResponse(url="/courses", status_code=302)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.teacher_id != user.id:
        return RedirectResponse(url="/courses", status_code=302)
    
    return templates.TemplateResponse(
        "assignments/assignment_create.html",
        {"request": request, "user": user, "course": course}
    )

@app.post("/courses/{course_id}/assignments/create")
async def assignment_create(
    request: Request,
    course_id: str,
    title: str = Form(...),
    description: str = Form(...),
    max_score: int = Form(100),
    due_date: str = Form(...),
    db: Session = Depends(get_db)
):
    """Создание нового задания"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        return RedirectResponse(url="/courses", status_code=302)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.teacher_id != user.id:
        return RedirectResponse(url="/courses", status_code=302)
    
    assignment = Assignment(
        id=uuid.uuid4(),
        course_id=course.id,
        created_by=user.id,
        title=title,
        description=description,
        max_score=max_score,
        due_date=datetime.fromisoformat(due_date),
        is_published=True
    )
    
    db.add(assignment)
    db.commit()
    
    return RedirectResponse(url=f"/courses/{course_id}", status_code=302)

@app.get("/assignments/{assignment_id}", response_class=HTMLResponse)
async def assignment_detail(request: Request, assignment_id: str, db: Session = Depends(get_db)):
    """Детальная страница задания"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse(url="/courses", status_code=302)
    
    # Проверка доступа
    if user.role == UserRole.STUDENT and user not in assignment.course.students:
        return RedirectResponse(url="/courses", status_code=302)
    
    # Проверка, сдавал ли студент работу
    submission = None
    if user.role == UserRole.STUDENT:
        submission = db.query(Submission).filter(
            Submission.assignment_id == assignment.id,
            Submission.student_id == user.id
            Продолжить с того места, где остановился. Напиши полную реализацию всех эндпоинтов и шаблонов. Я хочу видеть полный код для всего приложения. Я сказал вообще без JavaScript, значит ни строчки JS не должно быть. Вся логика на сервере, все формы отправляются с перезагрузкой страницы. Напиши код для всех страниц: профиль, оценки, проверка работ, админка и т.д. Я жду полный код.<｜end▁of▁thinking｜># EduGrader - Полный код (Python + HTML/CSS, БЕЗ JavaScript)

Продолжаю полную реализацию системы **без единой строчки JavaScript**. Вся логика на сервере, формы отправляются с перезагрузкой страницы.

## 📁 **Продолжение backend/app/main.py**

```python
# ==================== ЗАДАНИЯ (ПРОДОЛЖЕНИЕ) ====================

@app.get("/assignments/{assignment_id}/submit", response_class=HTMLResponse)
async def assignment_submit_page(request: Request, assignment_id: str, error: str = None, db: Session = Depends(get_db)):
    """Страница сдачи задания"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.STUDENT:
        return RedirectResponse(url="/login", status_code=302)
    
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse(url="/courses", status_code=302)
    
    # Проверка, сдавал ли уже
    existing = db.query(Submission).filter(
        Submission.assignment_id == assignment.id,
        Submission.student_id == user.id
    ).first()
    
    if existing and existing.status != SubmissionStatus.RETURNED:
        return RedirectResponse(url=f"/submissions/{existing.id}", status_code=302)
    
    return templates.TemplateResponse(
        "assignments/assignment_submit.html",
        {
            "request": request,
            "user": user,
            "assignment": assignment,
            "error": error,
            "now": datetime.now()
        }
    )

@app.post("/assignments/{assignment_id}/submit")
async def assignment_submit(
    request: Request,
    assignment_id: str,
    file: UploadFile = File(...),
    comments: str = Form(""),
    db: Session = Depends(get_db)
):
    """Обработка сдачи задания"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.STUDENT:
        return RedirectResponse(url="/login", status_code=302)
    
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse(url="/courses", status_code=302)
    
    # Проверка размера файла (макс 50 МБ)
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > 50 * 1024 * 1024:
        return RedirectResponse(
            url=f"/assignments/{assignment_id}/submit?error=Файл слишком большой (макс 50 МБ)",
            status_code=302
        )
    
    # Сохранение файла
    upload_dir = f"../frontend/static/uploads/{assignment_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = f"{upload_dir}/{user.id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Определение статуса (просрочено или нет)
    status = SubmissionStatus.LATE if datetime.now() > assignment.due_date else SubmissionStatus.SUBMITTED
    
    # Создание записи о сдаче
    submission = Submission(
        id=uuid.uuid4(),
        assignment_id=assignment.id,
        student_id=user.id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        comments=comments,
        status=status,
        attempt_number=1
    )
    
    db.add(submission)
    db.commit()
    
    return RedirectResponse(url=f"/submissions/{submission.id}", status_code=302)

# ==================== СДАННЫЕ РАБОТЫ ====================

@app.get("/submissions", response_class=HTMLResponse)
async def submissions_list(
    request: Request,
    status: str = "all",
    db: Session = Depends(get_db)
):
    """Список сданных работ"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    query = db.query(Submission)
    
    if user.role == UserRole.STUDENT:
        query = query.filter(Submission.student_id == user.id)
    elif user.role == UserRole.TEACHER:
        # Работы по курсам преподавателя
        query = query.join(Assignment).join(Course).filter(
            Course.teacher_id == user.id
        )
    
    if status != "all":
        query = query.filter(Submission.status == status)
    
    submissions = query.order_by(Submission.submitted_at.desc()).all()
    
    return templates.TemplateResponse(
        "submissions/submissions.html",
        {
            "request": request,
            "user": user,
            "submissions": submissions,
            "current_status": status,
            "now": datetime.now()
        }
    )

@app.get("/submissions/{submission_id}", response_class=HTMLResponse)
async def submission_detail(request: Request, submission_id: str, db: Session = Depends(get_db)):
    """Детальная страница сданной работы"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return RedirectResponse(url="/submissions", status_code=302)
    
    # Проверка доступа
    if user.role == UserRole.STUDENT and submission.student_id != user.id:
        return RedirectResponse(url="/submissions", status_code=302)
    
    if user.role == UserRole.TEACHER and submission.assignment.course.teacher_id != user.id:
        return RedirectResponse(url="/submissions", status_code=302)
    
    return templates.TemplateResponse(
        "submissions/submission_detail.html",
        {
            "request": request,
            "user": user,
            "submission": submission,
            "now": datetime.now()
        }
    )

@app.get("/submissions/{submission_id}/review", response_class=HTMLResponse)
async def submission_review_page(request: Request, submission_id: str, error: str = None, db: Session = Depends(get_db)):
    """Страница проверки работы"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.TEACHER:
        return RedirectResponse(url="/login", status_code=302)
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return RedirectResponse(url="/submissions", status_code=302)
    
    # Проверка, что работа принадлежит курсу преподавателя
    if submission.assignment.course.teacher_id != user.id:
        return RedirectResponse(url="/submissions", status_code=302)
    
    return templates.TemplateResponse(
        "submissions/submission_review.html",
        {
            "request": request,
            "user": user,
            "submission": submission,
            "assignment": submission.assignment,
            "error": error,
            "now": datetime.now()
        }
    )

@app.post("/submissions/{submission_id}/review")
async def submission_review(
    request: Request,
    submission_id: str,
    score: int = Form(...),
    feedback: str = Form(""),
    db: Session = Depends(get_db)
):
    """Обработка проверки работы"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.TEACHER:
        return RedirectResponse(url="/login", status_code=302)
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return RedirectResponse(url="/submissions", status_code=302)
    
    # Проверка, что работа принадлежит курсу преподавателя
    if submission.assignment.course.teacher_id != user.id:
        return RedirectResponse(url="/submissions", status_code=302)
    
    # Валидация баллов
    if score < 0 or score > submission.assignment.max_score:
        return RedirectResponse(
            url=f"/submissions/{submission_id}/review?error=Некорректное количество баллов",
            status_code=302
        )
    
    # Создание оценки
    grade = Grade(
        id=uuid.uuid4(),
        submission_id=submission.id,
        student_id=submission.student_id,
        grader_id=user.id,
        assignment_id=submission.assignment_id,
        total_score=score,
        max_score=submission.assignment.max_score,
        percentage=(score / submission.assignment.max_score) * 100,
        comments=feedback,
        is_published=True
    )
    
    db.add(grade)
    
    # Обновление статуса работы
    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now()
    submission.graded_by = user.id
    
    db.commit()
    
    return RedirectResponse(url=f"/submissions/{submission_id}", status_code=302)

# ==================== ОЦЕНКИ ====================

@app.get("/grades", response_class=HTMLResponse)
async def grades_list(
    request: Request,
    course_id: str = None,
    db: Session = Depends(get_db)
):
    """Страница со списком оценок"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    query = db.query(Grade)
    
    if user.role == UserRole.STUDENT:
        query = query.filter(Grade.student_id == user.id)
    elif user.role == UserRole.TEACHER:
        query = query.join(Assignment).join(Course).filter(
            Course.teacher_id == user.id
        )
    
    if course_id:
        query = query.join(Assignment).filter(Assignment.course_id == course_id)
    
    grades = query.order_by(Grade.created_at.desc()).all()
    
    # Получение списка курсов для фильтра
    courses = []
    if user.role == UserRole.STUDENT:
        courses = user.courses_enrolled
    elif user.role == UserRole.TEACHER:
        courses = user.courses_teaching
    
    return templates.TemplateResponse(
        "grades/grades.html",
        {
            "request": request,
            "user": user,
            "grades": grades,
            "courses": courses,
            "selected_course": course_id,
            "now": datetime.now()
        }
    )

# ==================== ПРОФИЛЬ ====================

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, success: str = None, error: str = None, db: Session = Depends(get_db)):
    """Страница профиля"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "profile/profile.html",
        {
            "request": request,
            "user": user,
            "success": success,
            "error": error,
            "now": datetime.now()
        }
    )

@app.post("/profile/update")
async def profile_update(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(None),
    group: str = Form(None),
    db: Session = Depends(get_db)
):
    """Обновление профиля"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    user.full_name = full_name
    user.phone = phone
    
    if user.role == UserRole.STUDENT:
        user.group = group
    
    user.updated_at = datetime.now()
    db.commit()
    
    return RedirectResponse(url="/profile?success=Профиль успешно обновлен", status_code=302)

@app.post("/profile/change-password")
async def profile_change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Смена пароля"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Проверка текущего пароля
    if not verify_password(current_password, user.password_hash):
        return RedirectResponse(
            url="/profile?error=Неверный текущий пароль",
            status_code=302
        )
    
    # Проверка нового пароля
    if new_password != confirm_password:
        return RedirectResponse(
            url="/profile?error=Новые пароли не совпадают",
            status_code=302
        )
    
    if len(new_password) < 8:
        return RedirectResponse(
            url="/profile?error=Пароль должен быть минимум 8 символов",
            status_code=302
        )
    
    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.now()
    db.commit()
    
    return RedirectResponse(url="/profile?success=Пароль успешно изменен", status_code=302)

# ==================== АДМИН-ПАНЕЛЬ ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Админ-панель"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=302)
    
    # Статистика
    total_users = db.query(User).count()
    total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    total_teachers = db.query(User).filter(User.role == UserRole.TEACHER).count()
    total_courses = db.query(Course).count()
    total_assignments = db.query(Assignment).count()
    total_submissions = db.query(Submission).count()
    
    # Последние пользователи
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    
    # Последние курсы
    recent_courses = db.query(Course).order_by(Course.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        "admin/admin_panel.html",
        {
            "request": request,
            "user": user,
            "total_users": total_users,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_courses": total_courses,
            "total_assignments": total_assignments,
            "total_submissions": total_submissions,
            "recent_users": recent_users,
            "recent_courses": recent_courses,
            "now": datetime.now()
        }
    )

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    page: int = 1,
    search: str = "",
    role: str = "",
    db: Session = Depends(get_db)
):
    """Управление пользователями"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=302)
    
    per_page = 20
    offset = (page - 1) * per_page
    
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    total = query.count()
    users = query.offset(offset).limit(per_page).all()
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "search": search,
            "role": role,
            "now": datetime.now()
        }
    )

@app.post("/admin/users/{user_id}/toggle-status")
async def admin_toggle_user_status(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Блокировка/разблокировка пользователя"""
    admin = get_current_user_from_cookie(request, db)
    if not admin or admin.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=302)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        return RedirectResponse(url="/admin/users", status_code=302)
    
    # Нельзя заблокировать самого себя
    if target_user.id == admin.id:
        return RedirectResponse(
            url="/admin/users?error=Нельзя заблокировать самого себя",
            status_code=302
        )
    
    target_user.is_active = not target_user.is_active
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@app.post("/admin/users/{user_id}/change-role")
async def admin_change_user_role(
    request: Request,
    user_id: str,
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    """Изменение роли пользователя"""
    admin = get_current_user_from_cookie(request, db)
    if not admin or admin.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=302)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        return RedirectResponse(url="/admin/users", status_code=302)
    
    target_user.role = role
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@app.get("/admin/import-users", response_class=HTMLResponse)
async def admin_import_users_page(request: Request, error: str = None, db: Session = Depends(get_db)):
    """Страница импорта пользователей"""
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse(
        "admin/import_users.html",
        {"request": request, "user": user, "error": error}
    )

@app.post("/admin/import-users")
async def admin_import_users(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Импорт пользователей из CSV"""
    admin = get_current_user_from_cookie(request, db)
    if not admin or admin.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=302)
    
    if not file.filename.endswith('.csv'):
        return RedirectResponse(
            url="/admin/import-users?error=Пожалуйста, загрузите CSV файл",
            status_code=302
        )
    
    content = await file.read()
    lines = content.decode('utf-8').split('\n')
    
    imported = 0
    errors = []
    
    for i, line in enumerate(lines[1:]):  # Пропускаем заголовок
        if not line.strip():
            continue
        
        try:
            parts = line.strip().split(',')
            if len(parts) < 3:
                continue
            
            email = parts[0].strip()
            full_name = parts[1].strip()
            role = parts[2].strip()
            group = parts[3].strip() if len(parts) > 3 else None
            
            # Проверка существования
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                errors.append(f"Строка {i+2}: Email {email} уже существует")
                continue
            
            # Создание пользователя
            user = User(
                id=uuid.uuid4(),
                email=email,
                full_name=full_name,
                role=role,
                group=group if role == 'student' else None,
                password_hash=get_password_hash("default123"),
                is_active=True,
                is_verified=True
            )
            
            db.add(user)
            imported += 1
            
        except Exception as e:
            errors.append(f"Строка {i+2}: Ошибка - {str(e)}")
    
    if imported > 0:
        db.commit()
    
    return templates.TemplateResponse(
        "admin/import_result.html",
        {
            "request": request,
            "user": admin,
            "imported": imported,
            "errors": errors,
            "now": datetime.now()
        }
    )

# ==================== API (для мобильных приложений) ====================

@app.get("/api/v1/users/me")
async def api_get_current_user(request: Request, db: Session = Depends(get_db)):
    """API: Получение текущего пользователя"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "group": user.group
    }

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)