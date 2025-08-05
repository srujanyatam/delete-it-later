from unittest import result
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import pyodbc
import cx_Oracle
import re
from docx import Document
import PyPDF2
import time
import pandas as pd
import threading
import webbrowser
import requests
from datetime import datetime
import os
from migration import SybaseToOracleMigration

import google.generativeai as genai
genai.configure(api_key="your api key")
gemini_model = genai.GenerativeModel("gemini-2.5-pro")

# Add this near top of app.py
converted_cache = {}

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')  # or any path you prefer
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Serve the main application page
@app.route('/')
def serve_page0():
    return send_from_directory('.','uipage1.html')

@app.route('/uipage0')
def serve_page1():
    return send_from_directory('.','uipage0.html')

@app.route('/uipage1')
def serve_page2():
    return send_from_directory('.','uipage1.html')

# Serve the second page (uipage2.html)
@app.route('/uipage2')
def serve_page3():
    return send_from_directory('.','uipage2.html')

@app.route('/uipage4.html')
def chat_page():
    return send_from_directory('.','uipage4.html')

@app.route('/regenerate')
def show_regenerate_page():
    return send_from_directory('regenerate.html')

@app.route('/get_converted_objects', methods=['GET'])
def get_converted_objects():
    return jsonify(converted_cache)


# ✅ Global in-memory credential store
stored_credentials = {
    'sybase': {},
    'oracle': {}
}

# ✅ Sybase connection
@app.route('/connect_sybase', methods=['POST'])
def connect_sybase():
    data = request.json
    try:
        conn_str = f"DRIVER=Adaptive Server Enterprise;SERVER={data['server']};PORT={data['port']};UID={data['username']};PWD={data['password']}"
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return jsonify({"connected": True})
    except Exception as e:
        print(f"Sybase connection error: {e}")
        return jsonify({"connected": False, "error": str(e)}), 400

# ✅ Oracle connection and save credentials on success
@app.route('/connect_oracle', methods=['POST'])
def connect_oracle():
    data = request.json
    try:
        dsn = cx_Oracle.makedsn("localhost", 1521, service_name=data['service'])
        conn = cx_Oracle.connect(user=data['username'], password=data['password'], dsn=dsn)
        conn.close()

        # Save credentials only if connection succeeds
        stored_credentials["oracle"] = {
            "user": data["username"],
            "password": data["password"],
            "service_name": data["service"]
        }

        return jsonify({"connected": True})
    except Exception as e:
        print(f"Oracle connection error: {e}")
        return jsonify({"connected": False, "error": str(e)}), 400
@app.route('/save_credentials', methods=['POST'])
def save_credentials():
    data = request.get_json()
    db_type = data.get('db_type')
    username = data.get('username')
    
    if db_type not in ['sybase', 'oracle']:
        return jsonify({'error': 'Invalid DB type'}), 400
    
    credentials = {}

    if db_type == 'sybase':
        credentials = {
            'user': username,
            'password': data.get('password'),
            'host': data.get('server'),
            'port': data.get('port'),
            'db': data.get('database')
        }
        stored_credentials['sybase'] = credentials

    elif db_type == 'oracle':  # ✅ ADD THIS
        credentials = {
            'user': username,
            'password': data.get('password'),
            'service_name': data.get('service')
        }
        stored_credentials['oracle'] = credentials   # ✅ Save Oracle creds too

    return jsonify({'message': f'{db_type.capitalize()} credentials saved successfully!'}), 200
    
@app.route('/get_sybase_databases', methods=['GET'])
def get_sybase_databases():
    try:
        if not stored_credentials['sybase']:
            return jsonify({'error': 'No stored Sybase credentials found'}), 400

        creds = stored_credentials['sybase']
        print("Using credentials:", creds)  # Log the credentials being used

        conn_str = (
            f"DRIVER=Adaptive Server Enterprise;"
            f"SERVER={creds['host']};"  # Ensure 'host' is correct
            f"PORT={creds['port']};"
            f"UID={creds['user']};"  # Ensure 'user' is correct
            f"PWD={creds['password']};"
            f"DATABASE=master;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sysdatabases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')")
        databases = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({'databases': databases})
    except Exception as e:
        print(f"Error fetching Sybase databases: {e}")  # Log the error
        return jsonify({'error': 'Unable to fetch Sybase databases', 'details': str(e)}), 500



@app.route('/DBload_sybase_objects', methods=['POST'])
def DBload_sybase_objects():
    data = request.get_json()
    database = data.get('database')
    object_types = data.get('objects')

    if not database or not object_types:
        return jsonify({'error': 'Missing database or object types'}), 400

    try:
        if not stored_credentials['sybase']:
            return jsonify({'error': 'No stored Sybase credentials found'}), 400

        creds = stored_credentials['sybase']
        conn_str = (
            f"DRIVER=Adaptive Server Enterprise;"
            f"SERVER={creds['host']};"
            f"PORT={creds['port']};"
            f"UID={creds['user']};"
            f"PWD={creds['password']};"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"USE {database}")

        result = {}

        # Fetching objects based on the selected types
        if 'Tables' in object_types:
            cursor.execute("SELECT name FROM sysobjects WHERE type = 'U'")
            result['Tables'] = [row[0] for row in cursor.fetchall()]  # Just list the table names

        if 'Procedures' in object_types:
            cursor.execute("SELECT name FROM sysobjects WHERE type = 'P'")
            proc_names = [row[0] for row in cursor.fetchall()]
            result['Procedures'] = []
            for name in proc_names:
                definition = get_object_definition(cursor, name)
                result['Procedures'].append({'name': name, 'definition': definition})


        if 'Triggers' in object_types:
            cursor.execute("SELECT name FROM sysobjects WHERE type = 'TR'")
            trigger_names = [row[0] for row in cursor.fetchall()]
            result['Triggers'] = []
            for name in trigger_names:
                definition = get_object_definition(cursor, name)
                result['Triggers'].append({'name': name, 'definition': definition})

        if 'Views' in object_types:
            cursor.execute("SELECT name FROM sysobjects WHERE type = 'V'")
            view_names = [row[0] for row in cursor.fetchall()]
            result['Views'] = []
            for name in view_names:
                definition = get_object_definition(cursor, name)
                result['Views'].append({'name': name, 'definition': definition})

        if 'Functions' in object_types:
            cursor.execute("SELECT name FROM sysobjects WHERE type IN ('FN', 'TF', 'IF')")
            result['Functions'] = []
            for name in cursor.fetchall():
                definition = get_object_definition(cursor, name)
                result['Functions'].append({'name': name, 'definition': definition})


        conn.close()
        return jsonify(result)

    except Exception as e:
        print(f"Error loading Sybase objects: {e}")  # Log the error
        return jsonify({'error': 'Failed to load objects', 'details': str(e)}), 500

def get_object_definition(cursor, name):
    cursor.execute(f"""
        SELECT c.text
        FROM sysobjects o
        JOIN syscomments c ON o.id = c.id
        WHERE o.name = ?
        ORDER BY c.colid
    """, (name,))
    return ''.join(row[0] for row in cursor.fetchall())

@app.route('/update_sybase_db', methods=['POST'])
def update_sybase_db():
    data = request.get_json()
    db_name = data.get('database')
    if db_name:
        stored_credentials['sybase']['db'] = db_name
        return jsonify({'message': 'Database updated successfully'}), 200
    return jsonify({'error': 'No database name provided'}), 400

@app.route('/get_object_content')
def get_object_content():
    obj_type = request.args.get('type')
    obj_name = request.args.get('name')
    db = request.args.get('database')

    if not obj_type or not obj_name or not db:
        return jsonify({"error": "Missing parameters"}), 400

    creds = stored_credentials['sybase']
    try:
        conn_str = (
            f"DRIVER=Adaptive Server Enterprise;"
            f"SERVER={creds['host']};"
            f"PORT={creds['port']};"
            f"UID={creds['user']};"
            f"PWD={creds['password']};"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"USE {db}")
        content = get_object_definition(cursor, obj_name)
        conn.close()

        return jsonify({"name": obj_name, "type": obj_type, "content": content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/object_detail.html')
def serve_object_detail():
    return send_from_directory('.', 'object_detail.html')

def extract_table_names(sql_code):
    """
    Extract all table names from SQL code for FROM, JOIN, INSERT, UPDATE, DELETE statements.
    """

    # 🔹 Remove comments so we don't detect tables mentioned inside comments
    sql_code = re.sub(r"/\*.*?\*/", "", sql_code, flags=re.DOTALL)
    sql_code = re.sub(r"--.*", "", sql_code)

    tables = set()

    # 🔹 Patterns to catch all table references
    patterns = [
        r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",           # SELECT ... FROM table
        r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)",           # JOIN table
        r"\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # INSERT INTO table
        r"\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)",         # UPDATE table
        r"\bDELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)"   # DELETE FROM table
    ]

    for pat in patterns:
        found = re.findall(pat, sql_code, flags=re.IGNORECASE)
        tables.update(found)

    return tables

@app.route('/DBconvert_objects', methods=['POST'])
def DBconvert_objects():
    print("✅ /convert_objects was hit!")
    data = request.get_json()
    objects = data.get('objects', {})
    db_name = data.get('database')  # ✅ FIX: Get selected DB from frontend

    filtered_objects = {
        obj_type: [item for item in items if item.strip() and not item.lower().startswith("no ")]
        for obj_type, items in objects.items()
        if items and any(item.strip() and not item.lower().startswith("no ") for item in items)
    }

    converted = {}
    tables_to_create = set()

    if not filtered_objects:
        return jsonify({
            **converted,
            "required_tables": list(tables_to_create)
        })

    for obj_type, items in filtered_objects.items():
        converted[obj_type] = []

        for item in items:
            if obj_type in ['Procedures', 'Functions', 'Triggers']:
                detected_tables = extract_table_names(item)
                tables_to_create.update(detected_tables)

            prompt = (
                f"Convert the following Sybase {obj_type} into equivalent Oracle PL/SQL code.\n"
                f"- Ignore all Sybase comments (both -- and /* ... */).\n"
                f"- Return only clean, executable Oracle PL/SQL code.\n"
                f"- Do not include any explanations, comments, or formatting like markdown.\n"
                f"- If the converted code is incomplete or contains syntax issues, fix them silently.\n\n"
                f"{item.strip()}"
            )

            converted_code = call_llm(prompt)
            converted[obj_type].append(converted_code if converted_code else "-- Conversion failed or timed out.")
            time.sleep(1)

    # ✅ Perform table migration only if required
    if tables_to_create:
        try:
            sybase = stored_credentials.get("sybase")
            oracle = stored_credentials.get("oracle")

            if sybase and oracle and db_name:
                sybase["db"] = db_name  # ✅ Force-insert the selected DB
                migrator = SybaseToOracleMigration(sybase, oracle)

                for table in tables_to_create:
                    status, msg = migrator.migrate_object(table, "Tables")
                    print(f"[MIGRATE] {table}: {status} - {msg}")

                migrator.close_connections()
            else:
                print("⚠ Missing credentials or database — skipping table creation.")
        except Exception as e:
            print(f"⚠ Error auto-creating tables: {e}")

    converted_cache.clear()
    converted_cache.update(converted)

    return jsonify({
        **converted,
        "required_tables": list(tables_to_create)
    })


def call_llm(prompt):
    for attempt in range(2):
        try:
            response = gemini_model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"-- Gemini failed (attempt {attempt+1}):", e)
            time.sleep(2)
    return ""



@app.route('/execute_tables', methods=["POST"])
def execute_tables():
    try:
        data = request.json
        db_name = data.get("database")
        
        # ✅ Use stored_credentials for consistency
        sybase = stored_credentials.get("sybase")
        oracle = stored_credentials.get("oracle")

        if not sybase or not oracle:
            return jsonify({"message": "Missing database credentials"}), 400

        # Add the selected database to the Sybase config
        sybase["db"] = db_name

        migrator = SybaseToOracleMigration(sybase, oracle)

        tables = data.get("tables") or migrator.load_tables()
        results = []
        for table in tables:
            status, message = migrator.migrate_object(table, "Tables")
            results.append(f"{table}: {status} - {message}")

        migrator.close_connections()
        return jsonify({"message": "\n".join(results)})

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/regenerate_objects', methods=['POST'])
def regenerate_objects():
    data = request.get_json()
    selected_objects = data.get('objects', {})

    updated = {}

    for obj_type, items in selected_objects.items():
        updated[obj_type] = []
        for item in items:
            prompt = (
                f"Convert the following Sybase {obj_type} into equivalent Oracle PL/SQL code.\n"
                f"- Ignore all Sybase comments (both -- and /* ... */).\n"
                f"- Return only clean, executable Oracle PL/SQL code.\n"
                f"- Do not include any explanations, comments, or formatting like markdown.\n"
                f"- If the converted code is incomplete or contains syntax issues, fix them silently.\n\n"
                f"{item.strip()}"
            )

            regenerated_code = call_llm(prompt)
            updated[obj_type].append(regenerated_code if regenerated_code else "-- Regeneration failed.")
            time.sleep(1)

    # Update converted_cache
    for obj_type, new_codes in updated.items():
        if obj_type in converted_cache:
            for i, code in enumerate(new_codes):
                try:
                    idx = converted_cache[obj_type].index(selected_objects[obj_type][i])
                    converted_cache[obj_type][idx] = code
                except ValueError:
                    pass

    return jsonify(updated)


# def execute_tables():
#     try:
#         data = request.json
#         db_name = data.get("database")

#         sybase = stored_credentials.get("sybase")
#         oracle = stored_credentials.get("oracle")

#         print(sybase, oracle)

#         if not sybase or not oracle:
#             return jsonify({"message": "Missing database credentials"}), 400

#         sybase["db"] = db_name

#         migrator = SybaseToOracleMigration(sybase, oracle)
#         tables = migrator.load_tables()
#         migrator.close_connections()

#         converted = {"Tables": []}

#         for table in tables:
#             prompt = (
#                 f"Convert the following Sybase table definition into equivalent Oracle DDL.\n"
#                 f"Return only the valid Oracle SQL code. Do not include explanations, comments, or markdown formatting.\n\n"
#                 f"{table.strip()}"
#             )

#             converted_code = call_llm(prompt)

#             if converted_code:
#                 converted["Tables"].append(converted_code)
#             else:
#                 converted["Tables"].append("-- Conversion failed or timed out.")
#             time.sleep(1)

#         return jsonify(converted)

#     except Exception as e:
#         return jsonify({"message": f"Error: {str(e)}"}), 500



# ✅ Use stored_credentials in execute_objects
@app.route('/execute_objects', methods=["POST"])
def execute_objects():
    try:
        data = request.json
        oracle = stored_credentials.get("oracle")
        if not oracle:
            return jsonify({"message": "Oracle credentials not found."}), 400

        dsn = cx_Oracle.makedsn("localhost", 1521, service_name=oracle["service_name"])
        conn = cx_Oracle.connect(user=oracle["user"], password=oracle["password"], dsn=dsn)
        cursor = conn.cursor()

        results = []
        for obj in data.get("objects", []):
            try:
                code = obj["code"]
                cursor.execute(code)
                conn.commit()
                results.append(f"{obj['object_type']}: Success")
            except Exception as e:
                results.append(f"{obj['object_type']}: Failed - {str(e)}")

        cursor.close()
        conn.close()
        return jsonify({"message": "\n".join(results)})

    except Exception as e:
        return jsonify({"message": f"Error executing Oracle objects: {str(e)}"}), 500



@app.route('/execute_oracle_objects', methods=['POST'])
def execute_oracle_objects():                       
    try:
        data = request.get_json()
        objects = data.get('objects', {})

        oracle_creds = stored_credentials.get('oracle')
        if not oracle_creds:
            return jsonify({"success": False, "error": "Oracle credentials not found."})

        dsn = cx_Oracle.makedsn("localhost", 1521, service_name=oracle_creds['service'])
        conn = cx_Oracle.connect(
            user=oracle_creds['username'],
            password=oracle_creds['password'],
            dsn=dsn
        )
        cursor = conn.cursor()

        for obj_type, obj_codes in objects.items():
            for code in obj_codes:
                try:
                    cursor.execute(code)
                except Exception as exec_err:
                    conn.rollback()
                    return jsonify({
                        "success": False,
                        "error": f"Error executing {obj_type}: {str(exec_err)}"
                    })

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        print(f"Error during execution: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500



# ---- Upload + Extract SQL from File ----
@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    filename = file.filename
    if filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        content = ""
        if filename.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        elif filename.endswith('.docx'):
            doc = Document(filepath)
            content = '\n'.join([para.text for para in doc.paragraphs])
        elif filename.endswith('.pdf'):
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() or ''
        elif filename.endswith(('.xls', '.xlsx')): 
            df = pd.read_excel(filepath)
            content = "\n".join(df.astype(str).apply(lambda x: ' '.join(x), axis=1))
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        procedures = []
        parts = re.split(r'(?i)(CREATE\s+(?:PROCEDURE|TABLE|VIEW|FUNCTION|TRIGGER))', content)
        for i in range(1, len(parts), 2):
            proc = parts[i] + parts[i + 1]
        proc_clean = proc.strip()
        procedures.append(proc_clean    )
        return jsonify(procedures)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- Helper: Send SQL to Local LLM ----
def generate_llm_response(prompt):
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Request Error: {str(e)}")
        return f"Gemini Error: {str(e)}"

    


@app.route('/convert_with_llm', methods=['POST'])
def convert_with_llm():
    data = request.get_json()
    sybase_sql = data.get("sql", "").strip()

    if not sybase_sql:
        return jsonify({"error": "No SQL content provided"}), 400

    prompt = (
        "Convert the following Sybase SQL to Oracle SQL.\n"
        "Return only the Oracle SQL code, wrapped in triple single quotes like this: '''...'''.\n"
        "Do not include any explanations, comments, or syntax comparisons.\n\n"
        f"{sybase_sql}"
    )

    oracle_sql = generate_llm_response(prompt)

    # 1. Try extracting from triple single quotes
    match = re.search(r"'''(.*?)'''", oracle_sql, re.DOTALL)
    if match:
        extracted_sql = match.group(1).strip()
    else:
        # 2. Fallback: extract lines between 'CREATE' and the first '/'
        lines = oracle_sql.splitlines()
        inside = False
        code_lines = []
        for line in lines:
            if not inside and re.match(r'^\s*CREATE', line, re.IGNORECASE):
                inside = True
            if inside:
                if line.strip() == '/':
                    break
                code_lines.append(line)
        extracted_sql = "\n".join(code_lines).strip()

    return jsonify({"oracle_sql": extracted_sql})

# @app.route('/validate_oracle_syntax', methods=['POST'])
# def validate_oracle_syntax():
#     data = request.get_json()
#     objects = data.get('objects', [])
#     print(objects)
#     oracle_user = data.get('oracle_user')
#     oracle_pass = data.get('oracle_pass')
#     oracle_service = data.get('oracle_service')

#     error_count = 0
#     success_count = 0
#     error_details = []

#     try:
#         dsn = cx_Oracle.makedsn("localhost", 1521, service_name=oracle_service)
#         conn = cx_Oracle.connect(user=oracle_user, password=oracle_pass, dsn=dsn)
#         cursor = conn.cursor()

#         for obj in objects:
#             try:
#                 cursor.execute(f"BEGIN {obj['code']} END;")
#                 success_count += 1
#             except Exception as e:
#                 error_count += 1
#                 error_details.append(f"{obj['object_type']}: {str(e)}")

#         cursor.close()
#         conn.close()
#         print("success_count", success_count)
#         print("error_count", error_count)
#         if error_count == 0:
#             return jsonify({"status": "success", "success_count": success_count, "message": "✅ All code is syntactically correct."})
#         else:
#             return jsonify({
#                 "status": "error",
#                 "error_count": error_count,
#                 "errors": error_details
#             })

#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)})
@app.route('/validate_oracle_syntax', methods=['POST'])
def validate_oracle_syntax():
    data = request.get_json()
    raw_objects = data.get('objects', [])

    print("Raw objects received for validation:", raw_objects)

    # Filter only objects with valid non-empty code
    objects = [obj for obj in raw_objects if obj.get("code", "").strip()]
    print("Filtered objects for validation:", objects)

    if not objects:
        return jsonify({
            "status": "no_objects",
            "message": "ℹ No valid Oracle objects were submitted for validation.",
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "success_details": []
        })

    oracle_user = data.get('oracle_user')
    oracle_pass = data.get('oracle_pass')
    oracle_service = data.get('oracle_service')

    error_count = 0
    success_count = 0
    error_details = []
    success_details = []

    try:
        dsn = cx_Oracle.makedsn("localhost", 1521, service_name=oracle_service)
        conn = cx_Oracle.connect(user=oracle_user, password=oracle_pass, dsn=dsn)
        cursor = conn.cursor()

        for obj in objects:
            code = obj.get('code', '').strip().rstrip(';')
            object_type = obj.get("object_type", "object")
            object_name = obj.get("object_name", "Unnamed")

            try:
                if code.upper().startswith("CREATE"):
                    cursor.execute(code)
                else:
                    cursor.execute(f"BEGIN {code}; END;")
                success_count += 1
                success_details.append(f"{object_type} - {object_name}: Success")
            except Exception as e:
                error_count += 1
                error_details.append(f"{object_type} - {object_name}: {str(e)}")

        cursor.close()
        conn.close()

        print("Validation completed.")
        print("Success count:", success_count)
        print("Error count:", error_count)

        return jsonify({
            "status": "completed",
            "success_count": success_count,
            "success_details": success_details,
            "error_count": error_count,
            "errors": error_details,
            "message": (
                "✅ All code is syntactically correct."
                if error_count == 0 else
                f"❌ Found {error_count} errors, {success_count} succeeded."
            )
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def regenerate_objects():
    data = request.get_json()
    selected_objects = data.get('objects', {})

    updated = {}

    for obj_type, items in selected_objects.items():
        updated[obj_type] = []
        for item in items:
            prompt = (
                f"Convert the following Sybase {obj_type} into equivalent Oracle PL/SQL code.\n"
                f"- Ignore all Sybase comments (both -- and /* ... */).\n"
                f"- Return only clean, executable Oracle PL/SQL code.\n"
                f"- Do not include any explanations, comments, or formatting like markdown.\n"
                f"- If the converted code is incomplete or contains syntax issues, fix them silently.\n\n"
                f"{item.strip()}"
            )

            regenerated_code = call_llm(prompt)
            updated[obj_type].append(regenerated_code if regenerated_code else "-- Regeneration failed.")
            time.sleep(1)
# Update the cache
    for obj_type, new_codes in updated.items():
        # OVERWRITE the old list for this object-type with the freshly generated one
        converted_cache[obj_type] = new_codes

    return jsonify(updated)

def generate_llm_response(prompt):
    """
    Uses Gemini to generate Oracle SQL from Sybase SQL (or any LLM prompt).
    Returns only the raw text result.
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"-- Gemini LLM request failed in generate_llm_response(): {str(e)}")
        return f"-- Gemini Error: {str(e)}"

# -----------------------
# LLM Ask AI Route
# -----------------------
@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    data = request.get_json()
    selection = data.get("selection", "")
    prompt = data.get("prompt", "")

    full_prompt = f"""
    You are an Oracle PL/SQL expert.
    The user has selected **only this part** of their Oracle code:

    {selection}

    Instruction: {prompt}

    🔴 IMPORTANT:
    - Only rewrite/improve the **selected code snippet**.
    - Do NOT regenerate the entire procedure or function.
    - Return ONLY the rewritten snippet, nothing else.
    """

    try:
        response = gemini_model.generate_content(full_prompt)
        ai_text = response.text.strip()

        # Clean up any markdown Gemini might return
        ai_text = ai_text.replace("```sql", "").replace("```", "").strip()

        # Remove extra quotes if Gemini wraps code in quotes
        if ai_text.startswith('"') and ai_text.endswith('"'):
            ai_text = ai_text[1:-1].strip()

        return jsonify({"answer": ai_text})

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"answer": "❌ AI Error: Could not regenerate right now. Please try again later."})





def get_oracle_connection():
    try:
        dsn = cx_Oracle.makedsn("localhost", 1521, service_name="XE")  # precise DSN
        conn = cx_Oracle.connect(user="system", password="virtusas4", dsn=dsn)
        return conn
    except cx_Oracle.DatabaseError as e:
        print("❌ Oracle connection error:", e)
        return None

@app.route('/compile_oracle_code', methods=['POST'])
def compile_oracle_code():
    try:
        data = request.get_json()
        raw_code = data.get('oracle_code', '').strip()

        if not raw_code:
            return jsonify({
                "success": False,
                "errors": [{"object": "Input", "type": "Validation", "message": "Oracle code is empty."}]
            })

        # ✅ Clean up weird comments that might confuse compiler
        raw_code = re.sub(r'^.*?converted.*?--\s*', '', raw_code, flags=re.IGNORECASE).strip()

        # ✅ REMOVE TRAILING SLASH (important!)
        if raw_code.endswith('/'):
            raw_code = raw_code[:-1].strip()

        oracle = stored_credentials.get("oracle")
        if not oracle:
            return jsonify({
                "success": False,
                "errors": [{"object": "Auth", "type": "Credentials", "message": "Oracle credentials not found."}]
            })

        dsn = cx_Oracle.makedsn("localhost", 1521, service_name=oracle["service_name"])
        conn = cx_Oracle.connect(user=oracle["user"], password=oracle["password"], dsn=dsn)
        cursor = conn.cursor()

        errors = []

        try:
            # ✅ Compile the full PL/SQL block (Procedure, Function, Trigger)
            cursor.execute(raw_code)

            # ✅ Extract object type & name (for error lookup)
            match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?(PROCEDURE|FUNCTION|PACKAGE|TRIGGER)\s+(\w+)', raw_code, re.IGNORECASE)
            if match:
                obj_type, obj_name = match.groups()
                obj_type = obj_type.upper()
                obj_name = obj_name.upper()

                # ✅ Query USER_ERRORS for compilation issues
                cursor.execute("""
                    SELECT line, position, text
                    FROM user_errors
                    WHERE name = :1 AND type = :2
                    ORDER BY sequence
                """, [obj_name, obj_type])

                fetched_errors = cursor.fetchall()
                for line, pos, text in fetched_errors:
                    errors.append({
                        "object": obj_name,
                        "type": obj_type,
                        "message": f"Line {line}, Pos {pos}: {text}"
                    })

        except cx_Oracle.DatabaseError as e:
            err, = e.args
            errors.append({
                "object": "Unknown",
                "type": "Execution",
                "message": err.message.strip()
            })

        finally:
            cursor.close()
            conn.close()

        if errors:
            return jsonify({"success": False, "errors": errors})
        return jsonify({"success": True, "message": "✅ Oracle code compiled successfully."})

    except Exception as e:
        return jsonify({
            "success": False,
            "errors": [{"object": "Server", "type": "Exception", "message": str(e)}]
        })



testing_procedures = {
  "GetDepartmentById": {
    "sybase_code": """
CREATE PROCEDURE GetDepartmentById
    @dept_id INT
AS
BEGIN
    SELECT * FROM Departments WHERE dept_id = @dept_id
END
""",
    "oracle_code": """
CREATE OR REPLACE PROCEDURE GetDepartmentById (
  dept_id_in IN NUMBER,
  dept_cursor OUT SYS_REFCURSOR
)
IS
BEGIN
  OPEN dept_cursor FOR
  SELECT * FROM Departments WHERE dept_id = dept_id_in;
END;
""",
    "sybase_function": "",
    "oracle_function": "",
    "status": "pending",
    "cause": ""
  },

  "AddDepartment": {
    "sybase_code": """
CREATE PROCEDURE AddDepartment
    @dept_id INT,
    @dept_name VARCHAR(50),
    @location VARCHAR(50)
AS
BEGIN
    INSERT INTO Departments (dept_id, dept_name, location)
    VALUES (@dept_id, @dept_name, @location)
END
""",
    "oracle_code": """
CREATE OR REPLACE PROCEDURE AddDepartment (
  dept_id_in IN NUMBER,
  dept_name_in IN VARCHAR2,
  location_in IN VARCHAR2
)
IS
BEGIN
  INSERT INTO Departments (dept_id, dept_name, location)
  VALUES (dept_id_in, dept_name_in, location_in);
END;
""",
    "sybase_function": "",
    "oracle_function": "",
    "status": "pending",
    "cause": ""
  }
}

def summarize_functionality_llm(code_text, dialect="sybase"):
    try:
        prompt = f"Summarize in one sentence what this {dialect.upper()} procedure does:\n\n{code_text}"
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini summary error: {e}")
        return "(Unable to summarize with Gemini)"

@app.route('/get_testing_procedure/<proc_name>')
def get_testing_procedure(proc_name):
    data = testing_procedures.get(proc_name, {})
    if not data:
        return jsonify({"error": "Procedure not found"}), 404

    # ✅ Auto-generate functionality summaries using Gemini
    if not data.get("sybase_function"):
        data["sybase_function"] = summarize_functionality_llm(data.get("sybase_code", ""), dialect="sybase")
    if not data.get("oracle_function"):
        data["oracle_function"] = summarize_functionality_llm(data.get("oracle_code", ""), dialect="oracle")

    return jsonify(data)


@app.route("/get_procedure_parameters")
def get_procedure_parameters():
    proc_name = request.args.get("name")
    if not proc_name:
        return jsonify({"error": "Procedure name is required"}), 400

    try:
        creds = stored_credentials["sybase"]
        conn_str = (
            f"DRIVER=Adaptive Server Enterprise;"
            f"SERVER={creds['host']};"
            f"PORT={creds['port']};"
            f"UID={creds['user']};"
            f"PWD={creds['password']};"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Switch to the correct DB if specified
        db = creds.get("db")
        if db:
            cursor.execute(f"USE {db}")
            cursor.execute("SET CHAINED OFF")

        # Call sp_help to get metadata
        cursor.execute(f"sp_help {proc_name}")

        all_result_sets = []
        while True:
            try:
                rows = cursor.fetchall()
                all_result_sets.append(rows)
                if not cursor.nextset():
                    break
            except:
                break

        # Try to extract parameter list from one of the result sets
        param_list = []
        for result in all_result_sets:
            if result and hasattr(result[0], 'Parameter_name'):
                for row in result:
                    param_name = row.Parameter_name.strip('@') if hasattr(row, 'Parameter_name') else None
                    param_type = row.Type if hasattr(row, 'Type') else None
                    if param_name and param_type:
                        param_list.append({
                            "name": param_name,
                            "type": param_type
                        })
                break  # found param table

        conn.close()
        return jsonify({"parameters": param_list})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# utils.py (or add this to your Flask app file)
def normalize_param_name(param_name):
    param_name = param_name.lower()
    if param_name.startswith('@'):
        param_name = param_name[1:]
    if param_name.endswith('_in') or param_name.endswith('_out'):
        param_name = param_name.rsplit('_', 1)[0]
    return param_name

@app.route("/get_parameter_mapping")
def get_parameter_mapping():
    proc_name = request.args.get("name")
    if not proc_name:
        return jsonify({"error": "Procedure name required."}), 400

    try:
        # Fetch param metadata (you already have this logic in /get_procedure_parameters)
        sybase_params = get_procedure_parameters(proc_name)  # returns [{name, type, direction}, ...]
        oracle_params = get_procedure_parameters(proc_name)

        param_map = map_procedure_parameters(sybase_params, oracle_params)
        return jsonify({"mapping": param_map})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def map_procedure_parameters(sybase_params, oracle_params):
    logical_map = {}

    for syb in sybase_params:
        logical = normalize_param_name(syb["name"])
        logical_map.setdefault(logical, {})["sybase"] = syb["name"]

    for ora in oracle_params:
        logical = normalize_param_name(ora["name"])
        logical_map.setdefault(logical, {})["oracle"] = ora["name"]

    return logical_map

@app.route("/run_sybase_procedure", methods=["POST"])
def run_sybase_procedure():
    data = request.get_json()
    proc_name = data.get("name")
    inputs = data.get("inputs", {})

    try:
        creds = stored_credentials["sybase"]
        conn_str = (
            f"DRIVER=Adaptive Server Enterprise;"
            f"SERVER={creds['host']};"
            f"PORT={creds['port']};"
            f"UID={creds['user']};"
            f"PWD={creds['password']};"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # ✅ Select database and set unchained mode
        db = creds.get("db")
        if db:
            cursor.execute(f"USE {db}")
        cursor.execute("SET CHAINED OFF")

        # ✅ Build parameter string with proper quoting
        param_str = ", ".join([
            str(v) if str(v).isdigit() else f"'{v}'"
            for v in inputs.values()
        ])
        query = f"EXEC {proc_name} {param_str}" if param_str else f"EXEC {proc_name}"
        print("Executing Sybase query:", query)

        # ✅ Execute and collect output
        cursor.execute(query)

        output = []
        try:
            while True:
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]
                result = [dict(zip(col_names, row)) for row in rows]
                output.extend(result)

                if not cursor.nextset():
                    break
        except pyodbc.ProgrammingError:
            output = "Procedure executed with no result set."

        conn.close()
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/run_oracle_procedure", methods=["POST"])
def run_oracle_procedure():
    data = request.get_json()
    proc_name = data.get("name")
    inputs = data.get("inputs", {})
    oracle_code = data.get("oracle_code")

    if not oracle_code:
        return jsonify({"error": "Oracle code is missing"}), 400

    try:
        creds = stored_credentials["oracle"]
        dsn = cx_Oracle.makedsn("localhost", 1521, service_name=creds["service_name"])
        conn = cx_Oracle.connect(user=creds["user"], password=creds["password"], dsn=dsn)
        cursor = conn.cursor()

        # Drop old procedure (skip if already exists)
        drop_proc_sql = f"""
        BEGIN
            EXECUTE IMMEDIATE 'DROP PROCEDURE {proc_name}';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -4043 THEN RAISE; END IF;
        END;
        """
        cursor.execute(drop_proc_sql)

        # Recreate
        try:
            cursor.execute(oracle_code)
            conn.commit()
        except Exception as ce:
            return jsonify({"error": f"Failed to create procedure: {ce}"}), 500

        # Determine if the procedure includes a SYS_REFCURSOR output
        uses_cursor = ":out_cursor" in oracle_code.lower() or "sys_refcursor" in oracle_code.lower()

        if uses_cursor:
            ref_cursor = conn.cursor()
            param_values = list(inputs.values()) + [ref_cursor]
            cursor.callproc(proc_name, param_values)

            rows = ref_cursor.fetchall()
            col_names = [desc[0] for desc in ref_cursor.description]
            result = [dict(zip(col_names, row)) for row in rows]
            return jsonify({"output": result})
        else:
            # Just DML — no output expected
            param_values = list(inputs.values())
            cursor.callproc(proc_name, param_values)
            conn.commit()
            return jsonify({"output": f"{proc_name} executed successfully."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/get_table_data_sybase", methods=["POST"])
def get_table_data_sybase():
    data = request.json
    table_name = data.get("table_name")

    if not table_name:
        return jsonify({"error": "Missing table name"}), 400

    try:
        creds = stored_credentials["sybase"]
        conn_str = (
            f"DRIVER=Adaptive Server Enterprise;"
            f"SERVER={creds['host']};"
            f"PORT={creds['port']};"
            f"UID={creds['user']};"
            f"PWD={creds['password']};"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        db = creds.get("db")
        if db:
            cursor.execute(f"USE {db}")
        cursor.execute("SET CHAINED OFF")

        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        results = [dict(zip(columns, row)) for row in rows]

        return jsonify({"data": results, "columns": columns})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/store_testing_result', methods=['POST'])
def store_testing_result():
    data = request.get_json()
    proc_name = data.get("procedure_name")
    status = data.get("status")
    cause = data.get("cause", "")
    if proc_name in testing_procedures:
        testing_procedures[proc_name]["status"] = status
        testing_procedures[proc_name]["cause"] = cause
        return jsonify({"message": "Result saved"}), 200
    else:
        return jsonify({"error": "Procedure not found"}), 404

@app.route('/gemini', methods=['POST'])
def call_gemini():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"response": "⚠ Prompt is empty."}), 400

        # Generate response using Gemini
        response = gemini_model.generate_content(prompt)
        answer = response.text.strip()

        return jsonify({"response": answer})

    except Exception as e:
        print("Gemini error:", str(e))
        return jsonify({"response": "❌ Gemini API error: " + str(e)}), 500

if __name__ == '__main__':

    app.run(debug=True)
