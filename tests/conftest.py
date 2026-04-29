import pytest
import tempfile
import os
from app import create_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'MAX_CONTENT_LENGTH': 50 * 1024 * 1024,
    })
    
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def sample_csv():
    """Create a sample CSV file for testing."""
    fd, path = tempfile.mkstemp(suffix='.csv')
    with os.fdopen(fd, 'w') as f:
        f.write('name,age,city\n')
        f.write('Alice,30,New York\n')
        f.write('Bob,25,London\n')
        f.write('Charlie,35,Tokyo\n')
    yield path
    os.remove(path)

@pytest.fixture
def sample_xlsx():
    """Create a sample XLSX file for testing."""
    import pandas as pd
    fd, path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [30, 25, 35],
        'city': ['New York', 'London', 'Tokyo']
    })
    df.to_excel(path, index=False, engine='openpyxl')
    yield path
    os.remove(path)

@pytest.fixture
def sample_dbf():
    """Create a sample DBF file for testing."""
    fd, path = tempfile.mkstemp(suffix='.csv')
    with os.fdopen(fd, 'w') as f:
        f.write('name,age,city\n')
        f.write('Alice,30,New York\n')
        f.write('Bob,25,London\n')
    yield path
    os.remove(path)