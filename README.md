# File Converter

A production-grade Flask web application for bidirectional file conversion between CSV, XLSX, XLS, and DBF formats.

## Overview

File Converter is designed for experienced professionals who value clarity, efficiency, and dignity. It features a modern, sleek interface inspired by Bloomberg Terminal and Apple Human Interface Guidelines, with dark mode as default, high-contrast typography, and keyboard accessibility throughout.

## Features

- **Bidirectional Conversion**: Convert between CSV, XLSX, XLS, and DBF formats seamlessly
- **3-Step Workflow**: Upload → Configure → Download
- **Drag & Drop Upload**: Intuitive file upload with large fallback button
- **Modern UI**: Dark mode default with electric blue accent, crisp typography (18px+), generous whitespace
- **Keyboard Accessible**: Full keyboard navigation support
- **Security**: MIME type validation, file size limits (50MB), secure headers
- **Production Quality**: Structured logging, comprehensive error handling, extensive tests

## Architecture

```
app/
├── __init__.py          # Flask app factory
├── routes.py            # HTTP routes and controllers
├── converter.py         # File conversion service
├── templates/           # Jinja2 templates
│   ├── base.html        # Base template
│   ├── index.html       # Upload step
│   ├── configure.html   # Configure step
│   └── download.html    # Download step
└── static/
    ├── css/
    │   ├── style.css    # Main styles
    │   └── icons.css    # Icon definitions
    └── js/
        └── main.js      # Client-side logic
```

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5000`.

## Usage

### Step 1: Upload

1. Navigate to the homepage
2. Drag and drop your file onto the upload zone, or click to browse
3. Supported formats: `.csv`, `.xlsx`, `.xls`, `.dbf`
4. Maximum file size: 50 MB

### Step 2: Configure

1. Review the uploaded file details (rows, columns, size)
2. Select your target format from the available options
3. Click "Convert to [FORMAT]"

### Step 3: Download

1. Your converted file is ready
2. Click "Download File" to save
3. Or click "Convert Another" to start over

## API Endpoints

### `POST /upload`

Upload a file for conversion.

**Request**: `multipart/form-data` with `file` field

**Response**:
```json
{
  "success": true,
  "filename": "example.csv",
  "extension": "csv",
  "size": 1024,
  "message": "File uploaded successfully"
}
```

### `POST /convert`

Convert the uploaded file.

**Request**: `application/x-www-form-urlencoded` with `target_format` field

**Response**:
```json
{
  "success": true,
  "message": "Conversion complete",
  "filename": "example.xlsx"
}
```

### `GET /download`

Download the converted file.

**Response**: File download

### `POST /api/file-info`

Get information about the uploaded file.

**Response**:
```json
{
  "success": true,
  "data": {
    "rows": 1000,
    "columns": 5,
    "column_names": ["col1", "col2"],
    "column_types": {"col1": {"type": "int64"}},
    "file_size": 10240,
    "memory_usage": 20480
  }
}
```

### `GET /api/available-targets/<source_ext>`

Get available target formats for a source format.

**Response**:
```json
{
  "success": true,
  "targets": ["xlsx", "xls", "dbf"]
}
```

## Supported Conversions

| From → To | CSV | XLSX | XLS | DBF |
|-----------|-----|------|-----|-----|
| **CSV**   | -   | ✓    | ✓   | ✓   |
| **XLSX**  | ✓   | -    | ✓   | ✓   |
| **XLS**   | ✓   | ✓    | -   | ✓   |
| **DBF**   | ✓   | ✓    | ✓   | -   |

## Security

- **File Size Limit**: 50 MB maximum
- **MIME Type Validation**: Extension-based validation
- **Secure Headers**: CSP, XSS protection, HSTS
- **Upload Sanitization**: Secure filename handling
- **Session Management**: Flask session with secret key

## Testing

Run the comprehensive test suite:

```bash
pytest tests/ -v
```

Or run the validation script:

```bash
bash validate.sh
```

Tests cover:
- Unit tests for conversion logic
- Integration tests for routes
- Security tests
- Edge cases and error conditions

## Design Decisions

### UI/UX

- **Dark Mode Default**: Reduces eye strain for extended use
- **Electric Blue Accent**: Single bold accent color (#00D4AA) for clarity
- **Large Typography**: 18px body, 24px+ headings for readability
- **No Animations**: Reduces distraction and improves performance
- **Card-Based Layout**: Clean separation of concerns

### Technical

- **Pandas**: Core data manipulation for reliable conversions
- **Openpyxl**: Modern Excel format support
- **XLRD**: Legacy Excel format support
- **DBFRead**: DBF file reading
- **Flask**: Lightweight, flexible web framework

### DBF Writing

Python has limited native DBF writing support. The application uses:
1. `dbf` library if available (full DBF support)
2. CSV fallback format (widely compatible)

For full DBF writing capability, install: `pip install dbf`

## Development

### Project Structure

```
.
├── app/                  # Application code
├── tests/                # Test suite
├── validate.sh           # Validation script
├── requirements.txt      # Dependencies
├── run.py                # Application entry point
└── README.md            # This file
```

### Adding New Formats

1. Add format to `ALLOWED_EXTENSIONS` in `routes.py`
2. Add conversion methods to `FileConverter` in `converter.py`
3. Update `SUPPORTED_TYPES` mapping
4. Add format icon to templates if desired

### Logging

Structured logging with levels:
- `INFO`: Normal operations
- `WARNING`: Handled errors
- `ERROR`: Unexpected failures

Logs are written to `logs/app.log` in production.

## Troubleshooting

### File Too Large

The 50 MB limit is configurable in `app/__init__.py`:

```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
```

### Conversion Failures

Check logs at `logs/app.log` for detailed error information.

### DBF Writing

If DBF writing fails, install the `dbf` library:

```bash
pip install dbf
```

## License

MIT License

## Support

For issues or questions, please check the logs first, then review the API documentation in the code.