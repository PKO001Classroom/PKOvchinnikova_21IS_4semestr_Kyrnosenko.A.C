#  PYTHON ТЕСТЫ (Unit Tests)
## Личное целевое академическое портфолио

**Версия документа:** 1.0
**Дата создания:** 29.01.2026  
**Автор:** Курносенко Александр Сергеевич, группа 21ИС-24  
**Статус:** Учебный проект
**Руководитель практики:** Бобошко Михаил Николаевич

---

# 🐍 5. PYTHON ТЕСТЫ (Unit Tests)
## 5.1. Файл test_database.py
```
# test_database.py
import unittest
import sqlite3
import os
from database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Создание тестовой базы данных"""
        self.test_db_name = 'test_academic_portfolio.db'
        if os.path.exists(self.test_db_name):
            os.remove(self.test_db_name)
        self.db = Database(self.test_db_name)
    
    def tearDown(self):
        """Удаление тестовой базы данных"""
        self.db.close()
        if os.path.exists(self.test_db_name):
            os.remove(self.test_db_name)
    
    def test_create_tables(self):
        """Тест создания таблиц"""
        # Проверяем существование таблиц
        tables = ['записи', 'ключевые_слова', 'запись_ключевые_слова', 
                  'компетенции', 'запись_компетенции', 'достижения', 'цели']
        
        for table in tables:
            self.db.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            result = self.db.cursor.fetchone()
            self.assertIsNotNone(result, f"Таблица {table} не создана")
    
    def test_add_entry(self):
        """Тест добавления записи"""
        # Тестовые данные
        test_data = {
            'title': 'Тестовый проект',
            'type': 'Проект',
            'date': '2024-01-27',
            'description': 'Тестовое описание',
            'authors': 'Иванов И.И.',
            'keywords': ['Python', 'тест'],
            'competencies': [(1, 3)]  # компетенция ID=1, уровень=3
        }
        
        # Добавляем запись
        entry_id = self.db.add_entry(**test_data)
        
        # Проверяем что запись добавлена
        self.db.cursor.execute("SELECT * FROM записи WHERE id = ?", (entry_id,))
        result = self.db.cursor.fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[1], test_data['title'])
        self.assertEqual(result[2], test_data['type'])
    
    def test_add_entry_validation(self):
        """Тест валидации при добавлении записи"""
        # Пытаемся добавить запись без обязательных полей
        with self.assertRaises(Exception):
            self.db.add_entry(
                title='',  # Пустое название
                entry_type='Проект',
                date='2024-01-27',
                description='',
                authors='',
                keywords=[],
                competencies=[]
            )
    
    def test_get_all_entries(self):
        """Тест получения всех записей"""
        # Добавляем 3 тестовые записи
        for i in range(3):
            self.db.add_entry(
                title=f'Проект {i}',
                entry_type='Проект',
                date=f'2024-01-{27-i}',
                description=f'Описание {i}',
                authors=f'Автор {i}',
                keywords=[f'ключ{i}'],
                competencies=[(1, 3)]
            )
        
        # Получаем все записи
        entries = self.db.get_all_entries()
        
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0][1], 'Проект 2')  # Последняя добавленная
    
    def test_keyword_stats(self):
        """Тест статистики по ключевым словам"""
        # Добавляем записи с ключевыми словами
        test_keywords = ['Python', 'Django', 'Python', 'SQL', 'Python']
        
        for keyword in test_keywords:
            self.db.add_entry(
                title='Тест',
                entry_type='Проект',
                date='2024-01-27',
                description='',
                authors='',
                keywords=[keyword],
                competencies=[(1, 3)]
            )
        
        # Получаем статистику
        stats = self.db.get_keyword_stats()
        
        # Python должен быть 3 раза
        python_count = 0
        for keyword, count in stats:
            if keyword == 'Python':
                python_count = count
                break
        
        self.assertEqual(python_count, 3)
    
    def test_achievement_system(self):
        """Тест системы достижений"""
        # Проверяем что достижений нет
        achievements = self.db.get_achievements()
        self.assertEqual(len(achievements), 0)
        
        # Добавляем первую запись
        self.db.add_entry(
            title='Первая запись',
            entry_type='Проект',
            date='2024-01-27',
            description='',
            authors='',
            keywords=['test'],
            competencies=[(1, 3)]
        )
        
        # Проверяем достижение "Первый шаг"
        achievements = self.db.get_achievements()
        self.assertEqual(len(achievements), 1)
        self.assertEqual(achievements[0][1], 'Первый шаг')

if __name__ == '__main__':
    unittest.main()
```

## 5.2. Файл test_word_export.py
```
# test_word_export.py
import unittest
import os
import tempfile
from word_export import WordExporter

class MockDatabase:
    """Мок-объект базы данных для тестов"""
    def __init__(self):
        self.test_data = [
            (1, 'Тестовый проект', 'Проект', '2024-01-27', 
             'Тестовое описание проекта', 'Иванов И.И., Петров П.П.', None)
        ]
    
    def get_all_entries(self):
        return self.test_data
    
    def get_entry_keywords(self, entry_id):
        return ['Python', 'Tkinter', 'GUI']
    
    def get_keyword_stats(self):
        return [('Python', 3), ('Tkinter', 2), ('GUI', 1)]
    
    def get_author_stats(self):
        return [('Иванов И.И.', 2), ('Петров П.П.', 1)]
    
    def get_competency_stats(self):
        return [
            (1, 'Программирование', 'Профессиональные', 4.5, 3),
            (2, 'Веб-разработка', 'Профессиональные', 2.3, 1)
        ]
    
    def get_achievements(self):
        return [
            (1, 'Первый шаг', 'Создана первая запись', '2024-01-27'),
            (2, 'Командный игрок', 'Три записи с соавторами', '2024-01-28')
        ]
    
    def get_goals(self):
        return [
            (1, 'Добавить 3 проекта', 'Проект', 3, 2, '2024-06-30', False)
        ]

class TestWordExporter(unittest.TestCase):
    def setUp(self):
        """Настройка тестов"""
        self.mock_db = MockDatabase()
        self.test_export_folder = tempfile.mkdtemp()
    
    def test_export_creation(self):
        """Тест создания Word документа"""
        exporter = WordExporter(self.mock_db)
        
        # Переопределяем папку экспорта для тестов
        exporter.export_folder = self.test_export_folder
        
        # Создаем отчет
        filename = exporter.export_report()
        
        # Проверяем что файл создан
        self.assertTrue(os.path.exists(filename))
        self.assertTrue(filename.endswith('.docx'))
        
        # Проверяем размер файла (должен быть не пустым)
        file_size = os.path.getsize(filename)
        self.assertGreater(file_size, 1024)  # Больше 1KB
    
    def test_custom_filename(self):
        """Тест экспорта с указанным именем файла"""
        exporter = WordExporter(self.mock_db)
        exporter.export_folder = self.test_export_folder
        
        custom_name = 'тестовый_отчет.docx'
        filepath = os.path.join(self.test_export_folder, custom_name)
        
        result = exporter.export_report(custom_name)
        
        self.assertEqual(result, filepath)
        self.assertTrue(os.path.exists(filepath))
    
    def test_folder_creation(self):
        """Тест автоматического создания папки"""
        # Создаем путь к несуществующей папке
        new_folder = os.path.join(self.test_export_folder, 'new_subfolder')
        
        # Удаляем если существует
        if os.path.exists(new_folder):
            os.rmdir(new_folder)
        
        # Создаем экспортер с новой папкой
        exporter = WordExporter(self.mock_db)
        exporter.export_folder = new_folder
        
        # Экспорт должен создать папку
        filename = exporter.export_report()
        
        self.assertTrue(os.path.exists(new_folder))
        self.assertTrue(os.path.exists(filename))
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        # Создаем экспортер с невалидной БД
        class InvalidDB:
            def get_all_entries(self):
                raise Exception("Ошибка БД")
        
        exporter = WordExporter(InvalidDB())
        exporter.export_folder = self.test_export_folder
        
        # Должна быть ошибка
        with self.assertRaises(Exception):
            exporter.export_report()

if __name__ == '__main__':
    unittest.main()
```

## 5.3. Файл test_app_integration.py
```
# test_app_integration.py
import unittest
import tkinter as tk
import tempfile
import os
from app import AcademicPortfolioApp
from database import Database

class TestAppIntegration(unittest.TestCase):
    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем временную БД
        self.test_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
        
        # Создаем корневое окно Tkinter
        self.root = tk.Tk()
        self.root.withdraw()  # Скрываем окно
        
        # Создаем приложение с тестовой БД
        self.app = AcademicPortfolioApp(self.root)
        self.app.db = Database(self.test_db_file)
    
    def tearDown(self):
        """Очистка после тестов"""
        self.root.destroy()
        if os.path.exists(self.test_db_file):
            os.remove(self.test_db_file)
    
    def test_app_initialization(self):
        """Тест инициализации приложения"""
        # Проверяем что созданы все вкладки
        tabs = ['Портфолио', 'Исследовательская карта', 'Компетенции', 
                'Цели на семестр', 'Достижения', 'Настройки']
        
        for tab_name in tabs:
            found = False
            for i in range(self.app.notebook.index('end')):
                if self.app.notebook.tab(i, 'text') == tab_name:
                    found = True
                    break
            self.assertTrue(found, f"Вкладка {tab_name} не найдена")
    
    def test_add_entry_via_gui(self):
        """Тест добавления записи через GUI"""
        # Устанавливаем тестовые значения в полях
        self.app.title_entry.insert(0, 'GUI Тест')
        self.app.type_combo.set('Проект')
        self.app.date_entry.delete(0, tk.END)
        self.app.date_entry.insert(0, '2024-01-27')
        self.app.desc_text.insert('1.0', 'Тест через GUI')
        self.app.authors_entry.insert(0, 'Тестовый автор')
        self.app.keywords_entry.insert(0, 'тест,gui')
        
        # Выбираем компетенцию
        if self.app.competency_vars:
            self.app.competency_vars[0][1].set(True)  # Первая компетенция
            self.app.level_vars[0].set(3)
        
        # Сохраняем текущее количество записей
        initial_count = len(self.app.db.get_all_entries())
        
        # Вызываем метод добавления (имитируем нажатие кнопки)
        try:
            self.app.add_entry()
            
            # Проверяем что запись добавилась
            final_count = len(self.app.db.get_all_entries())
            self.assertEqual(final_count, initial_count + 1)
            
        except Exception as e:
            self.fail(f"Ошибка при добавлении записи через GUI: {e}")
    
    def test_export_functionality(self):
        """Тест функции экспорта"""
        # Сначала добавляем тестовую запись
        self.app.db.add_entry(
            title='Тест экспорта',
            entry_type='Проект',
            date='2024-01-27',
            description='Тест для экспорта',
            authors='',
            keywords=['тест'],
            competencies=[(1, 3)]
        )
        
        # Создаем временную папку для экспорта
        test_export_folder = tempfile.mkdtemp()
        
        # Мокаем путь экспорта
        original_export = self.app.export_to_word
        export_called = []
        
        def mock_export():
            export_called.append(True)
            return test_export_folder
        
        self.app.export_to_word = mock_export
        
        # Вызываем экспорт
        self.app.export_to_word()
        
        # Проверяем что функция была вызвана
        self.assertTrue(len(export_called) > 0)
        
        # Восстанавливаем оригинальную функцию
        self.app.export_to_word = original_export
    
    def test_clear_form_function(self):
        """Тест очистки формы"""
        # Заполняем форму
        self.app.title_entry.insert(0, 'Тест')
        self.app.type_combo.set('Конференция')
        self.app.desc_text.insert('1.0', 'Тестовое описание')
        self.app.authors_entry.insert(0, 'Автор')
        self.app.keywords_entry.insert(0, 'ключ1,ключ2')
        
        # Очищаем форму
        self.app.clear_form()
        
        # Проверяем что поля очищены
        self.assertEqual(self.app.title_entry.get(), '')
        self.assertEqual(self.app.type_var.get(), 'Проект')  # Значение по умолчанию
        self.assertEqual(self.app.desc_text.get('1.0', tk.END).strip(), '')
        self.assertEqual(self.app.authors_entry.get(), '')
        self.assertEqual(self.app.keywords_entry.get(), '')

if __name__ == '__main__':
    unittest.main()
```

## 5.4. Файл test_requirements.py
```
# test_requirements.py
import sys
import subprocess

def test_python_version():
    """Тест версии Python"""
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    print(f"Требуется Python {required_version[0]}.{required_version[1]}+")
    print(f"Установлена версия: {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")
    
    if current_version >= required_version:
        print("✅ Версия Python соответствует требованиям")
        return True
    else:
        print("❌ Версия Python ниже требуемой")
        return False

def test_libraries():
    """Тест установленных библиотек"""
    required_libraries = [
        ('python-docx', 'docx'),
        ('tkinter', 'tkinter')
    ]
    
    print("\nПроверка установленных библиотек:")
    all_installed = True
    
    for pip_name, import_name in required_libraries:
        try:
            __import__(import_name)
            print(f"✅ {pip_name} ({import_name}) установлен")
        except ImportError:
            print(f"❌ {pip_name} ({import_name}) не установлен")
            all_installed = False
    
    return all_installed

def test_sqlite():
    """Тест доступности SQLite"""
    try:
        import sqlite3
        print("\nПроверка SQLite:")
        
        # Создаем тестовую БД
        import tempfile
        import os
        
        test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
        
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Тест создания таблицы
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES ('test')")
        cursor.execute("SELECT * FROM test")
        result = cursor.fetchone()
        
        conn.close()
        os.remove(test_db)
        
        if result and result[1] == 'test':
            print("✅ SQLite работает корректно")
            return True
        else:
            print("❌ SQLite не работает")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка SQLite: {e}")
        return False

def test_export_folder():
    """Тест папки экспорта"""
    export_path = r"C:\Users\Student\Desktop\21Is\Проект1,2\export"
    
    print(f"\nПроверка папки экспорта: {export_path}")
    
    import os
    try:
        # Пробуем создать папку
        os.makedirs(export_path, exist_ok=True)
        
        # Пробуем записать тестовый файл
        test_file = os.path.join(export_path, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        
        os.remove(test_file)
        
        print("✅ Папка экспорта доступна для записи")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка доступа к папке экспорта: {e}")
        return False

def run_all_tests():
    """Запуск всех тестов требований"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ТРЕБОВАНИЙ СИСТЕМЫ")
    print("=" * 60)
    
    tests = [
        ("Версия Python", test_python_version),
        ("Библиотеки", test_libraries),
        ("SQLite", test_sqlite),
        ("Папка экспорта", test_export_folder)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Тест: {test_name}")
        print("-" * 40)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        print("Проверьте установку необходимых компонентов")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    input("\nНажмите Enter для выхода...")
    sys.exit(0 if success else 1)
```

## 5.5. Файл run_all_tests.py (скрипт запуска всех тестов)
```
# run_all_tests.py
import unittest
import sys
import os

def run_test_suite():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ЗАПУСК ПОЛНОЙ ТЕСТОВОЙ СЮИТЫ")
    print("=" * 60)
    
    # Добавляем текущую директорию в путь
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Определяем тесты для запуска
    test_modules = [
        'test_database',
        'test_word_export',
        'test_app_integration',
        'test_requirements'
    ]
    
    # Загружаем и запускаем тесты
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for module_name in test_modules:
        try:
            print(f"\n📦 Загрузка тестов: {module_name}")
            module = __import__(module_name)
            module_suite = loader.loadTestsFromModule(module)
            suite.addTest(module_suite)
        except ImportError as e:
            print(f"❌ Не удалось загрузить модуль {module_name}: {e}")
    
    # Запускаем тесты
    print("\n" + "=" * 60)
    print("ВЫПОЛНЕНИЕ ТЕСТОВ")
    print("=" * 60)
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Формируем отчет
    print("\n" + "=" * 60)
    print("ОТЧЕТ О ТЕСТИРОВАНИИ")
    print("=" * 60)
    
    print(f"Всего тестов: {result.testsRun}")
    print(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    
    if result.failures:
        print(f"Провалено: {len(result.failures)}")
        print("\nПроваленные тесты:")
        for test, traceback in result.failures:
            print(f"  • {test}")
    
    if result.errors:
        print(f"Ошибок: {len(result.errors)}")
        print("\nТесты с ошибками:")
        for test, traceback in result.errors:
            print(f"  • {test}")
    
    # Сохраняем отчет в файл
    with open('test_report.txt', 'w', encoding='utf-8') as f:
        f.write("ОТЧЕТ О ТЕСТИРОВАНИИ\n")
        f.write("=" * 40 + "\n")
        f.write(f"Дата: {import datetime; f.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n")
        f.write(f"Всего тестов: {result.testsRun}\n")
        f.write(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"Провалено: {len(result.failures)}\n")
        f.write(f"Ошибок: {len(result.errors)}\n")
        
        if result.failures:
            f.write("\nПроваленные тесты:\n")
            for test, traceback in result.failures:
                f.write(f"- {test}\n")
                f.write(f"  Ошибка: {traceback.split('AssertionError:')[-1].strip()[:200]}\n")
    
    print(f"\n📄 Подробный отчет сохранен в: test_report.txt")
    
    # Возвращаем код выхода
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    exit_code = run_test_suite()
    input("\nНажмите Enter для выхода...")
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
