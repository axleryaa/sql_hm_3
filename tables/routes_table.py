# tables/routes_table.py
from dbtable import *

class RoutesTable(DbTable):
    def table_name(self):
        return self.dbconn.prefix + "route"

    def columns(self):
        return {
            "route_id": ["BIGINT", "GENERATED ALWAYS AS IDENTITY", "PRIMARY KEY"],
            "start_station_id": ["BIGINT", "NOT NULL"],
            "end_station_id": ["BIGINT", "NOT NULL"],
            "route_name": ["VARCHAR(200)"],
            "is_active": ["BOOLEAN", "NOT NULL", "DEFAULT TRUE"],
        }

    def primary_key(self):
        return ["route_id"]

    def table_constraints(self):
        return [
            "CONSTRAINT chk_route_start_end_not_same CHECK (start_station_id <> end_station_id)",
            "CONSTRAINT uq_route_start_end UNIQUE (start_station_id, end_station_id)",
        ]

    def all_by_start_station(self, start_station_id: int):
        sql = "SELECT * FROM " + self.table_name() + " WHERE start_station_id = %(sid)s ORDER BY route_id"
        cur = self.dbconn.conn.cursor()
        cur.execute(sql, {"sid": start_station_id})
        return cur.fetchall()