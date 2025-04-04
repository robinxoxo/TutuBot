import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
import typing
from typing import List, Dict, Optional, Any

from utils.role_definitions import RoleCategory, ROLE_DEFINITIONS

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
            title=f"{selected_category.value}",
            description="Select roles to add or remove from the dropdown below.",
            color=discord.Color.blue()
        )
        
        # Count how many roles the user has in this category
        category_roles = {k: v for k, v in ROLE_DEFINITIONS.items() if v["category"] == selected_category}
        user_role_names = [role.name for role in interaction.user.roles]
        
        user_has_roles = [role for role_id, role in category_roles.items() if role["name"] in user_role_names]
        
        if user_has_roles:
            role_list = ", ".join(f"{role['emoji']} {role['name']}" for role in user_has_roles)
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
        user_role_names = [role.name for role in user_roles]
        
        for role_id, role_info in category_roles.items():
            # Check if user has this role
            has_role = role_info["name"] in user_role_names
            
            description = role_info["description"]
            if description:
                description = f"{description}"
            else:
                description = "Click to toggle role"
                
            options.append(
                discord.SelectOption(
                    label=role_info["name"],
                    emoji=role_info["emoji"],
                    description=description,
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
        user_role_names = [role.name for role in user_roles]
        
        # Get all roles for this category
        category_roles = {k: v for k, v in ROLE_DEFINITIONS.items() if v["category"] == self.category}
        category_role_names = [info["name"] for info in category_roles.values()]
        
        # Find all server roles matching our category roles
        server_roles = {role.name: role for role in interaction.guild.roles}
        
        # Determine roles to add and remove
        selected_role_names = self.values
        roles_to_add = []
        roles_to_remove = []
        missing_roles = []
        
        # Check which roles should be added
        for role_name in selected_role_names:
            if role_name not in user_role_names and role_name in server_roles:
                roles_to_add.append(server_roles[role_name])
            elif role_name not in server_roles:
                missing_roles.append(role_name)
                
        # Check which category roles should be removed
        for role_info in category_roles.values():
            role_name = role_info["name"]
            if role_name in user_role_names and role_name not in selected_role_names and role_name in server_roles:
                roles_to_remove.append(server_roles[role_name])
        
        # Apply role changes
        try:
            if roles_to_add:
                await interaction.user.add_roles(*roles_to_add, reason="Self-assigned via role menu")
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove, reason="Self-removed via role menu")
                
            # Create embed for result
            embed = discord.Embed(
                title=f"{self.category.value}",
                description="Your roles have been updated.",
                color=discord.Color.green() if (roles_to_add or roles_to_remove) else discord.Color.blue()
            )
            
            # Get current roles in this category
            current_roles = []
            for role in interaction.user.roles:
                if any(role.name == info["name"] for info in category_roles.values()):
                    emoji = next((v["emoji"] for k, v in ROLE_DEFINITIONS.items() if v["name"] == role.name), "")
                    current_roles.append(f"{emoji} {role.name}")
                    
            # Add fields for added, removed, and current roles
            if roles_to_add:
                added_list = "\n".join(f"✓ {role.name}" for role in roles_to_add)
                embed.add_field(name="Added Roles", value=added_list, inline=True)
                
            if roles_to_remove:
                removed_list = "\n".join(f"✗ {role.name}" for role in roles_to_remove)
                embed.add_field(name="Removed Roles", value=removed_list, inline=True)
                
            if missing_roles:
                missing_list = "\n".join(f"⚠️ {role}" for role in missing_roles)
                embed.add_field(name="Missing Roles", value=missing_list + "\n*(Admin needs to create)*", inline=True)
                
            if current_roles:
                embed.add_field(name="Your Current Roles", value="\n".join(current_roles), inline=False)
            else:
                embed.add_field(name="Your Current Roles", value="None in this category", inline=False)
            
            # Create a new view with updated role selections using the user's updated roles
            updated_view = RolesView(self.category, interaction.user.roles)
            
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=updated_view
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to manage these roles. Please contact an admin.",
                ephemeral=True
            )
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
        else:
            # Add the category selection menu
            self.add_item(RoleCategorySelect())
            
    @ui.button(label="Back to Categories", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        """Return to the category selection menu."""
        view = RolesView()  # Create a new view with just the category selector
        
        # Create embed for main menu
        embed = discord.Embed(
            title="Role Management",
            description="Select a category of roles to manage from the dropdown below.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="How It Works",
            value="• Choose a category\n• Select roles you want\n• Unselect roles you don't want\n• Your current roles appear pre-selected"
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
            
        # Initialize the role category selection view
        view = RolesView(user_roles=interaction.user.roles)
        
        # Create embed for main menu
        embed = discord.Embed(
            title="Role Management",
            description="Select a category of roles to manage from the dropdown below.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="How It Works",
            value="• Choose a category\n• Select roles you want\n• Unselect roles you don't want\n• Your current roles appear pre-selected"
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
    @app_commands.command(name="syncroles", description="[Admin] Synchronize server roles with bot configuration")
    @app_commands.default_permissions(administrator=True)
    async def syncroles_command(self, interaction: discord.Interaction):
        """Admin command to synchronize missing roles with bot configuration."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
            
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get existing roles
        existing_roles = {role.name: role for role in interaction.guild.roles}
        
        # Track our changes
        created_roles = []
        updated_roles = []
        failed_roles = []
        
        # Process all roles defined in configuration
        for role_id, role_info in ROLE_DEFINITIONS.items():
            role_name = role_info["name"]
            role_color = role_info.get("color", discord.Color.default())
            
            if role_name not in existing_roles:
                # Create missing role
                try:
                    category = role_info["category"]
                    role = await interaction.guild.create_role(
                        name=role_name,
                        reason=f"Auto-created by role setup command - {category.value}",
                        color=role_color
                    )
                    created_roles.append(role)
                except Exception as e:
                    log.exception(f"Failed to create role {role_name}: {e}")
                    failed_roles.append(role_name)
            else:
                # Update existing role if needed
                existing_role = existing_roles[role_name]
                needs_update = False
                update_fields = []
                
                # Check if color needs to be updated
                if role_color != existing_role.color:
                    needs_update = True
                    update_fields.append("color")
                
                if needs_update:
                    try:
                        await existing_role.edit(
                            color=role_color,
                            reason="Auto-updated by role sync command"
                        )
                        updated_roles.append((existing_role, update_fields))
                    except Exception as e:
                        log.exception(f"Failed to update role {role_name}: {e}")
                        failed_roles.append(f"{role_name} (update)")
        
        # Create embed for results
        embed = discord.Embed(
            title="Role Synchronization Results",
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
            updated_list = "\n".join(f"🔄 {role.name} ({', '.join(fields)})" for role, fields in updated_roles)
            embed.add_field(name=f"Updated {len(updated_roles)} Roles", value=updated_list, inline=False)
        else:
            embed.add_field(name="No Roles Updated", value="All existing roles are up to date.", inline=False)
            
        # Add fields for failed roles
        if failed_roles:
            failed_list = "\n".join(f"✗ {role}" for role in failed_roles)
            embed.add_field(name=f"Failed Operations ({len(failed_roles)})", value=failed_list, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: 'TutuBot'):
    """Sets up the RoleCog."""
    await bot.add_cog(RoleCog(bot))
    log.info("RoleCog loaded.") 