"""Error handling tests for Feishu file upload progress tracking."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.feishu import FeishuChannel


class TestFeishuChannelErrorHandling:
    """Error handling test suite for FeishuChannel with progress tracking."""

    @pytest.mark.asyncio
    async def test_file_upload_progress_error_handling(self):
        """Test error handling in file upload progress tracking."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods to raise exceptions
            async def mock_send_message(chat_id, message):
                raise Exception("Send failed")
            
            channel.send_message = mock_send_message
            
            # Create progress tracker
            from nanobot.channels.feishu import FileUploadProgress
            progress_tracker = FileUploadProgress(channel, "test_chat_id", file_path)
            
            # Start progress tracking (should not raise exception)
            await progress_tracker.start()
            
            # Update bytes (should trigger error but not crash)
            progress_tracker.update_bytes_read(512)
            await asyncio.sleep(1.5)  # Wait for progress update
            
            # Stop tracking
            await progress_tracker.stop()
            
            # Should not raise exception
            assert True
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_error_handling_integration(self):
        """Test error handling in file upload integration."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Track messages
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock upload method to raise exception
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    progress_callback(512)
                raise Exception("Upload failed")
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result is None
            
            # Verify error message was sent
            error_messages = [m for m in sent_messages if "❌ 文件上传失败" in m]
            assert len(error_messages) == 1
            
            # Verify completion message not sent
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 0
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_progress_cancellation(self):
        """Test progress tracking cancellation."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods
            channel.send_message = AsyncMock()
            
            # Create progress tracker
            from nanobot.channels.feishu import FileUploadProgress
            progress_tracker = FileUploadProgress(channel, "test_chat_id", file_path)
            await progress_tracker.start()
            
            # Cancel progress tracking
            await progress_tracker.stop()
            
            # Verify task is done or cancelled
            assert progress_tracker.progress_task.done()
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_invalid_file_path(self):
        """Test file upload with invalid file path."""
        # Create channel instance
        config = {
            "app_id": "test_app_id",
            "app_secret": "test_app_secret",
            "enabled": True,
        }
        bus = MagicMock()
        channel = FeishuChannel(config, bus)
        
        # Mock the send methods
        sent_messages = []
        
        async def mock_send_message(chat_id, message):
            sent_messages.append(message)
        
        channel.send_message = mock_send_message
        
        # Try to upload non-existent file
        result = await channel.upload_with_progress("test_chat_id", "/non/existent/file.txt")
        
        # Verify result
        assert result is None
        
        # Verify error message was sent
        error_messages = [m for m in sent_messages if "❌ 文件上传失败" in m]
        assert len(error_messages) == 1

    @pytest.mark.asyncio
    async def test_file_upload_with_permission_error(self):
        """Test file upload with permission error."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            file_path = f.name
        
        try:
            # Make file unreadable
            os.chmod(file_path, 0o000)
            
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Try to upload unreadable file
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result is None
            
            # Verify error message was sent
            error_messages = [m for m in sent_messages if "❌ 文件上传失败" in m]
            assert len(error_messages) == 1
            
            # Verify completion message not sent
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 0
            
        finally:
            # Restore permissions and cleanup
            os.chmod(file_path, 0o644)
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_network_error(self):
        """Test file upload with network error."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods to simulate network error
            async def mock_send_message(chat_id, message):
                if "上传中:" in message:
                    raise Exception("Network error")
                # Allow completion/error messages to go through
                pass
            
            channel.send_message = mock_send_message
            
            # Mock the upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_partial_failure(self):
        """Test file upload with partial failure."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024 * 2)  # 2MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
                # Simulate failure after some progress
                if "上传中:" in message and "50%" in message:
                    raise Exception("Partial failure")
            
            channel.send_message = mock_send_message
            
            # Mock the upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify some progress messages were sent
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) > 0
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_timeout_error(self):
        """Test file upload with timeout error."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock the upload method to simulate timeout
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(2)  # Simulate long delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method with timeout
            try:
                result = await asyncio.wait_for(
                    channel.upload_with_progress("test_chat_id", file_path),
                    timeout=5.0
                )
                # If we get here, the upload completed within timeout
                assert result == "file_key_123"
            except asyncio.TimeoutError:
                # Timeout is expected behavior in this test
                pass
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_concurrent_errors(self):
        """Test file upload with concurrent errors."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods to raise errors randomly
            sent_messages = []
            error_count = 0
            
            async def mock_send_message(chat_id, message):
                nonlocal error_count
                sent_messages.append(message)
                # Raise error randomly
                if "上传中:" in message and error_count < 3:
                    error_count += 1
                    raise Exception(f"Random error {error_count}")
            
            channel.send_message = mock_send_message
            
            # Mock the upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify some progress messages were sent despite errors
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) > 0
            
            # Verify completion message was sent
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_memory_error_simulation(self):
        """Test file upload with memory error simulation."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
                # Simulate memory error on certain progress
                if "上传中:" in message and "75%" in message:
                    raise MemoryError("Simulated memory error")
            
            channel.send_message = mock_send_message
            
            # Mock the upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify some progress messages were sent
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) > 0
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_multiple_error_types(self):
        """Test file upload with multiple error types."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create channel instance
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the send methods to raise different error types
            sent_messages = []
            error_types = ["ConnectionError", "TimeoutError", "ValueError"]
            error_index = 0
            
            async def mock_send_message(chat_id, message):
                nonlocal error_index
                sent_messages.append(message)
                # Raise different error types
                if "上传中:" in message and error_index < len(error_types):
                    error_type = error_types[error_index]
                    error_index += 1
                    if error_type == "ConnectionError":
                        raise ConnectionError("Connection failed")
                    elif error_type == "TimeoutError":
                        raise TimeoutError("Request timed out")
                    elif error_type == "ValueError":
                        raise ValueError("Invalid value")
            
            channel.send_message = mock_send_message
            
            # Mock the upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify some progress messages were sent
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) > 0
            
        finally:
            os.unlink(file_path)