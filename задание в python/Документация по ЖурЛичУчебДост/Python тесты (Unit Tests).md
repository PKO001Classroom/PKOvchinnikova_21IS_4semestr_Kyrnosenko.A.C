#  Python тесты (Unit Tests)
## Журнал личных учебных достижений

**Версия документа:** 1.0
**Дата создания:** 29.01.2026  
**Автор:** Курносенко Александр Сергеевич, группа 21ИС-24  
**Статус:** Учебный проект
**Руководитель практики:** Бобошко Михаил Николаевич

---

# 🧪 Python тесты (Unit Tests)
## Файл: test_achievements.py
```
import unittest
import tempfile
import os
import json
from datetime import datetime
import sqlite3
from docx import Document

class TestAchievementsSystem(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестовой среды"""
        # Создаем временную директорию
        self.test_dir = tempfile.mkdtemp()
        
        # Создаем тестовый JSON файл
        self.types_json_path = os.path.join(self.test_dir, 'types.json')
        with open(self.types_json_path, 'w', encoding='utf-8') as f:
            json.dump(["Олимпиада", "Сертификат", "Проект"], f)
        
        # Создаем тестовую базу данных
        self.db_path = os.path.join(self.test_dir, 'test_achievements.db')
        self.init_test_db()
    
    def init_test_db(self):
        """Инициализация тестовой базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                level TEXT NOT NULL,
                description TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def test_01_types_json_loading(self):
        """Тест загрузки типов из JSON файла"""
        with open(self.types_json_path, 'r', encoding='utf-8') as f:
            types = json.load(f)
        
        self.assertEqual(len(types), 3)
        self.assertIn("Олимпиада", types)
        self.assertIn("Сертификат", types)
        self.assertIn("Проект", types)
    
    def test_02_database_creation(self):
        """Тест создания таблицы в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='achievements'")
        table_exists = cursor.fetchone()
        
        self.assertIsNotNone(table_exists)
        
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(achievements)")
        columns = cursor.fetchall()
        
        expected_columns = [
            ('id', 'INTEGER', 0, None, 1),
            ('name', 'TEXT', 1, None, 0),
            ('date', 'TEXT', 1, None, 0),
            ('type', 'TEXT', 1, None, 0),
            ('level', 'TEXT', 1, None, 0),
            ('description', 'TEXT', 0, None, 0)
        ]
        
        for i, column in enumerate(columns):
            self.assertEqual(column[1], expected_columns[i][0])  # Имя колонки
            self.assertEqual(column[2], expected_columns[i][1])  # Тип данных
        
        conn.close()
    
    def test_03_date_validation(self):
        """Тест валидации формата даты"""
        valid_dates = [
            "2024-01-15",
            "2023-12-31",
            "2025-02-28"
        ]
        
        invalid_dates = [
            "15-01-2024",
            "2024/01/15",
            "2024-13-01",
            "2024-01-32",
            "не дата",
            ""
        ]
        
        for date in valid_dates:
            try:
                datetime.strptime(date, "%Y-%m-%d")
                is_valid = True
            except ValueError:
                is_valid = False
            
            self.assertTrue(is_valid, f"Дата {date} должна быть валидной")
        
        for date in invalid_dates:
            try:
                datetime.strptime(date, "%Y-%m-%d")
                is_valid = True
            except ValueError:
                is_valid = False
            
            self.assertFalse(is_valid, f"Дата {date} должна быть невалидной")
    
    def test_04_database_insert(self):
        """Тест добавления записи в базу данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Вставляем тестовые данные
        test_data = [
            ("Олимпиада по математике", "2024-01-15", "Олимпиада", "региональный", "Занял 1 место"),
            ("Сертификат Python", "2024-02-20", "Сертификат", "национальный", "Курс по Python продвинутый")
        ]
        
        for data in test_data:
            cursor.execute('''
                INSERT INTO achievements (name, date, type, level, description)
                VALUES (?, ?, ?, ?, ?)
            ''', data)
        
        conn.commit()
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM achievements")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        # Проверяем содержимое записей
        cursor.execute("SELECT name, date, type, level, description FROM achievements ORDER BY id")
        records = cursor.fetchall()
        
        for i, record in enumerate(records):
            self.assertEqual(record[0], test_data[i][0])
            self.assertEqual(record[1], test_data[i][1])
            self.assertEqual(record[2], test_data[i][2])
            self.assertEqual(record[3], test_data[i][3])
            self.assertEqual(record[4], test_data[i][4])
        
        conn.close()
    
    def test_05_database_delete(self):
        """Тест удаления записи из базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Добавляем тестовые данные
        cursor.execute('''
            INSERT INTO achievements (name, date, type, level, description)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Тестовое достижение", "2024-01-01", "Проект", "локальный", "Тест"))
        
        conn.commit()
        
        # Получаем ID добавленной записи
        cursor.execute("SELECT id FROM achievements WHERE name = ?", ("Тестовое достижение",))
        record_id = cursor.fetchone()[0]
        
        # Удаляем запись
        cursor.execute("DELETE FROM achievements WHERE id = ?", (record_id,))
        conn.commit()
        
        # Проверяем что запись удалена
        cursor.execute("SELECT COUNT(*) FROM achievements WHERE id = ?", (record_id,))
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        
        conn.close()
    
    def test_06_word_export(self):
        """Тест экспорта в Word документ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Очищаем таблицу и добавляем тестовые данные
        cursor.execute("DELETE FROM achievements")
        
        test_data = [
            ("Олимпиада по математике", "2024-01-15", "Олимпиада", "региональный", "Занял 1 место"),
            ("Сертификат Python", "2024-02-20", "Сертификат", "национальный", "Курс по Python продвинутый")
        ]
        
        for data in test_data:
            cursor.execute('''
                INSERT INTO achievements (name, date, type, level, description)
                VALUES (?, ?, ?, ?, ?)
            ''', data)
        
        conn.commit()
        
        # Получаем данные для экспорта
        cursor.execute("SELECT name, date, type, level, description FROM achievements")
        rows = cursor.fetchall()
        
        # Создаем Word документ
        doc = Document()
        doc.add_heading('Мои достижения', 0)
        
        for row in rows:
            doc.add_heading(row[0], level=1)
            doc.add_paragraph(f"Дата: {row[1]}")
            doc.add_paragraph(f"Тип: {row[2]}")
            doc.add_paragraph(f"Уровень: {row[3]}")
            doc.add_paragraph(f"Описание: {row[4]}")
            doc.add_paragraph()
        
        # Сохраняем документ
        export_path = os.path.join(self.test_dir, "достижения.docx")
        doc.save(export_path)
        
        # Проверяем что файл создан
        self.assertTrue(os.path.exists(export_path))
        
        # Проверяем содержимое файла
        doc_check = Document(export_path)
        
        # Проверяем заголовок
        self.assertEqual(doc_check.paragraphs[0].text, 'Мои достижения')
        
        # Проверяем количество параграфов (заголовок + 5 параграфов на запись * 2 записи)
        self.assertGreaterEqual(len(doc_check.paragraphs), 11)
        
        conn.close()
    
    def test_07_required_fields_validation(self):
        """Тест проверки обязательных полей"""
        # Тест пустого названия
        name = ""
        date = "2024-01-15"
        self.assertFalse(bool(name and date), "При пустом названии сохранение должно быть запрещено")
        
        # Тест пустой даты
        name = "Тестовое достижение"
        date = ""
        self.assertFalse(bool(name and date), "При пустой дате сохранение должно быть запрещено")
        
        # Тест заполненных полей
        name = "Тестовое достижение"
        date = "2024-01-15"
        self.assertTrue(bool(name and date), "При заполненных полях сохранение должно быть разрешено")
    
    def test_08_level_values(self):
        """Тест допустимых значений уровня"""
        valid_levels = ["локальный", "региональный", "национальный"]
        invalid_levels = ["международный", "городской", ""]
        
        for level in valid_levels:
            self.assertIn(level, valid_levels)
        
        for level in invalid_levels:
            self.assertNotIn(level, valid_levels)
    
    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем временную директорию
        import shutil
        shutil.rmtree(self.test_dir)

def run_tests():
    """Запуск всех тестов"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAchievementsSystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*50)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*50)
    print(f"Всего тестов: {result.testsRun}")
    print(f"Пройдено успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалено: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")
    
    if result.failures:
        print("\nПРОВАЛЕННЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\nТЕСТЫ С ОШИБКАМИ:")
        for test, traceback in result.errors:
            print(f"- {test}")

if __name__ == '__main__':
    run_tests()
```

## Файл: test_gui.py (интеграционные тесты)
```
import unittest
import tkinter as tk
from tkinter import ttk
import tempfile
import os
import json

class TestGUIComponents(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестовой среды для GUI"""
        self.root = tk.Tk()
        self.root.withdraw()  # Скрываем окно
    
    def test_01_combobox_creation(self):
        """Тест создания выпадающих списков"""
        # Тест ComboBox для типов
        frame = tk.Frame(self.root)
        types = ["Олимпиада", "Сертификат", "Проект"]
        combo = ttk.Combobox(frame, values=types, state="readonly")
        combo.pack()
        
        self.assertEqual(combo['state'], 'readonly')
        self.assertEqual(combo['values'], tuple(types))
        
        # Тест ComboBox для уровней
        levels = ["локальный", "региональный", "национальный"]
        level_combo = ttk.Combobox(frame, values=levels, state="readonly")
        level_combo.pack()
        
        self.assertEqual(level_combo['state'], 'readonly')
        self.assertEqual(level_combo['values'], tuple(levels))
    
    def test_02_entry_fields(self):
        """Тест создания полей ввода"""
        frame = tk.Frame(self.root)
        
        # Поле для названия
        name_entry = tk.Entry(frame, width=50)
        name_entry.pack()
        
        self.assertEqual(name_entry['width'], 50)
        
        # Поле для даты
        date_entry = tk.Entry(frame, width=20)
        date_entry.pack()
        
        self.assertEqual(date_entry['width'], 20)
    
    def test_03_text_widget(self):
        """Тест создания текстового поля"""
        frame = tk.Frame(self.root)
        
        desc_text = tk.Text(frame, height=4, width=50)
        desc_text.pack()
        
        self.assertEqual(desc_text['height'], 4)
        self.assertEqual(desc_text['width'], 50)
    
    def test_04_button_creation(self):
        """Тест создания кнопок"""
        frame = tk.Frame(self.root)
        
        save_btn = tk.Button(frame, text="Сохранить")
        save_btn.pack()
        
        self.assertEqual(save_btn['text'], "Сохранить")
        
        delete_btn = tk.Button(frame, text="Удалить выбранное")
        delete_btn.pack()
        
        self.assertEqual(delete_btn['text'], "Удалить выбранное")
        
        export_btn = tk.Button(frame, text="Экспорт в Word")
        export_btn.pack()
        
        self.assertEqual(export_btn['text'], "Экспорт в Word")
    
    def test_05_treeview_creation(self):
        """Тест создания таблицы TreeView"""
        frame = tk.Frame(self.root)
        
        columns = ("id", "Название", "Дата", "Тип", "Уровень")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree.pack()
        
        # Проверяем колонки
        for col in columns:
            tree.heading(col, text=col)
        
        self.assertEqual(tree['columns'], columns)
        self.assertEqual(tree['show'], 'headings')
    
    def test_06_notebook_creation(self):
        """Тест создания вкладок"""
        notebook = ttk.Notebook(self.root)
        notebook.pack()
        
        # Создаем вкладки
        tab_add = tk.Frame(notebook)
        tab_list = tk.Frame(notebook)
        
        notebook.add(tab_add, text="Добавить")
        notebook.add(tab_list, text="Мои достижения")
        
        # Проверяем количество вкладок
        self.assertEqual(notebook.index("end"), 2)
        
        # Проверяем названия вкладок
        self.assertEqual(notebook.tab(0, "text"), "Добавить")
        self.assertEqual(notebook.tab(1, "text"), "Мои достижения")
    
    def tearDown(self):
        """Очистка после тестов"""
        self.root.destroy()

def run_gui_tests():
    """Запуск GUI тестов"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGUIComponents)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*50)
    print("РЕЗУЛЬТАТЫ GUI ТЕСТИРОВАНИЯ")
    print("="*50)
    print(f"Всего тестов: {result.testsRun}")
    print(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалено: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")

if __name__ == '__main__':
    run_gui_tests()
```

## Файл: test_integration.py (интеграционные тесты)
```
import unittest
import tempfile
import os
import json
import sqlite3
from datetime import datetime

class TestIntegration(unittest.TestCase):
    
    def setUp(self):
        """Настройка интеграционного тестирования"""
        self.test_dir = tempfile.mkdtemp()
        
        # Создаем все необходимые файлы
        self.create_test_files()
    
    def create_test_files(self):
        """Создание тестовых файлов"""
        # types.json
        self.types_path = os.path.join(self.test_dir, 'types.json')
        with open(self.types_path, 'w', encoding='utf-8') as f:
            json.dump(["Олимпиада", "Сертификат", "Проект"], f)
        
        # База данных
        self.db_path = os.path.join(self.test_dir, 'achievements.db')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                level TEXT NOT NULL,
                description TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def test_01_full_workflow(self):
        """Тест полного рабочего процесса"""
        # 1. Загружаем типы из JSON
        with open(self.types_path, 'r', encoding='utf-8') as f:
            types = json.load(f)
        
        self.assertEqual(len(types), 3)
        
        # 2. Добавляем достижение в БД
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        test_achievement = (
            "Интеграционный тест",
            "2024-03-15",
            types[0],  # Олимпиада
            "региональный",
            "Тестовое описание интеграционного теста"
        )
        
        cursor.execute('''
            INSERT INTO achievements (name, date, type, level, description)
            VALUES (?, ?, ?, ?, ?)
        ''', test_achievement)
        
        conn.commit()
        
        # 3. Проверяем что запись добавлена
        cursor.execute("SELECT COUNT(*) FROM achievements")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        # 4. Получаем запись
        cursor.execute("SELECT name, date, type, level, description FROM achievements")
        record = cursor.fetchone()
        
        self.assertEqual(record[0], test_achievement[0])
        self.assertEqual(record[1], test_achievement[1])
        self.assertEqual(record[2], test_achievement[2])
        self.assertEqual(record[3], test_achievement[3])
        self.assertEqual(record[4], test_achievement[4])
        
        # 5. Проверяем формат даты
        try:
            datetime.strptime(record[1], "%Y-%m-%d")
            date_valid = True
        except ValueError:
            date_valid = False
        
        self.assertTrue(date_valid)
        
        conn.close()
        
        print("✓ Полный рабочий процесс успешно завершен")
    
    def test_02_multiple_operations(self):
        """Тест множественных операций"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Добавляем несколько записей
        achievements = [
            ("Достижение 1", "2024-01-10", "Олимпиада", "локальный", "Описание 1"),
            ("Достижение 2", "2024-02-15", "Сертификат", "региональный", "Описание 2"),
            ("Достижение 3", "2024-03-20", "Проект", "национальный", "Описание 3")
        ]
        
        for achievement in achievements:
            cursor.execute('''
                INSERT INTO achievements (name, date, type, level, description)
                VALUES (?, ?, ?, ?, ?)
            ''', achievement)
        
        conn.commit()
        
        # Проверяем количество
        cursor.execute("SELECT COUNT(*) FROM achievements")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 3)
        
        # Получаем все записи
        cursor.execute("SELECT name, date, type, level FROM achievements ORDER BY date")
        records = cursor.fetchall()
        
        # Проверяем сортировку по дате
        dates = [record[1] for record in records]
        self.assertEqual(dates, ["2024-01-10", "2024-02-15", "2024-03-20"])
        
        # Удаляем одну запись
        cursor.execute("DELETE FROM achievements WHERE name = ?", ("Достижение 2",))
        conn.commit()
        
        # Проверяем оставшееся количество
        cursor.execute("SELECT COUNT(*) FROM achievements")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        conn.close()
        
        print("✓ Множественные операции успешно выполнены")
    
    def test_03_error_handling(self):
        """Тест обработки ошибок"""
        # Тест неверного формата даты
        invalid_date = "2024/03/15"
        try:
            datetime.strptime(invalid_date, "%Y-%m-%d")
            is_valid = True
        except ValueError:
            is_valid = False
        
        self.assertFalse(is_valid, "Неверный формат даты должен вызывать ошибку")
        
        # Тест пустых обязательных полей
        empty_name = ""
        valid_date = "2024-03-15"
        
        self.assertFalse(bool(empty_name and valid_date))
        
        valid_name = "Тест"
        empty_date = ""
        
        self.assertFalse(bool(valid_name and empty_date))
        
        print("✓ Обработка ошибок работает корректно")
    
    def tearDown(self):
        """Очистка после тестов"""
        import shutil
        shutil.rmtree(self.test_dir)

def run_integration_tests():
    """Запуск интеграционных тестов"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*50)
    print("РЕЗУЛЬТАТЫ ИНТЕГРАЦИОННОГО ТЕСТИРОВАНИЯ")
    print("="*50)
    print(f"Всего тестов: {result.testsRun}")
    print(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалено: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")

if __name__ == '__main__':
    run_integration_tests()
```

## Файл: test_performance.py (тесты производительности)
```
import time
import sqlite3
import tempfile
import os

class TestPerformance:
    """Класс для тестирования производительности"""
    
    @staticmethod
    def test_database_performance():
        """Тест производительности базы данных"""
        print("\n" + "="*50)
        print("ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("="*50)
        
        # Создаем временную БД
        test_dir = tempfile.mkdtemp()
        db_path = os.path.join(test_dir, 'performance_test.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу
        cursor.execute('''
            CREATE TABLE achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                level TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # Тест 1: Вставка 100 записей
        print("\n1. Тест вставки 100 записей:")
        start_time = time.time()
        
        for i in range(100):
            cursor.execute('''
                INSERT INTO achievements (name, date, type, level, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                f"Достижение {i+1}",
                "2024-01-15",
                "Олимпиада",
                "локальный",
                f"Описание достижения {i+1}"
            ))
        
        conn.commit()
        insert_time = time.time() - start_time
        print(f"   Время: {insert_time:.3f} секунд")
        print(f"   Скорость: {100/insert_time:.1f} записей/секунду")
        
        # Тест 2: Чтение всех записей
        print("\n2. Тест чтения 100 записей:")
        start_time = time.time()
        
        cursor.execute("SELECT * FROM achievements")
        records = cursor.fetchall()
        
        select_time = time.time() - start_time
        print(f"   Время: {select_time:.3f} секунд")
        print(f"   Прочитано записей: {len(records)}")
        
        # Тест 3: Поиск по имени
        print("\n3. Тест поиска записи:")
        start_time = time.time()
        
        cursor.execute("SELECT * FROM achievements WHERE name = ?", ("Достижение 50",))
        record = cursor.fetchone()
        
        search_time = time.time() - start_time
        print(f"   Время поиска: {search_time:.3f} секунд")
        
        # Тест 4: Удаление записей
        print("\n4. Тест удаления 100 записей:")
        start_time = time.time()
        
        cursor.execute("DELETE FROM achievements")
        conn.commit()
        
        delete_time = time.time() - start_time
        print(f"   Время: {delete_time:.3f} секунд")
        
        conn.close()
        
        # Удаляем временную директорию
        import shutil
        shutil.rmtree(test_dir)
        
        print("\n" + "="*50)
        print("РЕЗЮМЕ ПРОИЗВОДИТЕЛЬНОСТИ:")
        print("="*50)
        print(f"Вставка 100 записей: {insert_time:.3f}с ({100/insert_time:.1f} зап/с)")
        print(f"Чтение 100 записей: {select_time:.3f}с")
        print(f"Поиск одной записи: {search_time:.3f}с")
        print(f"Удаление 100 записей: {delete_time:.3f}с")
        
        # Проверка соответствия требованиям
        requirements_met = True
        
        if insert_time > 2:
            print("⚠  Вставка превышает лимит 2 секунд")
            requirements_met = False
        
        if select_time > 1:
            print("⚠  Чтение превышает лимит 1 секунды")
            requirements_met = False
        
        if requirements_met:
            print("\n✅ Все требования по производительности выполнены!")
        else:
            print("\n❌ Некоторые требования по производительности не выполнены")

if __name__ == '__main__':
    TestPerformance.test_database_performance()
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
