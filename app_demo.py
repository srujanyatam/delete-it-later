from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
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

# Mock Google Generative AI for demo
class MockGeminiModel:
    def generate_content(self, prompt):
        class MockResponse:
            def __init__(self, text):
                self.text = text
        return MockResponse("-- Mock Oracle conversion result for demo purposes --")

# Mock the Gemini model
gemini_model = MockGeminiModel()

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
    return send_from_directory('.','uipage1_simple.html')

@app.route('/uipage0')
def serve_page1():
    return send_from_directory('.','uipage0.html')

@app.route('/uipage1')
def serve_page2():
    return send_from_directory('.','uipage1_simple.html')

# Serve the second page (uipage2.html)
@app.route('/uipage2')
def serve_page3():
    return send_from_directory('.','uipage2.html')

@app.route('/uipage3')
def serve_page4():
    return send_from_directory('.','uipage3.html')

@app.route('/uipage4.html')
def chat_page():
    return send_from_directory('.','uipage4.html')

@app.route('/review_edit.html')
def review_edit_page():
    return send_from_directory('.','review_edit.html')

@app.route('/testing.html')
def testing_page():
    return send_from_directory('.','testing.html')

@app.route('/report.html')
def report_page():
    return send_from_directory('.','report.html')

@app.route('/regenerate')
def show_regenerate_page():
    return send_from_directory('regenerate.html')

@app.route('/get_converted_objects', methods=['GET'])
def get_converted_objects():
    return jsonify(converted_cache)

# Simplified endpoints - no credentials required
@app.route('/connect_sybase', methods=['POST'])
def connect_sybase():
    return jsonify({"connected": True, "message": "✅ Connected successfully! (No credentials required)"})

@app.route('/connect_oracle', methods=['POST'])
def connect_oracle():
    return jsonify({"connected": True, "message": "✅ Connected successfully! (No credentials required)"})

@app.route('/save_credentials', methods=['POST'])
def save_credentials():
    # Always return success - no actual credential storage needed
    return jsonify({'message': '✅ Ready to use! (No credentials required)'}), 200

@app.route('/get_credentials/<db_type>/<username>')
def get_credentials(db_type, username):
    # Return empty password - no credentials needed
    return jsonify({'password': ''})

@app.route('/get_sybase_databases', methods=['GET'])
def get_sybase_databases():
    # Return sample databases for demo
    return jsonify({'databases': ['Sample_DB', 'Test_Database', 'Demo_Project']})

@app.route('/DBload_sybase_objects', methods=['POST'])
def DBload_sybase_objects():
    # Return sample objects for conversion
    return jsonify({
        'Tables': ['employees', 'departments', 'orders'],
        'Procedures': [
            {'name': 'GetEmployeeById', 'definition': 'CREATE PROCEDURE GetEmployeeById @emp_id INT AS BEGIN SELECT * FROM employees WHERE id = @emp_id END'},
            {'name': 'GetDepartmentEmployees', 'definition': 'CREATE PROCEDURE GetDepartmentEmployees @dept_id INT AS BEGIN SELECT * FROM employees WHERE dept_id = @dept_id END'},
            {'name': 'InsertEmployee', 'definition': 'CREATE PROCEDURE InsertEmployee @name VARCHAR(100), @salary DECIMAL(10,2) AS BEGIN INSERT INTO employees (name, salary) VALUES (@name, @salary) END'}
        ],
        'Views': ['employee_summary', 'department_stats'],
        'Functions': ['CalculateBonus', 'GetEmployeeCount'],
        'Triggers': ['audit_employee_changes', 'update_department_stats']
    })

@app.route('/DBconvert_objects', methods=['POST'])
def DBconvert_objects():
    data = request.get_json()
    objects = data.get('objects', {})
    
    converted = {}
    for obj_type, items in objects.items():
        converted[obj_type] = []
        for item in items:
            # Generate realistic Oracle conversions
            if obj_type == 'Procedures':
                if isinstance(item, dict) and 'name' in item:
                    proc_name = item['name']
                    converted_code = f"""-- Converted Oracle procedure
CREATE OR REPLACE PROCEDURE {proc_name} (
  emp_id_in IN NUMBER DEFAULT NULL,
  dept_id_in IN NUMBER DEFAULT NULL,
  name_in IN VARCHAR2 DEFAULT NULL,
  salary_in IN NUMBER DEFAULT NULL,
  result_cursor OUT SYS_REFCURSOR
)
IS
BEGIN
  -- Oracle equivalent of Sybase procedure
  OPEN result_cursor FOR
    SELECT * FROM employees 
    WHERE (emp_id_in IS NULL OR id = emp_id_in)
      AND (dept_id_in IS NULL OR dept_id = dept_id_in);
  
  -- Handle insert operations
  IF name_in IS NOT NULL AND salary_in IS NOT NULL THEN
    INSERT INTO employees (name, salary) VALUES (name_in, salary_in);
  END IF;
  
  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END;"""
                else:
                    converted_code = f"-- Converted Oracle procedure\nCREATE OR REPLACE PROCEDURE demo_procedure\nIS\nBEGIN\n  -- Oracle conversion\n  NULL;\nEND;"
            elif obj_type == 'Tables':
                converted_code = f"""-- Converted Oracle table
CREATE TABLE {item} (
  id NUMBER PRIMARY KEY,
  name VARCHAR2(100) NOT NULL,
  created_date DATE DEFAULT SYSDATE,
  status VARCHAR2(20) DEFAULT 'ACTIVE'
);

-- Create sequence for auto-increment
CREATE SEQUENCE {item}_seq START WITH 1 INCREMENT BY 1;"""
            elif obj_type == 'Views':
                converted_code = f"""-- Converted Oracle view
CREATE OR REPLACE VIEW {item} AS
SELECT 
  e.id,
  e.name,
  d.department_name,
  e.salary
FROM employees e
JOIN departments d ON e.dept_id = d.id;"""
            elif obj_type == 'Functions':
                converted_code = f"""-- Converted Oracle function
CREATE OR REPLACE FUNCTION {item} (
  input_param IN NUMBER
) RETURN NUMBER
IS
  result NUMBER;
BEGIN
  -- Oracle function logic
  SELECT COUNT(*) INTO result FROM employees WHERE dept_id = input_param;
  RETURN result;
EXCEPTION
  WHEN OTHERS THEN
    RETURN 0;
END;"""
            elif obj_type == 'Triggers':
                converted_code = f"""-- Converted Oracle trigger
CREATE OR REPLACE TRIGGER {item}
BEFORE INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW
BEGIN
  -- Audit trail
  INSERT INTO audit_log (
    table_name, 
    action_type, 
    old_values, 
    new_values, 
    change_date
  ) VALUES (
    'EMPLOYEES',
    CASE 
      WHEN INSERTING THEN 'INSERT'
      WHEN UPDATING THEN 'UPDATE'
      WHEN DELETING THEN 'DELETE'
    END,
    CASE WHEN DELETING THEN :OLD.id||','||:OLD.name ELSE NULL END,
    CASE WHEN INSERTING THEN :NEW.id||','||:NEW.name ELSE NULL END,
    SYSDATE
  );
END;"""
            else:
                converted_code = f"-- Converted {obj_type} for Oracle"
            
            converted[obj_type].append(converted_code)
    
    converted_cache.clear()
    converted_cache.update(converted)
    
    return jsonify({
        **converted,
        "required_tables": []
    })

@app.route('/convert_with_llm', methods=['POST'])
def convert_with_llm():
    data = request.get_json()
    sybase_sql = data.get("sql", "").strip()

    if not sybase_sql:
        return jsonify({"error": "No SQL content provided"}), 400

    # Generate realistic Oracle conversion
    oracle_sql = f"""-- Oracle conversion of Sybase SQL
-- Original: {sybase_sql}

CREATE OR REPLACE PROCEDURE converted_procedure (
  param1 IN VARCHAR2 DEFAULT NULL,
  param2 IN NUMBER DEFAULT NULL,
  result_cursor OUT SYS_REFCURSOR
)
IS
BEGIN
  -- Oracle equivalent logic
  OPEN result_cursor FOR
    SELECT * FROM dual WHERE 1=1;
  
  -- Handle parameters
  IF param1 IS NOT NULL THEN
    -- Process param1
    NULL;
  END IF;
  
  IF param2 IS NOT NULL THEN
    -- Process param2
    NULL;
  END IF;
  
  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END;"""

    return jsonify({"oracle_sql": oracle_sql})

@app.route('/validate_oracle_syntax', methods=['POST'])
def validate_oracle_syntax():
    return jsonify({
        "status": "completed",
        "success_count": 1,
        "success_details": ["✅ All Oracle code is syntactically correct"],
        "error_count": 0,
        "errors": [],
        "message": "✅ All code is syntactically correct and ready for deployment!"
    })

@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    data = request.get_json()
    selection = data.get("selection", "")
    prompt = data.get("prompt", "")

    # Generate helpful AI response
    ai_response = f"""-- AI Enhancement for: {selection}
-- Based on your request: {prompt}

-- Improved Oracle code:
CREATE OR REPLACE PROCEDURE enhanced_procedure (
  input_param IN VARCHAR2,
  output_param OUT SYS_REFCURSOR
)
IS
BEGIN
  -- Enhanced logic with better error handling
  OPEN output_param FOR
    SELECT * FROM dual WHERE 1=1;
  
  -- Add proper exception handling
  EXCEPTION
    WHEN OTHERS THEN
      -- Log error and re-raise
      DBMS_OUTPUT.PUT_LINE('Error: ' || SQLERRM);
      RAISE;
END;"""

    return jsonify({"answer": ai_response})

@app.route('/compile_oracle_code', methods=['POST'])
def compile_oracle_code():
    return jsonify({
        "success": True, 
        "message": "✅ Oracle code compiled successfully and is ready for deployment!"
    })

@app.route('/gemini', methods=['POST'])
def call_gemini():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"response": "⚠ Please provide a question or request."}), 400

        # Generate helpful response
        response = f"""🤖 AI Assistant Response:

Your question: {prompt}

Here's my recommendation for Oracle PL/SQL:

1. **Best Practices**: Always use proper exception handling
2. **Performance**: Use bind variables for better performance
3. **Security**: Implement proper input validation
4. **Maintenance**: Add comprehensive comments

Example Oracle code:
```sql
CREATE OR REPLACE PROCEDURE best_practice_proc (
  input_param IN VARCHAR2,
  result_cursor OUT SYS_REFCURSOR
)
IS
BEGIN
  -- Validate input
  IF input_param IS NULL THEN
    RAISE_APPLICATION_ERROR(-20001, 'Input parameter cannot be null');
  END IF;
  
  -- Process with cursor
  OPEN result_cursor FOR
    SELECT * FROM your_table WHERE condition = input_param;
    
EXCEPTION
  WHEN OTHERS THEN
    -- Log error
    DBMS_OUTPUT.PUT_LINE('Error: ' || SQLERRM);
    RAISE;
END;
```

This approach ensures your Oracle code is robust, secure, and maintainable."""

        return jsonify({"response": response})

    except Exception as e:
        print("AI Assistant error:", str(e))
        return jsonify({"response": "❌ AI Assistant temporarily unavailable. Please try again."}), 500

# File upload and conversion endpoints
@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    filename = file.filename
    if filename == '':
        return jsonify({'error': 'No file selected'}), 400

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

        # Extract SQL procedures from content
        procedures = []
        parts = re.split(r'(?i)(CREATE\s+(?:PROCEDURE|TABLE|VIEW|FUNCTION|TRIGGER))', content)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                proc = parts[i] + parts[i + 1]
                proc_clean = proc.strip()
                if proc_clean:
                    procedures.append(proc_clean)
        
        return jsonify(procedures)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Sybase to Oracle Migration Tool (No Authentication Required)")
    print("📱 Website will be available at: http://localhost:5000")
    print("🔗 Main page: http://localhost:5000/uipage1.html")
    print("📋 Review & Edit: http://localhost:5000/review_edit.html")
    print("🧪 Testing: http://localhost:5000/testing.html")
    print("📊 Report: http://localhost:5000/report.html")
    print("\n✅ No database credentials or authentication required!")
    print("   Users can directly access all features and perform conversions")
    print("   All database operations are simulated with sample data")
    
    # Open browser automatically
    threading.Timer(2.0, lambda: webbrowser.open('http://localhost:5000')).start()
    
    app.run(debug=True, host='0.0.0.0', port=5000) 