"""AI-powered message generation for mentor engagement."""

import logging
import os
import random
from datetime import datetime
import anthropic

logger = logging.getLogger(__name__)


class EngagementMessageGenerator:
    """Generates varied engagement messages using Claude."""

    def __init__(self):
        """Initialize Claude client."""
        self.api_key = os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            # Fallback to xAI if Claude key not available
            self.api_key = os.getenv("XAI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "Neither CLAUDE_API_KEY nor XAI_API_KEY found in environment variables"
                )
            # Use xAI client
            from openai import OpenAI

            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.x.ai/v1",
            )
            self.use_claude = False
        else:
            # Use Claude client
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.use_claude = True

        # Tone/theme variations for weekly diversity
        self.themes = [
            "meme/internet culture",
            "sports/competition",
            "music/arts",
            "gaming/tech",
            "real talk/deep thoughts",
            "goals/ambitions",
            "funny/lighthearted",
            "challenges/support",
        ]

    def generate_engagement_message(self) -> dict:
        """
        Generate an engagement message for mentors using xAI.

        Returns:
            dict with keys:
                - mentor_reminder: Message to post in cool-ppl channel
                - mentee_template: Template mentors can copy-paste to mentees
        """
        # Pick a random theme for variety
        theme = random.choice(self.themes)

        try:
            logger.info(f"Generating engagement message with theme: {theme}")

            # Create diverse examples based on theme
            theme_examples = {
                "meme/internet culture": "Use memes, TikTok references, trending topics, viral content",
                "sports/competition": "Reference sports, competitions, team spirit, challenges",
                "music/arts": "Talk about music, shows, creative projects, playlists",
                "gaming/tech": "Gaming references, tech talk, online culture, streamers",
                "real talk/deep thoughts": "Deeper questions about life, future, feelings, growth",
                "goals/ambitions": "Dreams, college prep, career thoughts, aspirations",
                "funny/lighthearted": "Jokes, funny stories, light roasting, humor",
                "challenges/support": "Struggles, stress, need for support, helping each other",
            }

            prompt = (
                f"Theme: {theme}\n"
                f"Guidance: {theme_examples.get(theme, 'Be creative!')}\n\n"
                f"You're creating an engagement prompt for mentors to use with Gen Z teens (13-20).\n"
                f"Be EXTREMELY creative and varied. Each message should be completely unique.\n\n"
                f"Try formats like:\n"
                f"- Interactive polls or would-you-rather scenarios\n"
                f"- Creative sharing prompts (playlists, photos, stories)\n"
                f"- Mini-challenges or games\n"
                f"- Unconventional discussion starters\n"
                f"- Tier lists or rankings\n"
                f"- Fill-in-the-blank stories\n"
                f"- Hypothetical scenarios\n\n"
                f"Output as JSON with exactly these fields:\n"
                f'{{"mentor_reminder": "<@mentor> [gentle nudge, 150-200 chars]",\n'
                f' "mentee_template": "[super creative prompt for teens, 250-400 chars]"}}\n\n'
                f"The mentee_template should be FUN and ENGAGING - something teens will actually want to respond to.\n"
                f"Avoid boring generic questions. Be specific, quirky, or unexpected.\n"
                f"Date context: {datetime.now().strftime('%B %d, %Y')}"
            )

            if self.use_claude:
                # Use Claude API with latest Sonnet 4.5 model
                response = self.client.messages.create(
                    model="claude-sonnet-4-5-20250929",  # Latest model
                    max_tokens=1000,
                    temperature=1,
                    system="You're a creative genius helping mentors connect with Gen Z teens (13-20). Every message must be WILDLY different, unexpected, and fun. Never repeat formats or ideas. Be specific, quirky, and use current teen culture references.",
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.content[0].text
            else:
                # Fallback to xAI
                response = self.client.chat.completions.create(
                    model="grok-2-1212",
                    messages=[
                        {
                            "role": "system",
                            "content": "You're helping mentors connect with Gen Z teens. Be extremely creative and varied.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.9,
                    max_tokens=500,
                )
                content = response.choices[0].message.content
            logger.debug(f"AI response: {content}")

            # Parse JSON response
            import json

            # Try to extract JSON from the response
            try:
                # Sometimes Claude wraps JSON in markdown code blocks
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()

                parsed = json.loads(content)
            except json.JSONDecodeError as json_error:
                logger.error(f"Failed to parse JSON. Raw content: {content}")
                logger.error(f"JSON error: {json_error}")
                raise

            return {
                "mentor_reminder": parsed.get("mentor_reminder", ""),
                "mentee_template": parsed.get("mentee_template", ""),
            }

        except Exception as e:
            logger.error(f"Error generating engagement message: {e}")
            logger.error(f"Full error details: {type(e).__name__}: {str(e)}")
            if hasattr(e, "__dict__"):
                logger.error(f"Error attributes: {e.__dict__}")
            # Fallback message if AI fails
            return self._get_fallback_message()

    def _get_fallback_message(self) -> dict:
        """Fallback message if AI generation fails - more creative options."""
        fallbacks = [
            {
                "mentor_reminder": (
                    "<@&MENTOR_ROLE_ID> 🎮 Time for a vibe check with your groups! "
                    "Here's a fun prompt if you need inspiration."
                ),
                "mentee_template": (
                    "POV: You can only keep 3 apps on your phone for a month. "
                    "Which ones and why? Wrong answers only accepted too 😂"
                ),
            },
            {
                "mentor_reminder": (
                    "<@&MENTOR_ROLE_ID> 📸 Quick nudge to engage your squads! "
                    "Try this creative prompt or make your own."
                ),
                "mentee_template": (
                    "Hot take thread! Drop your most controversial (but harmless) opinion. "
                    "I'll start: Pineapple on pizza is actually elite. Fight me 🍕"
                ),
            },
            {
                "mentor_reminder": (
                    "<@&MENTOR_ROLE_ID> 🎯 Channel check-in time! "
                    "Here's a discussion starter or freestyle it."
                ),
                "mentee_template": (
                    "If your current mood was a song, what would it be? "
                    "Bonus points if you share the actual track 🎵"
                ),
            },
            {
                "mentor_reminder": (
                    "<@&MENTOR_ROLE_ID> 💭 Touch base with your crews when you can! "
                    "Fun conversation idea attached."
                ),
                "mentee_template": (
                    "Would you rather: Have to sing everything you say for a day OR "
                    "only communicate through interpretive dance? Explain your survival strategy 🕺"
                ),
            },
            {
                "mentor_reminder": (
                    "<@&MENTOR_ROLE_ID> ⚡ Weekly group engagement reminder! "
                    "Spice things up with this prompt."
                ),
                "mentee_template": (
                    "Rate your week using only emojis (max 5). "
                    "Then guess what happened based on someone else's emoji story 👀"
                ),
            },
            {
                "mentor_reminder": (
                    "<@&MENTOR_ROLE_ID> 🌟 Check in with your mentees! "
                    "Here's a creative starter."
                ),
                "mentee_template": (
                    "Quick! You're making a time capsule to open in 5 years. "
                    "What 3 things are you putting in and what message for future you?"
                ),
            },
        ]

        return random.choice(fallbacks)
