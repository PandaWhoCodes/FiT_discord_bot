# FiT Discord Bot - Engagement Tools Roadmap

This document outlines planned engagement tools for the FiT Discord Bot to foster community interaction and spiritual growth.

---

## 1. Prayer Wall

### Overview
A dedicated prayer channel where community members can post prayer requests. The bot intelligently extracts and stores prayers for easy retrieval and ongoing support.

### Features

#### Prayer Submission
- Users post prayers in a designated prayer channel
- Bot monitors the prayer channel for new messages
- Uses xAI to extract the actual prayer request from the message
- Stores structured prayer data in database

#### Prayer Retrieval - `/prayers` Command
- **Command**: `/prayers` or `prayers`
- **Functionality**: Returns all prayers from the last 7 days
- **Output Format**: Formatted list with:
  - User who posted
  - Prayer request (extracted)
  - Date posted
  - Optional: Reaction count for support

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE prayers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    discord_user_id TEXT NOT NULL,
    discord_username TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    raw_message TEXT NOT NULL,
    extracted_prayer TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prayers_posted_at ON prayers(posted_at);
CREATE INDEX idx_prayers_user_id ON prayers(discord_user_id);
```

#### xAI Integration
- **Purpose**: Extract prayer request from conversational message
- **Input**: Raw message text
- **Output**: Concise prayer request summary
- **Example**:
  - Input: "Hey everyone, I've been struggling with my job search lately. Would really appreciate prayers for wisdom and open doors. Thanks!"
  - Output: "Job search - wisdom and open doors"

#### Commands
1. **`/prayers`**
   - Retrieves prayers from last 7 days
   - Paginated if too many results
   - Each prayer shows username, request, and date

2. **Future**: `/prayers [timeframe]`
   - Options: `today`, `week`, `month`, `all`

#### Configuration
- Environment variable for prayer channel ID
- xAI API credentials in `.env`
- Configurable time window (default 7 days)

### User Flow

1. **Posting a Prayer**
   ```
   User → Posts in #prayer-wall
   Bot → Detects message
   Bot → Calls xAI to extract prayer
   Bot → Stores in database
   Bot → Reacts with 🙏 to confirm
   ```

2. **Viewing Prayers**
   ```
   User → Types /prayers
   Bot → Queries last 7 days
   Bot → Formats and returns list
   User → Can see who needs prayer
   ```

### Future Enhancements (Phase 2)
- Prayer answered/update tracking
- Private prayer requests (DM only)
- Prayer partner matching
- Weekly prayer digest sent to channel
- Analytics on prayer categories
- Reminder notifications for ongoing prayers

---

## 2. Prompt Tuesdays

### Overview
An automated weekly reminder system that encourages channel heads/creators to start conversations with engaging prompts every Tuesday.

### Features

#### Automated Tuesday Reminders
- Sends DM reminder to all channel heads every Tuesday
- Includes a conversation starter prompt
- Scheduled for optimal time (configurable, e.g., 9:00 AM)

#### Prompt Content
- Curated list of conversation starters
- Faith-based discussion questions
- Icebreakers and community-building prompts
- Rotates through prompt library

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE channel_heads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT UNIQUE NOT NULL,
    discord_username TEXT NOT NULL,
    channel_id TEXT,
    channel_name TEXT,
    role TEXT DEFAULT 'creator',
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompt_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text TEXT NOT NULL,
    category TEXT,
    difficulty TEXT DEFAULT 'medium',
    used_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompt_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    sent_to_user_id TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT 0,
    FOREIGN KEY (prompt_id) REFERENCES prompt_library(id)
);
```

#### Scheduling
- Uses `discord.ext.tasks` for scheduled tasks
- Cron-like schedule: Every Tuesday at specified time
- Timezone-aware (configured in `.env`)

#### Commands

1. **`/add-channel-head @user [channel]`** (Admin only)
   - Adds user to channel heads list
   - Optionally associates with specific channel

2. **`/remove-channel-head @user`** (Admin only)
   - Removes user from reminder list

3. **`/test-prompt`** (Admin only)
   - Sends test reminder immediately
   - For testing without waiting until Tuesday

4. **`/add-prompt "prompt text" [category]`** (Admin only)
   - Adds new prompt to library

5. **`/skip-tuesday`** (Channel head)
   - Opts out of next Tuesday's reminder
   - Useful for vacation/busy weeks

#### Prompt Selection Algorithm
```python
def select_weekly_prompt():
    # Prioritize prompts that haven't been used recently
    # Avoid repeating same category consecutively
    # Consider seasonal/relevant themes
    # Fallback to least-used prompts
```

### User Flow

1. **Tuesday Morning**
   ```
   Bot → Checks if Tuesday (cron schedule)
   Bot → Queries list of active channel heads
   Bot → Selects prompt from library
   For each channel head:
       Bot → Sends DM with prompt
       Bot → Logs in prompt_history
   ```

2. **DM Format**
   ```
   🎯 Happy Prompt Tuesday!

   Hey [Username]! Time to spark some conversation in the community.

   Here's this week's prompt:
   "If you could have dinner with any Biblical figure, who would it be and why?"

   Feel free to post this in your channel or modify it to fit your community's vibe!

   Want to skip next week? Use /skip-tuesday
   ```

3. **Admin Management**
   ```
   Admin → /add-channel-head @john #general
   Bot → "Added @john as channel head for #general"
   Bot → Will receive Tuesday reminders
   ```

### Configuration

Environment variables in `.env`:
```bash
# Prompt Tuesdays Configuration
PROMPT_TUESDAY_TIME=09:00  # 9 AM local time
PROMPT_TUESDAY_TIMEZONE=America/New_York
ADMIN_ROLE_ID=1234567890  # Role ID for admin commands
```

### Sample Prompts Library

**Icebreakers**
- "What's your favorite worship song right now and why?"
- "Share a 'God moment' from this week"
- "If you could have dinner with any Biblical figure, who would it be?"

**Deep Questions**
- "How has your faith journey changed in the last year?"
- "What's a Bible verse that's speaking to you lately?"
- "What does 'Faith in Tech' mean to you personally?"

**Fun & Lighthearted**
- "What's your go-to Bible app feature?"
- "Coffee or tea for your morning devotional?"
- "Share your favorite Christian podcast/YouTuber"

**Community Building**
- "What's something you're grateful for this week?"
- "How can we pray for you this week?"
- "What's a talent/skill you'd like to share with the community?"

### Future Enhancements (Phase 2)
- AI-generated prompts based on community trends
- Prompt voting system (community picks next week's)
- Track engagement metrics per prompt
- A/B testing different prompt styles
- Category-specific prompts per channel type
- Integration with church calendar (advent, lent, etc.)

---

## Implementation Priority

### Phase 1 (MVP)
1. **Prayer Wall** - Core functionality
   - Basic prayer storage and retrieval
   - xAI extraction
   - `/prayers` command

2. **Prompt Tuesdays** - Core functionality
   - Channel head management
   - Weekly scheduled reminders
   - Basic prompt library

### Phase 2 (Enhancements)
- Advanced prayer features (tracking, partners)
- Prompt analytics and optimization
- Admin dashboard
- User preferences and customization

### Phase 3 (Scale)
- Multi-server support
- API for external integrations
- Mobile app companion
- Advanced AI features

---

## Technical Considerations

### xAI Integration
- API endpoint: TBD (xAI API documentation)
- Rate limiting considerations
- Fallback if xAI unavailable (store raw message)
- Cost estimation per prayer extraction

### Performance
- Prayer retrieval should be <500ms
- Database indexing on timestamps and user IDs
- Pagination for large result sets
- Caching for frequently accessed prayers

### Privacy & Moderation
- Prayer channel visibility settings
- Optional private/public prayers
- Moderation tools for inappropriate content
- Data retention policies (GDPR compliance)

### Reliability
- Error handling for failed xAI calls
- Graceful degradation if services unavailable
- Logging for debugging
- Health checks for scheduled tasks

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Status**: Planning Phase
**Owner**: FiT Discord Bot Team
