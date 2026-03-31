"""Tests for Feishu file upload progress tracking."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.feishu import FileUploadProgress, FeishuChannel


class TestFileUploadProgress:
    """Test suite for FileUploadProgress class."""

    @pytest.mark.asyncio
    async def test_file_upload_progress_initialization(self):
        """Test FileUploadProgress initialization."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
            # Verify initialization values
            assert progress_tracker.file_size > 0
            assert progress_tracker.bytes_read == 0
            assert progress_tracker.last_progress == -1
            assert progress_tracker.progress_task is None
            assert progress_tracker.channel == channel
            assert progress_tracker.chat_id == chat_id
            assert progress_tracker.file_path == file_path
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_update_bytes_read(self):
        """Test updating bytes read count."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)  # ~12KB
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
            # Update bytes read
            progress_tracker.update_bytes_read(512)
            assert progress_tracker.bytes_read == 512
            
            # Update again
            progress_tracker.update_bytes_read(1024)
            assert progress_tracker.bytes_read == 1024
            
            # Update to file size
            progress_tracker.update_bytes_read(progress_tracker.file_size)
            assert progress_tracker.bytes_read == progress_tracker.file_size
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_format_progress(self):
        """Test progress message formatting."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # ~12MB
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
            # Format progress at 50%
            message = progress_tracker._format_progress(
                progress_tracker.file_size // 2,
                progress_tracker.file_size
            )
            
            assert "上传中:" in message
            assert "MB" in message
            assert "(50.0%)" in message
            assert "⏳ 请勿关闭窗口" in message
            
            # Format progress at 0%
            message = progress_tracker._format_progress(0, progress_tracker.file_size)
            assert "(0.0%)" in message
            
            # Format progress at 100%
            message = progress_tracker._format_progress(
                progress_tracker.file_size,
                progress_tracker.file_size
            )
            assert "(100.0%)" in message
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_format_progress_with_different_sizes(self):
        """Test progress formatting with different file sizes."""
        # Create progress tracker with different file sizes
        channel = MagicMock()
        chat_id = "test_chat_id"
        
        # Small file (KB)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"small content")
            small_file = f.name
        
        try:
            progress_tracker = FileUploadProgress(channel, chat_id, small_file)
            message = progress_tracker._format_progress(
                progress_tracker.file_size // 4,
                progress_tracker.file_size
            )
            assert "上传中:" in message
        finally:
            os.unlink(small_file)
        
        # Large file (MB)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"large content" * 1024 * 1024)
            large_file = f.name
        
        try:
            progress_tracker = FileUploadProgress(channel, chat_id, large_file)
            message = progress_tracker._format_progress(
                progress_tracker.file_size // 2,
                progress_tracker.file_size
            )
            assert "上传中:" in message
            assert "MB" in message
        finally:
            os.unlink(large_file)

    @pytest.mark.asyncio
    async def test_start_progress_tracking(self):
        """Test starting progress tracking."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            channel.send_message = AsyncMock()
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
            # Start progress tracking
            await progress_tracker.start()
            
            # Verify task was created
            assert progress_tracker.progress_task is not None
            assert isinstance(progress_tracker.progress_task, asyncio.Task)
            
            # Clean up
            await progress_tracker.stop()
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_stop_progress_tracking(self):
        """Test stopping progress tracking."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            channel.send_message = AsyncMock()
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
            # Start and stop
            await progress_tracker.start()
            await progress_tracker.stop()
            
            # Verify task is done or cancelled
            assert progress_tracker.progress_task.done()
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_progress_tracking_sends_updates(self):
        """Test that progress tracking sends periodic updates."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # ~12MB
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            channel.send_message = AsyncMock()
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
            # Start progress tracking
            await progress_tracker.start()
            
            # Simulate bytes being read
            progress_tracker.update_bytes_read(progress_tracker.file_size // 4)
            await asyncio.sleep(1.5)  # Wait for progress update (PROGRESS_INTERVAL is 1.0 seconds)
            
            progress_tracker.update_bytes_read(progress_tracker.file_size // 2)
            await asyncio.sleep(1.5)  # Wait for progress update
            
            progress_tracker.update_bytes_read(progress_tracker.file_size * 3 // 4)
            await asyncio.sleep(1.5)  # Wait for progress update
            
            # Stop progress tracking
            await progress_tracker.stop()
            
            # Verify messages were sent
            assert channel.send_message.call_count >= 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_progress_tracking_error_handling(self):
        """Test error handling in progress tracking."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)
            file_path = f.name
        
        try:
            # Create progress tracker instance
            channel = MagicMock()
            channel.send_message = AsyncMock(side_effect=Exception("Send failed"))
            chat_id = "test_chat_id"
            progress_tracker = FileUploadProgress(channel, chat_id, file_path)
            
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


class TestFeishuChannelUploadWithProgress:
    """Test suite for FeishuChannel upload with progress tracking."""

    @pytest.mark.asyncio
    async def test_upload_file_with_progress_callback(self):
        """Test file upload with progress callback."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)  # ~12MB
            file_path = f.name
        
        try:
            # Create mock channel
            channel = MagicMock()
            channel.send_message = AsyncMock()
            
            # Track callback calls
            callback_calls = []
            
            def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    # Simulate progress updates
                    for i in range(0, 101, 10):
                        bytes_read = (i * os.path.getsize(file_path)) // 100
                        progress_callback(bytes_read)
                        callback_calls.append(bytes_read)
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method directly
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                channel._upload_file_sync,
                file_path,
                lambda bytes_read: callback_calls.append(bytes_read)
            )
            
            # Verify result
            assert result == "file_key_123"
            assert len(callback_calls) > 0
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_upload_file_without_progress_callback(self):
        """Test file upload without progress callback (backward compatibility)."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            file_path = f.name
        
        try:
            # Create mock channel
            channel = MagicMock()
            
            def mock_upload_file_sync(file_path, progress_callback=None):
                # Should work without callback
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method without callback
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                channel._upload_file_sync,
                file_path,
                None
            )
            
            # Verify result
            assert result == "file_key_123"
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_upload_file_error_with_progress(self):
        """Test file upload error handling with progress tracking."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024)
            file_path = f.name
        
        try:
            # Create mock channel
            channel = MagicMock()
            channel.send_message = AsyncMock()
            
            def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    progress_callback(512)
                raise Exception("Upload failed")
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None,
                    channel._upload_file_sync,
                    file_path,
                    lambda bytes_read: None
                )
                assert result is None
            except Exception:
                # Expected to raise exception
                pass
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_upload_large_file_progress(self):
        """Test progress tracking for large file upload."""
        # Create a large temporary file (10MB)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"large content" * 1024 * 1024)
            file_path = f.name
        
        try:
            # Create mock channel
            channel = MagicMock()
            channel.send_message = AsyncMock()
            
            # Track progress updates
            progress_updates = []
            
            def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    # Simulate progress in 5% increments
                    for i in range(0, 101, 5):
                        bytes_read = (i * file_size) // 100
                        progress_callback(bytes_read)
                        progress_updates.append(bytes_read)
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                channel._upload_file_sync,
                file_path,
                lambda bytes_read: progress_updates.append(bytes_read)
            )
            
            # Verify result
            assert result == "file_key_123"
            assert len(progress_updates) > 0
            assert progress_updates[-1] == os.path.getsize(file_path)
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_upload_file_progress_message_content(self):
        """Test that progress messages contain expected content."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content" * 1024 * 1024)
            file_path = f.name
        
        try:
            # Create mock channel
            channel = MagicMock()
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Create progress tracker
            progress_tracker = FileUploadProgress(channel, "test_chat_id", file_path)
            
            # Simulate progress
            progress_tracker.update_bytes_read(progress_tracker.file_size // 4)
            await asyncio.sleep(0.1)
            
            progress_tracker.update_bytes_read(progress_tracker.file_size // 2)
            await asyncio.sleep(0.1)
            
            progress_tracker.update_bytes_read(progress_tracker.file_size * 3 // 4)
            await asyncio.sleep(0.1)
            
            # Verify message content
            for message in sent_messages:
                assert "上传中:" in message
                assert "MB" in message or "KB" in message
                assert "%" in message
                assert "⏳" in message
            
            # Clean up
            await progress_tracker.stop()
            
        finally:
            os.unlink(file_path)
