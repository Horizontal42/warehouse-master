[English](ARCHITECTURE.md)

# Архитектура

## Обзор

Warehouse Master — десктопное приложение для печати нумерованных этикеток в PDF и синхронизации пересборки ноутбуков через Google Sheets. Два независимых таба: Labels (генерация PDF) и Reassembly (синхронизация с таблицей).

## Структура файлов

| Файл | Назначение |
|------|-----------|
| **main.py** | Entry point, главное окно `LabelApp`, жизненный цикл табов, dispatch i18n |
| **printing.py** | Утилиты: файловый ввод-вывод, пути к ресурсам, обнаружение принтеров, папка конфига |
| **styles.py** | Генератор стилей: `build_stylesheet(dark: bool)` → возвращает CSS для обеих тем |
| **workers.py** | Фоновые потоки: `PDFWorker` (reportlab), `ReassemblyWorker` (синхронизация gspread) |
| **widgets.py** | Переиспользуемые UI компоненты: `NoScrollComboBox`, `RangeRowWidget`, `PreferencesDialog` |
| **strings.py** | i18n: словарь `STRINGS` `{"en": {...}, "ru": {...}}` со всеми строками UI |
| **sheet_manager.py** | Обёртка Google Sheets API: конфиг-управляемые индексы колонок, вычисление категории, батч-обновления |
| **sheet_config.example.json** | Шаблон конфига: листы, маппинги колонок, переводчики типов, статусы |
| **WarehouseMaster.spec** | Спек PyInstaller: бандлит Inter.ttf, собирает single-file exe |
| **requirements.txt** | Зависимости: PyQt5, reportlab, gspread, google-auth |

## Ответственность модулей

### main.py
- Загружает/сохраняет QSettings (тема, язык, состояние окна)
- Рендерит два таба: labels и reassembly
- Подключает обработчики событий
- Вызывает `_retranslate()` при смене языка
- Очистка временных файлов при закрытии

### printing.py
- `resource_path()` — ищет бандлированные файлы (Inter.ttf, icon.ico)
- `app_data_dir()` — `%APPDATA%/WarehouseMaster/` для token.json, локальных конфигов
- `config_path()` — возвращает sheet_config.json (локальный или из appdata)
- `register_fonts()` — загружает Inter.ttf в reportlab
- `get_installed_printers()` — перечисляет принтеры Windows (win32api)
- `open_file()` — кросс-платформенный открыватель файлов (Windows/macOS/Linux)
- `print_file()` — печать на конкретный принтер или системный по умолчанию

### styles.py
- `build_stylesheet(dark: bool)` — одна функция, возвращает полный CSS палитры
- Цвета захардкожены (dark: #212529 фон, #f8f9fa текст; light: инверсия)
- Вызывается при переключении темы → `setStyleSheet()`

### workers.py
- `PDFWorker(QThread)` — генерирует PDF в фоне, эмитит `finished(filepath)` или `error_occurred(str)`
- `ReassemblyWorker(QThread)` — вызывает `SheetManager.process_reassembly()`, эмитит `finished_signal(comment, tech_op)` или `error_signal(str)`
- Оба предотвращают блокировку UI

### widgets.py
- `NoScrollComboBox` — подавляет скроллинг на колесике мыши
- `RangeRowWidget` — поля start/end + кнопки +/-; управляется callback-ами
- `PreferencesDialog` — язык + тема + URL таблицы + папка сохранения, сохраняет в QSettings

### strings.py
- Два словаря: `STRINGS["en"]`, `STRINGS["ru"]`
- Ключи: `"window_title"`, `"tab_labels"`, шаблоны сообщений с `{n}` плейсхолдерами
- Никакой логики переключения локали — main.py читает `settings.value("locale")` и индексирует

### sheet_manager.py
- `SheetManager(sheet_url, config_path)` — загружает config.json, авторизует gspread
- `process_reassembly(laptop_id, parts_str, ssd_id, akb_id)` — атомарно обновляет: отмечает запчасти отгруженными, пишет грейды в строку ноутбука, пересчитывает категорию (D/C/B/A/NEW)
- `_calculate_category(laptop_data)` — правило-based скоринг (D если любая деталь ≤rank 1, NEW если все ≥A и cycles < 150 и т.д.)
- Управляется конфигом: все индексы колонок, range clears, значения статусов из sheet_config.json

## Горячие пути

### Генерация PDF
1. Пользователь нажимает «Generate PDF»
2. `_start_generation()` валидирует диапазоны (start ≤ end), спавнит `PDFWorker`
3. `PDFWorker.run()` → `reportlab.canvas` рисует этикетки в сеточном макете
4. При успехе: `_on_pdf_done()` → открыть файл или печать
5. UI разблокирован (рабочий поток)

### Синхронизация пересборки
1. Пользователь заполняет заказ/запчасти, нажимает «Apply changes»
2. `_run_reassembly()` спавнит `ReassemblyWorker`
3. `ReassemblyWorker.run()` → `SheetManager.process_reassembly()`
4. Manager: фетчит ID из всех листов, обрабатывает каждую запчасть (SSD/АКБ/запчасть), вычисляет новую категорию
5. Батч-обновляет все листы, возвращает comment + tech строки
6. `_on_reassembly_done()` отображает результаты
7. UI разблокирован

## Добавление функциональности

### Новый формат этикетки (например 6×6 сетка)
1. Добавить в `PAGE_SIZES` и `DEFAULT_FONT_SIZES` в workers.py
2. Добавить radio button в `_init_gen_tab()`
3. Добавить ветку в `PDFWorker.run()` для макета сетки

### Новое поле пересборки
1. Добавить ключ конфига в sheet_config.example.json (например `"warranty_months": 52`)
2. Прочитать в `SheetManager.__init__()` через self.cfg
3. Добавить обработку в `_process_part()` или новый `_process_<thing>()` метод

### Новый язык
1. Добавить `STRINGS["new_lang"]` словарь в strings.py
2. Добавить в языковую комбобокс в PreferencesDialog (widgets.py)
3. Маппировать индекс комбо → код локали (например index 2 → "de")

### Новый лист Google Sheets
1. Добавить в `sheet_config.json` → `worksheets`
2. Добавить маппинги колонок если нужно
3. Добавить fetch/batch в методы `SheetManager`
4. Подключить в `process_reassembly()`

## Подводные камни

- **QSettings кейс:** На Linux имена файлов case-sensitive; использовать lowercase ключи (`"sheet_url"` не `"SheetURL"`)
- **Обновление токена:** Если учетные данные gspread истекают во время сессии, рабочий поток упадёт; пользователь должен перезапустить и переавторизоваться
- **Выравнивание колонок:** В reportlab canvas Y-ось направлена вверх (0 = внизу). Сеточный макет правильно смещает Y через `ph - (row + 1) * cell_h`
- **Конфиг отсутствует:** Если sheet_config.json не найден, SheetManager выбросит на инит; обработать в UI с try-except, показать понятное сообщение
- **Кириллические грейды:** Перед проверкой ранга нормализовать кириллицу А/В/С/Д → латинь A/B/C/D через `str.maketrans()`
- **Принтер не найден:** Если сохранённый принтер удалён, `findText()` вернёт -1; guard перед `setCurrentIndex()`
- **Временные файлы:** Если приложение упадёт, временные PDF не удалятся; рассмотреть OS-уровневую очистку tmp директорий (автоматическая purge)
