"""
Migra datos de SQLite local a MySQL de Railway.
Uso: python scripts/migrate_to_mysql.py
"""
import sqlite3
import pymysql
import sys

SQLITE_PATH = "torqly_local.db"
MYSQL_URL = "mysql://root:BdtoHowbsMxlgAHjQeDoNJIUIjVQtEIl@turntable.proxy.rlwy.net:30091/railway"

# Orden respetando foreign keys
TABLE_ORDER = [
    "companies",
    "users",
    "catalog_families",
    "catalog_subfamilies",
    "services_catalog",
    "clients",
    "vehicles",
    "cash_sessions",
    "cash_movements",
    "cash_cuts",
    "service_orders",
    "service_order_items",
    "service_order_washers",
    "payments",
    "payment_items",
    "commissions",
    "commission_payments",
    "payroll_settings",
    "payroll_deductions",
    "salary_payments",
    "inventory_products",
    "inventory_movements",
    "client_credit_accounts",
    "client_credit_movements",
    "integration_accounts",
    "external_sync_records",
    "notifications",
    "internal_bot_messages",
    "whatsapp_conversations",
    "whatsapp_messages",
    "audit_logs",
    "integration_logs",
    "service_jobs",
]

SKIP_TABLES = {"alembic_version"}


def parse_mysql_url(url: str) -> dict:
    # mysql://user:pass@host:port/db
    url = url.replace("mysql://", "")
    user_pass, rest = url.split("@", 1)
    user, password = user_pass.split(":", 1)
    host_port, db = rest.rsplit("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host, port = host_port, 3306
    return {"host": host, "port": port, "user": user, "password": password, "db": db}


def get_sqlite_tables(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return {row[0] for row in cur.fetchall()}


def migrate():
    print("Conectando a SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print("Conectando a MySQL...")
    cfg = parse_mysql_url(MYSQL_URL)
    mysql_conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["db"],
        charset="utf8mb4",
        autocommit=False,
    )
    mysql_cur = mysql_conn.cursor()

    sqlite_tables = get_sqlite_tables(sqlite_cur)

    print("Deshabilitando foreign key checks...")
    mysql_cur.execute("SET FOREIGN_KEY_CHECKS = 0")

    total_migrated = 0

    for table in TABLE_ORDER:
        if table in SKIP_TABLES or table not in sqlite_tables:
            continue

        sqlite_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = sqlite_cur.fetchone()[0]

        if count == 0:
            print(f"  {table}: vacía, omitida")
            continue

        sqlite_cur.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cur.fetchall()
        columns = [d[0] for d in sqlite_cur.description]

        col_list = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"

        inserted = 0
        errors = 0
        for row in rows:
            values = [row[c] for c in columns]
            try:
                mysql_cur.execute(sql, values)
                inserted += 1
            except pymysql.err.IntegrityError as e:
                errors += 1
                if errors <= 3:
                    print(f"    WARN {table}: {e}")

        mysql_conn.commit()
        total_migrated += inserted
        status = f"{inserted}/{count}"
        if errors:
            status += f" ({errors} errores)"
        print(f"  {table}: {status}")

    print("\nRehabilitando foreign key checks...")
    mysql_cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    mysql_conn.commit()

    mysql_cur.close()
    mysql_conn.close()
    sqlite_conn.close()

    print(f"\nMigración completa. {total_migrated} filas migradas.")


if __name__ == "__main__":
    migrate()
