import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
import typing
from typing import List, Dict, Optional, Any

from utils.role_definitions import RoleCategory, ROLE_DEFINITIONS
from utils.permission_checks import is_owner_or_administrator

if typing.TYPE_CHECKING:
    from main import TutuBot

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
        embed = discord.Embed(
            title=f"🏷️ {selected_category.value}",
            description="Select roles to add or remove from the dropdown below.",
            color=discord.Color.blue()
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
            embed = discord.Embed(
                title=f"🏷️ {self.category.value}",
                description="Your roles have been updated.",
                color=discord.Color.green() if (roles_to_add or roles_to_remove) else discord.Color.blue()
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
            
            # Create a new view with updated role selections using the updated member's roles
            updated_view = RolesView(self.category, updated_member.roles)
            
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=updated_view
            )
        except discord.Forbidden:
            # Create a more detailed error message about role permissions
            error_embed = discord.Embed(
                title="✗ Permission Error",
                description=f"I don't have permission to manage these roles in the '{self.category.value}' category.",
                color=discord.Color.red()
            )
            
            error_embed.add_field(
                name="Possible Reasons",
                value=(
                    "• The bot's role is lower in the server hierarchy than it should be.\n"
                    "• The bot lacks 'Manage Roles' permission.\n"
                    "• These specific roles are restricted by server settings."
                ),
                inline=False
            )
            
            # Add troubleshooting advice
            error_embed.add_field(
                name="Solutions",
                value=(
                    "• Ask a server admin to move the bot's role higher in the role list.\n"
                    "• Ensure the bot has 'Manage Roles' permission.\n"
                    "• Contact a server admin for assistance."
                ),
                inline=False
            )
            
            # Log specific details for debugging
            role_names = []
            if roles_to_add:
                role_names.extend([role.name for role in roles_to_add])
            if roles_to_remove:
                role_names.extend([role.name for role in roles_to_remove])
                
            log.error(f"Permission denied while managing roles in category '{self.category.value}'. Roles: {', '.join(role_names)}")
            
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except Exception as e:
            log.exception(f"Error managing roles: {e}")
            await interaction.response.send_message(
                f"An error occurred while managing roles: {str(e)}",
                ephemeral=True
            )

class RolesView(ui.View):
    """View for role selection within a category."""
    
    def __init__(self, category: Optional[RoleCategory] = None, user_roles: Optional[List[discord.Role]] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        
        self.user_roles = user_roles or []
        
        if category:
            # Add the role selection menu for this category with user's current roles
            self.add_item(RolesSelect(category, self.user_roles))
            self.category = category
            
            # Add back button only when in a specific category
            back_button = ui.Button(label="Back to Categories", style=discord.ButtonStyle.secondary)
            back_button.callback = self.back_button_callback
            self.add_item(back_button)
        else:
            # Add the category selection menu
            self.add_item(RoleCategorySelect())
    
    async def back_button_callback(self, interaction: discord.Interaction):
        """Return to the category selection menu."""
        # We need a valid member with roles
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            # Fall back to a simple view with no user roles
            view = RolesView()
            
            # Simple embed without role information
            embed = discord.Embed(
                title="👤 Role Management",
                description="Select a category of roles to manage from the dropdown below.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="How It Works",
                value="• Choose a category\n• Select roles you want\n• Unselect roles you don't want\n• Your current roles appear pre-selected",
                inline=False
            )
            
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=view
            )
            return
            
        # Get updated member to ensure we have the latest roles
        member = await interaction.guild.fetch_member(interaction.user.id)
        
        # Create a new view with the updated roles
        view = RolesView(user_roles=member.roles)
        
        # Create embed for main menu
        embed = discord.Embed(
            title="👤 Role Management",
            description="Select a category of roles to manage from the dropdown below.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="How It Works",
            value="• Choose a category\n• Select roles you want\n• Unselect roles you don't want\n• Your current roles appear pre-selected",
            inline=False
        )
        
        # Group user's current roles by category
        member_role_names = [role.name.lower() for role in member.roles]
        roles_by_category = {}
        
        # Initialize categories for sorting
        for category in RoleCategory:
            roles_by_category[category] = []
            
        # Sort roles into categories
        for role_id, role_info in ROLE_DEFINITIONS.items():
            if role_info["name"].lower() in member_role_names:
                category = role_info["category"]
                # Display role name in title case for better readability
                display_name = role_info["name"].lower().title()
                roles_by_category[category].append(f"{role_info['emoji']} {display_name}")
        
        # Add fields for current roles by category
        has_roles = False
        for category, roles in roles_by_category.items():
            if roles:
                has_roles = True
                embed.add_field(
                    name=f"{category.value}",
                    value="\n".join(roles),
                    inline=True
                )
        
        if not has_roles:
            embed.add_field(
                name="Roles",
                value="You don't have any roles yet. Select a category to add roles.",
                inline=False
            )
        else:
            embed.add_field(
                name="Your Current Roles",
                value="Your current roles are displayed above.",
                inline=False
            )
        
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=view
        )

class RoleCog(commands.Cog, name="Roles"):
    """Manages community roles through interactive UI."""
    
    def __init__(self, bot: 'TutuBot'):
        self.bot = bot
        
    @app_commands.command(name="roles", description="Manage your community roles")
    async def roles_command(self, interaction: discord.Interaction):
        """Displays the role management interface."""
        # Check if we're in a guild
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
            
        # We need to ensure the user is a Member to get roles
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("There was an error retrieving your roles. Please try again.", ephemeral=True)
            return
            
        # Get updated member to ensure we have the latest roles
        member = await interaction.guild.fetch_member(interaction.user.id)
            
        # Initialize the role category selection view
        view = RolesView(user_roles=member.roles)
        
        # Create embed for main menu
        embed = discord.Embed(
            title="👤 Role Management",
            description="Select a category of roles to manage from the dropdown below.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="How It Works",
            value="• Choose a category\n• Select roles you want\n• Unselect roles you don't want\n• Your current roles appear pre-selected",
            inline=False
        )
        
        # Group user's current roles by category
        member_role_names = [role.name.lower() for role in member.roles]
        roles_by_category = {}
        
        # Initialize categories for sorting
        for category in RoleCategory:
            roles_by_category[category] = []
            
        # Sort roles into categories
        for role_id, role_info in ROLE_DEFINITIONS.items():
            if role_info["name"].lower() in member_role_names:
                category = role_info["category"]
                # Display role name in title case for better readability
                display_name = role_info["name"].lower().title()
                roles_by_category[category].append(f"{role_info['emoji']} {display_name}")
        
        # Add fields for current roles by category
        has_roles = False
        for category, roles in roles_by_category.items():
            if roles:
                has_roles = True
                embed.add_field(
                    name=f"{category.value}",
                    value="\n".join(roles),
                    inline=True
                )
        
        if not has_roles:
            embed.add_field(
                name="Roles",
                value="You don't have any roles yet. Select a category to add roles.",
                inline=False
            )
        else:
            embed.add_field(
                name="Your Current Roles",
                value="Your current roles are displayed above.",
                inline=False
            )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
    @app_commands.command(name="syncroles", description="[Admin] Synchronize server roles with bot configuration")
    @is_owner_or_administrator()
    async def syncroles_command(self, interaction: discord.Interaction):
        """Admin command to synchronize missing roles with bot configuration."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get existing roles (case-insensitive)
        existing_roles_lower = {}
        for role in interaction.guild.roles:
            existing_roles_lower[role.name.lower()] = role
        
        # Track our changes
        created_roles = []
        updated_roles = []
        failed_roles = []
        
        # Before processing, explicitly log existing roles with mixed/title case
        log.info(f"--- Role Sync: Starting role audit ---")
        for role in interaction.guild.roles:
            if role.name.lower() != role.name:
                log.info(f"Found title/mixed case role: '{role.name}' (will convert to: '{role.name.lower()}')")
        
        # Process all roles defined in configuration
        for role_id, role_info in ROLE_DEFINITIONS.items():
            # Get defined role name and convert to lowercase for storage
            original_role_name = role_info["name"]
            role_name = original_role_name.lower()  # Always store as lowercase
            role_color = role_info.get("color", discord.Color.default())
            
            log.info(f"Processing role definition: '{role_name}'")
            
            # Check if role exists (case-insensitive)
            if role_name in existing_roles_lower:
                # Role exists, check if it needs to be updated
                existing_role = existing_roles_lower[role_name]
                needs_update = False
                update_fields = []
                
                # Debug output for troubleshooting
                log.info(f"Found existing role: '{existing_role.name}' for '{role_name}'")
                
                # Compare names directly - this ensures we catch any case differences
                if existing_role.name != role_name:
                    log.info(f"Name case mismatch: '{existing_role.name}' vs '{role_name}'")
                    needs_update = True
                    update_fields.append(f"name (from '{existing_role.name}' to '{role_name}')")
                
                # Check if color needs to be updated
                if role_color != existing_role.color:
                    log.info(f"Color mismatch: {existing_role.color} vs {role_color}")
                    needs_update = True
                    update_fields.append("color")
                
                if needs_update:
                    try:
                        log.info(f"Updating role '{existing_role.name}' to name='{role_name}', color={role_color}")
                        
                        # Perform the edit
                        await existing_role.edit(
                            name=role_name,  # Force to lowercase
                            color=role_color,
                            reason="Auto-updated by role sync command"
                        )
                        
                        # Verify the update
                        updated_role = interaction.guild.get_role(existing_role.id)
                        
                        if updated_role is None:
                            log.warning(f"Failed to retrieve the updated role with id {existing_role.id}")
                            failed_roles.append(f"{role_name} (role not found after update)")
                        else:
                            log.info(f"After update: role name='{updated_role.name}'")
                            
                            if updated_role.name != role_name:
                                log.warning(f"Update verification failed! Name is still '{updated_role.name}' instead of '{role_name}'")
                                failed_roles.append(f"{role_name} (update failed)")
                            else:
                                updated_roles.append((updated_role, update_fields))
                                log.info(f"✓ Role '{role_name}' updated successfully")
                    
                    except discord.Forbidden:
                        log.error(f"Permission denied while updating role '{role_name}'")
                        failed_roles.append(f"{role_name} (permission denied)")
                    except Exception as e:
                        log.exception(f"Error updating role '{role_name}': {e}")
                        failed_roles.append(f"{role_name} (error: {str(e)})")
            else:
                # Create missing role with lowercase name
                try:
                    category = role_info["category"]
                    log.info(f"Creating new role: '{role_name}' (category: {category.value})")
                    
                    role = await interaction.guild.create_role(
                        name=role_name,  # Use lowercase
                        reason=f"Auto-created by role setup command - {category.value}",
                        color=role_color
                    )
                    created_roles.append(role)
                except Exception as e:
                    log.exception(f"Failed to create role {role_name}: {e}")
                    failed_roles.append(role_name)
        
        # Create embed for results
        embed = discord.Embed(
            title="🔄 Role Synchronization Results",
            color=discord.Color.green() if (created_roles or updated_roles) else discord.Color.blue()
        )
        
        # Add fields for created roles
        if created_roles:
            created_list = "\n".join(f"✓ {role.name}" for role in created_roles)
            embed.add_field(name=f"Created {len(created_roles)} Roles", value=created_list, inline=False)
        else:
            embed.add_field(name="No New Roles Created", value="All required roles already exist.", inline=False)
        
        # Add fields for updated roles
        if updated_roles:
            updated_list = "\n".join(f"✓ {role.name} ({', '.join(fields)})" for role, fields in updated_roles)
            embed.add_field(name=f"Updated {len(updated_roles)} Roles", value=updated_list, inline=False)
        else:
            embed.add_field(name="No Roles Updated", value="All existing roles are up to date.", inline=False)
            
        # Add fields for failed roles
        if failed_roles:
            failed_list = "\n".join(f"✗ {role.title() if isinstance(role, str) else role}" for role in failed_roles)
            embed.add_field(name=f"Failed Operations ({len(failed_roles)})", value=failed_list, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @syncroles_command.error
    async def syncroles_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for the syncroles command."""
        if isinstance(error, app_commands.errors.CheckFailure):
            embed = discord.Embed(
                title="✗ Error",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="✗ Error",
                description=f"An error occurred: {str(error)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            log.error(f"Error in syncroles command: {error}")

async def setup(bot: 'TutuBot'):
    """Sets up the RoleCog."""
    await bot.add_cog(RoleCog(bot))
    log.info("RoleCog loaded.") 