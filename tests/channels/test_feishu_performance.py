"""Performance tests for Feishu file upload progress tracking."""

import asyncio
import os
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.feishu import FeishuChannel


class TestFeishuChannelPerformance:
    """Performance test suite for FeishuChannel with progress tracking."""

    @pytest.mark.asyncio
    async def test_large_file_upload_performance(self):
        """Test performance of large file upload with progress tracking."""
        # Create a 100MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
            f.write(b"test content" * 1024 * 1024 * 100)  # 100MB
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
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Record start time
            start_time = time.time()
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Record end time
            end_time = time.time()
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify upload time is reasonable
            upload_time = end_time - start_time
            assert upload_time < 60  # Should complete in under 60 seconds
            
            # Verify progress messages were sent
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_multiple_large_files_upload_performance(self):
        """Test performance of uploading multiple large files."""
        # Create test files
        file_paths = []
        try:
            # Create 3 large files (50MB each)
            for i in range(3):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
                    f.write(b"test content" * 1024 * 1024 * 50)  # 50MB
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
            
            # Record start time
            start_time = time.time()
            
            # Upload all files
            results = []
            for file_path in file_paths:
                result = await channel.upload_with_progress("test_chat_id", file_path)
                results.append(result)
            
            # Record end time
            end_time = time.time()
            
            # Verify all uploads succeeded
            assert all(r == "file_key_123" for r in results)
            
            # Verify total time is reasonable
            total_time = end_time - start_time
            assert total_time < 180  # Should complete in under 3 minutes
            
            # Verify progress messages for each file
            for i, file_path in enumerate(file_paths):
                # Count progress messages for this file
                progress_messages = [m for m in sent_messages if "上传中:" in m]
                assert len(progress_messages) >= 5  # At least 5 progress updates per file
            
            # Verify completion messages
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 3  # One completion message per file
            
        finally:
            # Clean up
            for file_path in file_paths:
                try:
                    os.unlink(file_path)
                except:
                    pass

    @pytest.mark.asyncio
    async def test_file_upload_memory_usage(self):
        """Test memory usage during file upload with progress tracking."""
        # Create a 50MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test content" * 1024 * 1024 * 50)  # 50MB
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
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Record initial memory usage
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Record final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify memory usage increase is reasonable
            memory_increase = final_memory - initial_memory
            assert memory_increase < 100  # Should not increase by more than 100MB
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_cpu_usage(self):
        """Test CPU usage during file upload with progress tracking."""
        # Create a 20MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"test content" * 1024 * 1024 * 20)  # 20MB
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
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Record initial CPU usage
            import psutil
            process = psutil.Process()
            initial_cpu = process.cpu_percent(interval=0.1)
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Record final CPU usage
            final_cpu = process.cpu_percent(interval=0.1)
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify CPU usage is reasonable
            assert final_cpu < 90  # Should not exceed 90% CPU usage
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_throughput(self):
        """Test file upload throughput with progress tracking."""
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
                            await asyncio.sleep(0.1)  # Simulate upload delay
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Record start time
            start_time = time.time()
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Record end time
            end_time = time.time()
            
            # Verify result
            assert result == "file_key_123"
            
            # Calculate throughput
            upload_time = end_time - start_time
            file_size = os.path.getsize(file_path)
            throughput = file_size / upload_time / 1024 / 1024  # MB/s
            
            # Verify throughput is reasonable
            assert throughput > 0.1  # Should be at least 0.1 MB/s
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_concurrent_users(self):
        """Test file upload performance with concurrent users."""
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
            
            # Record start time
            start_time = time.time()
            
            # Simulate concurrent uploads
            chat_ids = [f"chat_id_{i}" for i in range(10)]
            tasks = []
            
            for chat_id in chat_ids:
                task = channel.upload_with_progress(chat_id, file_path)
                tasks.append(task)
            
            # Wait for all uploads to complete
            results = await asyncio.gather(*tasks)
            
            # Record end time
            end_time = time.time()
            
            # Verify all uploads succeeded
            assert all(r == "file_key_123" for r in results)
            
            # Verify total time is reasonable
            total_time = end_time - start_time
            assert total_time < 30  # Should complete in under 30 seconds
            
            # Verify progress messages for each user
            for chat_id in chat_ids:
                # Count progress messages for this user
                progress_messages = [m for m in sent_messages if m[0] == chat_id and "上传中:" in m[1]]
                assert len(progress_messages) >= 5  # At least 5 progress updates per user
            
            # Verify completion messages
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m[1]]
            assert len(completion_messages) == 10  # One completion message per user
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_network_latency(self):
        """Test file upload performance with simulated network latency."""
        # Create a 5MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
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
            
            # Mock the send methods
            sent_messages = []
            
            async def mock_send_message(chat_id, message):
                sent_messages.append(message)
            
            channel.send_message = mock_send_message
            
            # Mock the upload method with network latency
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
                            await asyncio.sleep(0.5)  # Simulate network latency
                return "file_key_123"
            
            channel._upload_file_sync = mock_upload_file_sync
            
            # Record start time
            start_time = time.time()
            
            # Call upload method
            result = await channel.upload_with_progress("test_chat_id", file_path)
            
            # Record end time
            end_time = time.time()
            
            # Verify result
            assert result == "file_key_123"
            
            # Verify upload time is reasonable given latency
            upload_time = end_time - start_time
            assert upload_time < 60  # Should complete in under 60 seconds despite latency
            
            # Verify progress messages
            progress_messages = [m for m in sent_messages if "上传中:" in m]
            assert len(progress_messages) >= 5  # At least 5 progress updates
            
            # Verify completion message
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m]
            assert len(completion_messages) == 1
            
        finally:
            os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_file_upload_with_high_concurrency(self):
        """Test file upload performance with high concurrency."""
        # Create a 1MB test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
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
            
            # Record start time
            start_time = time.time()
            
            # Simulate high concurrency
            chat_ids = [f"chat_id_{i}" for i in range(20)]
            tasks = []
            
            for chat_id in chat_ids:
                task = channel.upload_with_progress(chat_id, file_path)
                tasks.append(task)
            
            # Wait for all uploads to complete
            results = await asyncio.gather(*tasks)
            
            # Record end time
            end_time = time.time()
            
            # Verify all uploads succeeded
            assert all(r == "file_key_123" for r in results)
            
            # Verify total time is reasonable
            total_time = end_time - start_time
            assert total_time < 60  # Should complete in under 60 seconds
            
            # Verify progress messages for each user
            for chat_id in chat_ids:
                # Count progress messages for this user
                progress_messages = [m for m in sent_messages if m[0] == chat_id and "上传中:" in m[1]]
                assert len(progress_messages) >= 3  # At least 3 progress updates per user
            
            # Verify completion messages
            completion_messages = [m for m in sent_messages if "✅ 文件上传完成" in m[1]]
            assert len(completion_messages) == 20  # One completion message per user
            
        finally:
            os.unlink(file_path)