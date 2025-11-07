# Prayer Management System Design

**Date:** 2025-01-08
**Feature:** Prayer Wall Tracking and Mentor Distribution

## Overview

Add prayer request management to FiT Discord Bot, allowing automatic capture of prayers from the prayer-wall channel and distribution to mentors via `/prayer` slash command.

## Requirements

1. Monitor messages in "prayer-wall" channel
2. Use xAI to extract core prayer requests from messages
3. Store prayers in database with metadata
4. Provide `/prayer` slash command for mentors
5. Send current week's prayers (Monday-Sunday) to mentors via DM

## Architecture

### Component Structure

```
src/
├── main.py                      # Add prayer message handler
├── prayer_extraction.py         # NEW: xAI prayer extraction
├── database.py                  # Add prayers table + queries
└── commands/
    └── slash_commands.py       # Add /prayer command
```

### Data Flow

```
Message in prayer-wall
    ↓
Extract prayer using xAI (retry once)
    ↓
If valid prayer → Store in DB
    ↓
Mentor uses /prayer
    ↓
Query current week's prayers
    ↓
Format and send via DM
```

## Database Schema

### Table: `prayers`

```sql
CREATE TABLE IF NOT EXISTS prayers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    discord_user_id TEXT NOT NULL,
    discord_username TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    raw_message TEXT NOT NULL,
    extracted_prayer TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prayers_posted_at ON prayers(posted_at);
CREATE INDEX IF NOT EXISTS idx_prayers_user_id ON prayers(discord_user_id);
```

**Fields:**
- `message_id`: Discord message ID (unique)
- `discord_user_id`: User who posted prayer
- `discord_username`: Username with discriminator
- `channel_id`: Channel ID (for reference)
- `raw_message`: Original message text
- `extracted_prayer`: AI-cleaned prayer request
- `posted_at`: Message creation timestamp (ISO 8601)
- `created_at`: DB insertion timestamp (ISO 8601)

## Components

### 1. Prayer Extraction Module

**File:** `src/prayer_extraction.py`

**Function:** `extract_prayer(message_text: str) -> str | None`

**Process:**
1. Call xAI API with extraction prompt
2. Model: `grok-beta` (fast extraction)
3. Temperature: 0.3 (deterministic)
4. Timeout: 10 seconds
5. If "NO_PRAYER" or empty → return None
6. If API fails → retry once
7. Second failure → return None

**Prompt:**
```
Extract the core prayer request from this message.
Return only the prayer need in one concise sentence.
If no prayer request exists, return 'NO_PRAYER'.

Message: {message_text}
```

**Error Handling:**
- Network errors: Retry once with exponential backoff
- Rate limit (429): Log and return None
- Timeout: Return None
- All failures logged with message_id

### 2. Database Functions

**File:** `src/database.py`

**New Functions:**

**`save_prayer(prayer_data: dict) -> None`**
- Insert prayer into database
- Commit and sync to Turso
- Log success/failure

**`get_prayers_for_week(start_date: datetime, end_date: datetime) -> list[dict]`**
- Query prayers WHERE posted_at BETWEEN start AND end
- Return: `[{id, discord_username, extracted_prayer, posted_at}, ...]`
- Ordered by posted_at ASC

### 3. Message Capture

**File:** `src/main.py`

**Modify:** `on_message` event handler

**Flow:**
```python
@bot.event
async def on_message(message):
    # Existing: Store for analytics
    await store_message(message)

    # NEW: Handle prayers
    if message.channel.name == "prayer-wall" and not message.author.bot:
        await handle_prayer_message(message)

    # Existing: Text commands
    await handle_text_command(message, command_context)
```

**New Function:** `handle_prayer_message(message)`
1. Extract prayer using `extract_prayer(message.content)`
2. If None → skip storage (log for debugging)
3. If valid → build prayer_data dict
4. Call `save_prayer(prayer_data)`
5. Silent operation (no confirmation message)

### 4. /prayer Slash Command

**File:** `src/commands/slash_commands.py`

**Command:** `/prayer`
**Description:** "Get this week's prayer requests (Mentors only)"

**Flow:**

1. **Role Check**
   - Search roles for "mentor" (case-insensitive)
   - If not found → "❌ This command is only available to mentors." (ephemeral)

2. **Calculate Week**
   - Current Monday 00:00:00 to Sunday 23:59:59
   - Use ISO week definition

3. **Query Database**
   - Call `get_prayers_for_week(start, end)`
   - If empty → "No prayers posted this week (Jan 6-12)."

4. **Format Response**
   ```
   This week's prayers (Jan 6-12):
   1. Mom's surgery tomorrow - @John
   2. Job interview for friend - @Sarah
   3. Healing from illness - @Mary
   ```

5. **Send DM**
   - Create DM channel
   - Send formatted list
   - Respond: "✅ Sent this week's prayers to your DM!"
   - Handle Forbidden error if DMs disabled

## Configuration

### Environment Variables

Add to `.env`:
```bash
XAI_API_KEY=xai-...
```

Reuse existing:
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`

### Dependencies

Add to `requirements.txt`:
```
openai  # For xAI API via OpenAI SDK
```

## Edge Cases

### Empty Week
- No prayers this week → "No prayers posted this week (Jan 6-12)."

### Bot Messages
- Skip using `not message.author.bot`

### Non-Prayer Messages
- Casual chat → AI returns "NO_PRAYER" → not stored
- Only emojis → AI returns "NO_PRAYER" → not stored

### AI Failures
- First failure → retry once
- Second failure → skip storage, log error
- Prayer not captured but system continues

### DM Failures
- Mentor has DMs disabled → "❌ I couldn't send you a DM. Please enable DMs."

### Rate Limiting
- xAI 429 error → log warning, skip storage
- Graceful degradation

### Large Prayer Lists
- If >2000 chars → split into multiple DMs
- Discord message limit handling

## Testing Checklist

### Manual Tests
- [ ] Post prayer in prayer-wall → verify stored
- [ ] Post casual message → verify NOT stored
- [ ] Post emoji-only → verify NOT stored
- [ ] Use `/prayer` as non-mentor → verify rejection
- [ ] Use `/prayer` as mentor → verify DM received
- [ ] Test on Monday (week start)
- [ ] Test on Sunday (week end)
- [ ] Test with no prayers → verify empty message
- [ ] Test with DMs disabled → verify error handling

### Database Tests
- [ ] Verify prayers table created
- [ ] Verify indexes created
- [ ] Query prayers for specific week
- [ ] Verify Turso sync working

### AI Tests
- [ ] Valid prayer → extracted correctly
- [ ] No prayer → returns None
- [ ] API failure → retries once
- [ ] Rate limit → handles gracefully

## Future Enhancements

### Phase 2 Potential Features
- Track which mentors received which prayers (avoid duplicates)
- `/prayer-history` command for past weeks
- Prayer status tracking (answered/ongoing)
- Prayer categories/tags
- Multi-channel support (not just "prayer-wall")
- Analytics: most active prayer requesters, response times

### Technical Improvements
- Batch AI extraction for performance
- Cache week calculations
- Add Redis for distributed mentor tracking
- Webhook notifications when new prayers posted

## Implementation Order

1. Write design document ✓
2. Update database schema (prayers table)
3. Create prayer_extraction.py module
4. Add prayer capture to main.py
5. Add /prayer command to slash_commands.py
6. Manual testing
7. Deploy and monitor

## Success Criteria

- [ ] Prayers automatically captured from prayer-wall
- [ ] Only valid prayers stored (no casual chat)
- [ ] Mentors can retrieve current week's prayers via `/prayer`
- [ ] Prayers formatted clearly in DM
- [ ] System handles AI failures gracefully
- [ ] No disruption to existing bot functionality

---

**Status:** Ready for Implementation
**Estimated Time:** 2-3 hours
**Risk Level:** Low (isolated feature, graceful degradation)
