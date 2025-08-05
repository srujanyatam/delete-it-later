# 🚀 Sybase to Oracle Migration Tool - Free Online Converter

A completely free, no-registration-required online tool to convert Sybase database objects to Oracle PL/SQL.

## ✨ Features

- 🔧 **Smart Conversion**: Convert Sybase procedures, functions, triggers, and views to Oracle
- ⚡ **Instant Results**: No waiting, immediate conversion
- 🔒 **100% Free**: No registration, no hidden costs
- 📱 **Works Everywhere**: Desktop, tablet, mobile - no software needed
- 🛡️ **Secure**: All processing happens locally in your browser
- 📊 **Best Practices**: Generated Oracle code follows industry standards

## 🌐 Live Demo

**Coming Soon**: This tool will be deployed to Netlify for free public access.

## 🚀 Quick Start

### Option 1: Use Online (Recommended)
1. Visit the live website (will be available soon)
2. Paste your Sybase SQL code
3. Click "Convert to Oracle"
4. Copy the converted Oracle code

### Option 2: Run Locally
1. Clone this repository
2. Open `index.html` in your browser
3. Start converting immediately

## 📋 Supported Conversions

| Sybase Object | Oracle Equivalent |
|---------------|-------------------|
| `CREATE PROCEDURE` | `CREATE OR REPLACE PROCEDURE` |
| `CREATE FUNCTION` | `CREATE OR REPLACE FUNCTION` |
| `CREATE TRIGGER` | `CREATE OR REPLACE TRIGGER` |
| `CREATE VIEW` | `CREATE OR REPLACE VIEW` |
| `@parameter` | `parameter_in IN/OUT` |
| `SELECT` | `OPEN cursor FOR SELECT` |

## 🔧 Example Conversion

### Input (Sybase):
```sql
CREATE PROCEDURE GetEmployeeById
    @emp_id INT
AS
BEGIN
    SELECT * FROM employees WHERE id = @emp_id
END
```

### Output (Oracle):
```sql
-- Converted from Sybase to Oracle
-- Original: CREATE PROCEDURE GetEmployeeById

CREATE OR REPLACE PROCEDURE GetEmployeeById (
  emp_id_in IN NUMBER,
  result_cursor OUT SYS_REFCURSOR
)
IS
BEGIN
  OPEN result_cursor FOR
    SELECT * FROM employees WHERE id = emp_id_in;
EXCEPTION
  WHEN OTHERS THEN
    RAISE;
END;
```

## 🛠️ Technical Details

- **Frontend**: Pure HTML, CSS, JavaScript
- **No Backend Required**: All processing happens in the browser
- **No Dependencies**: No external libraries or frameworks
- **Cross-Platform**: Works on any modern browser

## 📦 Files Structure

```
├── index.html              # Main converter page
├── netlify.toml            # Netlify configuration
├── requirements_netlify.txt # Python dependencies (if needed)
├── runtime.txt             # Python runtime specification
└── README.md              # This file
```

## 🌍 Deployment to Netlify

### Step 1: Prepare for Deployment
1. Ensure all files are in the repository
2. The `index.html` file should be in the root directory
3. Include the `netlify.toml` configuration file

### Step 2: Deploy to Netlify
1. Go to [netlify.com](https://netlify.com)
2. Sign up for a free account
3. Click "New site from Git"
4. Connect your GitHub repository
5. Deploy settings:
   - **Build command**: Leave empty (static site)
   - **Publish directory**: `.` (root directory)
6. Click "Deploy site"

### Step 3: Custom Domain (Optional)
1. In your Netlify dashboard, go to "Domain settings"
2. Click "Add custom domain"
3. Follow the DNS configuration instructions

## 🔒 Security & Privacy

- ✅ **No Data Storage**: Your code never leaves your browser
- ✅ **No Registration**: No personal information required
- ✅ **No Tracking**: No analytics or user tracking
- ✅ **Open Source**: Code is transparent and auditable

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

- **Issues**: Create an issue on GitHub
- **Questions**: Check the documentation or create a discussion
- **Feature Requests**: Submit via GitHub issues

## 🎯 Roadmap

- [ ] Advanced conversion patterns
- [ ] Batch file processing
- [ ] More database object types
- [ ] Syntax validation
- [ ] Performance optimization suggestions
- [ ] Export to different formats

---

**Made with ❤️ for the developer community**

*This tool helps developers migrate from Sybase to Oracle databases efficiently and cost-effectively.*
