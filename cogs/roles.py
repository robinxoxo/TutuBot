import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
import typing
from typing import List, Dict, Optional, Any, TYPE_CHECKING

from utils.role_definitions import RoleCategory, ROLE_DEFINITIONS
from utils.permission_checks import is_owner_or_administrator
from utils.embed_builder import EmbedBuilder

# Import utilities - prevent circular imports
if typing.TYPE_CHECKING:
    from main import TutuBot
else:
    # Import interaction utils at runtime
    from utils.interaction_utils import send_ephemeral_message

log = logging.getLogger(__name__)

class RoleCategorySelect(ui.Select):
    """Select menu for choosing a role category."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label=category.value,
                description=f"View roles for {category.value}",
                emoji=next((v["emoji"] for v in ROLE_DEFINITIONS.values() if v["category"] == category), None)
            ) for category in RoleCategory
        ]
        
        super().__init__(
            placeholder="Choose a role category...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Get the selected category
        selected_category = RoleCategory(self.values[0])
        
        # We need to get the user's current roles for pre-selection
        assert isinstance(interaction.user, discord.Member)
        
        # Create a view with role selections for this category
        view = RolesView(selected_category, interaction.user.roles)
        
        # Create embed for category
        embed = EmbedBuilder.info(
            title=f"🏷️ {selected_category.value}",
            description="Select roles to add or remove from the dropdown below."
        )
        
        # Count how many roles the user has in this category
        category_roles = {k: v for k, v in ROLE_DEFINITIONS.items() if v["category"] == selected_category}
        user_role_names = [role.name.lower() for role in interaction.user.roles]
        
        user_has_roles = [role for role_id, role in category_roles.items() if role["name"].lower() in user_role_names]
        
        if user_has_roles:
            # Display roles with title case for better readability
            role_list = ", ".join(f"{role['emoji']} {role['name'].lower().title()}" for role in user_has_roles)
            embed.add_field(name="Your Current Roles", value=role_list, inline=False)
        else:
            embed.add_field(name="Your Current Roles", value="None in this category", inline=False)
        
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=view
        )

class RolesSelect(ui.Select):
    """Select menu for choosing roles from a specific category."""
    
    def __init__(self, category: RoleCategory, user_roles: List[discord.Role]):
        self.category = category
        
        # Filter roles for this category
        category_roles = {k: v for k, v in ROLE_DEFINITIONS.items() if v["category"] == category}
        
        # Create options
        options = []
        # Make case-insensitive role name check
        user_role_names = [role.name.lower() for role in user_roles]
        
        for role_id, role_info in category_roles.items():
            # Check if user has this role (case-insensitive)
            has_role = role_info["name"].lower() in user_role_names
            
            description = role_info["description"]
            if description:
                description = f"{description}"
            else:
                description = "Click to toggle role"
            
            # Use title case for display but lowercase for value
            display_name = role_info["name"].lower().title()
            role_value = role_info["name"].lower()
            
            options.append(
                discord.SelectOption(
                    label=display_name,
                    emoji=role_info["emoji"],
                    description=description,
                    value=role_value,
                    default=has_role
                )
            )
        
        super().__init__(
            placeholder=f"Select roles from {category.value}...",
            min_values=0,  # Allow deselecting all
            max_values=min(len(options), 25),  # Discord max is 25
            options=options
        )
        
    async def callback(self, interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member), "User must be a Member"
        assert interaction.guild is not None, "Guild must exist"
        
        # Get the user's current roles
        user_roles = interaction.user.roles
        # Make case-insensitive role name check
        user_role_names = [role.name.lower() for role in user_roles]
        
        # Get all roles for this category
        category_roles = {k: v for k, v in ROLE_DEFINITIONS.items() if v["category"] == self.category}
        category_role_names = [info["name"].lower() for info in category_roles.values()]
        
        # Find all server roles matching our category roles (case-insensitive)
        server_roles = {}
        for role in interaction.guild.roles:
            server_roles[role.name.lower()] = role
        
        # All self.values are already lowercase from the SelectOption value
        selected_role_names = self.values
        roles_to_add = []
        roles_to_remove = []
        missing_roles = []
        
        # Check which roles should be added (case-insensitive)
        for role_name in selected_role_names:
            if role_name not in user_role_names and role_name in server_roles:
                roles_to_add.append(server_roles[role_name])
            elif role_name not in server_roles:
                # Get display name for missing role
                display_name = role_name.title()
                missing_roles.append(display_name)
                
        # Check which category roles should be removed (case-insensitive)
        for role_info in category_roles.values():
            role_name = role_info["name"].lower()
            if role_name in user_role_names and role_name not in selected_role_names:
                if role_name in server_roles:
                    roles_to_remove.append(server_roles[role_name])
        
        # Apply role changes
        try:
            if roles_to_add:
                await interaction.user.add_roles(*roles_to_add, reason="Self-assigned via role menu")
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove, reason="Self-removed via role menu")
                
            # Create embed for result
            embed = EmbedBuilder.success(
                title=f"🏷️ {self.category.value}",
                description="Your roles have been updated."
            ) if (roles_to_add or roles_to_remove) else EmbedBuilder.info(
                title=f"🏷️ {self.category.value}",
                description="Your roles have been updated."
            )
            
            # Get updated member to ensure we have the latest roles
            updated_member = await interaction.guild.fetch_member(interaction.user.id)
            
            # Get current roles in this category using updated member
            current_roles = []
            for role in updated_member.roles:
                role_name_lower = role.name.lower()
                for info in category_roles.values():
                    if role_name_lower == info["name"].lower():
                        emoji = info["emoji"]
                        # Display in title case for better readability
                        display_name = role.name.lower().title()
                        current_roles.append(f"{emoji} {display_name}")
                        break
                    
            # Add fields for added, removed, and current roles
            if roles_to_add:
                added_list = "\n".join(f"✓ {role.name.title()}" for role in roles_to_add)
                embed.add_field(name="Added Roles", value=added_list, inline=True)
                
            if roles_to_remove:
                removed_list = "\n".join(f"✗ {role.name.title()}" for role in roles_to_remove)
                embed.add_field(name="Removed Roles", value=removed_list, inline=True)
                
            if missing_roles:
                missing_list = "\n".join(f"⚠️ {role}" for role in missing_roles)
                embed.add_field(name="Missing Roles", value=missing_list + "\n*(Admin needs to sync)*", inline=True)
                
            if current_roles:
                embed.add_field(name="Your Current Roles", value="\n".join(current_roles), inline=False)
            else:
                embed.add_field(name="Your Current Roles", value="None in this category", inline=False)
                
            # Create a new view with updated defaults
            view = RolesView(self.category, updated_member.roles)
            await interaction.response.edit_message(embed=embed, view=view)
            
        except discord.Forbidden:
            # Create a more detailed error message about role permissions
            error_embed = EmbedBuilder.error(
                title="✗ Permission Error",
                description=f"I don't have permission to manage these roles in the '{self.category.value}' category."
            )
            
            error_embed.add_field(
                name="What Happened?",
                value="Either the requested roles are managed by Discord or I lack permission to change them.",
                inline=False
            )
            
            error_embed.add_field(
                name="Solution",
                value="Ask a server administrator to fix the role hierarchy or permissions.",
                inline=False
            )
            
            await interaction.response.edit_message(embed=error_embed, view=self.view)
            
        except Exception as e:
            log.exception(f"Error updating roles for user {interaction.user} in category {self.category}: {e}")
            await interaction.response.edit_message(
                embed=EmbedBuilder.error(
                    title="✗ Error",
                    description=f"An error occurred while updating your roles: {str(e)}"
                ),
                view=self.view
            )

class RolesView(ui.View):
    """View for managing roles with categories."""
    
    def __init__(self, category: Optional[RoleCategory] = None, user_roles: Optional[List[discord.Role]] = None):
        super().__init__(timeout=180)  # 3 minute timeout
        
        if category:
            # View for a specific category with roles
            self.add_item(RolesSelect(category, user_roles or []))
            self.add_item(ui.Button(label="Back to Categories", style=discord.ButtonStyle.secondary, custom_id="back"))
            
            # Set callback for back button
            for item in self.children:
                if isinstance(item, ui.Button) and item.custom_id == "back":
                    item.callback = self.back_button_callback
            
        else:
            # Main category selection view
            self.add_item(RoleCategorySelect())
            
    async def back_button_callback(self, interaction: discord.Interaction):
        """Returns to the main category selection."""
        assert isinstance(interaction.user, discord.Member), "User must be a Member"
        
        # Simple embed without role information  
        embed = EmbedBuilder.info(
            title="👤 Role Management",
            description="Select a category of roles to manage from the dropdown below."
        )
        
        # Create a view with category selection
        view = RolesView()
        
        await interaction.response.edit_message(embed=embed, view=view)

class RoleCog(commands.Cog, name="Roles"):
    """Handles role management for the server."""

    def __init__(self, bot: 'TutuBot'):
        self.bot = bot

    @app_commands.command(name="roles", description="Manage your community roles")
    async def roles_command(self, interaction: discord.Interaction):
        """Displays an interactive role manager to add/remove roles.
        
        Args:
            interaction: The interaction
        """
        # Guild check
        if not interaction.guild:
            await send_ephemeral_message(
                interaction,
                content="This command can only be used in a server."
            )
            return
            
        # Ensure we have a member to manage roles on
        if not isinstance(interaction.user, discord.Member):
            await send_ephemeral_message(
                interaction,
                content="Could not identify you as a member of this server."
            )
            return
            
        # Create embed for main menu
        embed = EmbedBuilder.info(
            title="👤 Role Management",
            description="Select a category of roles to manage from the dropdown below."
        )
            
        # Create view with role category selection
        view = RolesView()
        
        await send_ephemeral_message(interaction, embed=embed, view=view)
        
    @app_commands.command(name="syncroles", description="[Admin] Synchronize server roles with bot configuration")
    @is_owner_or_administrator()
    async def syncroles_command(self, interaction: discord.Interaction):
        """Create or update server roles based on role definitions.
        
        This command will:
        1. Check existing roles in the server
        2. Create any missing roles from the configuration
        3. Update existing role properties to match the configuration
        """
        # Guard: Must be in a guild
        if not interaction.guild:
            await send_ephemeral_message(
                interaction,
                content="This command can only be used in a server."
            )
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get current server roles
        existing_roles = {role.name.lower(): role for role in interaction.guild.roles}
        
        # Track stats
        created_roles = []
        updated_roles = []
        unchanged_roles = []
        
        # Process all role definitions
        for role_id, role_info in ROLE_DEFINITIONS.items():
            role_name = role_info["name"]
            role_name_lower = role_name.lower()
            emoji = role_info.get("emoji", "")
            position = role_info.get("position", 0)
            
            # Check color handling (hexcode or discord.Color)
            color_value = role_info.get("color", 0)
            if isinstance(color_value, str) and color_value.startswith("#"):
                # Convert hex color to int
                color_value = int(color_value.lstrip("#"), 16)
                
            role_color = discord.Color(color_value)
            
            # Add defaults for role properties
            mentionable = role_info.get("mentionable", True)
            hoist = role_info.get("hoist", False)  # Whether to display separately
            
            # If role already exists, update it
            if role_name_lower in existing_roles:
                existing_role = existing_roles[role_name_lower]
                
                # Find properties that need updating
                updates_needed = []
                
                if existing_role.color.value != role_color.value:
                    updates_needed.append(f"color: {existing_role.color} → {role_color}")
                
                if existing_role.mentionable != mentionable:
                    updates_needed.append(f"mentionable: {existing_role.mentionable} → {mentionable}")
                    
                if existing_role.hoist != hoist:
                    updates_needed.append(f"hoist: {existing_role.hoist} → {hoist}")
                
                # Apply updates if needed
                if updates_needed:
                    try:
                        await existing_role.edit(
                            color=role_color,
                            mentionable=mentionable,
                            hoist=hoist,
                            reason="Role sync from bot configuration"
                        )
                        
                        updated_roles.append((role_name, ", ".join(updates_needed)))
                    except discord.Forbidden:
                        log.warning(f"Missing permissions to edit role: {role_name}")
                    except Exception as e:
                        log.error(f"Error updating role {role_name}: {e}")
                else:
                    unchanged_roles.append(role_name)
            else:
                # Create new role
                try:
                    new_role = await interaction.guild.create_role(
                        name=role_name,
                        color=role_color,
                        mentionable=mentionable,
                        hoist=hoist,
                        reason="Role creation from bot configuration"
                    )
                    created_roles.append(role_name)
                except discord.Forbidden:
                    log.warning(f"Missing permissions to create role: {role_name}")
                except Exception as e:
                    log.error(f"Error creating role {role_name}: {e}")
        
        # Create embed for results
        embed = EmbedBuilder.success(
            title="🔄 Role Synchronization Results",
            description=f"Role synchronization completed."
        ) if (created_roles or updated_roles) else EmbedBuilder.info(
            title="🔄 Role Synchronization Results",
            description=f"Role synchronization completed. No changes needed."
        )
        
        # Add results to embed
        if created_roles:
            created_list = "\n".join(f"✓ {name}" for name in created_roles)
            embed.add_field(name=f"Created Roles ({len(created_roles)})", value=created_list, inline=False)
            
        if updated_roles:
            updated_list = "\n".join(f"✓ {name}: {changes}" for name, changes in updated_roles)
            embed.add_field(name=f"Updated Roles ({len(updated_roles)})", value=updated_list, inline=False)
            
        if unchanged_roles:
            embed.add_field(
                name=f"Unchanged Roles ({len(unchanged_roles)})",
                value=f"{len(unchanged_roles)} roles were already configured correctly.",
                inline=False
            )
            
        await send_ephemeral_message(interaction, embed=embed)
        
    @syncroles_command.error
    async def syncroles_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for the syncroles command."""
        if isinstance(error, app_commands.errors.CheckFailure):
            embed = EmbedBuilder.error(
                title="✗ Error",
                description="You need administrator permissions to use this command."
            )
            await send_ephemeral_message(interaction, embed=embed)
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred: {str(error)}"
            )
            await send_ephemeral_message(interaction, embed=embed)

async def setup(bot: 'TutuBot'):
    """Sets up the RoleCog."""
    await bot.add_cog(RoleCog(bot))
    log.info("RoleCog loaded.") 