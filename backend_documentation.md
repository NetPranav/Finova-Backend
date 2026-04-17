# Finova Backend Documentation

This document provides a comprehensive, detailed breakdown of every model (and its variables/functions), view, and serializer created across the **Users**, **groups**, and **chat** sections of the Finova backend. 

---

## 1. **Users App (`Users`)**

The `Users` app forms the foundation for authentication, user profiles, and gamification tracking within Finova.

### **Models (`models.py`)**

#### **Function: `generate_finova_id()`**
- **What it does:** Generates a unique 6-character alphanumeric code (e.g., `FHW397`) used for user lookup and direct messaging. It validates against the database to ensure no duplicates.

#### **Class: `User` (inherits `AbstractUser`)**
The central user profile containing authentication data, personal info, and platform statistics.

**Variables (Fields):**
- `id`: A unique UUID4 acting as the primary key.
- `finova_id`: Auto-generated, 6-character unique identifier for public profiles.
- `username`: Required, unique identifier for login/display.
- `email`: Required, unique primary identifier for login and notifications.
- `first_name` & `last_name`: Personal name fields.
- `date_of_birth`: Used for age verification (must be 18+) and demographics.
- `gender_identity`: Chosen from dropdown (woman, man, non-binary, etc.).
- `gender_identity_custom`: Freespace text if 'other' is selected for gender.
- `profile_picture`: Image upload path to Amazon S3 / local media folder.
- `bio`: Short user description (max 500 chars).
- `is_verified`: Boolean tracking if the user has validated their email.
- `phone_number`: Optional for 2FA tracking.
- `individual_virtual_capital`: Decimal amount tracking personal simulated funds available to deposit into group pools. Defaults to ₹55,000 for women and ₹30,000 for men.
- `consensus_score`: Gamification points awarded for positive engagement.
- `learning_level`: Tier (1-10) tracking feature unlocks and platform knowledge.
- `user_level`: Categorization (beginner, intermediate, advanced, expert).
- `total_reels_watched`: Engagement stat tracking video content consumed.
- `total_votes_cast`: Tracks how many stock polls the user has participated in.
- `notification_preferences` & `privacy_settings`: JSON fields to store user configurations.
- `created_at` & `updated_at` & `last_login`: Standard timestamps.

**Functions/Methods:**
- `__str__()`: Returns a string representation like `@username [FINOVAID] (email)`.
- `save()`: Overridden to automatically generate a `finova_id` if missing, and assign starting virtual capital based on `gender_identity` upon creation.
- `get_full_name()`: Returns merged first and last name, or falls back to username.
- `get_short_name()`: Returns just first name or username.
- `@property age`: Dynamically calculates the exact age of the user today using `date_of_birth`.
- `@property display_gender()`: Returns the readable version of `gender_identity`, or `gender_identity_custom` if "Other" was picked.
- `increment_consensus_score(points=1)`: Utility to easily add points to the user's trust score and save to DB.
- `mark_reel_watched()`: Automates incrementing the reels engagement metric.
- `record_vote()`: Automates incrementing the vote count metric.

### **Views (`views.py`)**

- **`UserRegistrationView`**: Exposes `POST /api/users/register/`. Uses `generate_finova_id` and age validation to create an account. Open to `AllowAny`.
- **`UserViewSet`**: Main CRUD interface for user modification. 
  - `get_queryset()`: Allows searching users by username or filtering by verified status.
  - `@action me()`: Retrieves the profile of the current logged-in user.
  - `@action update_profile()`: Wrapper around `UserUpdateSerializer` to modify user details.
  - `@action change_password()`: Secure endpoint confirming the old password before changing it to the new one.
  - `@action stats()`: Grabs just the gamification attributes (consensus score, learning level).
  - `@action verify_email()`: Placeholder endpoint to flip `is_verified` to True.
  - `@action deactivate_account()`: Performs a soft-delete (flips `is_active` to False) instead of permanently deleting the user records.

---

## 2. **Groups App (`groups`)**

This handles the collaborative investing mechanics: joining pods, sharing capital pools, discussing stock proposals, and invoking consensus voting with the dynamic timer mechanisms.

### **Models (`models.py`)**

#### **Class: `Group`**
**Variables:**
- `id`, `finova_id` (e.g. GRP-XYZ123), `name`, `description`, `guidelines`, `group_photo`.
- `risk_level`: String indicating trading aggression (conservative, moderate, aggressive).
- `max_members`: Integer limit on the group size (2-50).
- `created_by`: Foreign key pointing to the user who made the group.
- `is_active`, `created_at`, `updated_at`.

**Functions:**
- `save()`: Generates a distinct group finova-id using `generate_group_finova_id()`.
- `@property member_count`: Returns total active members.
- `@property is_full`: Returns `True` if `member_count` >= `max_members`.

#### **Class: `GroupMember`**
**Variables:** `id`, `group` (FK), `user` (FK), `role` (admin, moderator, member), `is_active`, `joined_at`. Tracks who is in what group and what moderation privileges they hold.

#### **Class: `GroupWallet`**
**Variables:** `id`, `group` (OneToOne), `current_balance` (Decimal), `updated_at`. Holds the pooled funds from members.

#### **Class: `WalletTransaction`**
**Variables:** `id`, `wallet` (FK), `user` (FK), `amount`, `transaction_type` (deposit, withdraw, locked, refund), `reference_id` (to link back to a poll ID), `created_at`. Acts as an indelible ledger ensuring money is never lost during atomic locks.

#### **Class: `GroupMessage`**
**Variables:** 
- `id`, `group`, `sender`, `content`.
- `message_type`: Enum for 'text', 'stock_card', 'news_card', 'system'.
- `stock_symbol`: Populated dynamically if a `/stocks AAPL` string is found.
- `reply_to`: Recursive FK allowing thread replies. 
- `is_pinned`: Boolean if an admin has pinned it.

**Functions:**
- `save()`: Contains parser logic utilizing `detect_message_type(self.content)` to see if the user triggered a stock/news command to spin up UI Cards automatically.

#### **Class: `Discussion` (The Proposal Pipeline)**
**Variables:**
- `id`, `group`, `proposed_by`.
- `stock_symbol` (e.g. AAPL), `stock_name`.
- `discussion_type`: 'buy', 'sell', or 'hold'.
- `reasoning`: Text explaining the proposal.
- `status`: Tracking pipeline ('open', 'pooling', 'voting', 'executed', etc.).
- `min_engagement_to_unlock_vote`: Threshold of comments required before a vote happens (default 3).
- `engagement_count`: Real-time tracker for the threshold.
- `required_capital`: Money needed.
- `expires_at`: Timer restricting how long the proposal lingers in the 'pooling' phase waiting for deposits before background tasks kill it.

**Functions:**
- `@property can_unlock_voting`: Checks if `status == 'open'` AND `engagement_count >= min_engagement_to_unlock_vote`.
- `unlock_voting()`: Transitions state from 'open' -> 'voting', triggers creation of a linked `TradePoll` model for formal polling, and stamps `voting_unlocked_at`.

#### **Class: `DiscussionComment`**
**Variables:** `id`, `discussion`, `author`, `content`, `created_at`. Links chat debate directly to the proposal and increments `engagement_count`.

#### **Class: `TradePoll` (Consensus Protocol)**
**Variables:**
- `id`, `discussion` (OneToOne).
- `quorum_percentage`: Win threshold required (default 60%).
- `voting_deadline`: Live countdown timestamp.
- `original_deadline`: Hardcoded 24-hr mark.
- `reduced_deadline`: Time drop point if turbo triggers.
- `turbo_reduction_applied`: Boolean preventing re-triggering.
- `status`: ('active', 'passed', 'failed', 'expired').
- `result_buy_count`, `result_sell_count`, `result_hold_count`: Flat integers tallying counts.

**Functions:**
- `@property total_votes`: Adds up the 3 tally variables.
- `@property total_eligible_voters`: Hits the `Group` model mapping.
- `@property is_expired`: Validates if `timezone.now() > voting_deadline`.
- `@property quorum_met`: Calculation verifying if participation percentage breaches `quorum_percentage`.
- `apply_turbo_reduction()`: **CRITICAL LOGIC.** Observes if `total_votes == total_eligible_voters`. If true, it multiplies the remaining time delta by 0.05 (reducing time remaining by 95%), modifying `voting_deadline`.
- `resolve()`: Invoked when the deadline ends. Verifies if quorum is met, checks which option won strictly by comparing `buy`, `sell`, and `hold` values, updates its own `status`, and updates the parent `Discussion.status` (e.g., to 'executed').

#### **Class: `Vote`**
**Variables:** `id`, `poll` (FK), `voter` (FK), `choice` ('buy', 'sell', 'hold'), `cast_at`. Enforces via Constraints that one user = one vote per poll.

---

### **Views (`views.py`)**

- **`GroupLookupMixin`**: Helper that injects `get_group()` to lookup Groups using string `finova_id` rather than raw UUIDs.
- **`GroupViewSet`**: 
  - `join()`: Validates sizing metrics and ties User to GroupMember.
  - `leave()`: Disables membership (unless only admin is leaving).
  - `members()`, `promote()`, `kick()`: Admin commands for user hierarchy moderation.
  - `deposit()`, `withdraw()`: **CRITICAL LOGIC.** Implements `transaction.atomic()` alongside `.select_for_update()` to lock the `User` and `GroupWallet` rows. Prevents race-condition exploits. Modifies user individual funds relative to group pool funds, then logs in `WalletTransaction`.
- **`GroupMessageViewSet`**:
  - Automatically ties messages to groups and sends it to the chat payload.
  - `pin()`: Moderator endpoint to flip `is_pinned`.
- **`DiscussionViewSet`**:
  - `comment()`: Writes a comment, increments engagement count, then checks if it should call `unlock_voting()` on the parent model.
  - `direct_vote()`: **BYPASS ROUTE**. Immediately pushes past the discussion phase. Evaluates `group.wallet.current_balance`. If capital is sufficient, pushes state to 'voting' and spins up `TradePoll`. If insufficient, pushes state to 'pooling' and appends an `expires_at` timer so members can scramble to deposit money.
- **`TradePollViewSet`**:
  - `vote()`: Receives a 'buy/sell/hold' post. Fails if poll is expired or duplicate. Increases matching string `result_*_count` by +1. Increments global user vote stats. Calls `apply_turbo_reduction()`. Finally, checks if quorum was met and auto-calls `resolve()` if so.

---

## 3. **Chat App (`chat`)**

Manages global 1:1 direct messaging outside of the Investment Pods. Features an architecture mapped entirely by `finova_id`.

### **Models (`models.py`)**

#### **Class: `Conversation`**
**Variables:**
- `id`, `participant_one` & `participant_two` (FK to Users), `is_active`, `created_at`, `updated_at`.
- *Constraints*: Imposes a `UniqueConstraint` on `participant_one` + `participant_two` pairs so duplicate chats cannot exist between two people.

**Functions:**
- `get_other_participant(user)`: Utility to quickly map whose name/profile picture should render based on who requested the API.
- `@property last_message`: Grabs the most recent `DirectMessage` generated inside this thread.
- `@property unread_count_for`: Pass-through shell handled later in the Serializer.

#### **Class: `DirectMessage`**
**Variables:**
- `id`, `conversation` (FK), `sender` (FK), `content`, `reply_to` (for threading).
- `message_type` & `stock_symbol`: Exact same UI detection logic used in Groups.
- `is_read`: Boolean determining read receipts. 
- `created_at`.

**Functions:**
- `save()`: Triggers `detect_message_type()` from `groups.utils` to evaluate if `/stocks` or `/news` tags were invoked, flipping the `message_type` field appropriately.

---

### **Views (`views.py`)**

- **`StartConversationView` (`/start/`)**: 
  - User submits a target `finova_id`. Looks up the DB explicitly searching with `Q` objects: `(p1=Me & p2=Them) OR (p1=Them & p2=Me)`. If found, redirects to the existing chat ID. If not found, initializes a new `Conversation` row.
- **`FindUserView` (`/find/<finova_id>/`)**:
  - Lookup protocol for client UI to grab profile picture, bio, and verification of user before initiating a chat string.
- **`ConversationListView`**:
  - Fetches all active message threads for the token holder, sorted by `-updated_at` (bumping active threads to the top). 
- **`ConversationMessageListView`**:
  - Retrieves the timeline of messages for a single Thread ID. Verifies using strict logical gates that the requester is explicitly Participant 1 or Participant 2.
  - Upon POST, updates the parent `Conversation`'s `updated_at` field so the chat list order moves the thread to the top.
- **`MarkReadView` (`/read/`)**:
  - Fires an `update(is_read=True)` patch modifying all `DirectMessage` rows inside a specific conversation that do NOT belong to the requester (i.e. changing the other person's messages from "unread" to "read").
