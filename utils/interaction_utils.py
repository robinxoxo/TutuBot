"""
Utility functions for handling Discord interactions.

This module provides utilities for working with Discord interactions, including:
- Auto-dismissing ephemeral messages after a specified timeout
- Helper functions for sending and managing interaction responses

The main feature is auto-dismissal of ephemeral messages after 2 minutes by default,
which helps keep the user's interface clean by removing responses that are no longer needed.
"""

import discord
import asyncio
import logging
from typing import Optional, Union, Dict, Any, TYPE_CHECKING

# Configure logging
log = logging.getLogger(__name__)

async def send_ephemeral_message(
    interaction: discord.Interaction, 
    content: Optional[str] = None, 
    *, 
    embed: Optional[discord.Embed] = None,
    embeds: Optional[list[discord.Embed]] = None,
    view: Optional[discord.ui.View] = None,
    auto_dismiss: bool = True,
    dismiss_after: float = 120.0,  # 2 minutes by default
) -> None:
    """Send an ephemeral message that will auto-dismiss after the specified time.
    
    Args:
        interaction: The Discord interaction to respond to
        content: Text content of the message (optional)
        embed: A single embed to send (optional)
        embeds: Multiple embeds to send (optional)
        view: UI view to attach to the message (optional)
        auto_dismiss: Whether to auto-dismiss the message (default: True)
        dismiss_after: Seconds to wait before dismissing (default: 120s/2min)
    """
    try:
        # Prepare kwargs for the send method
        kwargs = {
            "content": content,
            "ephemeral": True
        }
        
        # Only add view if not None
        if view is not None:
            kwargs["view"] = view
        
        # Only add one of embed or embeds to avoid the error
        if embeds is not None:
            kwargs["embeds"] = embeds
        elif embed is not None:
            kwargs["embed"] = embed
            
        # Send the ephemeral message
        if interaction.response.is_done():
            # Use followup if response is already sent
            kwargs["wait"] = True  # Need to get message object for deletion
            message = await interaction.followup.send(**kwargs)
        else:
            # Use response if not already done
            await interaction.response.send_message(**kwargs)
            message = await interaction.original_response()
        
        # Schedule message dismissal if enabled
        if auto_dismiss:
            # Create task to delete the message after specified time
            asyncio.create_task(
                _delete_message_after(message, dismiss_after)
            )
    except Exception as e:
        log.error(f"Error sending ephemeral message: {e}")

async def _delete_message_after(message: discord.Message, delay: float) -> None:
    """Delete a message after a specified delay.
    
    Args:
        message: The Discord message to delete
        delay: Seconds to wait before deleting
    """
    try:
        await asyncio.sleep(delay)
        await message.delete()
        log.debug(f"Auto-dismissed ephemeral message after {delay}s")
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
        # Message may already be deleted or permissions changed
        log.debug(f"Failed to auto-dismiss message: {e}")
    except Exception as e:
        # Catch any other unexpected errors
        log.error(f"Unexpected error when auto-dismissing message: {e}") 