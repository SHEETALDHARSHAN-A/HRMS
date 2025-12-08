import pytest
import os
from unittest.mock import patch


def test_connection_manager_testing_env():
    """Test TESTING environment branch in connection_manager - covers lines 26-29"""
    # Mock os.getenv to return True for TESTING
    with patch.dict(os.environ, {'TESTING': '1'}):
        # Need to reload the module to trigger the if block
        import importlib
        import app.db.connection_manager as cm
        importlib.reload(cm)
        
        # Verify that _DummyBase is used when TESTING is set
        assert hasattr(cm, 'Base')
        # The Base should be _DummyBase when TESTING=1
        assert cm.Base.__name__ == '_DummyBase' or not hasattr(cm.Base, 'metadata')


def test_connection_manager_normal_env():
    """Test normal environment (no TESTING) uses declarative_base"""
    # Mock os.getenv to return None for TESTING
    with patch.dict(os.environ, {}, clear=True):
        # Remove TESTING if it exists
        if 'TESTING' in os.environ:
            del os.environ['TESTING']
        
        # Reload the module
        import importlib
        import app.db.connection_manager as cm
        importlib.reload(cm)
        
        # Verify that declarative_base is used when TESTING is not set
        assert hasattr(cm, 'Base')
        # In normal mode, Base should have metadata (from declarative_base)
        assert hasattr(cm.Base, 'metadata') or cm.Base.__name__ != '_DummyBase'


@pytest.mark.asyncio
async def test_get_db():
    """Test get_db function"""
    import app.db.connection_manager as cm
    
    # Test that get_db yields a session
    async for db in cm.get_db():
        assert db is not None
        # Should be an AsyncSession or have commit/rollback methods
        assert hasattr(db, 'commit') or hasattr(db, 'close')
        break  # Only test the first yield


@pytest.mark.asyncio
async def test_init_db():
    """Test init_db function - covers lines 38-39"""
    import app.db.connection_manager as cm
    from unittest.mock import AsyncMock, patch, MagicMock
    
    # Create a mock engine with a working begin context manager
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()
    
    # Set up the async context manager for begin
    mock_begin_context = MagicMock()
    mock_begin_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin_context.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_begin_context
    
    # Patch the engine at module level
    with patch.object(cm, 'engine', mock_engine):
        # Call init_db
        await cm.init_db()
        
        # Verify that engine.begin was called
        mock_engine.begin.assert_called_once()
        # Verify that run_sync was called
        mock_conn.run_sync.assert_called_once()


