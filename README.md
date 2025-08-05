# AI-Powered Sybase to Oracle Migration Tool

An intelligent migration solution that leverages Generative AI to automate and optimize database conversion from Sybase to Oracle with accuracy.

## Overview
Migrating enterprise databases from Sybase ASE to Oracle is complex and error-prone. 
This tool uses AI-driven conversion, human-in-the-loop review, and automated testing to ensure fast and reliable migrations.

## Key Features
- Smart Code Conversion: AI-powered transformation of schema objects (tables, views, procedures).
- Interactive Review: Human-in-the-loop editing interface.
- Automated Testing: Pre-migration validation of converted objects.
- Comprehensive Reporting: Detailed analytics and unique migration IDs.
  
## structure

```
project-root/
├── app.py # FastAPI application entry point
├── migration.py # Handles LLM-based SQL conversion logic
├── uploads/ # Stores user-uploaded .sql files
├── report.html # Report generation UI
├── review_edit.html # Inline AI assistant for editing converted SQL
├── testing.html # AI-based testing UI

├── uipage0.html → uipage4.html # UI pages for navigation and workflow
├── circular_logo.png # Branding image
├── venv/ # Python virtual environment
├── pycache/ # Compiled bytecode files
└── README.md # Project documentation (this file)
```
```
# Flow of work


   ┌─────────────┐        ┌─────────────┐       ┌─────────────┐
   │  Oracle DB  │        │ Sybase DB   │       │   AI Model  │
   └──────┬──────┘        └──────┬──────┘       └──────┬──────┘
          │                       │                   │
          │                       │                   │
   ┌──────▼──────┐       ┌────────▼────────┐   ┌──────▼───────┐
   │  DB Connect │────▶ │ Object Selection│──▶│ AI Conversion│
   └──────┬──────┘       └────────┬────────┘   └──────┬───────┘
          │                        │                  │
          │                        ▼                  │
          │                ┌───────────────┐          │
          │                │ Review & Edit │◀─────────┘
          │                └──────┬────────┘
          │                       ▼
          │                ┌───────────────┐
          │                │   Testing     │
          │                └──────┬────────┘
          │                       ▼
          │                ┌───────────────┐
          └──────────────▶│ Migration &    │
                           │   Reporting   │
                           └───────────────┘

```

# Technical Stack
Frontend: HTML5, Streamlit

Backend: Python 3.8+

AI Engine: Fine-tuned LLM (Transformers)

Database Connectors: Sybase ASE, Oracle CX

## Installation & Setup

1. ** Clone the Repository **
``` bash
git clone https://github.com/KarthikGaneshC/VIRTUSA-JatayuS4-NEXUS
cd VIRTUSA-JatayuS4-NEXUS
```

**2. Initialize Virtual Environment**
``` bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows 
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Databases & AI Model**
  

``` 
SYBASE_DSN=your_sybase_connection
ORACLE_DSN=your_oracle_connection
GEMINI_API = REPLACE WITH YOUR API
```

**5. Launch the Application**
``` bash
python app.py
```

## Example Usage
- Login and connect to Sybase & Oracle databases.

- Select schema objects to migrate.

- Review and adjust AI-generated conversions.

- Validate with automated testing.

- Execute migration and download reports.
