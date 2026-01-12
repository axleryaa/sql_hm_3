import psycopg2
from pydantic_settings import BaseSettings, SettingsConfigDict
from psycopg2.extensions import connection as PgConnection

class ServiceConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

class DBConfig(ServiceConfig):
    host: str = "localhost"
    port: int = 5432
    user: str
    password: str
    db: str
    table_prefix: str = ""

    model_config = SettingsConfigDict(env_prefix="DB_")

    @property
    def dsn(self) -> str:
        return (
            f"dbname={self.db} "
            f"user={self.user} "
            f"password={self.password} "
            f"host={self.host} "
            f"port={self.port}"
        )


class DbConnection:
    def __init__(self, config: DBConfig):
        self.config = config
        self.conn: PgConnection | None = None

    @property
    def prefix(self) -> str:
        return self.config.table_prefix

    def connect(self) -> PgConnection:
        if not self.conn:
            self.conn = psycopg2.connect(self.config.dsn)
        return self.conn

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> PgConnection:
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def test(self) -> bool:
        with self.connect().cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS test CASCADE")
            cur.execute("CREATE TABLE test(test integer)")
            cur.execute("INSERT INTO test(test) VALUES (1)")
            self.conn.commit()

            cur.execute("SELECT test FROM test")
            result = cur.fetchone()

            cur.execute("DROP TABLE test")
            self.conn.commit()

        return result[0] == 1
