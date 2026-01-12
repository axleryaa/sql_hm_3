# tables/stations_table.py
from dbtable import *

class StationsTable(DbTable):
    def table_name(self):
        return self.dbconn.prefix + "station"

    def columns(self):
        return {
            "station_id": ["BIGINT", "GENERATED ALWAYS AS IDENTITY", "PRIMARY KEY"],
            "name": ["VARCHAR(200)", "NOT NULL"],
            "tariff_zone": ["INTEGER", "NOT NULL"],
            "line_order": ["INTEGER", "NOT NULL"],
            "is_active": ["BOOLEAN", "NOT NULL", "DEFAULT TRUE"],
        }

    def primary_key(self):
        return ["station_id"]

    def table_constraints(self):
        return [
            "CONSTRAINT chk_station_tariff_zone CHECK (tariff_zone >= 0)",
            "CONSTRAINT chk_station_line_order CHECK (line_order > 0)",
            "CONSTRAINT uq_station_name UNIQUE (name)",
            "CONSTRAINT uq_station_line_order UNIQUE (line_order)",
        ]
