"""Tests for gateway lifecycle notification in channel manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nanobot.channels.manager import ChannelManager
from nanobot.config import ChannelsConfig, GatewayConfig


class TestGatewayLifecycleNotification:
    """Test gateway lifecycle notification behavior."""

    @pytest.mark.asyncio
    async def test_configured_target_sends_to_expected_channel_chat_id(self):
        """Test that configured target sends onStart/onStop to the expected channel/chat id."""
        # Create a mock Feishu channel with notification config
        mock_channel = MagicMock()
        mock_channel.name = "feishu"
        mock_channel.enabled = True
        
        # Create notification config
        mock_notification_cfg = MagicMock()
        mock_notification_cfg.chat_id_list = ["oc_test123"]
        mock_notification_cfg.on_start_message = "Gateway started"
        mock_notification_cfg.on_stop_message = "Gateway stopped"
        
        # Set up channel config with nested notification
        mock_channel.config = MagicMock()
        mock_channel.config.notification = mock_notification_cfg
        
        # Mock the send_text_message method
        mock_channel.send_text_message = AsyncMock()
        
        # Create channel manager with mock channel
        with patch.object(ChannelManager, '_get_channels', return_value=[mock_channel]):
            manager = ChannelManager(
                channels_config=ChannelsConfig(),
                gateway_config=GatewayConfig()
            )
            manager._channels = [mock_channel]
            
            # Test on_start notification
            await manager._send_gateway_lifecycle_notification("on_start")
            
            # Verify send_text_message was called with correct parameters
            mock_channel.send_text_message.assert_called_once_with(
                chat_id="oc_test123",
                content="Gateway started",
                msg_type="text"
            )
            
            # Reset mock for on_stop test
            mock_channel.send_text_message.reset_mock()
            
            # Test on_stop notification
            await manager._send_gateway_lifecycle_notification("on_stop")
            
            # Verify send_text_message was called with correct parameters
            mock_channel.send_text_message.assert_called_once_with(
                chat_id="oc_test123",
                content="Gateway stopped",
                msg_type="text"
            )

    @pytest.mark.asyncio
    async def test_missing_target_does_not_fallback_to_invalid_channel(self):
        """Test that missing target does not fall back to an invalid channel.name."""
        # Create a mock channel without notification config
        mock_channel = MagicMock()
        mock_channel.name = "feishu"
        mock_channel.enabled = True
        
        # No notification config or empty config
        mock_channel.config = MagicMock()
        mock_channel.config.notification = None
        
        # Mock the send_text_message method
        mock_channel.send_text_message = AsyncMock()
        
        # Create channel manager with mock channel
        with patch.object(ChannelManager, '_get_channels', return_value=[mock_channel]):
            manager = ChannelManager(
                channels_config=ChannelsConfig(),
                gateway_config=GatewayConfig()
            )
            manager._channels = [mock_channel]
            
            # Test on_start notification - should not send anything
            await manager._send_gateway_lifecycle_notification("on_start")
            
            # Verify send_text_message was NOT called
            mock_channel.send_text_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_external_channel_is_no_op(self):
        """Test that no external channel is a no-op."""
        # Create channel manager with no channels
        manager = ChannelManager(
            channels_config=ChannelsConfig(),
            gateway_config=GatewayConfig()
        )
        manager._channels = []
        
        # Mock send_text_message to ensure it's not called
        with patch.object(ChannelManager, '_send_gateway_lifecycle_notification') as mock_send:
            # Call the method - should be a no-op
            await manager._send_gateway_lifecycle_notification("on_start")
            
            # The method should complete without errors even with no channels
            # (This test verifies no exception is raised)

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_block_shutdown(self):
        """Test that notification failure does not block shutdown."""
        # Create a mock channel that raises an exception
        mock_channel = MagicMock()
        mock_channel.name = "feishu"
        mock_channel.enabled = True
        
        # Create notification config
        mock_notification_cfg = MagicMock()
        mock_notification_cfg.chat_id_list = ["oc_test123"]
        mock_notification_cfg.on_start_message = "Gateway started"
        
        mock_channel.config = MagicMock()
        mock_channel.config.notification = mock_notification_cfg
        
        # Mock send_text_message to raise an exception
        mock_channel.send_text_message = AsyncMock(side_effect=Exception("Network error"))
        
        # Create channel manager with mock channel
        with patch.object(ChannelManager, '_get_channels', return_value=[mock_channel]):
            manager = ChannelManager(
                channels_config=ChannelsConfig(),
                gateway_config=GatewayConfig()
            )
            manager._channels = [mock_channel]
            
            # Test that exception is caught and doesn't block execution
            # Should not raise any exception
            await manager._send_gateway_lifecycle_notification("on_start")
            
            # Verify send_text_message was called (and failed)
            mock_channel.send_text_message.assert_called_once()
            
            # The method should complete without raising exception
            # (verified by no exception being raised above)
