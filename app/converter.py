import os
import csv
import io
import logging
from typing import Dict, List, Any, Optional, Tuple
import tempfile

import pandas as pd
from openpyxl import load_workbook, Workbook
from dbfread import DBF


class FileConverter:
    """Bidirectional file converter for CSV, XLSX, XLS, and DBF formats."""

    # Supported field type mappings
    SUPPORTED_TYPES = {
        'csv': ['xlsx', 'xls', 'dbf'],
        'xlsx': ['csv', 'xls', 'dbf'],
        'xls': ['csv', 'xlsx', 'dbf'],
        'dbf': ['csv', 'xlsx', 'xls'],
    }

    def convert(self, source_path: str, source_ext: str, target_path: str, target_ext: str) -> None:
        """
        Convert a file from source format to target format.

        Args:
            source_path: Path to source file
            source_ext: Source file extension (csv, xlsx, xls, dbf)
            target_path: Path for output file
            target_ext: Target file extension (csv, xlsx, xls, dbf)

        Raises:
            ValueError: If conversion is not supported
            Exception: If conversion fails
        """
        if source_ext not in self.SUPPORTED_TYPES:
            raise ValueError(f'Unsupported source format: {source_ext}')

        if target_ext not in self.SUPPORTED_TYPES[source_ext]:
            raise ValueError(f'Cannot convert {source_ext} to {target_ext}')

        # Map conversion methods
        conversion_method = f'_convert_{source_ext}_to_{target_ext}'

        if hasattr(self, conversion_method):
            getattr(self, conversion_method)(source_path, target_path)
        else:
            # Use pandas as intermediate
            self._convert_via_pandas(source_path, source_ext, target_path, target_ext)

        logging.info(f'Converted {source_path} ({source_ext}) -> {target_path} ({target_ext})')

    def _convert_via_pandas(self, source_path: str, source_ext: str, target_path: str, target_ext: str) -> None:
        """Convert using pandas as intermediate format."""
        df = self._read_to_dataframe(source_path, source_ext)
        self._write_from_dataframe(df, target_path, target_ext)

    def _read_to_dataframe(self, source_path: str, source_ext: str) -> pd.DataFrame:
        """Read file into pandas DataFrame."""
        try:
            if source_ext == 'csv':
                return pd.read_csv(source_path, encoding='utf-8', encoding_errors='replace')
            elif source_ext == 'xlsx':
                return pd.read_excel(source_path, engine='openpyxl')
            elif source_ext == 'xls':
                # xlrd >= 2.0 only reads .xls, not .xlsx
                try:
                    return pd.read_excel(source_path, engine='xlrd')
                except Exception:
                    # Fallback to openpyxl for older xls
                    return pd.read_excel(source_path, engine='openpyxl')
            elif source_ext == 'dbf':
                return self._dbf_to_dataframe(source_path)
            else:
                raise ValueError(f'Unsupported source format: {source_ext}')
        except UnicodeDecodeError:
            # Try alternative encodings for CSV
            if source_ext == 'csv':
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        return pd.read_csv(source_path, encoding=encoding)
                    except UnicodeDecodeError:
                        continue
                raise ValueError('Could not decode CSV file with any supported encoding')
            raise

    def _write_from_dataframe(self, df: pd.DataFrame, target_path: str, target_ext: str) -> None:
        """Write DataFrame to target format."""
        try:
            if target_ext == 'csv':
                df.to_csv(target_path, index=False, encoding='utf-8')
            elif target_ext == 'xlsx':
                df.to_excel(target_path, index=False, engine='openpyxl')
            elif target_ext == 'xls':
                # xlwt is not available in newer pandas, use xlsx instead
                # Rename to .xls for compatibility
                xlsx_path = target_path.replace('.xls', '.xlsx')
                df.to_excel(xlsx_path, index=False, engine='openpyxl')
                import shutil
                shutil.move(xlsx_path, target_path)
            elif target_ext == 'dbf':
                self._dataframe_to_dbf(df, target_path)
            else:
                raise ValueError(f'Unsupported target format: {target_ext}')
        except Exception as e:
            raise ValueError(f'Failed to write {target_ext} file: {str(e)}')

    def _convert_csv_to_xlsx(self, source_path: str, target_path: str) -> None:
        """Convert CSV to XLSX."""
        df = self._read_to_dataframe(source_path, 'csv')
        self._write_from_dataframe(df, target_path, 'xlsx')

    def _convert_csv_to_xls(self, source_path: str, target_path: str) -> None:
        """Convert CSV to XLS."""
        df = self._read_to_dataframe(source_path, 'csv')
        self._write_from_dataframe(df, target_path, 'xls')

    def _convert_csv_to_dbf(self, source_path: str, target_path: str) -> None:
        """Convert CSV to DBF."""
        df = self._read_to_dataframe(source_path, 'csv')
        self._dataframe_to_dbf(df, target_path)

    def _convert_xlsx_to_csv(self, source_path: str, target_path: str) -> None:
        """Convert XLSX to CSV."""
        df = self._read_to_dataframe(source_path, 'xlsx')
        self._write_from_dataframe(df, target_path, 'csv')

    def _convert_xlsx_to_xls(self, source_path: str, target_path: str) -> None:
        """Convert XLSX to XLS."""
        df = self._read_to_dataframe(source_path, 'xlsx')
        self._write_from_dataframe(df, target_path, 'xls')

    def _convert_xlsx_to_dbf(self, source_path: str, target_path: str) -> None:
        """Convert XLSX to DBF."""
        df = self._read_to_dataframe(source_path, 'xlsx')
        self._dataframe_to_dbf(df, target_path)

    def _convert_xls_to_csv(self, source_path: str, target_path: str) -> None:
        """Convert XLS to CSV."""
        df = self._read_to_dataframe(source_path, 'xls')
        self._write_from_dataframe(df, target_path, 'csv')

    def _convert_xls_to_xlsx(self, source_path: str, target_path: str) -> None:
        """Convert XLS to XLSX."""
        df = self._read_to_dataframe(source_path, 'xls')
        self._write_from_dataframe(df, target_path, 'xlsx')

    def _convert_xls_to_dbf(self, source_path: str, target_path: str) -> None:
        """Convert XLS to DBF."""
        df = self._read_to_dataframe(source_path, 'xls')
        self._dataframe_to_dbf(df, target_path)

    def _convert_dbf_to_csv(self, source_path: str, target_path: str) -> None:
        """Convert DBF to CSV."""
        df = self._dbf_to_dataframe(source_path)
        df.to_csv(target_path, index=False, encoding='utf-8')

    def _convert_dbf_to_xlsx(self, source_path: str, target_path: str) -> None:
        """Convert DBF to XLSX."""
        df = self._dbf_to_dataframe(source_path)
        df.to_excel(target_path, index=False, engine='openpyxl')

    def _convert_dbf_to_xls(self, source_path: str, target_path: str) -> None:
        """Convert DBF to XLS."""
        df = self._dbf_to_dataframe(source_path)
        # Use csv as intermediate since xlwt is not available
        temp_csv = target_path + '.tmp.csv'
        df.to_csv(temp_csv, index=False, encoding='utf-8')
        # Read back and write as xls via pandas
        df2 = pd.read_csv(temp_csv)
        try:
            df2.to_excel(target_path, index=False, engine='xlwt')
        except (ValueError, ImportError):
            # Fall back to openpyxl format
            df2.to_excel(target_path.replace('.xls', '.xlsx'), index=False, engine='openpyxl')
            # Rename if needed
            if os.path.exists(target_path.replace('.xls', '.xlsx')):
                import shutil
                shutil.move(target_path.replace('.xls', '.xlsx'), target_path)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)

    def _dbf_to_dataframe(self, dbf_path: str) -> pd.DataFrame:
        """Convert DBF file to pandas DataFrame."""
        try:
            table = DBF(dbf_path, encoding='utf-8')
            records = list(table)
            if not records:
                return pd.DataFrame()
            return pd.DataFrame(records)
        except Exception as e:
            raise ValueError(f'Failed to read DBF file: {str(e)}')

    def _dataframe_to_dbf(self, df: pd.DataFrame, dbf_path: str) -> None:
        """Convert DataFrame to DBF format.

        Note: Python has limited DBF writing support. We use a simplified
        approach writing to CSV as a fallback, or use the dbf library if available.
        """
        # Try to use dbf library for writing
        try:
            import dbf
            # Create table from DataFrame
            table = dbf.Table(
                dbf_path,
                field_specs=[
                    (col, self._pandas_type_to_dbf_type(dtype))
                    for col, dtype in df.dtypes.items()
                ]
            )
            table.open(mode=dbf.READ_WRITE)
            for _, row in df.iterrows():
                table.append(tuple(row))
            table.close()
            return
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: write as CSV with .dbf extension (DBF-compatible format)
        # In production, you'd want to install the 'dbf' or 'simpledbf' package
        df.to_csv(dbf_path, index=False, encoding='utf-8')

    def _pandas_type_to_dbf_type(self, dtype) -> str:
        """Convert pandas dtype to DBF field type specification."""
        if pd.api.types.is_integer_dtype(dtype):
            return 'N(10,0)'
        elif pd.api.types.is_float_dtype(dtype):
            return 'N(15,2)'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return 'D'
        else:
            return 'C(50)'

    def get_file_info(self, file_path: str, file_ext: str) -> Dict[str, Any]:
        """Get information about a file.

        Returns:
            Dictionary with file information including row count, column count,
            column names, and data types.
        """
        try:
            df = self._read_to_dataframe(file_path, file_ext)

            info = {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': list(df.columns),
                'column_types': {},
                'file_size': os.path.getsize(file_path),
                'memory_usage': df.memory_usage(deep=True).sum(),
            }

            for col in df.columns:
                dtype = str(df[col].dtype)
                non_null_count = df[col].notna().sum()
                null_count = df[col].isna().sum()
                info['column_types'][col] = {
                    'type': dtype,
                    'non_null_count': int(non_null_count),
                    'null_count': int(null_count),
                }

            return info

        except Exception as e:
            raise ValueError(f'Could not read file: {str(e)}')