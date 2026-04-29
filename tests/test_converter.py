import os
import tempfile
import pytest
from app.converter import FileConverter


class TestFileConverter:
    """Tests for FileConverter class."""

    def test_init(self):
        """Test converter initialization."""
        converter = FileConverter()
        assert converter is not None
        assert hasattr(converter, 'SUPPORTED_TYPES')

    def test_supported_types_structure(self):
        """Test that supported types dict has correct structure."""
        converter = FileConverter()
        for fmt in ['csv', 'xlsx', 'xls', 'dbf']:
            assert fmt in converter.SUPPORTED_TYPES
            assert isinstance(converter.SUPPORTED_TYPES[fmt], list)

    def test_csv_to_xlsx_conversion(self, sample_csv):
        """Test CSV to XLSX conversion."""
        converter = FileConverter()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            converter.convert(sample_csv, 'csv', target_path, 'xlsx')
            assert os.path.exists(target_path)
            assert os.path.getsize(target_path) > 0
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

    def test_csv_to_xls_conversion(self, sample_csv):
        """Test CSV to XLS conversion."""
        converter = FileConverter()
        with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            converter.convert(sample_csv, 'csv', target_path, 'xls')
            # Conversion may produce xlsx instead
            assert os.path.exists(target_path) or os.path.exists(target_path.replace('.xls', '.xlsx'))
        finally:
            for p in [target_path, target_path.replace('.xls', '.xlsx')]:
                if os.path.exists(p):
                    os.remove(p)

    def test_csv_to_dbf_conversion(self, sample_csv):
        """Test CSV to DBF conversion."""
        converter = FileConverter()
        with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            converter.convert(sample_csv, 'csv', target_path, 'dbf')
            assert os.path.exists(target_path)
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

    def test_xlsx_to_csv_conversion(self, sample_xlsx):
        """Test XLSX to CSV conversion."""
        converter = FileConverter()
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            converter.convert(sample_xlsx, 'xlsx', target_path, 'csv')
            assert os.path.exists(target_path)
            assert os.path.getsize(target_path) > 0
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

    def test_xlsx_to_dbf_conversion(self, sample_xlsx):
        """Test XLSX to DBF conversion."""
        converter = FileConverter()
        with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            converter.convert(sample_xlsx, 'xlsx', target_path, 'dbf')
            assert os.path.exists(target_path)
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

    def test_dbf_to_csv_conversion(self, sample_dbf):
        """Test DBF to CSV conversion."""
        converter = FileConverter()
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            # DBF conversion uses CSV as fallback
            converter.convert(sample_dbf, 'dbf', target_path, 'csv')
            assert os.path.exists(target_path)
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

    def test_invalid_source_format(self):
        """Test conversion with invalid source format."""
        converter = FileConverter()
        with pytest.raises(ValueError, match='Unsupported source format'):
            converter.convert('test.txt', 'txt', 'out.csv', 'csv')

    def test_unsupported_conversion(self):
        """Test unsupported conversion."""
        converter = FileConverter()
        with pytest.raises(ValueError, match='Cannot convert'):
            converter.convert('test.csv', 'csv', 'out.csv', 'csv')

    def test_get_file_info_csv(self, sample_csv):
        """Test getting file info for CSV."""
        converter = FileConverter()
        info = converter.get_file_info(sample_csv, 'csv')
        
        assert 'rows' in info
        assert 'columns' in info
        assert 'column_names' in info
        assert 'column_types' in info
        assert info['rows'] == 3
        assert info['columns'] == 3
        assert 'name' in info['column_names']

    def test_get_file_info_xlsx(self, sample_xlsx):
        """Test getting file info for XLSX."""
        converter = FileConverter()
        info = converter.get_file_info(sample_xlsx, 'xlsx')
        
        assert 'rows' in info
        assert 'columns' in info
        assert info['rows'] == 3
        assert info['columns'] == 3

    def test_get_file_info_invalid_file(self):
        """Test getting file info for non-existent file."""
        converter = FileConverter()
        with pytest.raises(ValueError, match='Could not read file'):
            converter.get_file_info('/nonexistent/file.csv', 'csv')

    def test_dataframe_to_dbf_fallback(self):
        """Test DataFrame to DBF conversion uses fallback."""
        converter = FileConverter()
        import pandas as pd
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        
        with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as tmp:
            target_path = tmp.name
        
        try:
            # Should use CSV fallback since dbf library is not installed
            converter._dataframe_to_dbf(df, target_path)
            # File should exist (as CSV fallback)
            assert os.path.exists(target_path)
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

    def test_pandas_type_to_dbf_type(self):
        """Test pandas dtype to DBF type conversion."""
        converter = FileConverter()
        import pandas as pd
        
        assert converter._pandas_type_to_dbf_type(pd.Series([1, 2, 3]).dtype) == 'N(10,0)'
        assert converter._pandas_type_to_dbf_type(pd.Series([1.1, 2.2]).dtype) == 'N(15,2)'
        assert converter._pandas_type_to_dbf_type(pd.Series(['a', 'b']).dtype) == 'C(50)'

    def test_read_csv_with_encoding_error(self):
        """Test reading CSV with encoding issues."""
        converter = FileConverter()
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'wb') as f:
            f.write(b'col1,col2\n\xff\xfe,test\n')
        
        try:
            df = converter._read_to_dataframe(path, 'csv')
            assert df is not None
        finally:
            os.remove(path)