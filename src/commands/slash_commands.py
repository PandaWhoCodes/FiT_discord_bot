"""Slash command registration and handlers."""

import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands

from ..database import get_prayers_for_week
from ..engagement.message_generator import EngagementMessageGenerator

logger = logging.getLogger(__name__)


def register_slash_commands(tree: app_commands.CommandTree, context: dict) -> None:
    """
    Register all slash commands with the command tree.

    Args:
        tree: Discord command tree to register commands with
        context: Shared context containing bot resources (questions, sessions, etc.)
    """

    @tree.command(name="personality", description="Take the full MBTI personality test")
    async def personality_full(interaction: discord.Interaction) -> None:
        """Slash command to start the full personality test in DM."""
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        try:
            # Send DM to user
            dm_channel = await interaction.user.create_dm()

            await context["start_test_func"](
                dm_channel, user_id, username, is_dummy=False, **context["test_data"]
            )

            await interaction.followup.send(
                "✅ Check your DMs! I've started the personality test there.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I couldn't send you a DM. Please enable DMs from server members in your privacy settings.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Error starting test for {username}: {e}")
            await interaction.followup.send(
                "❌ An error occurred while starting the test. Please try again.", ephemeral=True
            )

    @tree.command(name="personality-quick", description="Take a quick 5-question personality test")
    async def personality_quick(interaction: discord.Interaction) -> None:
        """Slash command to start the quick personality test in DM."""
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        try:
            # Send DM to user
            dm_channel = await interaction.user.create_dm()

            await context["start_test_func"](
                dm_channel, user_id, username, is_dummy=True, **context["test_data"]
            )

            await interaction.followup.send(
                "✅ Check your DMs! I've started the quick test there.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I couldn't send you a DM. Please enable DMs from server members in your privacy settings.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Error starting test for {username}: {e}")
            await interaction.followup.send(
                "❌ An error occurred while starting the test. Please try again.", ephemeral=True
            )

    @tree.command(name="prayer", description="Get this week's prayer requests (Mentors only)")
    async def prayer_command(interaction: discord.Interaction) -> None:
        """Slash command to get current week's prayers for mentors."""
        await interaction.response.defer(ephemeral=True)

        # Check if user has mentor role (case-insensitive)
        has_mentor_role = False
        if hasattr(interaction.user, "roles"):
            for role in interaction.user.roles:
                if role.name.lower() == "mentor":
                    has_mentor_role = True
                    break

        if not has_mentor_role:
            await interaction.followup.send(
                "❌ This command is only available to mentors.", ephemeral=True
            )
            return

        # Calculate current week (Monday to Sunday)
        now = datetime.now(timezone.utc)
        # Get Monday of current week
        days_since_monday = now.weekday()  # Monday = 0, Sunday = 6
        monday = now - timedelta(days=days_since_monday)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get Sunday of current week
        sunday = monday + timedelta(days=6)
        sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

        logger.info(f"Fetching prayers for week: {monday.date()} to {sunday.date()}")

        # Query database
        prayers = get_prayers_for_week(monday, sunday)

        if not prayers or len(prayers) == 0:
            week_range = f"{monday.strftime('%b %d')}-{sunday.strftime('%d')}"
            await interaction.followup.send(
                f"No prayers posted this week ({week_range}).", ephemeral=True
            )
            return

        # Format prayers
        week_range = f"{monday.strftime('%b %d')}-{sunday.strftime('%d')}"
        prayer_lines = [f"**This week's prayers ({week_range}):**\n"]

        for i, prayer in enumerate(prayers, 1):
            username = prayer["discord_username"].split("#")[0]  # Remove discriminator
            prayer_text = prayer["extracted_prayer"]
            prayer_lines.append(f"{i}. {prayer_text} - @{username}")

        formatted_message = "\n".join(prayer_lines)

        # Check if message is too long (Discord limit: 2000 chars)
        if len(formatted_message) > 2000:
            # Split into multiple messages
            messages = []
            current_message = prayer_lines[0]  # Start with header

            for line in prayer_lines[1:]:
                if len(current_message) + len(line) + 1 > 1900:  # Leave buffer
                    messages.append(current_message)
                    current_message = line
                else:
                    current_message += "\n" + line

            messages.append(current_message)
        else:
            messages = [formatted_message]

        # Send via DM
        try:
            dm_channel = await interaction.user.create_dm()

            for msg in messages:
                await dm_channel.send(msg)

            await interaction.followup.send(
                "✅ Sent this week's prayers to your DM!", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I couldn't send you a DM. Please enable DMs from server members in your privacy settings.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Error sending prayers to {interaction.user.name}: {e}")
            await interaction.followup.send(
                "❌ An error occurred while sending prayers. Please try again.", ephemeral=True
            )

    @tree.command(name="engage", description="Send mentor engagement message (Admin only)")
    async def engage_command(interaction: discord.Interaction) -> None:
        """Slash command to manually trigger mentor engagement message (admin only)."""
        await interaction.response.defer(ephemeral=True)

        # Check if user is admin
        admin_user_id = int(os.getenv("ADMIN_USER_ID", "0"))
        if interaction.user.id != admin_user_id:
            await interaction.followup.send(
                "❌ This command is only available to administrators.", ephemeral=True
            )
            return

        # Get engagement channel
        channel_id = int(os.getenv("ENGAGEMENT_CHANNEL_ID", "0"))
        channel = interaction.guild.get_channel(channel_id)

        if not channel:
            await interaction.followup.send(
                f"❌ Engagement channel not found (ID: {channel_id}). Please check configuration.",
                ephemeral=True,
            )
            return

        try:
            # Generate message using AI
            logger.info(f"Admin {interaction.user.name} triggered /engage command")
            message_generator = EngagementMessageGenerator()
            message_data = message_generator.generate_engagement_message()

            mentor_reminder = message_data.get("mentor_reminder", "")
            mentee_template = message_data.get("mentee_template", "")

            if not mentor_reminder:
                await interaction.followup.send(
                    "❌ Failed to generate engagement message. Please try again.", ephemeral=True
                )
                return

            # Get mentor role to tag properly
            mentor_role = discord.utils.get(channel.guild.roles, name="mentor")

            if mentor_role:
                # Replace placeholder with actual role mention
                mentor_reminder = mentor_reminder.replace("<@&MENTOR_ROLE_ID>", mentor_role.mention)
            else:
                logger.warning("Mentor role not found in guild")
                # Remove placeholder if role not found
                mentor_reminder = mentor_reminder.replace("<@&MENTOR_ROLE_ID>", "@mentor")

            # Format the complete message
            embed = discord.Embed(
                title="📣 Weekly Mentor Check-In",
                description=mentor_reminder,
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )

            if mentee_template:
                embed.add_field(
                    name="💭 Optional Conversation Starter (feel free to use your own!)",
                    value=f"```\n{mentee_template}\n```",
                    inline=False,
                )

            embed.set_footer(text="FiT Bot • Encouraging mentorship connections")

            # Send the message to the engagement channel
            await channel.send(embed=embed)

            await interaction.followup.send(
                f"✅ Engagement message sent to {channel.mention}!", ephemeral=True
            )

            logger.info(f"Engagement message sent to {channel.name} by {interaction.user.name}")

        except Exception as e:
            logger.error(f"Error in /engage command: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while sending the engagement message. Please try again.",
                ephemeral=True,
            )

    logger.info("Slash commands registered: /personality, /personality-quick, /prayer, /engage")
