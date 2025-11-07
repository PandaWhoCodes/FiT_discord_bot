"""Prayer extraction using xAI API."""

import logging
import os
import time

from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize xAI client
xai_client = None


def init_xai_client() -> None:
    """Initialize xAI client with API key from environment."""
    global xai_client

    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        logger.warning("XAI_API_KEY not found - prayer extraction will be disabled")
        return

    xai_client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )
    logger.info("xAI client initialized")


def extract_prayer(message_text: str, retry_count: int = 0) -> str | None:
    """
    Extract core prayer request from a message using xAI.

    Args:
        message_text: The raw message text from Discord
        retry_count: Current retry attempt (0 = first attempt)

    Returns:
        Extracted prayer text, or None if no prayer found or extraction failed
    """
    if xai_client is None:
        logger.error("xAI client not initialized - cannot extract prayer")
        return None

    if not message_text or len(message_text.strip()) == 0:
        logger.debug("Empty message text - skipping extraction")
        return None

    try:
        prompt = f"""Extract the core prayer request from this message.
Return only the prayer need in one concise sentence.
If no prayer request exists, return 'NO_PRAYER'.

Message: {message_text}"""

        logger.debug(f"Extracting prayer from message (attempt {retry_count + 1})")

        completion = xai_client.chat.completions.create(
            model="grok-4-fast-non-reasoning",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.3,
            max_tokens=100,
            timeout=10.0,
        )

        response = completion.choices[0].message.content.strip()

        # Check if AI determined there's no prayer
        if response.upper() == "NO_PRAYER" or len(response) == 0:
            logger.debug(f"No prayer detected in message: {message_text[:50]}...")
            return None

        logger.info(f"Extracted prayer: {response}")
        return response

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Prayer extraction attempt {retry_count + 1} failed: {error_msg}")

        # Check if we should retry
        if retry_count < 1:
            # Exponential backoff: 2 seconds before retry
            time.sleep(2)
            logger.info("Retrying prayer extraction...")
            return extract_prayer(message_text, retry_count=retry_count + 1)

        # Max retries reached
        logger.error(
            f"Prayer extraction failed after {retry_count + 1} attempts for message: "
            f"{message_text[:50]}..."
        )
        return None
