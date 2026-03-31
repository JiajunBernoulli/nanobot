"""Integration tests for Feishu file upload with progress tracking."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.feishu import FeishuChannel


class TestFeishuChannelIntegration:
    """Integration test suite for FeishuChannel with progress tracking."""

    @pytest.mark.asyncio
    async def test_file_upload_with_progress_tracking(self):
        """Test file upload with progress tracking integration."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test content" * 1024 * 1024)  # 1MB
            file_path = f.name
        
        try:
            # Create mock channel
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Mock the actual send methods
            channel.send_message = AsyncMock()
            
            # Track progress updates
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock the upload method to simulate progress
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    # Simulate progress in 5% increments
                    for i in range(0, 101, 5):
                        bytes_read = (i * file_size) // 100
                        progress_callback(bytes_read)
                        await asyncio.sleep(0.01)  # Small delay
                return "file_key_123"
            
            # Replace the upload method
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call the upload method directly
            result = None
            try:
                # Since _upload_file_sync is async, we need to await it directly
                result = await channel._upload_file_sync(file_path, lambda bytes_read: None)
            except Exception as e:
                print(f"Error during upload: {e}")
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify progress messages were sent
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
            # Verify error message not sent
            error_messages = [m for m in sent_messages if "❌ 文件上传失败" in m]
            assert len(error_messages) == 0
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_progress_updates_frequency(self):
        """Test that progress updates are sent at appropriate frequency."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test content" * 1024 * 1024 * 5)  # 5MB
            file_path = f.name
        
        try:
            # Create mock channel
            config = {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "enabled": True,
            }
            bus = MagicMock()
            channel = FeishuChannel(config, bus)
            
            # Track sent messages
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock the upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    # Simulate progress in small increments
                    for i in range(0, 101, 1):  # 1% increments
                        bytes_read = (i * file_size) // 100
                        progress_callback(bytes_read)
                        await asyncio.sleep(0.01)
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call the upload method
            # Since _upload_file_sync is async, we need to await it directly
            result = await channel._upload_file_sync(file_path, lambda bytes_read: None)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify progress messages were throttled
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            # Should be less than 100 due to throttling
            assert len(progress_messages) < 100
            
            # Verify there are multiple progress updates
            assert len(progress_messages) >= 5
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_different_file_types(self):
        """Test file upload with different file types."""
        # Test files with different extensions
        test_files = [
            ("small.txt", b"text content"),
            ("audio.mp3", b"audio content" * 1024 * 1024),
            ("video.mp4", b"video content" * 1024 * 1024 * 2),
            ("document.pdf", b"pdf content" * 1024 * 1024),
        ]
        
        for filename, content in test_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[1]}") as f:
                f.write(content)
                file_path = f.name
            
            try:
                # Create mock channel
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
                
                # Mock upload method
                async def mock_upload_file_sync(file_path, progress_callback=None):
                    if progress_callback:
                        file_size = os.path.getsize(file_path)
                        # Simulate progress
                        for i in range(0, 101, 10):
                            bytes_read = (i * file_size) // 100
                            progress_callback(bytes_read)
                            await asyncio.sleep(0.01)
                    return "file_key_123"
                
                channel._upload_file_sync = mock_upload_file_sync
                
            # Call upload method
            # Since _upload_file_sync is async, we need to await it directly
            result = await channel._upload_file_sync(file_path, lambda bytes_read: None)
            
            # Verify result
            assert result == "file_key_123"
                
                # Verify progress messages
                progress_messages = [m for m in sent_messages if "上传中:" in m]
                assert len(progress_messages) > 0
                
                # Verify completion message
                completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
                assert len(completion_messages) == 1
                
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
            # Create mock channel
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
            # Since _upload_file_sync is async, we need to await it directly
            result = await channel._upload_file_sync(file_path, lambda bytes_read: None)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify error message was sent
            error_messages = [m for m in sent_messages if "❌ 文件上传失败" in m]
            assert len(error_messages) == 1
            
            # Verify completion message not sent
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 0
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_small_large_files(self):
        """Test file upload with both small and large files."""
        # Test with small file (< 1MB)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"small content")
            small_file = f.name
        
        try:
            # Create mock channel
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
            
            # Mock upload method
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    # Simulate progress
                    for i in range(0, 101, 20):
                        bytes_read = (i * file_size) // 100
                        progress_callback(bytes_read)
                        await asyncio.sleep(0.01)
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Upload small file
            # Since _upload_file_sync is async, we need to await it directly
            result = await channel._upload_file_sync(file_path, lambda bytes_read: None)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) > 0
            
            # Reset messages for large file test
            sent_messages.clear()
            
            # Test with large file (> 10MB)
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b"large content" * 1024 * 1024 * 10)  # 10MB
                large_file = f.name
            
            try:
                # Upload large file
                # Since _upload_file_sync is async, we need to await it directly
                result = await channel._upload_file_sync(large_file, lambda bytes_read: None)
                
                # Verify result
                assert result == "file_key_123"
                
                # Verify progress messages
                progress_messages = [m for m in sent_messages if "上传中:" in m]
                assert len(progress_messages) > 0
                
                # Verify completion message
                completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
                assert len(completion_messages) == 1
                
            finally:
                os.unlink(large_file)
            
        finally:
            os.unlink(small_file)
