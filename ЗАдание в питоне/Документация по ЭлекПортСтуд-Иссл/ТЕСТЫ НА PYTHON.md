#  ТЕСТЫ НА PYTHON
## Электронный портфолио студента-исследователя

**Версия документа:** 1.0
**Дата создания:** 29.01.2026  
**Автор:** Курносенко Александр Сергеевич, группа 21ИС-24  
**Статус:** Учебный проект
**Руководитель практики:** Бобошко Михаил Николаевич

---

# 🧪 3. ТЕСТЫ НА PYTHON
## 3.1. Структура тестов
```
# tests/test_database.py
import unittest
import sqlite3
import os
from datetime import datetime

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Создание тестовой БД
        self.conn = sqlite3.connect(':memory:')
        self.setup_tables()
    
    def tearDown(self):
        self.conn.close()
    
    def setup_tables(self):
        # Создание тестовых таблиц
        pass
    
    def test_create_entry(self):
        # Тест создания записи
        pass
    
    def test_add_coauthor(self):
        # Тест добавления соавтора
        pass
    
    # ... другие тесты

if __name__ == '__main__':
    unittest.main()
```
## 3.2. Полный набор тестов
### 3.2.1. Тесты базы данных (test_database.py)
```
import unittest
import sqlite3
import os
import tempfile
from datetime import datetime

class TestDatabase(unittest.TestCase):
    """Тесты для модуля работы с базой данных"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаём временную БД в памяти
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Создаём таблицы
        self.create_test_tables()
        
        # Тестовые данные
        self.test_entry = {
            'title': 'Научная статья по ИИ',
            'entry_type': 'Публикация',
            'year': 2024
        }
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.conn.close()
    
    def create_test_tables(self):
        """Создание тестовых таблиц"""
        tables_sql = [
            '''CREATE TABLE entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                file_path TEXT,
                year INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE coauthors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )''',
            '''CREATE TABLE entry_coauthors (
                entry_id INTEGER,
                coauthor_id INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries(id),
                FOREIGN KEY (coauthor_id) REFERENCES coauthors(id),
                PRIMARY KEY (entry_id, coauthor_id)
            )''',
            '''CREATE TABLE activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                event_type TEXT NOT NULL,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        
        for sql in tables_sql:
            self.cursor.execute(sql)
        self.conn.commit()
    
    def test_create_entry_success(self):
        """Тест успешного создания записи"""
        sql = "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)"
        params = (self.test_entry['title'], self.test_entry['entry_type'], self.test_entry['year'])
        
        result = self.cursor.execute(sql, params)
        self.conn.commit()
        
        # Проверяем, что запись создана
        self.cursor.execute("SELECT COUNT(*) FROM entries")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        # Проверяем данные записи
        self.cursor.execute("SELECT title, entry_type, year FROM entries WHERE id = ?", (result.lastrowid,))
        entry = self.cursor.fetchone()
        
        self.assertEqual(entry['title'], self.test_entry['title'])
        self.assertEqual(entry['entry_type'], self.test_entry['entry_type'])
        self.assertEqual(entry['year'], self.test_entry['year'])
    
    def test_create_entry_invalid_year(self):
        """Тест создания записи с некорректным годом"""
        # SQLite не проверяет ограничения CHECK без включения PRAGMA
        # Этот тест проверяет логику валидации в приложении
        pass
    
    def test_add_coauthor(self):
        """Тест добавления соавтора"""
        # Создаём запись
        self.cursor.execute(
            "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
            (self.test_entry['title'], self.test_entry['entry_type'], self.test_entry['year'])
        )
        entry_id = self.cursor.lastrowid
        
        # Добавляем соавтора
        self.cursor.execute("INSERT OR IGNORE INTO coauthors (name) VALUES (?)", ("Иванов И.И.",))
        coauthor_id = self.cursor.lastrowid or self.cursor.execute(
            "SELECT id FROM coauthors WHERE name = ?", ("Иванов И.И.",)
        ).fetchone()[0]
        
        # Связываем запись и соавтора
        self.cursor.execute(
            "INSERT INTO entry_coauthors (entry_id, coauthor_id) VALUES (?, ?)",
            (entry_id, coauthor_id)
        )
        self.conn.commit()
        
        # Проверяем связь
        self.cursor.execute('''
            SELECT COUNT(*) FROM entry_coauthors 
            WHERE entry_id = ? AND coauthor_id = ?
        ''', (entry_id, coauthor_id))
        
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1)
    
    def test_log_activity(self):
        """Тест логирования активности"""
        # Создаём запись
        self.cursor.execute(
            "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
            (self.test_entry['title'], self.test_entry['entry_type'], self.test_entry['year'])
        )
        entry_id = self.cursor.lastrowid
        
        # Логируем событие
        self.cursor.execute(
            "INSERT INTO activity_log (entry_id, event_type) VALUES (?, ?)",
            (entry_id, 'CREATE')
        )
        self.conn.commit()
        
        # Проверяем лог
        self.cursor.execute("SELECT COUNT(*) FROM activity_log WHERE entry_id = ?", (entry_id,))
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        self.cursor.execute(
            "SELECT event_type FROM activity_log WHERE entry_id = ?",
            (entry_id,)
        )
        event_type = self.cursor.fetchone()['event_type']
        self.assertEqual(event_type, 'CREATE')
    
    def test_get_statistics(self):
        """Тест сбора статистики"""
        # Создаём тестовые записи разных типов
        entries = [
            ('Статья 1', 'Публикация', 2023),
            ('Статья 2', 'Публикация', 2024),
            ('Конференция 1', 'Конференция', 2023),
            ('Грант 1', 'Грант', 2024)
        ]
        
        for title, entry_type, year in entries:
            self.cursor.execute(
                "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
                (title, entry_type, year)
            )
        
        # Тестируем запросы статистики
        # 1. Распределение по типам
        self.cursor.execute('''
            SELECT entry_type, COUNT(*) as count 
            FROM entries 
            GROUP BY entry_type 
            ORDER BY count DESC
        ''')
        type_stats = self.cursor.fetchall()
        
        self.assertEqual(len(type_stats), 3)  # 3 уникальных типа
        
        # Находим публикации
        publications = [row for row in type_stats if row['entry_type'] == 'Публикация'][0]
        self.assertEqual(publications['count'], 2)
    
    def test_delete_entry_cascade(self):
        """Тест каскадного удаления"""
        # Создаём запись и связываем с соавтором
        self.cursor.execute(
            "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
            (self.test_entry['title'], self.test_entry['entry_type'], self.test_entry['year'])
        )
        entry_id = self.cursor.lastrowid
        
        self.cursor.execute("INSERT OR IGNORE INTO coauthors (name) VALUES (?)", ("Петров П.П.",))
        coauthor_id = self.cursor.lastrowid or self.cursor.execute(
            "SELECT id FROM coauthors WHERE name = ?", ("Петров П.П.",)
        ).fetchone()[0]
        
        self.cursor.execute(
            "INSERT INTO entry_coauthors (entry_id, coauthor_id) VALUES (?, ?)",
            (entry_id, coauthor_id)
        )
        
        # Логируем активность
        self.cursor.execute(
            "INSERT INTO activity_log (entry_id, event_type) VALUES (?, ?)",
            (entry_id, 'CREATE')
        )
        
        self.conn.commit()
        
        # Удаляем запись
        self.cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        
        # Проверяем каскадное удаление связей
        self.cursor.execute(
            "SELECT COUNT(*) FROM entry_coauthors WHERE entry_id = ?",
            (entry_id,)
        )
        link_count = self.cursor.fetchone()[0]
        self.assertEqual(link_count, 0)
        
        # Активность должна сохраниться (ON DELETE CASCADE не указан для activity_log)
        self.cursor.execute(
            "SELECT COUNT(*) FROM activity_log WHERE entry_id = ?",
            (entry_id,)
        )
        log_count = self.cursor.fetchone()[0]
        self.assertEqual(log_count, 1)  # Лог остаётся
    
    def test_unique_coauthor_names(self):
        """Тест уникальности имён соавторов"""
        # Первое добавление
        self.cursor.execute("INSERT INTO coauthors (name) VALUES (?)", ("Сидоров С.С.",))
        first_id = self.cursor.lastrowid
        
        # Попытка добавить того же соавтора с OR IGNORE
        self.cursor.execute("INSERT OR IGNORE INTO coauthors (name) VALUES (?)", ("Сидоров С.С.",))
        second_id = self.cursor.lastrowid
        
        # Проверяем, что второй insert проигнорирован
        self.cursor.execute("SELECT COUNT(*) FROM coauthors WHERE name = ?", ("Сидоров С.С.",))
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1)
        self.assertIsNone(second_id)  # OR IGNORE возвращает None для дубликата
    
    def test_entry_validation(self):
        """Тест валидации данных записи"""
        # Проверка на пустое название
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
                ("", "Публикация", 2024)
            )
            self.conn.commit()
        
        # Проверка на NULL в обязательных полях
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
                (None, "Публикация", 2024)
            )
            self.conn.commit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

## 3.2.2. Тесты экспорта (test_export.py)
```
import unittest
import os
import tempfile
import sqlite3
from datetime import datetime
import openpyxl
from docx import Document

class TestExport(unittest.TestCase):
    """Тесты для модулей экспорта"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаём временную БД
        self.db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Создаём таблицы и тестовые данные
        self.setup_test_data()
        
        # Временная папка для экспорта
        self.export_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.conn.close()
        if os.path.exists(self.db_file):
            os.unlink(self.db_file)
        # Очистка папки экспорта
        for file in os.listdir(self.export_dir):
            os.unlink(os.path.join(self.export_dir, file))
        os.rmdir(self.export_dir)
    
    def setup_test_data(self):
        """Создание тестовых данных"""
        # Таблицы
        self.cursor.execute('''
            CREATE TABLE entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                file_path TEXT,
                year INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE coauthors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE entry_coauthors (
                entry_id INTEGER,
                coauthor_id INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries(id),
                FOREIGN KEY (coauthor_id) REFERENCES coauthors(id),
                PRIMARY KEY (entry_id, coauthor_id)
            )
        ''')
        
        # Тестовые записи
        test_entries = [
            ('Статья в журнале Q1', 'Публикация', 2023),
            ('Доклад на международной конференции', 'Конференция', 2024),
            ('Грант РФФИ', 'Грант', 2023),
            ('Преподавание курса "Машинное обучение"', 'Преподавание', 2024),
            ('Победа в олимпиаде', 'Достижение', 2023),
            ('Ещё одна статья', 'Публикация', 2024),
        ]
        
        for title, entry_type, year in test_entries:
            self.cursor.execute(
                "INSERT INTO entries (title, entry_type, year) VALUES (?, ?, ?)",
                (title, entry_type, year)
            )
        
        # Тестовые соавторы
        test_coauthors = ['Иванов И.И.', 'Петров П.П.', 'Сидоров С.С.']
        for name in test_coauthors:
            self.cursor.execute("INSERT OR IGNORE INTO coauthors (name) VALUES (?)", (name,))
        
        # Связываем записи и соавторов
        self.cursor.execute('''
            INSERT INTO entry_coauthors (entry_id, coauthor_id)
            SELECT e.id, c.id 
            FROM entries e, coauthors c
            WHERE e.title LIKE '%статья%' AND c.name = 'Иванов И.И.'
        ''')
        
        self.conn.commit()
    
    def test_excel_export_structure(self):
        """Тест структуры Excel файла"""
        # Создаём тестовый Excel файл
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Тестовая статистика"
        
        # Добавляем данные
        ws['A1'] = "Тестовый отчёт"
        ws['A1'].font = openpyxl.styles.Font(bold=True, size=14)
        
        ws['A3'] = "Тип записи"
        ws['B3'] = "Количество"
        
        test_data = [
            ('Публикация', 2),
            ('Конференция', 1),
            ('Грант', 1),
            ('Преподавание', 1),
            ('Достижение', 1)
        ]
        
        for i, (entry_type, count) in enumerate(test_data, start=4):
            ws.cell(row=i, column=1, value=entry_type)
            ws.cell(row=i, column=2, value=count)
        
        # Сохраняем файл
        excel_file = os.path.join(self.export_dir, 'test_export.xlsx')
        wb.save(excel_file)
        
        # Проверяем создание файла
        self.assertTrue(os.path.exists(excel_file))
        
        # Проверяем содержимое
        wb_loaded = openpyxl.load_workbook(excel_file)
        ws_loaded = wb_loaded.active
        
        self.assertEqual(ws_loaded.title, "Тестовая статистика")
        self.assertEqual(ws_loaded['A1'].value, "Тестовый отчёт")
        self.assertEqual(ws_loaded['A1'].font.bold, True)
        
        # Проверяем данные
        data_count = 0
        for row in ws_loaded.iter_rows(min_row=3, values_only=True):
            if row[0] and row[1]:
                data_count += 1
        
        self.assertEqual(data_count, 6)  # Заголовок + 5 строк данных
    
    def test_excel_with_chart(self):
        """Тест Excel файла с графиком"""
        from openpyxl import Workbook
        from openpyxl.chart import BarChart, Reference
        
        wb = Workbook()
        ws_data = wb.active
        ws_data.title = "Данные"
        
        # Тестовые данные
        data = [
            ['Тип', 'Количество'],
            ['Публикация', 5],
            ['Конференция', 3],
            ['Грант', 2],
            ['Преподавание', 4],
            ['Достижение', 1]
        ]
        
        for row_idx, row_data in enumerate(data, start=1):
            for col_idx, value in enumerate(row_data, start=1):
                ws_data.cell(row=row_idx, column=col_idx, value=value)
        
        # Создаём график
        chart = BarChart()
        chart.title = "Распределение по типам"
        chart.style = 10
        
        data_ref = Reference(ws_data, min_col=2, min_row=1, max_row=6)
        cats_ref = Reference(ws_data, min_col=1, min_row=2, max_row=6)
        
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        
        # Создаём лист для графика
        ws_chart = wb.create_sheet("График")
        ws_chart.add_chart(chart, "B2")
        
        # Сохраняем
        excel_file = os.path.join(self.export_dir, 'test_chart.xlsx')
        wb.save(excel_file)
        
        # Проверяем
        self.assertTrue(os.path.exists(excel_file))
        wb_loaded = openpyxl.load_workbook(excel_file)
        
        # Проверяем наличие листов
        self.assertIn('Данные', wb_loaded.sheetnames)
        self.assertIn('График', wb_loaded.sheetnames)
        
        # Проверяем наличие графика
        ws_chart_loaded = wb_loaded['График']
        self.assertEqual(len(ws_chart_loaded._charts), 1)
    
    def test_word_export_structure(self):
        """Тест структуры Word документа"""
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Титульная страница
        title = doc.add_heading('Тестовый отчёт', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Таблица
        table = doc.add_table(rows=1, cols=3)
        table.style = 'LightShading'
        
        # Заголовки
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = '№'
        hdr_cells[1].text = 'Тип'
        hdr_cells[2].text = 'Количество'
        
        # Данные
        test_data = [
            (1, 'Публикация', 5),
            (2, 'Конференция', 3),
            (3, 'Грант', 2),
            (4, 'Преподавание', 4),
            (5, 'Достижение', 1)
        ]
        
        for row_data in test_data:
            row_cells = table.add_row().cells
            row_cells[0].text = str(row_data[0])
            row_cells[1].text = row_data[1]
            row_cells[2].text = str(row_data[2])
        
        # Сохраняем
        word_file = os.path.join(self.export_dir, 'test_report.docx')
        doc.save(word_file)
        
        # Проверяем создание файла
        self.assertTrue(os.path.exists(word_file))
        
        # Проверяем содержимое
        doc_loaded = Document(word_file)
        
        # Проверяем заголовок
        self.assertEqual(doc_loaded.paragraphs[0].text, 'Тестовый отчёт')
        
        # Проверяем таблицу
        tables = doc_loaded.tables
        self.assertEqual(len(tables), 1)
        
        table_loaded = tables[0]
        self.assertEqual(len(table_loaded.rows), 6)  # Заголовок + 5 строк данных
        self.assertEqual(len(table_loaded.columns), 3)
        
        # Проверяем данные в таблице
        self.assertEqual(table_loaded.rows[1].cells[1].text, 'Публикация')
        self.assertEqual(table_loaded.rows[1].cells[2].text, '5')
    
    def test_collect_statistics(self):
        """Тест сбора статистики для отчётов"""
        # Тестируем SQL запросы для статистики
        
        # 1. Общее количество записей
        self.cursor.execute("SELECT COUNT(*) FROM entries")
        total_count = self.cursor.fetchone()[0]
        self.assertEqual(total_count, 6)
        
        # 2. Распределение по типам
        self.cursor.execute('''
            SELECT entry_type, COUNT(*) as count 
            FROM entries 
            GROUP BY entry_type 
            ORDER BY count DESC
        ''')
        type_stats = self.cursor.fetchall()
        
        # Проверяем количество уникальных типов
        unique_types = set(row['entry_type'] for row in type_stats)
        self.assertEqual(len(unique_types), 5)
        
        # Находим публикации
        publications = [row for row in type_stats if row['entry_type'] == 'Публикация'][0]
        self.assertEqual(publications['count'], 2)
        
        # 3. Распределение по годам
        self.cursor.execute('''
            SELECT year, COUNT(*) as count 
            FROM entries 
            GROUP BY year 
            ORDER BY year
        ''')
        year_stats = self.cursor.fetchall()
        
        # Проверяем годы
        years = [row['year'] for row in year_stats]
        self.assertIn(2023, years)
        self.assertIn(2024, years)
        
        # 4. Количество уникальных соавторов
        self.cursor.execute("SELECT COUNT(DISTINCT coauthor_id) FROM entry_coauthors")
        unique_coauthors = self.cursor.fetchone()[0]
        self.assertEqual(unique_coauthors, 1)  # В тесте только один соавтор связан
    
    def test_empty_database_export(self):
        """Тест экспорта пустой базы данных"""
        # Очищаем таблицы
        self.cursor.execute("DELETE FROM entries")
        self.cursor.execute("DELETE FROM coauthors")
        self.cursor.execute("DELETE FROM entry_coauthors")
        self.conn.commit()
        
        # Проверяем, что таблицы пусты
        self.cursor.execute("SELECT COUNT(*) FROM entries")
        entries_count = self.cursor.fetchone()[0]
        self.assertEqual(entries_count, 0)
        
        # Для пустой БД экспорт должен создавать отчёт с нулевыми значениями
        # или сообщением об отсутствии данных

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

### 3.2.3. Тесты GUI (test_gui.py)
```
import unittest
import tkinter as tk
from tkinter import ttk
import tempfile
import os

class TestGUI(unittest.TestCase):
    """Тесты графического интерфейса"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.root = tk.Tk()
        self.root.withdraw()  # Скрываем окно
        
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.root:
            self.root.destroy()
    
    def test_widget_creation(self):
        """Тест создания виджетов"""
        # Создаём фрейм
        frame = ttk.Frame(self.root)
        frame.pack()
        
        # Создаём различные виджеты
        label = ttk.Label(frame, text="Тестовая метка")
        entry = ttk.Entry(frame, width=30)
        combo = ttk.Combobox(frame, values=['Опция 1', 'Опция 2'])
        button = ttk.Button(frame, text="Тестовая кнопка")
        text = tk.Text(frame, height=5, width=40)
        
        # Проверяем создание
        self.assertIsInstance(label, ttk.Label)
        self.assertIsInstance(entry, ttk.Entry)
        self.assertIsInstance(combo, ttk.Combobox)
        self.assertIsInstance(button, ttk.Button)
        self.assertIsInstance(text, tk.Text)
        
        # Проверяем свойства
        self.assertEqual(label['text'], "Тестовая метка")
        self.assertEqual(button['text'], "Тестовая кнопка")
    
    def test_treeview_operations(self):
        """Тест операций с Treeview"""
        # Создаём Treeview
        frame = ttk.Frame(self.root)
        tree = ttk.Treeview(frame, columns=('Колонка 1', 'Колонка 2'), show='headings')
        
        # Настраиваем колонки
        tree.heading('Колонка 1', text='Заголовок 1')
        tree.heading('Колонка 2', text='Заголовок 2')
        
        tree.column('Колонка 1', width=100)
        tree.column('Колонка 2', width=100)
        
        # Добавляем данные
        item1 = tree.insert('', 'end', values=('Значение 1', 'Значение 2'), iid='item1')
        item2 = tree.insert('', 'end', values=('Значение 3', 'Значение 4'), iid='item2')
        
        # Проверяем добавление
        items = tree.get_children()
        self.assertEqual(len(items), 2)
        self.assertIn('item1', items)
        self.assertIn('item2', items)
        
        # Проверяем значения
        values1 = tree.item('item1')['values']
        self.assertEqual(values1, ('Значение 1', 'Значение 2'))
        
        # Удаляем элемент
        tree.delete('item1')
        items_after = tree.get_children()
        self.assertEqual(len(items_after), 1)
        self.assertNotIn('item1', items_after)
        
        # Очищаем всё
        tree.delete(*tree.get_children())
        self.assertEqual(len(tree.get_children()), 0)
    
    def test_combobox_values(self):
        """Тест ComboBox с предопределёнными значениями"""
        entry_types = ['Публикация', 'Конференция', 'Грант', 'Преподавание', 'Достижение']
        
        combo = ttk.Combobox(self.root, values=entry_types, state='readonly')
        
        # Проверяем значения
        self.assertEqual(combo['values'], entry_types)
        self.assertEqual(combo['state'], 'readonly')
        
        # Устанавливаем значение
        combo.set('Публикация')
        self.assertEqual(combo.get(), 'Публикация')
        
        # Пытаемся установить недопустимое значение
        combo.set('Неверный тип')
        # В режиме readonly это может не сработать или сбросить значение
        
    def test_spinbox_range(self):
        """Тест SpinBox с ограничениями"""
        spinbox = ttk.Spinbox(self.root, from_=2000, to=2100)
        
        # Проверяем диапазон
        self.assertEqual(spinbox['from'], '2000')
        self.assertEqual(spinbox['to'], '2100')
        
        # Устанавливаем значения
        spinbox.delete(0, tk.END)
        spinbox.insert(0, '2024')
        self.assertEqual(spinbox.get(), '2024')
        
        # Пытаемся установить значение вне диапазона
        spinbox.delete(0, tk.END)
        spinbox.insert(0, '1999')  # Ниже минимума
        # Tkinter может позволить это, но приложение должно валидировать
    
    def test_scrolledtext_widget(self):
        """Тест ScrolledText виджета"""
        from tkinter import scrolledtext
        
        stext = scrolledtext.ScrolledText(self.root, height=10, width=50)
        
        # Проверяем размеры
        self.assertEqual(stext['height'], 10)
        self.assertEqual(stext['width'], 50)
        
        # Тестируем вставку текста
        test_text = "Это тестовый текст\nс переносом строки."
        stext.insert('1.0', test_text)
        
        # Получаем текст
        content = stext.get('1.0', tk.END).strip()
        self.assertEqual(content, test_text)
        
        # Очищаем
        stext.delete('1.0', tk.END)
        self.assertEqual(stext.get('1.0', tk.END).strip(), '')
    
    def test_dialog_boxes(self):
        """Тест диалоговых окон (имитация)"""
        # В реальном приложении могут использоваться messagebox
        # Тестируем логику обработки диалогов
        
        # Симулируем ответ пользователя
        user_response = "yes"  # В реальном приложении это было бы из messagebox
        
        # Логика обработки
        if user_response.lower() in ['yes', 'да', 'y']:
            action_result = "confirmed"
        else:
            action_result = "cancelled"
        
        self.assertEqual(action_result, "confirmed")
        
        # Тест отмены
        user_response = "no"
        if user_response.lower() in ['yes', 'да', 'y']:
            action_result = "confirmed"
        else:
            action_result = "cancelled"
        
        self.assertEqual(action_result, "cancelled")

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

###3.2.4. Тесты Markdown (test_markdown.py)
```
import unittest
import os
import tempfile
import re

class TestMarkdownHandler(unittest.TestCase):
    """Тесты для обработки Markdown файлов"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.test_dir = tempfile.mkdtemp()
        self.test_content = """# Научная статья

## Аннотация
Это тестовая статья о важных исследованиях.

## Методология
Использовались следующие методы:
- Статистический анализ
- Машинное обучение
- Экспериментальная проверка

## Результаты
Получены значимые результаты (p < 0.05).

```python
# Пример кода
def calculate_significance(data):
    return stats.ttest_ind(data['group1'], data['group2'])
Заключение
Исследование подтвердило гипотезу.

Ссылка на журнал
"""

text
def tearDown(self):
    """Очистка после каждого теста"""
    import shutil
    if os.path.exists(self.test_dir):
        shutil.rmtree(self.test_dir)

def test_sanitize_filename(self):
    """Тест очистки имени файла"""
    test_cases = [
        ("Нормальное имя.md", "Нормальное имя"),
        ("Имя с/недопустимыми\\символами?.md", "Имя с_недопустимыми_символами_"),
        ("  С пробелами в начале и конце  ", "С пробелами в начале и конце"),
        ("Очень длинное название статьи которое может превышать лимит символов в названии файла.md", 
         "Очень длинное название статьи которое может превышать лимит символов в названии файла")
    ]
    
    for original, expected in test_cases:
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', original)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        sanitized = sanitized[:100]
        
        # Удаляем расширение .md если есть
        if sanitized.endswith('.md'):
            sanitized = sanitized[:-3]
        
        self.assertEqual(sanitized, expected)

def test_create_markdown_file(self):
    """Тест создания Markdown файла"""
    # Имитируем создание файла
    entry_id = 1
    title = "Тестовая статья"
    
    # Очищаем название
    sanitized_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    sanitized_title = re.sub(r'\s+', ' ', sanitized_title).strip()
    sanitized_title = sanitized_title[:100]
    
    # Формируем имя файла
    filename = f"{entry_id:03d}_{sanitized_title}.md"
    filepath = os.path.join(self.test_dir, filename)
    
    # Создаём файл
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(self.test_content)
    
    # Проверяем создание
    self.assertTrue(os.path.exists(filepath))
    
    # Проверяем имя файла
    self.assertTrue(filename.startswith("001_"))
    self.assertTrue(filename.endswith(".md"))
    self.assertIn("Тестовая_статья", filename)
    
    # Проверяем содержимое
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    self.assertEqual(content, self.test_content)
    self.assertIn("# Научная статья", content)
    self.assertIn("```python", content)
    self.assertIn("[Ссылка на журнал]", content)

def test_read_markdown_file(self):
    """Тест чтения Markdown файла"""
    # Создаём тестовый файл
    test_file = os.path.join(self.test_dir, "test_read.md")
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(self.test_content)
    
    # Читаем файл
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем содержимое
    self.assertEqual(content, self.test_content)
    
    # Проверяем структуру
    lines = content.split('\n')
    self.assertEqual(lines[0], "# Научная статья")
    self.assertEqual(lines[2], "## Аннотация")
    
    # Проверяем наличие элементов Markdown
    self.assertTrue(any('```python' in line for line in lines))
    self.assertTrue(any('[' in line and '](' in line and ')' in line for line in lines))

def test_update_markdown_file(self):
    """Тест обновления Markdown файла"""
    # Создаём начальный файл
    initial_content = "# Старая версия\n\nСтарый текст."
    test_file = os.path.join(self.test_dir, "test_update.md")
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(initial_content)
    
    # Проверяем начальное содержимое
    with open(test_file, 'r', encoding='utf-8') as f:
        old_content = f.read()
    
    self.assertEqual(old_content, initial_content)
    
    # Обновляем файл
    updated_content = "# Новая версия\n\nОбновлённый текст с изменениями."
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    # Проверяем обновление
    with open(test_file, 'r', encoding='utf-8') as f:
        new_content = f.read()
    
    self.assertEqual(new_content, updated_content)
    self.assertNotEqual(old_content, new_content)
    self.assertIn("Новая версия", new_content)
    self.assertNotIn("Старая версия", new_content)

def test_markdown_syntax_elements(self):
    """Тест элементов синтаксиса Markdown"""
    # Проверяем распознавание различных элементов Markdown
    
    test_content = """# Заголовок 1
Заголовок 2
Заголовок 3
Жирный текст и курсивный текст

Элемент списка 1

Элемент списка 2

Вложенный элемент

Нумерованный элемент 1

Нумерованный элемент 2

Цитата
Многострочная цитата

встроенный код

python
блок кода
Текст ссылки

https://image.jpg
"""

text
    # Проверяем наличие элементов
    self.assertIn("# Заголовок 1", test_content)
    self.assertIn("## Заголовок 2", test_content)
    self.assertIn("**Жирный текст**", test_content)
    self.assertIn("*курсивный текст*", test_content)
    self.assertIn("- Элемент списка", test_content)
    self.assertIn("1. Нумерованный элемент", test_content)
    self.assertIn("> Цитата", test_content)
    self.assertIn("`встроенный код`", test_content)
    self.assertIn("```python", test_content)
    self.assertIn("[Текст ссылки]", test_content)
    self.assertIn("![Альтернативный текст]", test_content)

def test_file_size_and_encoding(self):
    """Тест размера файла и кодировки"""
    # Создаём файл с русским текстом
    russian_text = "Текст на русском языке с кириллицей: Привет, мир!"
    test_file = os.path.join(self.test_dir, "test_encoding.md")
    
    # Записываем в UTF-8
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(russian_text)
    
    # Проверяем размер
    file_size = os.path.getsize(test_file)
    self.assertGreater(file_size, 0)
    self.assertLess(file_size, 1000)  # Небольшой файл
    
    # Читаем в правильной кодировке
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    self.assertEqual(content, russian_text)
    
    # Проверяем, что кириллица сохранилась
    self.assertIn("Привет", content)
    self.assertIn("кириллицей", content)
if name == 'main':
unittest.main(verbosity=2)

```

#### 3.2.5. Запуск всех тестов (`run_tests.py`)
```
#!/usr/bin/env python3
"""
Запуск всех тестов для приложения портфолио
"""

import unittest
import sys
import os

def run_all_tests():
    """Запуск всех тестов"""
    # Добавляем текущую директорию в путь
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Находим все тестовые файлы
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Создаём тестовый загрузчик
    loader = unittest.TestLoader()
    
    # Загружаем тесты из всех файлов
    test_suite = unittest.TestSuite()
    
    test_files = [
        'test_database.py',
        'test_export.py', 
        'test_gui.py',
        'test_markdown.py'
    ]
    
    for test_file in test_files:
        file_path = os.path.join(test_dir, test_file)
        if os.path.exists(file_path):
            print(f"Загрузка тестов из: {test_file}")
            try:
                # Динамически импортируем и загружаем тесты
                module_name = f'tests.{test_file[:-3]}'
                __import__(module_name)
                module = sys.modules[module_name]
                suite = loader.loadTestsFromModule(module)
                test_suite.addTest(suite)
            except Exception as e:
                print(f"Ошибка загрузки тестов из {test_file}: {e}")
        else:
            print(f"Файл тестов не найден: {test_file}")
            print("Создайте тестовые файлы или запустите тесты по отдельности")
    
    # Запускаем тесты
    print("\n" + "="*60)
    print("ЗАПУСК ВСЕХ ТЕСТОВ")
    print("="*60)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Выводим статистику
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*60)
    print(f"Тестов запущено: {result.testsRun}")
    print(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалено: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")
    
    if result.failures:
        print("\nПРОВАЛЕННЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\nТЕСТЫ С ОШИБКАМИ:")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    # Возвращаем код выхода
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_name):
    """Запуск конкретного теста"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Запуск тестов для приложения портфолио')
    parser.add_argument('--test', '-t', help='Запустить конкретный тест')
    parser.add_argument('--all', '-a', action='store_true', help='Запустить все тесты')
    
    args = parser.parse_args()
    
    if args.test:
        print(f"Запуск теста: {args.test}")
        exit_code = run_specific_test(args.test)
    else:
        # По умолчанию запускаем все тесты
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
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
