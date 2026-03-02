import pytest
from unittest.mock import patch, MagicMock
from src.api.models import (
    init_db,
    save_initial_upload,
    update_resize_status,
    get_metadata,
)


@patch("src.api.models.sqlite3.connect")
class TestModels:

    def _setup_mock(self, mock_connect):
        """Helper to set up the context manager mock."""
        mock_conn = MagicMock()
        # This is the critical fix: ensures 'with get_db() as conn' works
        mock_conn.__enter__.return_value = mock_conn
        mock_connect.return_value = mock_conn
        return mock_conn

    # 1. Test init_db SQL
    def test_init_db_creates_table(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        init_db()

        # Verify execute was called on the mock_conn returned by __enter__
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS images" in call_args

    # 2. Test initial save SQL
    def test_save_initial_upload_query(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        save_initial_upload("id-123", "/path/orig.jpg")

        mock_conn.execute.assert_called_once_with(
            "INSERT INTO images (id, original_path, status) VALUES (?, ?, ?)",
            ("id-123", "/path/orig.jpg", "processing"),
        )

    # 3. Test full update SQL mapping
    def test_update_resize_status_query(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        update_resize_status("uuid", "thumb.png", 128, 128, "small")

        expected_params = ("thumb.png", 128, 128, "small", "uuid")
        # Checking that the params tuple order matches the UPDATE placeholders
        assert mock_conn.execute.call_args[0][1] == expected_params

    # 4. Test the trailing comma fix for single-argument queries
    def test_get_metadata_tuple_structure(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        get_metadata("test-id")

        # Verify it passed ("test-id",) NOT "test-id"
        params = mock_conn.execute.call_args[0][1]
        assert isinstance(params, tuple)
        assert params == ("test-id",)

    # 5. Test dictionary return (Row Factory)
    def test_get_metadata_returns_dict(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        mock_conn.execute.return_value.fetchone.return_value = {
            "id": "123",
            "status": "ok",
        }

        result = get_metadata("123")
        assert result["id"] == "123"
        assert isinstance(result, dict)

    # 6. Test missing record behavior
    def test_get_metadata_none_handling(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        mock_conn.execute.return_value.fetchone.return_value = None

        assert get_metadata("fake") is None

    # 7. Test DB connection parameters
    def test_db_connection_settings(self, mock_connect):
        from src.api.models import get_db

        self._setup_mock(mock_connect)
        get_db()
        mock_connect.assert_called_with("images.db", check_same_thread=False)

    # 8. Test commit trigger on update
    def test_update_calls_commit(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        update_resize_status("id", "p", 1, 1, "s")
        assert mock_conn.commit.called

    # 9. Test SQL Injection resistance via tuple
    def test_sql_injection_safety(self, mock_connect):
        mock_conn = self._setup_mock(mock_connect)
        malicious = "1; DROP TABLE images;"
        get_metadata(malicious)
        assert mock_conn.execute.call_args[0][1] == (malicious,)

    # 10. Test row_factory configuration
    def test_row_factory_is_sqlite_row(self, mock_connect):
        from src.api.models import get_db, sqlite3

        mock_conn = self._setup_mock(mock_connect)
        get_db()
        assert mock_conn.row_factory == sqlite3.Row
