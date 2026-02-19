# PYTHON ТЕСТЫ
## Планировщик индивидуального образовательного маршрута

**Версия документа:** 1.0
**Дата создания:** 29.01.2026  
**Автор:** Курносенко Александр Сергеевич, группа 21ИС-24  
**Статус:** Учебный проект
**Руководитель практики:** Бобошко Михаил Николаевич

---

# 🧪 3. PYTHON ТЕСТЫ
## 3.1. Структура тестов
```
tests/
├── unit/
│   ├── test_database.py
│   ├── test_models.py
│   ├── test_processor.py
│   └── test_report.py
├── integration/
│   ├── test_gui.py
│   └── test_workflow.py
├── fixtures/
│   └── test_data.json
└── conftest.py
```

## 3.2. Тесты базы данных
```
import unittest
import sqlite3
import os
import tempfile

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_table_creation(self):
        tables = ['цели', 'навыки', 'компетенции']
        for table in tables:
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            result = self.cursor.fetchone()
            self.assertIsNotNone(result, f"Таблица {table} не создана")
    
    def test_goal_insert(self):
        self.cursor.execute("""
            INSERT INTO цели (название, тип, статус) 
            VALUES ('Тест цель', 'учебная', 'запланирована')
        """)
        self.cursor.execute("SELECT COUNT(*) FROM цели")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1)
    
    def test_foreign_keys(self):
        self.cursor.execute("PRAGMA foreign_keys")
        result = self.cursor.fetchone()[0]
        self.assertEqual(result, 1)
    
    def test_unique_constraint(self):
        self.cursor.execute("""
            INSERT INTO навыки (название) VALUES ('Python')
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("""
                INSERT INTO навыки (название) VALUES ('Python')
            """)

if __name__ == '__main__':
    unittest.main()
```

## 3.3. Тесты обработки текста
```
class TestTextProcessor(unittest.TestCase):
    def setUp(self):
        from main import PlannerApp
        self.processor = PlannerApp()
    
    def test_markdown_processing(self):
        test_cases = [
            ("- элемент списка", "• элемент списка"),
            ("*важный*", "ВАЖНЫЙ"),
            ("# заголовок", "▶ заголовок"),
            ("@ задача", "✓ задача"),
            ("обычный текст", "обычный текст")
        ]
        
        for input_text, expected in test_cases:
            result = self.processor.process_text(input_text)
            self.assertEqual(result, expected)
    
    def test_multiline_processing(self):
        text = "- первый\n- второй\n*важно*\nобычный"
        expected = "• первый\n• второй\nВАЖНО\nобычный"
        result = self.processor.process_text(text)
        self.assertEqual(result, expected)
    
    def test_empty_text(self):
        result = self.processor.process_text("")
        self.assertEqual(result, "")
    
    def test_special_characters(self):
        text = "Текст с *звездочками* и - дефисами"
        expected = "Текст с ЗВЕЗДОЧКАМИ и - дефисами"
        result = self.processor.process_text(text)
        self.assertEqual(result, expected)
```

## 3.4. Тесты генерации отчетов
```
class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        
    def test_txt_export(self):
        from main import PlannerApp
        app = PlannerApp()
        app.export_dir = self.temp_dir
        
        test_data = [
            (1, 'Тест цель 1', 'учебная', 'в процессе', '2024-01-01', None, 'Описание'),
            (2, 'Тест цель 2', 'внеучебная', 'выполнена', '2024-02-01', '2024-02-15', '')
        ]
        
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE цели (
                id INTEGER PRIMARY KEY,
                название TEXT,
                тип TEXT,
                статус TEXT,
                план_дата TEXT,
                факт_дата TEXT,
                описание TEXT
            )
        """)
        
        for data in test_data:
            cursor.execute("INSERT INTO цели VALUES (?, ?, ?, ?, ?, ?, ?)", data)
        
        conn.commit()
        
        export_path = os.path.join(self.temp_dir, 'test_export.txt')
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("Тестовый экспорт\n")
        
        self.assertTrue(os.path.exists(export_path))
        
    def test_word_report_structure(self):
        try:
            from docx import Document
            
            doc = Document()
            doc.add_heading('Тестовый отчет', 0)
            doc.add_paragraph('Тестовый параграф')
            
            temp_file = os.path.join(self.temp_dir, 'test.docx')
            doc.save(temp_file)
            
            self.assertTrue(os.path.exists(temp_file))
            self.assertGreater(os.path.getsize(temp_file), 1000)
            
        except ImportError:
            self.skipTest("python-docx не установлен")
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
```
## 3.5. Интеграционные тесты
```
class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.app = PlannerApp()
        self.app.root.withdraw()
    
    def test_complete_workflow(self):
        # 1. Добавление цели
        self.app.add_goal()
        
        # 2. Проверка отображения
        self.app.refresh_goals()
        
        # 3. Редактирование
        self.app.edit_goal()
        
        # 4. Экспорт
        self.app.export_data_txt()
        
        # 5. Генерация отчета
        self.app.generate_report_docx()
    
    def test_data_persistence(self):
        conn = sqlite3.connect(self.app.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM цели")
        initial_count = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO цели (название, тип, статус) 
            VALUES ('Персистентная цель', 'учебная', 'запланирована')
        """)
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM цели")
        new_count = cursor.fetchone()[0]
        
        self.assertEqual(new_count, initial_count + 1)
        conn.close()
```

## 3.6. Фикстуры для тестов
```
# tests/fixtures/test_data.json
{
  "goals": [
    {
      "id": 1,
      "название": "Изучить Python",
      "тип": "учебная",
      "статус": "выполнена",
      "план_дата": "2024-01-01",
      "факт_дата": "2024-06-01",
      "описание": "- основы\n- ООП\n*важно* практика"
    }
  ],
  "skills": [
    {"id": 1, "название": "Python программирование"},
    {"id": 2, "название": "Работа с БД"}
  ],
  "competences": [
    {
      "id": 1,
      "название": "Технические навыки",
      "категория": "Hard Skills"
    }
  ]
}
```

## 3.7. Запуск тестов
```
# Запуск всех тестов
python -m pytest tests/ -v

# Запуск unit тестов
python -m pytest tests/unit/ -v

# Запуск с покрытием кода
python -m pytest --cov=main tests/

# Генерация отчета покрытия
python -m pytest --cov=main --cov-report=html tests/
```

---

**Разработал:**  
___________________________  
**Курносенко Александр Сергеевич**  
Студент группы 21ИС-24  
Дата: 29.01.2026

**Принял:**  
___________________________  
**Бобошко Михаил Николаевич**  
Руководитель учебной практики  
Дата: ___________________

---
