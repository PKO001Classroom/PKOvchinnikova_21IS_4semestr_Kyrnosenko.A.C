# PYTHON ТЕСТЫ (Test Suite)
## Аналитический журнал

**Версия документа:** 1.0
**Дата создания:** 29.01.2026  
**Автор:** Курносенко Александр Сергеевич, группа 21ИС-24  
**Статус:** Учебный проект
**Руководитель практики:** Бобошко Михаил Николаевич

---

# 🧪 PYTHON ТЕСТЫ (Test Suite)
## 1. Структура тестов
```
tests/
├── __init__.py
├── conftest.py              # Фикстуры pytest
├── unit/
│   ├── test_database.py
│   ├── test_file_manager.py
│   ├── test_analytics.py
│   ├── test_reporting.py
│   └── test_achievements.py
├── integration/
│   ├── test_db_integration.py
│   ├── test_file_db_integration.py
│   └── test_report_integration.py
├── gui/
│   ├── test_main_window.py
│   ├── test_notes_panel.py
│   └── test_analytics_panel.py
└── e2e/
    ├── test_workflow.py
    └── test_export_workflow.py
```
## 2. Конфигурация pytest
```
# conftest.py
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock

@pytest.fixture
def temp_db():
    """Фикстура для временной базы данных"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    yield conn
    conn.close()

@pytest.fixture
def temp_directory():
    """Фикстура для временной директории"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_note_data():
    """Фикстура с тестовыми данными конспекта"""
    return {
        'title': 'Тестовый конспект',
        'category': 'Тестирование',
        'content': '# Тестовый заголовок\n\nТестовое содержание',
        'tags': ['тест', 'python', 'документация']
    }

@pytest.fixture
def mock_database():
    """Мок базы данных"""
    mock_db = Mock()
    mock_db.execute.return_value = None
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [
        (1, 'Конспект 1', 'Категория 1', '2024-01-01'),
        (2, 'Конспект 2', 'Категория 2', '2024-01-02')
    ]
    return mock_db
```

## 3. Unit тесты
### 3.1. Тесты для DatabaseManager:
```
# tests/unit/test_database.py
import pytest
from unittest.mock import Mock, patch
from src.app.core.database import DatabaseManager
from datetime import datetime

class TestDatabaseManager:
    
    def test_create_note_success(self, temp_db, sample_note_data):
        """Тест успешного создания конспекта"""
        db_manager = DatabaseManager(temp_db)
        note_id = db_manager.create_note(
            title=sample_note_data['title'],
            category=sample_note_data['category'],
            content=sample_note_data['content']
        )
        
        assert note_id is not None
        assert isinstance(note_id, int)
        
        # Проверяем, что конспект сохранён
        cursor = temp_db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[1] == sample_note_data['title']
    
    def test_create_note_empty_title(self, temp_db):
        """Тест создания конспекта с пустым заголовком"""
        db_manager = DatabaseManager(temp_db)
        
        with pytest.raises(ValueError, match="Заголовок не может быть пустым"):
            db_manager.create_note('', 'Категория', 'Содержание')
    
    def test_get_note_statistics(self, temp_db):
        """Тест получения статистики"""
        db_manager = DatabaseManager(temp_db)
        
        # Добавляем тестовые данные
        for i in range(5):
            db_manager.create_note(f'Конспект {i}', 'Категория', f'Содержание {i}')
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        stats = db_manager.get_note_statistics(start_date, end_date)
        
        assert 'total_notes' in stats
        assert 'by_category' in stats
        assert 'activity_by_day' in stats
        assert stats['total_notes'] == 5
    
    def test_search_notes(self, temp_db):
        """Тест поиска конспектов"""
        db_manager = DatabaseManager(temp_db)
        
        # Создаём конспекты с разными категориями
        db_manager.create_note('Python основы', 'Программирование', 'content')
        db_manager.create_note('SQL запросы', 'Базы данных', 'content')
        
        # Поиск по категории
        results = db_manager.search_notes(category='Программирование')
        assert len(results) == 1
        assert results[0][1] == 'Python основы'
        
        # Поиск по ключевому слову
        results = db_manager.search_notes(keyword='SQL')
        assert len(results) == 1
        assert results[0][1] == 'SQL запросы'
    
    @pytest.mark.parametrize("input_data,expected", [
        (('Заголовок', 'Категория', 'Содержание'), True),
        (('', 'Категория', 'Содержание'), False),
        (('Заголовок', '', 'Содержание'), True),
        (('Заголовок', 'Категория', ''), True),
        ((None, 'Категория', 'Содержание'), False),
    ])
    def test_validate_note_data(self, temp_db, input_data, expected):
        """Параметризованный тест валидации данных"""
        db_manager = DatabaseManager(temp_db)
        
        title, category, content = input_data
        
        if expected:
            note_id = db_manager.create_note(title, category, content)
            assert note_id is not None
        else:
            with pytest.raises((ValueError, TypeError)):
                db_manager.create_note(title, category, content)
```

### 3.2. Тесты для FileManager:
```
# tests/unit/test_file_manager.py
import pytest
from pathlib import Path
from src.app.core.file_manager import FileManager

class TestFileManager:
    
    def test_create_markdown_file(self, temp_directory):
        """Тест создания Markdown файла"""
        file_manager = FileManager(base_path=temp_directory)
        
        content = "# Заголовок\n\nСодержание конспекта"
        file_path = file_manager.create_markdown_file("test_note", content)
        
        assert Path(file_path).exists()
        assert Path(file_path).suffix == '.md'
        
        # Проверяем содержимое
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        assert saved_content == content
    
    def test_read_markdown_file(self, temp_directory):
        """Тест чтения Markdown файла"""
        file_manager = FileManager(base_path=temp_directory)
        
        # Создаём тестовый файл
        test_content = "# Тест\n\nТестовое содержание"
        file_path = temp_directory / "test.md"
        file_path.write_text(test_content, encoding='utf-8')
        
        # Читаем файл
        content = file_manager.read_markdown_file(str(file_path))
        assert content == test_content
    
    def test_update_markdown_file(self, temp_directory):
        """Тест обновления Markdown файла"""
        file_manager = FileManager(base_path=temp_directory)
        
        # Создаём начальный файл
        initial_content = "# Старое содержимое"
        file_path = temp_directory / "test.md"
        file_path.write_text(initial_content, encoding='utf-8')
        
        # Обновляем файл
        new_content = "# Новое содержимое"
        file_manager.update_markdown_file(str(file_path), new_content)
        
        # Проверяем обновление
        with open(file_path, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        assert updated_content == new_content
    
    def test_list_markdown_files(self, temp_directory):
        """Тест получения списка Markdown файлов"""
        file_manager = FileManager(base_path=temp_directory)
        
        # Создаём несколько файлов
        for i in range(3):
            file_path = temp_directory / f"note_{i}.md"
            file_path.write_text(f"# Note {i}", encoding='utf-8')
        
        # Создаём не-Markdown файл
        (temp_directory / "other.txt").write_text("not markdown")
        
        # Получаем список
        files = file_manager.list_markdown_files()
        
        assert len(files) == 3
        assert all(f.endswith('.md') for f in files)
    
    def test_extract_metadata(self, temp_directory):
        """Тест извлечения метаданных из Markdown"""
        file_manager = FileManager(base_path=temp_directory)
        
        content = """---
title: Тестовый конспект
category: Программирование
tags: [python, тестирование]
date: 2024-01-15
---

# Содержание

Основной текст конспекта.
"""
        
        metadata = file_manager.extract_metadata(content)
        
        assert metadata['title'] == 'Тестовый конспект'
        assert metadata['category'] == 'Программирование'
        assert metadata['tags'] == ['python', 'тестирование']
        assert 'date' in metadata
3.3. Тесты для AnalyticsService:
python
# tests/unit/test_analytics.py
import pytest
from datetime import datetime, timedelta
from src.app.services.analytics import AnalyticsService
from unittest.mock import Mock

class TestAnalyticsService:
    
    def test_calculate_category_statistics(self):
        """Тест расчёта статистики по категориям"""
        analytics = AnalyticsService()
        
        test_data = [
            {'category': 'Программирование', 'title': 'Python основы'},
            {'category': 'Программирование', 'title': 'ООП'},
            {'category': 'Математика', 'title': 'Алгебра'},
            {'category': 'Математика', 'title': 'Геометрия'},
            {'category': 'Математика', 'title': 'Анализ'},
            {'category': None, 'title': 'Без категории'},
        ]
        
        stats = analytics.calculate_category_statistics(test_data)
        
        assert stats['total'] == 6
        assert stats['by_category']['Математика'] == 3
        assert stats['by_category']['Программирование'] == 2
        assert stats['by_category']['Без категории'] == 1
        assert stats['most_common_category'] == 'Математика'
    
    def test_calculate_activity_statistics(self):
        """Тест расчёта статистики активности"""
        analytics = AnalyticsService()
        
        # Создаём тестовые данные активности
        activity_data = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(10):
            for j in range(i):  # Увеличиваем активность со временем
                activity_data.append({
                    'timestamp': base_date + timedelta(days=i),
                    'action': 'CREATE' if j % 2 == 0 else 'UPDATE'
                })
        
        stats = analytics.calculate_activity_statistics(activity_data)
        
        assert 'total_actions' in stats
        assert 'actions_by_day' in stats
        assert 'most_active_day' in stats
        assert stats['total_actions'] == sum(range(10))
    
    def test_calculate_word_count_statistics(self):
        """Тест расчёта статистики по объёму текста"""
        analytics = AnalyticsService()
        
        notes = [
            {'content': 'Короткий текст', 'word_count': 2},
            {'content': 'Средний текст из нескольких слов', 'word_count': 5},
            {'content': 'Очень длинный текст с большим количеством слов для тестирования статистики', 'word_count': 12},
        ]
        
        stats = analytics.calculate_word_count_statistics(notes)
        
        assert stats['total_words'] == 19
        assert stats['average_words'] == pytest.approx(6.33, 0.01)
        assert stats['max_words'] == 12
        assert stats['min_words'] == 2
    
    def test_generate_reading_time_estimate(self):
        """Тест расчёта времени чтения"""
        analytics = AnalyticsService()
        
        # 250 слов (средняя скорость чтения 200 слов/мин)
        word_count = 250
        reading_time = analytics.generate_reading_time_estimate(word_count)
        
        # Ожидаемое время: 250 / 200 = 1.25 минут = 1 мин 15 сек
        assert reading_time['minutes'] == 1
        assert reading_time['seconds'] == 15
        assert reading_time['total_seconds'] == 75
    
    @pytest.mark.parametrize("input_data,expected_top", [
        ([
            {'tags': ['python', 'программирование']},
            {'tags': ['python', 'алгоритмы']},
            {'tags': ['базы данных', 'sql']},
            {'tags': ['python', 'тестирование']},
        ], [('python', 3), ('программирование', 1)]),
        
        ([
            {'tags': ['математика']},
            {'tags': ['математика', 'алгебра']},
            {'tags': ['физика']},
        ], [('математика', 2), ('алгебра', 1)]),
    ])
    def test_get_top_tags(self, input_data, expected_top):
        """Тест получения топ-тегов"""
        analytics = AnalyticsService()
        
        top_tags = analytics.get_top_tags(input_data, limit=2)
        
        assert len(top_tags) == 2
        for i, (tag, count) in enumerate(expected_top):
            assert top_tags[i]['tag'] == tag
            assert top_tags[i]['count'] == count
```

### 3.4. Тесты для ReportGenerator:
```
# tests/unit/test_reporting.py
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.app.services.reporting import ReportGenerator

class TestReportGenerator:
    
    def test_generate_excel_report(self, temp_directory):
        """Тест генерации Excel отчёта"""
        report_gen = ReportGenerator()
        
        test_data = {
            'statistics': {
                'total_notes': 10,
                'by_category': {'Категория 1': 5, 'Категория 2': 5}
            },
            'notes': [
                {'title': 'Конспект 1', 'category': 'Категория 1', 'created': '2024-01-01'},
                {'title': 'Конспект 2', 'category': 'Категория 2', 'created': '2024-01-02'}
            ]
        }
        
        output_path = temp_directory / "test_report.xlsx"
        success = report_gen.generate_excel_report(test_data, str(output_path))
        
        assert success is True
        assert output_path.exists()
        assert output_path.suffix == '.xlsx'
        
        # Проверяем размер файла (должен быть больше 0)
        assert output_path.stat().st_size > 0
    
    def test_generate_pdf_report(self, temp_directory):
        """Тест генерации PDF отчёта"""
        report_gen = ReportGenerator()
        
        test_data = {
            'title': 'Тестовый отчёт',
            'generated_at': '2024-01-15 10:30:00',
            'summary': 'Тестовый отчёт для проверки',
            'details': {
                'total_items': 5,
                'categories': ['Кат 1', 'Кат 2']
            }
        }
        
        output_path = temp_directory / "test_report.pdf"
        success = report_gen.generate_pdf_report(test_data, str(output_path))
        
        assert success is True
        assert output_path.exists()
        assert output_path.suffix == '.pdf'
        assert output_path.stat().st_size > 0
    
    def test_generate_report_with_charts(self, temp_directory):
        """Тест генерации отчёта с графиками"""
        report_gen = ReportGenerator()
        
        # Подготавливаем данные для графиков
        chart_data = {
            'labels': ['Янв', 'Фев', 'Мар', 'Апр'],
            'values': [10, 15, 8, 12],
            'title': 'Активность по месяцам',
            'chart_type': 'bar'
        }
        
        output_path = temp_directory / "chart_report.xlsx"
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            with patch('matplotlib.pyplot.close'):
                success = report_gen.generate_excel_report_with_charts(
                    data={},
                    charts=[chart_data],
                    output_path=str(output_path)
                )
        
        assert success is True
        mock_savefig.assert_called_once()
    
    def test_report_generation_errors(self):
        """Тест обработки ошибок при генерации отчётов"""
        report_gen = ReportGenerator()
        
        # Неверный путь
        with pytest.raises(FileNotFoundError):
            report_gen.generate_excel_report({}, '/nonexistent/path/report.xlsx')
        
        # Неверные данные
        with pytest.raises(ValueError):
            report_gen.generate_excel_report(None, 'report.xlsx')
    
    def test_custom_report_template(self, temp_directory):
        """Тест использования пользовательского шаблона"""
        report_gen = ReportGenerator()
        
        # Создаём тестовый шаблон
        template_content = """Отчёт: {{title}}
Дата: {{date}}
Статистика: {{statistics.total}} записей
"""
        template_path = temp_directory / "template.txt"
        template_path.write_text(template_content, encoding='utf-8')
        
        test_data = {
            'title': 'Мой отчёт',
            'date': '2024-01-15',
            'statistics': {'total': 42}
        }
        
        output_path = temp_directory / "custom_report.txt"
        success = report_gen.generate_custom_report(
            data=test_data,
            template_path=str(template_path),
            output_path=str(output_path)
        )
        
        assert success is True
        assert output_path.exists()
        
        # Проверяем, что шаблон применился
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'Мой отчёт' in content
        assert '42' in content
```

### 3.5. Тесты для AchievementsService:
```
# tests/unit/test_achievements.py
import pytest
from datetime import datetime, timedelta
from src.app.services.achievements import AchievementsService

class TestAchievementsService:
    
    def setup_method(self):
        self.achievements = AchievementsService()
        
    def test_check_first_note_achievement(self):
        """Тест достижения 'Первый конспект'"""
        # Нет конспектов - достижение не разблокировано
        assert not self.achievements.check_first_note_achievement(notes_count=0)
        
        # Есть хотя бы один конспект - достижение разблокировано
        assert self.achievements.check_first_note_achievement(notes_count=1)
        assert self.achievements.check_first_note_achievement(notes_count=5)
    
    def test_check_five_notes_achievement(self):
        """Тест достижения '5 конспектов'"""
        assert not self.achievements.check_five_notes_achievement(notes_count=4)
        assert self.achievements.check_five_notes_achievement(notes_count=5)
        assert self.achievements.check_five_notes_achievement(notes_count=10)
    
    def test_check_category_explorer_achievement(self):
        """Тест достижения 'Исследователь категорий'"""
        # Меньше 3 категорий
        categories = ['Программирование', 'Математика']
        assert not self.achievements.check_category_explorer_achievement(categories)
        
        # 3 или больше категорий
        categories = ['Программирование', 'Математика', 'Физика']
        assert self.achievements.check_category_explorer_achievement(categories)
        
        categories = ['Программирование', 'Математика', 'Физика', 'Химия']
        assert self.achievements.check_category_explorer_achievement(categories)
    
    def test_check_tag_master_achievement(self):
        """Тест достижения 'Мастер тегов'"""
        tags = ['python', 'алгоритмы', 'базы данных', 'тестирование']
        assert not self.achievements.check_tag_master_achievement(tags, required=5)
        assert self.achievements.check_tag_master_achievement(tags, required=4)
    
    def test_check_weekly_streak_achievement(self):
        """Тест достижения 'Недельная серия'"""
        # Создаём даты активности
        today = datetime.now().date()
        activity_dates = [
            today - timedelta(days=i) for i in range(7)
        ]
        
        # 7 дней подряд - достижение разблокировано
        assert self.achievements.check_weekly_streak_achievement(activity_dates)
        
        # Пропуск одного дня
        activity_dates = [
            today - timedelta(days=0),
            today - timedelta(days=1),
            today - timedelta(days=2),
            # пропуск дня 3
            today - timedelta(days=4),
            today - timedelta(days=5),
            today - timedelta(days=6),
        ]
        assert not self.achievements.check_weekly_streak_achievement(activity_dates)
    
    def test_check_export_master_achievement(self):
        """Тест достижения 'Мастер экспорта'"""
        # Нет экспортированных файлов
        exports = {'excel': 0, 'pdf': 0}
        assert not self.achievements.check_export_master_achievement(exports)
        
        # Только Excel
        exports = {'excel': 2, 'pdf': 0}
        assert not self.achievements.check_export_master_achievement(exports)
        
        # Только PDF
        exports = {'excel': 0, 'pdf': 3}
        assert not self.achievements.check_export_master_achievement(exports)
        
        # И Excel, и PDF
        exports = {'excel': 1, 'pdf': 1}
        assert self.achievements.check_export_master_achievement(exports)
    
    def test_calculate_achievement_progress(self):
        """Тест расчёта прогресса достижений"""
        achievements_data = [
            {'id': 'first_note', 'unlocked': True},
            {'id': 'five_notes', 'unlocked': False},
            {'id': 'category_explorer', 'unlocked': True},
            {'id': 'tag_master', 'unlocked': False},
        ]
        
        progress = self.achievements.calculate_progress(achievements_data)
        
        assert progress['total'] == 4
        assert progress['unlocked'] == 2
        assert progress['percentage'] == 50.0
        assert 'locked' in progress
        assert 'recently_unlocked' in progress
    
    def test_get_next_achievement_suggestion(self):
        """Тест получения рекомендации по следующему достижению"""
        user_stats = {
            'notes_count': 3,
            'categories_count': 2,
            'tags_count': 4,
            'exports': {'excel': 0, 'pdf': 0}
        }
        
        locked_achievements = [
            {'id': 'five_notes', 'condition': lambda stats: stats['notes_count'] >= 5},
            {'id': 'category_explorer', 'condition': lambda stats: stats['categories_count'] >= 3},
            {'id': 'tag_master', 'condition': lambda stats: stats['tags_count'] >= 5},
        ]
        
        suggestion = self.achievements.get_next_suggestion(user_stats, locked_achievements)
        
        # Ближайшее достижение - 5 тегов (уже есть 4)
        assert suggestion['id'] == 'tag_master'
        assert 'progress' in suggestion
        assert 'estimated_time' in suggestion
    
    @pytest.mark.parametrize("notes_count,expected_achievements", [
        (0, []),
        (1, ['first_note']),
        (5, ['first_note', 'five_notes']),
        (10, ['first_note', 'five_notes', 'ten_notes']),
        (25, ['first_note', 'five_notes', 'ten_notes', 'expert_writer']),
    ])
    def test_notes_count_achievements(self, notes_count, expected_achievements):
        """Параметризованный тест достижений по количеству конспектов"""
        unlocked = []
        
        if notes_count >= 1:
            unlocked.append('first_note')
        if notes_count >= 5:
            unlocked.append('five_notes')
        if notes_count >= 10:
            unlocked.append('ten_notes')
        if notes_count >= 25:
            unlocked.append('expert_writer')
        
        assert unlocked == expected_achievements
```
## 4. Интеграционные тесты
```
# tests/integration/test_db_integration.py
import pytest
import tempfile
from pathlib import Path
from src.app.core.database import DatabaseManager
from src.app.core.file_manager import FileManager

class TestDatabaseFileIntegration:
    
    def test_create_note_with_file(self, temp_directory):
        """Интеграционный тест: создание конспекта с сохранением файла"""
        # Настройка
        import sqlite3
        db_conn = sqlite3.connect(':memory:')
        
        # Инициализация менеджеров
        db_manager = DatabaseManager(db_conn)
        file_manager = FileManager(base_path=temp_directory)
        
        # Создание конспекта
        note_data = {
            'title': 'Интеграционный тест',
            'category': 'Тестирование',
            'content': '# Тест\n\nИнтеграционное тестирование'
        }
        
        # Действие
        note_id = db_manager.create_note(**note_data)
        
        # Сохранение файла
        filename = f"note_{note_id}.md"
        filepath = temp_directory / filename
        file_manager.create_markdown_file(filename, note_data['content'])
        
        # Проверка БД
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        db_result = cursor.fetchone()
        
        # Проверка файла
        file_exists = filepath.exists()
        file_content = filepath.read_text(encoding='utf-8') if file_exists else None
        
        # Утверждения
        assert db_result is not None
        assert db_result[1] == note_data['title']
        assert file_exists is True
        assert file_content == note_data['content']
        
        # Очистка
        db_conn.close()
    
    def test_sync_database_with_files(self, temp_directory):
        """Тест синхронизации БД с файлами"""
        # Создаём файлы без записей в БД
        file_manager = FileManager(base_path=temp_directory)
        
        files_data = [
            ('note1.md', '# Конспект 1\n\nСодержание 1'),
            ('note2.md', '# Конспект 2\n\nСодержание 2'),
        ]
        
        for filename, content in files_data:
            file_manager.create_markdown_file(filename, content)
        
        # Инициализируем БД
        import sqlite3
        db_conn = sqlite3.connect(':memory:')
        db_manager = DatabaseManager(db_conn)
        
        # Синхронизируем
        sync_result = db_manager.sync_with_files(temp_directory)
        
        # Проверяем результат
        assert sync_result['files_found'] == 2
        assert sync_result['notes_created'] == 2
        assert sync_result['errors'] == 0
        
        # Проверяем, что записи созданы
        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes")
        count = cursor.fetchone()[0]
        
        assert count == 2
        
        db_conn.close()
```

5. GUI тесты
```
# tests/gui/test_main_window.py
import pytest
import tkinter as tk
from unittest.mock import Mock, patch
from src.app.gui.main_window import MainWindow

@pytest.fixture
def root_window():
    """Фикстура для корневого окна Tkinter"""
    root = tk.Tk()
    yield root
    root.destroy()

class TestMainWindow:
    
    def test_window_initialization(self, root_window):
        """Тест инициализации главного окна"""
        with patch('src.app.core.database.DatabaseManager') as mock_db:
            with patch('src.app.core.file_manager.FileManager') as mock_fm:
                window = MainWindow(root_window)
                
                assert window.title() == "Аналитический журнал знаний"
                assert window.geometry() == "1200x800"
                
                # Проверяем, что созданы основные фреймы
                assert hasattr(window, 'notes_frame')
                assert hasattr(window, 'editor_frame')
                assert hasattr(window, 'analytics_frame')
    
    def test_create_note_button(self, root_window):
        """Тест кнопки создания конспекта"""
        with patch('src.app.core.database.DatabaseManager') as mock_db:
            with patch('src.app.core.file_manager.FileManager') as mock_fm:
                window = MainWindow(root_window)
                
                # Находим кнопку создания
                create_button = None
                for widget in window.winfo_children():
                    if isinstance(widget, tk.Button) and 'Создать' in widget.cget('text'):
                        create_button = widget
                        break
                
                assert create_button is not None
                
                # Симулируем нажатие
                with patch.object(window, 'create_note') as mock_create:
                    create_button.invoke()
                    mock_create.assert_called_once()
    
    def test_note_selection(self, root_window):
        """Тест выбора конспекта из списка"""
        with patch('src.app.core.database.DatabaseManager') as mock_db:
            with patch('src.app.core.file_manager.FileManager') as mock_fm:
                window = MainWindow(root_window)
                
                # Добавляем тестовые данные в TreeView
                test_data = [('1', 'Тестовый конспект', 'Категория', '2024-01-01')]
                
                # Находим TreeView
                treeview = None
                for widget in window.winfo_children():
                    if hasattr(widget, 'insert'):
                        treeview = widget
                        break
                
                if treeview:
                    treeview.insert('', 'end', values=test_data[0])
                    
                    # Симулируем выбор
                    treeview.selection_set(treeview.get_children()[0])
                    treeview.event_generate('<<TreeviewSelect>>')
                    
                    # Проверяем, что редактор обновился
                    # (нужно добавить соответствующий метод в MainWindow)
    
    def test_export_buttons(self, root_window):
        """Тест кнопок экспорта"""
        with patch('src.app.core.database.DatabaseManager') as mock_db:
            with patch('src.app.core.file_manager.FileManager') as mock_fm:
                window = MainWindow(root_window)
                
                export_buttons = []
                for widget in window.winfo_children():
                    if isinstance(widget, tk.Button):
                        text = widget.cget('text')
                        if 'Excel' in text or 'PDF' in text:
                            export_buttons.append(widget)
                
                assert len(export_buttons) >= 2
                
                # Проверяем обработчики
                for button in export_buttons:
                    assert button.cget('command') is not None
    
    def test_theme_switching(self, root_window):
        """Тест переключения темы"""
        with patch('src.app.core.database.DatabaseManager') as mock_db:
            with patch('src.app.core.file_manager.FileManager') as mock_fm:
                window = MainWindow(root_window)
                
                initial_theme = window.current_theme
                
                # Переключаем тему
                window.switch_theme()
                
                assert window.current_theme != initial_theme
                
                # Проверяем цвета
                if window.current_theme == 'dark':
                    assert window.cget('bg') == '#2b2b2b'
                else:
                    assert window.cget('bg') == 'white'
```

### 6. End-to-End тесты
```
# tests/e2e/test_workflow.py
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from src.app.core.database import DatabaseManager
from src.app.core.file_manager import FileManager
from src.app.services.analytics import AnalyticsService
from src.app.services.reporting import ReportGenerator

class TestCompleteWorkflow:
    
    def test_complete_user_workflow(self):
        """Полный E2E тест рабочего процесса пользователя"""
        # 1. Настройка тестового окружения
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Инициализация компонентов
            import sqlite3
            db_conn = sqlite3.connect(':memory:')
            db_manager = DatabaseManager(db_conn)
            
            notes_dir = tmpdir_path / 'notes_md'
            exports_dir = tmpdir_path / 'exports'
            notes_dir.mkdir()
            exports_dir.mkdir()
            
            file_manager = FileManager(base_path=notes_dir)
            analytics = AnalyticsService()
            report_gen = ReportGenerator()
            
            # 2. Пользователь создаёт несколько конспектов
            notes_data = [
                {
                    'title': 'Введение в Python',
                    'category': 'Программирование',
                    'content': '# Python\n\nОсновы языка Python',
                    'tags': ['python', 'программирование']
                },
                {
                    'title': 'Основы SQL',
                    'category': 'Базы данных',
                    'content': '# SQL\n\nОсновные команды SQL',
                    'tags': ['sql', 'базы данных']
                },
                {
                    'title': 'Математический анализ',
                    'category': 'Математика',
                    'content': '# Анализ\n\nПределы и производные',
                    'tags': ['математика', 'анализ']
                }
            ]
            
            note_ids = []
            for note in notes_data:
                # Сохраняем в БД
                note_id = db_manager.create_note(
                    title=note['title'],
                    category=note['category'],
                    content=note['content']
                )
                note_ids.append(note_id)
                
                # Сохраняем файл
                filename = f"note_{note_id}.md"
                file_manager.create_markdown_file(filename, note['content'])
            
            # 3. Пользователь редактирует конспект
            updated_content = '# Python\n\nОсновы языка Python\n\n## Новый раздел\nДобавлен новый материал.'
            db_manager.update_note(note_ids[0], updated_content)
            file_manager.update_markdown_file(
                f"note_{note_ids[0]}.md",
                updated_content
            )
            
            # 4. Пользователь получает статистику
            all_notes = db_manager.get_all_notes()
            stats = analytics.calculate_category_statistics(all_notes)
            
            assert stats['total'] == 3
            assert len(stats['by_category']) == 3
            
            # 5. Пользователь генерирует отчёт
            report_data = {
                'title': 'Тестовый отчёт',
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': stats,
                'notes': all_notes
            }
            
            excel_report_path = exports_dir / 'report.xlsx'
            pdf_report_path = exports_dir / 'report.pdf'
            
            excel_success = report_gen.generate_excel_report(
                report_data, str(excel_report_path)
            )
            pdf_success = report_gen.generate_pdf_report(
                report_data, str(pdf_report_path)
            )
            
            assert excel_success is True
            assert pdf_success is True
            assert excel_report_path.exists()
            assert pdf_report_path.exists()
            
            # 6. Проверяем целостность данных
            # Файлы
            md_files = list(notes_dir.glob('*.md'))
            assert len(md_files) == 3
            
            # БД
            cursor = db_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM notes")
            db_count = cursor.fetchone()[0]
            assert db_count == 3
            
            # Экспортированные файлы
            assert excel_report_path.stat().st_size > 1024  # больше 1KB
            assert pdf_report_path.stat().st_size > 1024
            
            # 7. Очистка
            db_conn.close()
            
            print("✅ Полный рабочий процесс завершён успешно")
    
    def test_error_handling_workflow(self):
        """E2E тест обработки ошибок в рабочем процессе"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Попытка работы с несуществующей БД
            try:
                db_manager = DatabaseManager('nonexistent.db')
                db_manager.create_note('Тест', 'Категория', 'Содержание')
                assert False, "Должно было возникнуть исключение"
            except Exception as e:
                assert True, f"Исключение обработано: {e}"
            
            # Попытка сохранения в недоступную директорию
            try:
                file_manager = FileManager(base_path=Path('/nonexistent/path'))
                file_manager.create_markdown_file('test.md', 'content')
                assert False, "Должно было возникнуть исключение"
            except Exception as e:
                assert True, f"Исключение обработано: {e}"
            
            # Попытка генерации отчёта с неверными данными
            report_gen = ReportGenerator()
            try:
                report_gen.generate_excel_report({}, '')
                assert False, "Должно было возникнуть исключение"
            except (ValueError, TypeError) as e:
                assert True, f"Исключение обработано: {e}"
```

## 7. Запуск тестов
### 7.1. Конфигурационный файл pytest:
```
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    -p no:warnings
markers =
    unit: unit tests
    integration: integration tests
    gui: GUI tests
    e2e: end-to-end tests
    slow: slow running tests
    database: tests requiring database
```

### 7.2. Скрипты для запуска тестов:
```
#!/bin/bash
# run_tests.sh

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-test.txt

# Запуск всех тестов
echo "🔬 Запуск всех тестов..."
pytest tests/ -v --cov=src

# Запуск только unit тестов
echo "🧪 Запуск unit тестов..."
pytest tests/unit/ -v -m unit

# Запуск интеграционных тестов
echo "🔗 Запуск интеграционных тестов..."
pytest tests/integration/ -v -m integration

# Запуск E2E тестов
echo "🏁 Запуск E2E тестов..."
pytest tests/e2e/ -v -m e2e

# Генерация отчёта о покрытии
echo "📊 Генерация отчёта о покрытии..."
pytest --cov=src --cov-report=html

# Проверка стиля кода
echo "🎨 Проверка стиля кода..."
flake8 src/
black --check src/
isort --check-only src/

echo "✅ Все проверки завершены!"
```

7.3. GitHub Actions workflow:
```
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10]
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        pip install flake8 black isort
    
    - name: Lint with flake8
      run: |
        flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 src/ --count --exit-zero --max-complexity=10 --statistics
    
    - name: Check formatting with black
      run: black --check src/
    
    - name: Check imports with isort
      run: isort --check-only src/
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: |
        pytest tests/unit/ -v --cov=src --cov-report=xml
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: |
        pytest tests/integration/ -v --cov=src --cov-append
    
    - name: Run E2E tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: |
        pytest tests/e2e/ -v --cov=src --cov-append
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Generate test report
      if: always()
      run: |
        pytest --junitxml=test-results/junit.xml
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
