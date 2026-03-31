"""End-to-end tests for Feishu file upload progress tracking."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.feishu import FeishuChannel


class TestFeishuChannelE2E:
    """End-to-end test suite for FeishuChannel with progress tracking."""

    @pytest.mark.asyncio
    async def test_e2e_file_upload_with_progress(self):
        """End-to-end test for file upload with progress tracking."""
        # Create test files of different sizes
        test_files = [
            ("small.txt", b"small content"),
            ("medium.mp3", b"medium content" * 1024 * 1024),  # 1MB
            ("large.mp4", b"large content" * 1024 * 1024 * 5),  # 5MB
        ]
        
        for filename, content in test_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[1]}") as f:
                f.write(content)
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
                
                # Mock the actual send methods
                channel.send_message = AsyncMock()
                
                # Mock the upload method to simulate real behavior
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
                
                # Replace the upload method
                channel._upload_file_sync = mock_upload_file_sync
                
                # Call the upload method
                result = await channel.upload_with_progress("test_chat_id", file_path)
                
                # Verify result
                assert result == "file_key_123"
                
                # Verify progress messages were sent
                assert channel.send_message.call_count >= 3  # At least 3 calls: progress + completion
                
                # Verify at least one progress message
                progress_sent = False
                for call in channel.send_message.call_args_list:
                    if "上传中:" in call[1][1]:
                        progress_sent = True
                        break
                assert progress_sent
                
                # Verify completion message
                completion_sent = False
                for call in channel.send_message.call_args_list:
                    if "✅ 文件上传完成" in call[1][1]:
                        completion_sent = True
                        break
                assert completion_sent
                
            finally:
                os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_updates(self):
        """Test that progress updates are sent during actual file upload."""
        # Create a 2MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
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
            
            # Track sent messages
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
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
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 2  # At least 2 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_real_file(self):
        """Test file upload progress with real file."""
        # Create a real test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as f:
            # Write a 3MB file
            content = b"test content" * 1024 * 1024 * 3
            f.write(content)
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
            
            # Track sent messages
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
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
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 3  # At least 3 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_real_file_and_realistic_speed(self):
        """Test file upload progress with realistic upload speed."""
        # Create a 5MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"test content" * 1024 * 1024 * 5)  # 5MB
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
            
            # Track sent messages
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock the upload method with realistic speed
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
                            await asyncio.sleep(0.5)  # Simulate slower upload
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_multiple_files(self):
        """Test file upload progress with multiple files."""
        # Create test files
        file_paths = []
        try:
            # Create small file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
                f.write(b"small content")
                file_paths.append(f.name)
            
            # Create medium file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(b"medium content" * 1024 * 1024)
                file_paths.append(f.name)
            
            # Create large file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
                f.write(b"large content" * 1024 * 1024 * 5)
                file_paths.append(f.name)
            
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
            
            # Upload each file
            for file_path in file_paths:
                result = await channel.upload_with_progress("test_chat_id", file_path)
                
                # Verify result
                assert result == "file_key_123"
                
                # Verify progress messages
                progress_messages = [m for m in sent_messages if "上传中:" in m]
                assert len(progress_messages) >= 1
                
                # Reset messages for next file
                sent_messages.clear()
            
        finally:
            # Clean up
            for file_path in file_paths:
                try:
                    os.unlink(file_path)
                except:
                    pass

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_realistic_file_types(self):
        """Test file upload progress with realistic file types."""
        # Create test files
        file_paths = []
        try:
            # Create document file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as f:
                f.write(b"document content" * 1024 * 1024 * 2)  # 2MB
                file_paths.append(f.name)
            
            # Create audio file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(b"audio content" * 1024 * 1024 * 3)  # 3MB
                file_paths.append(f.name)
            
            # Create video file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
                f.write(b"video content" * 1024 * 1024 * 5)  # 5MB
                file_paths.append(f.name)
            
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
            
            # Upload each file
            for file_path in file_paths:
                result = await channel.upload_with_progress("test_chat_id", file_path)
                
                # Verify result
                assert result == "file_key_123"
                
                # Verify progress messages
                progress_messages = [m for m in sent_messages if "上传中:" in m]
                assert len(progress_messages) >= 3  # At least 3 progress updates
                
                # Verify completion message
                completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
                assert len(completion_messages) == 1
                
                # Reset messages for next file
                sent_messages.clear()
            
        finally:
            # Clean up
            for file_path in file_paths:
                try:
                    os.unlink(file_path)
                except:
                    pass

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_realistic_speed(self):
        """Test file upload progress with realistic upload speed."""
        # Create a 10MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
            f.write(b"test content" * 1024 * 1024 * 10)  # 10MB
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
                            await asyncio.sleep(0.5)  # Simulate slower upload
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_realistic_network_conditions(self):
        """Test file upload progress with simulated network conditions."""
        # Create a 5MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test content" * 1024 * 1024 * 5)  # 5MB
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
            
            # Track sent messages
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock the upload method with simulated network conditions
            async def mock_upload_file_sync(file_path, progress_callback=None):
                if progress_callback:
                    file_size = os.path.getsize(file_path)
                    chunk_size = 1024 * 1024  # 1MB chunks
                    bytes_read = 0
                    
                    with open(file_path, "rb") as f:
                        while True:
                            # Simulate network jitter
                            delay = 0.1 + (os.path.getsize(file_path) / (1024 * 1024 * 10))  # Base delay + file size factor
                            
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            progress_callback(bytes_read)
                            await asyncio.sleep(delay)  # Simulate network delay
                    
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_e2e_file_upload_progress_with_multiple_users(self):
        """Test file upload progress with multiple users."""
        # Create a test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
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
                sent_messages.append((chat_id, message))
            
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
            
            # Simulate uploads for multiple users
            chat_ids = [f"chat_id_{i}" for i in range(5)]
            results = []
            
            for chat_id in chat_ids:
                result = await channel.upload_with_progress(chat_id, file_path)
                results.append(result)
                
            # Verify all uploads succeeded
            assert all(r == "file_key_123" for r in results)
            
            # Verify messages were sent to all users
            for chat_id in chat_ids:
                # Verify progress messages
                progress_messages = [m for m in sent_messages if m[0] == chat_id and "上传中:" in m[1]]
                assert len(progress_messages) >= 3  # At least 3 progress updates
                
                # Verify completion message
                completion_messages = [m for m in sent_messages if m[0] == chat_id and "✅ 文件上传完成" in m[1]]
                assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)