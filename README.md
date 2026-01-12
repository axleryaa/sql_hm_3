# SQL Homework 3

Приложение для управления станциями и маршрутами метро с использованием PostgreSQL.

## Функциональность

- **CRUD операции со станциями**: добавление, просмотр, редактирование, удаление
- **Управление маршрутами**: создание маршрутов между станциями, просмотр по станции начала
- **Валидация данных**: уникальность названий станций, порядка на линии, маршрутов
- **Обработка ошибок**: понятные сообщения об ошибках базы данных

## Запуск

### Требования

- Python 3.12+
- Docker и Docker Compose
- PostgreSQL (запускается в контейнере)

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd sql-hm-3
```

2. Установите зависимости:
```bash
uv sync
```

3. Запустите базу данных:
```bash
docker-compose up -d
```

4. Запустите приложение:
```bash
uv run python main.py
```

### Инициализация базы данных

В приложении перейдите в меню "3 — инициализация" и выберите:
1. "2 — удалить таблицы" (если таблицы существуют)
2. "1 — создать таблицы"

## Тестирование

### Установка зависимостей для тестирования

```bash
uv sync --group dev
```

### Запуск тестов

```bash
# Запуск всех тестов
python run_tests.py

# Запуск с подробным выводом
python run_tests.py -v

# Запуск конкретного теста
python run_tests.py -k test_add_station_success

# Запуск с покрытием кода
python run_tests.py --cov=main --cov=tables --cov=dbconnection
```

### Структура тестов

Тесты покрывают следующие сценарии:

#### CRUD станции
- ✅ Успешное добавление станции
- ✅ Нарушение уникальности названия станции
- ✅ Нарушение уникальности порядка на линии
- ✅ Нарушение CHECK ограничений (тарифная зона, порядок на линии)
- ✅ Успешное обновление станции
- ✅ Успешное удаление станции

#### Операции с маршрутами
- ✅ Успешное добавление маршрута
- ✅ Нарушение ограничения одинаковых станций начала/конца
- ✅ Нарушение уникальности маршрута
- ✅ Получение маршрутов по станции начала
- ✅ Успешное удаление маршрута

#### Обработка ошибок
- ✅ Нарушение внешнего ключа
- ✅ Нарушение NOT NULL ограничения

#### Подключение к БД
- ✅ Успешное подключение
- ✅ Тестовый метод подключения

## Архитектура

### Основные компоненты

- `main.py` - главный файл приложения с пользовательским интерфейсом
- `dbconnection.py` - управление подключением к PostgreSQL
- `dbtable.py` - базовый класс для работы с таблицами
- `tables/stations_table.py` - класс для работы со станциями
- `tables/routes_table.py` - класс для работы с маршрутами

### Модель данных

#### Станции (public_station)
- `station_id` - BIGINT, PRIMARY KEY, GENERATED ALWAYS AS IDENTITY
- `name` - VARCHAR(200), NOT NULL, UNIQUE
- `tariff_zone` - INTEGER, NOT NULL, CHECK (tariff_zone >= 0)
- `line_order` - INTEGER, NOT NULL, UNIQUE, CHECK (line_order > 0)
- `is_active` - BOOLEAN, NOT NULL, DEFAULT TRUE

#### Маршруты (public_route)
- `route_id` - BIGINT, PRIMARY KEY, GENERATED ALWAYS AS IDENTITY
- `start_station_id` - BIGINT, NOT NULL, FK → public_station.station_id
- `end_station_id` - BIGINT, NOT NULL, FK → public_station.station_id
- `route_name` - VARCHAR(200)
- `is_active` - BOOLEAN, NOT NULL, DEFAULT TRUE

#### Ограничения
- `uq_station_name` - уникальность названий станций
- `uq_station_line_order` - уникальность порядка на линии
- `chk_station_tariff_zone` - тарифная зона >= 0
- `chk_station_line_order` - порядок на линии > 0
- `chk_route_start_end_not_same` - станции начала и конца разные
- `uq_route_start_end` - уникальность маршрута между станциями

## Конфигурация

Настройки подключения к БД в файле `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=qwerty
DB_DB=postgres
DB_TABLE_PREFIX=public_
```

## Разработка

### Структура проекта
```
sql-hm-3/
├── main.py                 # Главное приложение
├── dbconnection.py         # Подключение к БД
├── dbtable.py             # Базовый класс таблицы
├── tables/
│   ├── stations_table.py  # Таблица станций
│   └── routes_table.py    # Таблица маршрутов
├── test_app.py           # Тесты
├── run_tests.py          # Скрипт запуска тестов
├── pyproject.toml        # Конфигурация проекта
├── docker-compose.yaml   # Конфигурация БД
└── .env                  # Переменные окружения
```

### Добавление новых тестов

1. Добавьте новые тестовые методы в `test_app.py`
2. Следуйте паттернам существующих тестов
3. Используйте фикстуры `db_connection` и `app`
4. Запустите тесты: `python run_tests.py -v`
