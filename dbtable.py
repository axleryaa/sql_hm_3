# dbtable.py
from __future__ import annotations

from psycopg2 import sql


class DbTable:
    dbconn = None

    def table_name(self) -> str:
        return self.dbconn.prefix + "table"

    def columns(self) -> dict[str, list[str]]:
        return {"id": ["serial", "PRIMARY KEY"]}

    def primary_key(self) -> list[str]:
        return ["id"]

    def column_names(self) -> list[str]:
        return list(self.columns().keys())

    def column_names_without_pk(self) -> list[str]:
        cols = self.column_names()
        pk = self.primary_key()[0]
        if pk in cols:
            cols.remove(pk)
        return cols

    def table_constraints(self) -> list[str]:
        return []

    # DDL 
    def create(self) -> None:
        parts: list[str] = []
        for k, v in self.columns().items():
            parts.append(f"{k} {' '.join(v)}")
        parts += self.table_constraints()

        q = sql.SQL("CREATE TABLE {} ({});").format(
            sql.Identifier(self.table_name()),
            sql.SQL(", ").join(sql.SQL(p) for p in parts),
        )
        cur = self.dbconn.conn.cursor()
        cur.execute(q)
        self.dbconn.conn.commit()

    def drop(self) -> None:
        q = sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(self.table_name()))
        cur = self.dbconn.conn.cursor()
        cur.execute(q)
        self.dbconn.conn.commit()

    # SELECT 
    def all(self) -> list[tuple]:
        q = sql.SQL("SELECT * FROM {} ORDER BY {}").format(
            sql.Identifier(self.table_name()),
            sql.SQL(", ").join(sql.Identifier(c) for c in self.primary_key()),
        )
        cur = self.dbconn.conn.cursor()
        cur.execute(q)
        return cur.fetchall()

    def find_by_position(self, num: int) -> tuple | None:
        """
        Возвращает 1 запись по порядковому номеру (1..N) в сортировке по PK.
        Удобно для UI без показа surrogate key: пользователь вводит "№", а вы получаете строку.
        """
        if num < 1:
            return None

        q = sql.SQL("SELECT * FROM {} ORDER BY {} LIMIT 1 OFFSET {}").format(
            sql.Identifier(self.table_name()),
            sql.SQL(", ").join(sql.Identifier(c) for c in self.primary_key()),
            sql.Placeholder("offset"),
        )
        cur = self.dbconn.conn.cursor()
        cur.execute(q, {"offset": num - 1})
        return cur.fetchone()

    def count(self) -> int:
        q = sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.table_name()))
        cur = self.dbconn.conn.cursor()
        cur.execute(q)
        return int(cur.fetchone()[0])

    # INSERT 
    def insert_one(self, vals: list | tuple) -> bool:
        cols = self.column_names_without_pk()

        q = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(self.table_name()),
            sql.SQL(", ").join(sql.Identifier(c) for c in cols),
            sql.SQL(", ").join(sql.Placeholder() for _ in cols),
        )
        cur = self.dbconn.conn.cursor()
        cur.execute(q, vals)
        self.dbconn.conn.commit()
        return True

    # UPDATE
    def update_by_pk(self, pk_value, vals_dict: dict) -> bool:
        pk = self.primary_key()[0]

        if pk in vals_dict:
            vals_dict = dict(vals_dict)
            vals_dict.pop(pk)

        if not vals_dict:
            return True

        set_parts = [
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k))
            for k in vals_dict.keys()
        ]

        q = sql.SQL("UPDATE {} SET {} WHERE {} = {}").format(
            sql.Identifier(self.table_name()),
            sql.SQL(", ").join(set_parts),
            sql.Identifier(pk),
            sql.Placeholder("pk"),
        )

        params = dict(vals_dict)
        params["pk"] = pk_value

        cur = self.dbconn.conn.cursor()
        cur.execute(q, params)
        self.dbconn.conn.commit()
        return True

    # DELETE
    def delete_by_pk(self, pk_value) -> bool:
        pk = self.primary_key()[0]
        q = sql.SQL("DELETE FROM {} WHERE {} = {}").format(
            sql.Identifier(self.table_name()),
            sql.Identifier(pk),
            sql.Placeholder(),
        )
        cur = self.dbconn.conn.cursor()
        cur.execute(q, (pk_value,))
        self.dbconn.conn.commit()
        return True


    def column_names_without_id(self) -> list[str]:
        return self.column_names_without_pk()

    def update_by_id(self, row_id, vals_dict: dict) -> None:
        return self.update_by_pk(row_id, vals_dict)

    def delete_by_id(self, row_id) -> None:
        return self.delete_by_pk(row_id)
