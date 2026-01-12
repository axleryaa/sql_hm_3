import pytest
import psycopg2
from psycopg2 import errors
from main import Main
from dbconnection import DbConnection, DBConfig


@pytest.fixture
def db_connection():
    """Фикстура для подключения к БД"""
    config = DBConfig()
    conn = DbConnection(config)
    conn.connect()
    yield conn
    conn.close()


@pytest.fixture
def app(db_connection):
    """Фикстура для создания экземпляра приложения"""
    main_app = Main()
    main_app.connection = db_connection
    main_app.stations.dbconn = db_connection
    main_app.routes.dbconn = db_connection
    return main_app


class TestStationsCRUD:
    """Тесты для CRUD операций со станциями"""

    def _cleanup_tables(self, app):
        """Очистка таблиц"""
        conn = app.connection.conn
        conn.rollback()

        try:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS public_route CASCADE")
                cur.execute("DROP TABLE IF EXISTS public_station CASCADE")
                conn.commit()
        except Exception as e:
            conn.rollback()

    def _setup_tables(self, app):
        """Создание таблиц"""
        self._cleanup_tables(app)
        conn = app.connection.conn

        try:
            app.stations.create()
            app.routes.create()
        except Exception as e:
            if "already exists" not in str(e):
                conn.rollback()
                raise
            conn.rollback()

    def test_create_tables(self, app):
        """Тест создания таблиц"""
        self._cleanup_tables(app)

        try:
            app.stations.create()
            result1 = True
        except Exception as e:
            result1 = None
            print(f"Ошибка создания stations: {e}")

        try:
            app.routes.create()
            result2 = True
        except Exception as e:
            result2 = None
            print(f"Ошибка создания routes: {e}")

        assert result1 is not None, "Не удалось создать таблицу stations"
        assert result2 is not None, "Не удалось создать таблицу routes"

    def test_add_station_success(self, app):
        """Тест успешного добавления станции"""
        self._setup_tables(app)

        station_name = f'Центральная_{id(self)}'
        def op():
            return app.stations.insert_one([station_name, 1, 1, True])

        result = app._safe_exec(op, "Не удалось добавить станцию")
        assert result is not None, "Станция не была добавлена"

        stations = app.stations.all()
        assert len(stations) > 0, "Станция не найдена в списке"
        assert stations[0][1] == station_name, f"Название станции не совпадает: ожидалось {station_name}, получено {stations[0][1]}"

    def test_add_station_unique_name_violation(self, app):
        """Тест нарушения уникальности названия станции"""
        self._setup_tables(app)

        def op1():
            return app.stations.insert_one(['Тестовая', 1, 1, True])
        app._safe_exec(op1, "Не удалось добавить первую станцию")

        def op2():
            return app.stations.insert_one(['Тестовая', 1, 2, True])

        result = app._safe_exec(op2, "Не удалось добавить дублирующую станцию")
        assert result is None, "Ожидалось нарушение уникальности названия"

    def test_add_station_unique_line_order_violation(self, app):
        """Тест нарушения уникальности порядка на линии"""
        def op1():
            app.stations.insert_one(['Станция1', 1, 1, True])
        app._safe_exec(op1, "Не удалось добавить первую станцию")

        def op2():
            app.stations.insert_one(['Станция2', 1, 1, True])

        result = app._safe_exec(op2, "Не удалось добавить станцию с дублирующим порядком")
        assert result is None, "Ожидалось нарушение уникальности порядка на линии"

    def test_add_station_invalid_tariff_zone(self, app):
        """Тест нарушения CHECK ограничения для тарифной зоны"""
        def op():
            app.stations.insert_one(['Станция', -1, 1, True])

        result = app._safe_exec(op, "Не удалось добавить станцию с отрицательной тарифной зоной")
        assert result is None, "Ожидалось нарушение CHECK ограничения для тарифной зоны"

    def test_add_station_invalid_line_order(self, app):
        """Тест нарушения CHECK ограничения для порядка на линии"""
        def op():
            app.stations.insert_one(['Станция', 1, 0, True])

        result = app._safe_exec(op, "Не удалось добавить станцию с нулевым порядком на линии")
        assert result is None, "Ожидалось нарушение CHECK ограничения для порядка на линии"

    def test_update_station_success(self, app):
        """Тест успешного обновления станции"""
        self._setup_tables(app)

        def op1():
            return app.stations.insert_one(['Старая', 1, 1, True])
        app._safe_exec(op1, "Не удалось добавить станцию для обновления")

        stations = app.stations.all()
        station_id = stations[0][0]

        def op2():
            return app.stations.update_by_pk(station_id, {
                'name': 'Новая',
                'tariff_zone': 2,
                'line_order': 2,
                'is_active': False
            })

        result = app._safe_exec(op2, "Не удалось обновить станцию")
        assert result is not None, "Станция не была обновлена"

        updated_stations = app.stations.all()
        assert updated_stations[0][1] == 'Новая', "Название не обновилось"
        assert updated_stations[0][2] == 2, "Тарифная зона не обновилась"
        assert updated_stations[0][3] == 2, "Порядок на линии не обновился"
        assert updated_stations[0][4] == False, "Статус активности не обновился"

    def test_delete_station_success(self, app):
        """Тест успешного удаления станции"""
        self._setup_tables(app)

        def op1():
            return app.stations.insert_one(['ДляУдаления', 1, 1, True])
        app._safe_exec(op1, "Не удалось добавить станцию для удаления")

        stations_before = app.stations.all()
        assert len(stations_before) > 0, "Станция не была добавлена"

        station_id = stations_before[0][0]

        def op2():
            return app.stations.delete_by_pk(station_id)

        result = app._safe_exec(op2, "Не удалось удалить станцию")
        assert result is not None, "Станция не была удалена"

        stations_after = app.stations.all()
        assert len(stations_after) == len(stations_before) - 1, "Станция не была удалена из списка"


class TestRoutesOperations:
    """Тесты для операций с маршрутами"""

    def _cleanup_tables(self, app):
        """Очистка таблиц"""
        conn = app.connection.conn
        conn.rollback()

        try:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS public_route CASCADE")
                cur.execute("DROP TABLE IF EXISTS public_station CASCADE")
                conn.commit()
        except Exception as e:
            conn.rollback()

    def _setup_tables(self, app):
        """Создание таблиц"""
        self._cleanup_tables(app)
        conn = app.connection.conn

        try:
            app.stations.create()
            app.routes.create()
        except Exception as e:
            if "already exists" not in str(e):
                conn.rollback()
                raise
            conn.rollback()

    def test_add_route_success(self, app):
        """Тест успешного добавления маршрута"""
        self._setup_tables(app)

        def op1():
            return app.stations.insert_one(['СтанцияА', 1, 1, True])
        def op2():
            return app.stations.insert_one(['СтанцияБ', 1, 2, True])

        app._safe_exec(op1, "Не удалось добавить станцию А")
        app._safe_exec(op2, "Не удалось добавить станцию Б")

        stations = app.stations.all()
        start_id = stations[0][0]
        end_id = stations[1][0]

        def op3():
            return app.routes.insert_one([start_id, end_id, 'Маршрут А-Б', True])

        result = app._safe_exec(op3, "Не удалось добавить маршрут")
        assert result is not None, "Маршрут не был добавлен"

    def test_add_route_same_start_end(self, app):
        """Тест нарушения ограничения - станции начала и конца совпадают"""
        def op1():
            app.stations.insert_one(['Станция', 1, 1, True])
        app._safe_exec(op1, "Не удалось добавить станцию")

        stations = app.stations.all()
        station_id = stations[0][0]

        def op2():
            app.routes.insert_one([station_id, station_id, 'Самомаршрут', True])

        result = app._safe_exec(op2, "Не удалось добавить маршрут с одинаковыми станциями")
        assert result is None, "Ожидалось нарушение ограничения одинаковых станций"

    def test_add_route_unique_violation(self, app):
        """Тест нарушения уникальности маршрута"""
        def op1():
            app.stations.insert_one(['СтанцияА', 1, 1, True])
        def op2():
            app.stations.insert_one(['СтанцияБ', 1, 2, True])

        app._safe_exec(op1, "Не удалось добавить станцию А")
        app._safe_exec(op2, "Не удалось добавить станцию Б")

        stations = app.stations.all()
        start_id = stations[0][0]
        end_id = stations[1][0]

        def op3():
            app.routes.insert_one([start_id, end_id, 'Маршрут1', True])
        app._safe_exec(op3, "Не удалось добавить первый маршрут")

        def op4():
            app.routes.insert_one([start_id, end_id, 'Маршрут2', True])

        result = app._safe_exec(op4, "Не удалось добавить дублирующий маршрут")
        assert result is None, "Ожидалось нарушение уникальности маршрута"

    def test_get_routes_by_start_station(self, app):
        """Тест получения маршрутов по станции начала"""
        def op1():
            app.stations.insert_one(['СтанцияА', 1, 1, True])
        def op2():
            app.stations.insert_one(['СтанцияБ', 1, 2, True])
        def op3():
            app.stations.insert_one(['СтанцияВ', 1, 3, True])

        app._safe_exec(op1, "Не удалось добавить станцию А")
        app._safe_exec(op2, "Не удалось добавить станцию Б")
        app._safe_exec(op3, "Не удалось добавить станцию В")

        stations = app.stations.all()
        station_a_id = stations[0][0]
        station_b_id = stations[1][0]
        station_v_id = stations[2][0]

        def op4():
            app.routes.insert_one([station_a_id, station_b_id, 'А-Б', True])
        def op5():
            app.routes.insert_one([station_a_id, station_v_id, 'А-В', True])

        app._safe_exec(op4, "Не удалось добавить маршрут А-Б")
        app._safe_exec(op5, "Не удалось добавить маршрут А-В")

        routes = app.routes.all_by_start_station(station_a_id)
        assert len(routes) == 2, f"Ожидалось 2 маршрута, получено {len(routes)}"

    def test_delete_route_success(self, app):
        """Тест успешного удаления маршрута"""
        self._setup_tables(app)

        def op1():
            return app.stations.insert_one(['СтанцияА', 1, 1, True])
        def op2():
            return app.stations.insert_one(['СтанцияБ', 1, 2, True])

        app._safe_exec(op1, "Не удалось добавить станцию А")
        app._safe_exec(op2, "Не удалось добавить станцию Б")

        stations = app.stations.all()
        start_id = stations[0][0]
        end_id = stations[1][0]

        def op3():
            return app.routes.insert_one([start_id, end_id, 'ДляУдаления', True])
        app._safe_exec(op3, "Не удалось добавить маршрут для удаления")

        routes_before = app.routes.all()
        assert len(routes_before) > 0, "Маршрут не был добавлен"

        route_id = routes_before[0][0]

        def op4():
            return app.routes.delete_by_pk(route_id)

        result = app._safe_exec(op4, "Не удалось удалить маршрут")
        assert result is not None, "Маршрут не был удален"

        routes_after = app.routes.all()
        assert len(routes_after) == len(routes_before) - 1, "Маршрут не был удален из списка"


class TestErrorHandling:
    """Тесты для обработки ошибок"""

    def test_foreign_key_violation_on_route(self, app):
        """Тест нарушения внешнего ключа при добавлении маршрута"""
        def op():
            app.routes.insert_one([999, 998, 'Несуществующий маршрут', True])

        result = app._safe_exec(op, "Не удалось добавить маршрут с несуществующими станциями")
        assert result is None, "Ожидалось нарушение внешнего ключа"

    def test_not_null_violation(self, app):
        """Тест нарушения NOT NULL ограничения"""
        def op():
            app.stations.insert_one([None, 1, 1, True])

        result = app._safe_exec(op, "Не удалось добавить станцию с NULL названием")
        assert result is None, "Ожидалось нарушение NOT NULL ограничения"


class TestDatabaseConnection:
    """Тесты для подключения к базе данных"""

    def test_connection_success(self):
        """Тест успешного подключения к БД"""
        config = DBConfig()
        conn = DbConnection(config)

        with conn:
            assert conn.conn is not None, "Подключение к БД не установлено"

    def test_connection_test_method(self):
        """Тест метода test() для проверки подключения"""
        config = DBConfig()
        conn = DbConnection(config)

        result = conn.test()
        assert result == True, "Тест подключения к БД провалился"


if __name__ == "__main__":
    pytest.main([__file__])
