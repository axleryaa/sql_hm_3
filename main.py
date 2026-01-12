# main.py
import psycopg2
from psycopg2 import errors

from dbconnection import DbConnection
from dbconnection import DBConfig

from tables.stations_table import StationsTable
from tables.routes_table import RoutesTable


class Main:
    def __init__(self):
        self.connection = DbConnection(DBConfig())

        self.stations = StationsTable()
        self.stations.dbconn = self.connection

        self.routes = RoutesTable()
        self.routes.dbconn = self.connection


    def _input_nonempty(self, prompt: str, max_len: int | None = None) -> str:
        while True:
            s = input(prompt).strip()
            if not s:
                print("Ошибка: значение не должно быть пустым.")
                continue
            if max_len is not None and len(s) > max_len:
                print(f"Ошибка: длина не должна превышать {max_len}.")
                continue
            return s

    def _input_int(self, prompt: str, *, min_value: int | None = None, strict_gt: int | None = None) -> int:
        while True:
            s = input(prompt).strip()
            try:
                v = int(s)
            except ValueError:
                print("Ошибка: нужно целое число.")
                continue
            if min_value is not None and v < min_value:
                print(f"Ошибка: значение должно быть >= {min_value}.")
                continue
            if strict_gt is not None and v <= strict_gt:
                print(f"Ошибка: значение должно быть > {strict_gt}.")
                continue
            return v

    def _input_bool(self, prompt: str, default: bool | None = None) -> bool:
        while True:
            s = input(prompt).strip().lower()
            if not s and default is not None:
                return default
            if s in ("y", "yes", "д", "да", "1", "true", "t"):
                return True
            if s in ("n", "no", "н", "нет", "0", "false", "f"):
                return False
            print("Ошибка: введите y/n (да/нет).")

    def _input_optional_str(self, prompt: str, max_len: int | None = None) -> str | None:
        s = input(prompt).strip()
        if not s:
            return None
        if max_len is not None and len(s) > max_len:
            print(f"Ошибка: длина не должна превышать {max_len}.")
            return self._input_optional_str(prompt, max_len=max_len)
        return s

    def _safe_exec(self, fn, context: str):
        """
        Выполнить БД-операцию, перехватить ошибки, сделать rollback,
        вывести понятное сообщение.
        """
        try:
            return fn()
        except ValueError as e:
            print(f"Ошибка: {e}")
            return None
        except psycopg2.Error as e:
            self.connection.conn.rollback()

            if isinstance(e, errors.UniqueViolation):
                constraint_name = getattr(e.diag, 'constraint_name', None)
                if constraint_name == 'uq_station_name':
                    print(f"Ошибка: станция с таким названием уже существует. {context}")
                elif constraint_name == 'uq_station_line_order':
                    print(f"Ошибка: станция с таким порядком на линии уже существует. {context}")
                elif constraint_name == 'uq_route_start_end':
                    print(f"Ошибка: маршрут между этими станциями уже существует. {context}")
                else:
                    print(f"Ошибка: нарушено уникальное ограничение ({constraint_name}). {context}")
            elif isinstance(e, errors.CheckViolation):
                constraint_name = getattr(e.diag, 'constraint_name', None)
                if constraint_name == 'chk_station_tariff_zone':
                    print(f"Ошибка: тарифная зона должна быть >= 0. {context}")
                elif constraint_name == 'chk_station_line_order':
                    print(f"Ошибка: порядок на линии должен быть > 0. {context}")
                elif constraint_name == 'chk_route_start_end_not_same':
                    print(f"Ошибка: начальная и конечная станции маршрута должны быть разными. {context}")
                else:
                    print(f"Ошибка: нарушено ограничение CHECK ({constraint_name}). {context}")
            elif isinstance(e, errors.ForeignKeyViolation):
                print(f"Ошибка: есть связанные записи (нарушение внешнего ключа). {context}")
            elif isinstance(e, errors.NotNullViolation):
                print(f"Ошибка: обязательное поле не заполнено. {context}")
            else:
                msg = str(e).strip().split("\n")[0]
                print(f"Ошибка БД: {context}")
                print(f"Детали: {msg}")
            return None


    # UI: printing/choosing
    def _print_stations(self, stations: list[tuple]):
        if not stations:
            print("Станций нет.")
            return

        print("\nСтанции:")
        print("№ | Название | Тарифная зона | Порядок на линии | Активна")
        print("--+----------+--------------+------------------+--------")
        for i, row in enumerate(stations, start=1):
            _, name, tz, lo, active = row
            print(f"{i} | {name} | {tz} | {lo} | {'да' if active else 'нет'}")

    def _choose_station_row(self, prompt: str) -> tuple | None:
        stations = self.stations.all()
        self._print_stations(stations)
        if not stations:
            return None

        idx = self._input_int(prompt, min_value=1)
        if idx > len(stations):
            print("Ошибка: такого номера нет.")
            return None
        return stations[idx - 1]

    def _print_routes(self, routes: list[tuple], end_name_resolver):
        if not routes:
            print("Маршрутов для выбранной станции начала нет.")
            return

        print("\nМаршруты (по станции начала):")
        print("№ | Станция конца | Название маршрута | Активен")
        print("--+--------------+-------------------+--------")
        for i, r in enumerate(routes, start=1):
            route_id, start_id, end_id, route_name, active = r
            end_name = end_name_resolver(end_id) or f"(station_id={end_id})"
            rn = route_name if route_name and str(route_name).strip() else "-"
            print(f"{i} | {end_name} | {rn} | {'да' if active else 'нет'}")

    def _station_name_by_id(self, station_id: int) -> str | None:
        cur = self.connection.conn.cursor()
        cur.execute(f"SELECT name FROM {self.stations.table_name()} WHERE station_id=%s", (station_id,))
        row = cur.fetchone()
        return row[0] if row else None


    # Stations: CRUD via DbTable
    def station_add(self):
        name = self._input_nonempty("Название станции: ", max_len=200)
        tariff_zone = self._input_int("Тарифная зона (целое >= 0): ", min_value=0)
        line_order = self._input_int("Порядок на линии (целое > 0): ", strict_gt=0)
        is_active = self._input_bool("Активна? (y/n) [y]: ", default=True)

        def op():
            self.stations.insert_one([name, tariff_zone, line_order, is_active])

        result = self._safe_exec(op, "Не удалось добавить станцию")
        if result is not None:
            print("Станция добавлена.")

    def station_edit(self):
        row = self._choose_station_row("Введите № станции для редактирования: ")
        if not row:
            return

        station_id, old_name, old_tz, old_lo, old_active = row
        print("Новые значения. Enter — оставить прежнее.")

        name = input(f"Название [{old_name}]: ").strip() or old_name

        tz_raw = input(f"Тарифная зона [{old_tz}]: ").strip()
        if tz_raw:
            try:
                tariff_zone = int(tz_raw)
                if tariff_zone < 0:
                    print("Ошибка: тарифная зона должна быть >= 0.")
                    return
            except ValueError:
                print("Ошибка: тарифная зона должна быть целым числом.")
                return
        else:
            tariff_zone = old_tz

        lo_raw = input(f"Порядок на линии [{old_lo}]: ").strip()
        if lo_raw:
            try:
                line_order = int(lo_raw)
                if line_order <= 0:
                    print("Ошибка: порядок на линии должен быть > 0.")
                    return
            except ValueError:
                print("Ошибка: порядок на линии должен быть целым числом.")
                return
        else:
            line_order = old_lo

        active = self._input_bool(
            f"Активна? (y/n) [{'y' if old_active else 'n'}]: ",
            default=old_active,
        )

        def op():
            self.stations.update_by_pk(
                station_id,
                {
                    "name": name,
                    "tariff_zone": tariff_zone,
                    "line_order": line_order,
                    "is_active": active,
                },
            )

        result = self._safe_exec(op, "Не удалось обновить станцию")
        if result is not None:
            print("Станция обновлена.")

    def station_delete(self):
        row = self._choose_station_row("Введите № станции для удаления: ")
        if not row:
            return

        station_id, name, *_ = row
        confirm = self._input_bool(f"Точно удалить станцию «{name}»? (y/n) [n]: ", default=False)
        if not confirm:
            print("Удаление отменено.")
            return

        def op():
            self.stations.delete_by_pk(station_id)

        result = self._safe_exec(op, "Не удалось удалить станцию")
        if result is not None:
            print("Станция удалена.")

    def stations_menu(self):
        while True:
            stations = self.stations.all()
            self._print_stations(stations)

            print("\nСтанции (CRUD):")
            print("1 — добавить")
            print("2 — изменить")
            print("3 — удалить")
            print("0 — назад")
            c = input("> ").strip()

            if c == "1":
                self.station_add()
            elif c == "2":
                self.station_edit()
            elif c == "3":
                self.station_delete()
            elif c == "0":
                return
            else:
                print("Неизвестная команда.")


    # Routes: list/add/delete per start station
    def routes_menu(self):
        start_row = self._choose_station_row("Выберите станцию НАЧАЛА (введите №): ")
        if not start_row:
            return

        start_station_id, start_name, *_ = start_row

        while True:
            print(f"\nСтанция начала: {start_name}")

            # Прикладная выборка: метод в наследнике
            routes = self._safe_exec(
                lambda: self.routes.all_by_start_station(start_station_id),
                "Не удалось получить список маршрутов.",
            )
            if routes is None:
                routes = []

            self._print_routes(routes, self._station_name_by_id)

            print("\nМаршруты:")
            print("1 — добавить маршрут (к этой станции начала)")
            print("2 — удалить маршрут")
            print("0 — назад")
            c = input("> ").strip()

            if c == "1":
                self.route_add(start_station_id)
            elif c == "2":
                self.route_delete(routes)
            elif c == "0":
                return
            else:
                print("Неизвестная команда.")

    def route_add(self, start_station_id: int):
        all_stations = self.stations.all()
        if len(all_stations) < 2:
            print("Нужно минимум 2 станции, чтобы добавить маршрут.")
            return

        self._print_stations(all_stations)
        end_idx = self._input_int("Введите № станции конца: ", min_value=1)
        if end_idx > len(all_stations):
            print("Ошибка: такого номера нет.")
            return

        end_station_id, end_name, *_ = all_stations[end_idx - 1]

        if end_station_id == start_station_id:
            print("Ошибка: станция начала и конца не должны совпадать.")
            return

        route_name = self._input_optional_str("Название маршрута (можно пусто): ", max_len=200)
        is_active = self._input_bool("Активен? (y/n) [y]: ", default=True)

        def op():
            if self._station_name_by_id(start_station_id) is None:
                raise ValueError("Станция начала не найдена.")
            if self._station_name_by_id(end_station_id) is None:
                raise ValueError("Станция конца не найдена.")

            self.routes.insert_one([start_station_id, end_station_id, route_name, is_active])

        result = self._safe_exec(op, "Не удалось добавить маршрут")
        if result is not None:
            print(f"Маршрут добавлен (конец: {end_name}).")

    def route_delete(self, routes: list[tuple]):
        if not routes:
            print("Удалять нечего: список маршрутов пуст.")
            return

        idx = self._input_int("Введите № маршрута для удаления: ", min_value=1)
        if idx > len(routes):
            print("Ошибка: такого номера нет.")
            return

        route_id, _, end_station_id, _, _ = routes[idx - 1]
        end_name = self._station_name_by_id(end_station_id) or "?"

        confirm = self._input_bool(f"Точно удалить маршрут до «{end_name}»? (y/n) [n]: ", default=False)
        if not confirm:
            print("Удаление отменено.")
            return

        def op():
            self.routes.delete_by_pk(route_id)

        result = self._safe_exec(op, "Не удалось удалить маршрут")
        if result is not None:
            print("Маршрут удалён.")


    # Init menu (DDL via DbTable.create/drop)
    def init_menu(self):
        while True:
            print("\nИнициализация:")
            print("1 — создать таблицы (station, route)")
            print("2 — удалить таблицы (station, route)")
            print("0 — назад")
            c = input("> ").strip()

            if c == "1":
                self._safe_exec(lambda: self.stations.create(), "Не удалось создать station.")
                self._safe_exec(lambda: self.routes.create(), "Не удалось создать route.")
                print("Операция создания выполнена.")
            elif c == "2":
                self._safe_exec(lambda: self.routes.drop(), "Не удалось удалить route.")
                self._safe_exec(lambda: self.stations.drop(), "Не удалось удалить station.")
                print("Операция удаления выполнена.")
            elif c == "0":
                return
            else:
                print("Неизвестная команда.")


    # Main loop
    def run(self):
        with self.connection: 
            while True:
                print("\nГлавное меню:")
                print("1 — станции (CRUD)")
                print("2 — маршруты по станции начала (просмотр/добавление/удаление)")
                print("3 — инициализация (создать/удалить таблицы)")
                print("9 — выход")

                c = input("> ").strip()
                if c == "1":
                    self.stations_menu()
                elif c == "2":
                    self.routes_menu()
                elif c == "3":
                    self.init_menu()
                elif c == "9":
                    print("Выход.")
                    return
                else:
                    print("Неизвестная команда.")


if __name__ == "__main__":
    Main().run()
