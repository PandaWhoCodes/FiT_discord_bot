# Discord MBTI Personality Bot - Design Document

**Date:** 2025-11-05
**Status:** Approved

## Overview

A Discord bot that administers a comprehensive 40+ question MBTI personality test via slash command `/get-personality`. Users interact through step-by-step button clicks, and receive results connecting their personality type to Biblical characters, spiritual gifts, and ministry suggestions.

## Architecture

### Clean Architecture Pattern

```
discord_personality_check/
├── domain/              # Core business logic (no dependencies)
│   ├── models/         # MBTI types, Question, TestResult, User
│   ├── services/       # PersonalityCalculator, ResultsGenerator
│   └── interfaces/     # Repository contracts
├── application/         # Use cases & orchestration
│   ├── commands/       # StartTestCommand, SubmitAnswerCommand
│   └── queries/        # GetUserResultQuery
├── infrastructure/      # External concerns
│   ├── discord/        # Discord.py bot, interaction handlers
│   ├── database/       # SQLite repositories
│   └── loaders/        # YAML question loader
└── tests/
    ├── unit/           # Domain & application tests
    └── integration/    # Database & loader tests
```

### Key Dependencies
- `discord.py` (v2.x) for Discord interactions
- `pydantic` for data validation and models
- `sqlite3` (stdlib) for persistence
- `pyyaml` for question configuration
- `pytest` for testing
- `python-dotenv` for configuration

## Domain Models

### Core Entities

**PersonalityDimension Enum:**
- E/I (Extraversion/Introversion)
- S/N (Sensing/Intuition)
- T/F (Thinking/Feeling)
- J/P (Judging/Perceiving)

**Question Model:**
- id: str
- text: str
- dimension: PersonalityDimension
- options: List[Option] (each option has weight -2 to +2)

**TestSession Model:**
- session_id: UUID
- user_id: int (Discord user ID)
- answers: Dict[question_id, selected_option]
- current_question_index: int
- started_at: datetime
- completed: bool

**PersonalityResult Model:**
- mbti_type: str (e.g., "INTJ")
- dimension_scores: Dict[dimension, score]
- biblical_characters: List[str]
- spiritual_gifts: List[str]
- ministry_suggestions: List[str]
- description: str

### Core Services

**PersonalityCalculator:**
- Pure business logic
- Takes answers, calculates scores per dimension
- Determines MBTI type from scores
- No side effects, fully testable

**ResultsGenerator:**
- Content generation
- Takes MBTI type, returns Biblical interpretation
- Loads character/ministry mappings from data files
- Deterministic output for same input

## Application Layer

### Command Handlers

**StartTestCommand:**
- Input: Discord user ID, interaction context
- Creates new TestSession in database
- Loads first question
- Returns formatted Discord message with buttons
- Idempotent: if active session exists, resume it

**SubmitAnswerCommand:**
- Input: session_id, question_id, selected_option
- Validates session exists and isn't completed
- Records answer in session
- If more questions: return next question
- If complete: invoke PersonalityCalculator, save result, return formatted results

**GetPastResultQuery:**
- Input: Discord user ID
- Returns most recent completed test result
- Used for "view previous result" functionality

### Session Management
- Sessions stored in database with 24-hour expiration
- Background cleanup task removes abandoned sessions
- Users can only have one active session at a time

### Error Handling
- Domain layer: raises custom exceptions (InvalidSessionError, etc.)
- Application layer: catches and translates to user-friendly messages
- Infrastructure layer: handles Discord API errors, logs technical details

## Infrastructure

### Discord Integration

**Bot Configuration:**
- Uses discord.py with slash commands
- Intents: guilds, guild_messages (minimal permissions)
- Slash command: `/get-personality`
- Button interactions for A/B/C/D answers
- Ephemeral messages (only visible to user taking test)

**Interaction Flow:**
1. User types `/get-personality`
2. Bot creates session, sends first question as ephemeral message
3. Message shows question text, four buttons (A, B, C, D), progress indicator
4. User clicks button → bot edits message to show next question
5. After final answer → bot displays results
6. Results include "View Details" button for expanded information

**Button Components:**
- Custom IDs encode: `answer:{session_id}:{question_id}:{option_index}`
- 15-minute interaction timeout (Discord limit)
- Buttons disabled after selection to prevent double-clicks

**Message Formatting:**
- Discord embeds for clean appearance
- Color coding: Blue for questions, Green for results
- Emoji indicators for personality dimensions

### Database Schema

```sql
-- users table
user_id INTEGER PRIMARY KEY  -- Discord user ID
first_test_date TIMESTAMP
last_test_date TIMESTAMP

-- test_sessions table
session_id TEXT PRIMARY KEY  -- UUID
user_id INTEGER
started_at TIMESTAMP
completed_at TIMESTAMP
current_question_index INTEGER
answers JSON  -- Stored as JSON blob

-- test_results table
result_id INTEGER PRIMARY KEY
user_id INTEGER
session_id TEXT
mbti_type TEXT
dimension_scores JSON
completed_at TIMESTAMP
FOREIGN KEY (user_id) REFERENCES users(user_id)
```

**Repository Pattern:**
- `ITestSessionRepository` interface in domain
- `SQLiteTestSessionRepository` implementation in infrastructure
- `ITestResultRepository` interface in domain
- `SQLiteTestResultRepository` implementation in infrastructure
- All repositories use context managers for connection handling

### Data Files

**questions.yaml:**
```yaml
questions:
  - id: "ei_01"
    text: "At social gatherings, you usually..."
    dimension: "EI"
    options:
      - text: "Seek out new people to meet"
        weight: 2
      - text: "Stick with people you know"
        weight: -2
```

**personality_profiles.yaml:**
```yaml
INTJ:
  biblical_characters: ["Apostle Paul", "Moses", "Daniel"]
  spiritual_gifts: ["Teaching", "Knowledge", "Leadership"]
  ministry_suggestions: ["Strategic planning", "Theology teaching", "Mission strategy"]
  description: "The Architect - Strategic and independent thinker..."
```

## Testing Strategy

### Unit Tests (Domain & Application)
- `test_personality_calculator.py`: Score calculation with known answer sets
- `test_results_generator.py`: Verify correct Biblical profiles returned
- `test_commands.py`: Test command logic with mocked repositories
- Mock all infrastructure dependencies

### Integration Tests
- `test_sqlite_repositories.py`: Test actual database operations with in-memory SQLite
- `test_yaml_loader.py`: Verify questions load correctly from YAML
- Use pytest fixtures for test data setup

**Test Coverage Goal:** 80%+ on domain and application layers

## Local Development Setup

### Environment Configuration
```
# .env file
DISCORD_BOT_TOKEN=your_token_here
DATABASE_PATH=./data/personality_test.db
```

### Setup Steps
1. Create Discord bot at https://discord.com/developers
2. Enable "bot" and "applications.commands" scopes
3. Copy bot token to .env
4. Run: `python -m venv venv`
5. Run: `source venv/bin/activate`
6. Run: `pip install -r requirements.txt`
7. Run: `python -m src.main`
8. Bot comes online, slash command registers automatically

### Development Features
- Logging configured for DEBUG level in local
- Sample questions.yaml with 44 curated MBTI questions included
- All 16 personality profiles pre-written in personality_profiles.yaml

## Migration Path to Turso

SQLite is used for local development. Migration to Turso DB requires:
1. Change connection string in repository configuration
2. Use libsql-client instead of sqlite3
3. No schema changes needed - Turso is SQLite-compatible
