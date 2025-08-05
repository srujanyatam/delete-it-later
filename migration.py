import pyodbc
import cx_Oracle
import traceback

class SybaseToOracleMigration:
    def __init__(self, sybase_credentials, oracle_credentials):
        self.sybase_credentials = sybase_credentials
        self.oracle_credentials = oracle_credentials

        # Connect to Sybase with autocommit ON
        self.sybase_conn = pyodbc.connect(
            f'DRIVER={{Adaptive Server Enterprise}};'
            f'SERVER={self.sybase_credentials["host"]};'
            f'PORT={self.sybase_credentials["port"]};'
            f'UID={self.sybase_credentials["user"]};'
            f'PWD={self.sybase_credentials["password"]};'
            f'DATABASE={self.sybase_credentials["db"]}',
            autocommit=True
        )
        self.sybase_cursor = self.sybase_conn.cursor()

        # Connect to Oracle
        dsn = cx_Oracle.makedsn(
            "localhost", 1521, service_name=self.oracle_credentials["service_name"]
        )
        self.oracle_conn = cx_Oracle.connect(
            user=self.oracle_credentials["user"],
            password=self.oracle_credentials["password"],
            dsn=dsn
        )
        self.oracle_cursor = self.oracle_conn.cursor()

    def load_tables(self):
        """Fetch all user tables from Sybase."""
        self.sybase_cursor.execute("SELECT name FROM sysobjects WHERE type = 'U'")
        return [row[0] for row in self.sybase_cursor.fetchall()]

    def get_table_structure(self, table_name):
        """Retrieve columns, types, length, precision/scale, and nullability for a Sybase table."""
        query = f"""
        SELECT 
            c.name AS column_name,
            t.name AS data_type,
            c.length,
            c.prec,
            c.scale,
            CASE WHEN (c.status & 8) = 8 THEN 1 ELSE 0 END AS is_nullable
        FROM syscolumns c
        JOIN systypes t ON c.usertype = t.usertype
        WHERE LOWER(OBJECT_NAME(c.id)) = LOWER('{table_name}')
        ORDER BY c.colid
        """

        self.sybase_cursor.execute(query)
        return [
            {
                "column_name": row[0],
                "data_type": row[1],
                "length": row[2],
                "precision": row[3],
                "scale": row[4],
                "nullable": bool(row[5])
            }
            for row in self.sybase_cursor.fetchall()
        ]


    def sybase_to_oracle_datatype(self, sybase_type, length=None, precision=None, scale=None):
        """Map Sybase datatype to Oracle."""
        base_type = sybase_type.lower().strip()

        if base_type in ['char', 'varchar', 'nchar', 'nvarchar']:
            length = length if length and length > 0 else 255
            return {
                'char': f'CHAR({length})',
                'varchar': f'VARCHAR2({length})',
                'nchar': f'NCHAR({length})',
                'nvarchar': f'NVARCHAR2({length})'
            }.get(base_type)

        if base_type in ['decimal', 'numeric']:
            if precision and scale:
                return f'NUMBER({precision},{scale})'
            elif precision:
                return f'NUMBER({precision})'
            else:
                return 'NUMBER'

        return {
            'int': 'NUMBER(10)',
            'integer': 'NUMBER(10)',
            'smallint': 'NUMBER(5)',
            'tinyint': 'NUMBER(3)',
            'bigint': 'NUMBER(19)',
            'float': 'FLOAT',
            'double': 'FLOAT',
            'double precision': 'FLOAT',
            'real': 'FLOAT',
            'money': 'NUMBER(19,4)',
            'smallmoney': 'NUMBER(10,4)',
            'text': 'CLOB',
            'ntext': 'NCLOB',
            'datetime': 'DATE',
            'smalldatetime': 'DATE',
            'date': 'DATE',
            'time': 'DATE',
            'timestamp': 'DATE',
            'binary': 'BLOB',
            'varbinary': 'BLOB',
            'bit': 'NUMBER(1)',
            'boolean': 'NUMBER(1)',  # Optional: Oracle doesn't support BOOLEAN natively in SQL
            'image': 'BLOB',
            'uniqueidentifier': 'RAW(16)',  # UUID/GUID
            'xml': 'CLOB',
            'json': 'CLOB',  # Oracle 21c+ has native JSON type, use 'JSON' if you're on that
            'sysname': 'VARCHAR2(256)'  # Common internal name type
        }.get(base_type, 'VARCHAR2(4000)')

    def create_table_in_oracle(self, table_name, columns):
        """Create table in Oracle if it doesn't exist."""
        table_name_upper = table_name.upper()
        safe_table_name = f'"{table_name_upper}"'  # Quote table name

        # Check if table already exists
        self.oracle_cursor.execute("""
            SELECT COUNT(*) FROM user_tables WHERE table_name = :table_name
        """, [table_name_upper])

        if self.oracle_cursor.fetchone()[0] > 0:
            print(f"Table {table_name_upper} already exists in Oracle.")
            return "exists"

        # Generate CREATE TABLE statement
        column_definitions = []
        for col in columns:
            oracle_type = self.sybase_to_oracle_datatype(
                col["data_type"],
                length=col.get("length"),
                precision=col.get("precision"),
                scale=col.get("scale")
            )
            nullable = "" if col["nullable"] else "NOT NULL"
            safe_col_name = f'"{col["column_name"].upper()}"'
            column_definitions.append(f"{safe_col_name} {oracle_type} {nullable}")

        create_stmt = f"""
        CREATE TABLE {safe_table_name} (
            {', '.join(column_definitions)}
        )
        """
        try:
            self.oracle_cursor.execute(create_stmt)
            self.oracle_conn.commit()
            print(f"Table {table_name_upper} created successfully.")
            return "created"
        except cx_Oracle.DatabaseError as e:
            error_msg = str(e)
            print(f"CREATE TABLE failed for {table_name_upper}: {error_msg}")
            raise


    def migrate_table_data(self, table_name):
        """Migrate all data from a Sybase table to Oracle with flexible name resolution."""
        candidates = [
            table_name,
            table_name.lower(),
            table_name.upper(),
            f'dbo.{table_name}',
            f'dbo.{table_name.lower()}',
            f'dbo.{table_name.upper()}'
        ]

        sybase_found = False
        used_name = None

        for name in candidates:
            try:
                self.sybase_cursor.execute(f'SELECT * FROM {name}')
                sybase_found = True
                used_name = name
                break
            except Exception:
                continue

        if not sybase_found:
            print(f"⚠️ Table '{table_name}' not found in Sybase (tried variations: {candidates}). Data not migrated.")
            return

        rows = self.sybase_cursor.fetchall()
        if not rows:
            print(f"ℹ️ No data to migrate for '{table_name}'.")
            return

        columns = [desc[0] for desc in self.sybase_cursor.description]
        placeholders = ",".join([f":{i+1}" for i in range(len(columns))])
        quoted_cols = [f'"{col.upper()}"' for col in columns]
        insert_stmt = f'INSERT INTO "{table_name.upper()}" ({", ".join(quoted_cols)}) VALUES ({placeholders})'

        inserted = 0
        failed = 0

        for row in rows:
            try:
                self.oracle_cursor.execute(insert_stmt, row)
                inserted += 1
            except Exception as e:
                failed += 1
                print(f"❌ Failed to insert row into '{table_name}': {e}")

        self.oracle_conn.commit()
        print(f"✅ {table_name}: Inserted {inserted} rows | ❌ Failed {failed} | 🗂️ Sybase table used: '{used_name}'")




    def migrate_object(self, table_name, object_type):
        """Orchestrates migration for supported object types."""
        if object_type == "Tables":
            try:
                columns = self.get_table_structure(table_name)
                status = self.create_table_in_oracle(table_name, columns)

                if status == "exists":
                    return "Exists", f"Table {table_name} already exists in Oracle."

                self.migrate_table_data(table_name)
                return "Success", f"Table {table_name} migrated successfully."

            except Exception as e:
                traceback.print_exc()  # Optional: comment this out in production
                return "Failed", f"Error: {str(e)}"

        return "Skipped", f"Object type {object_type} not supported."

    def close_connections(self):
        """Close all DB connections."""
        self.sybase_cursor.close()
        self.sybase_conn.close()
        self.oracle_cursor.close()
        self.oracle_conn.close()
