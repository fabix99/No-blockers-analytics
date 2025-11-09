# Point Outcome Logic Reference

This document outlines all the logic and conditions that determine point outcomes (win/loss) in the Live Event Tracker system.

## Core Principle

**Point Type Determination:**
- If we **win** a point → next point we **serve**
- If we **lose** a point → next point we **receive**

## Point-Winning Conditions

A point is won by our team when:

### 1. Attack Outcomes
- **Kill**: Attack results in a point (ball lands in bounds on opponent's court)
- **Ace**: Serve results in a point (opponent cannot return the serve)

### 2. Block Outcomes
- **Block Kill**: Block results in a point (ball lands in bounds on opponent's court)

### 3. Opponent Errors
- **Opponent Attack Error**: Opponent's attack goes out, into net, or is blocked by us
- **Opponent Serve Error**: Opponent's serve goes out or into net
- **Opponent Receive Error**: Opponent fails to receive our serve
- **Opponent Set Error**: Opponent's set goes out or into net

## Point-Losing Conditions

A point is lost by our team when:

### 1. Our Attack Errors
- **Attack Out**: Our attack lands out of bounds
- **Attack Net**: Our attack hits the net
- **Attack Blocked**: Our attack is blocked and lands on our side

### 2. Our Service Errors
- **Serve Error**: Our serve goes out or into net

### 3. Our Reception Errors
- **Receive Error**: We fail to receive opponent's serve (ball hits floor)

### 4. Our Setting Errors
- **Set Error**: Our set goes out or into net

### 5. General Errors
- **Error**: Any general error committed by our team

## Rotation Logic

### Rotation Sequence
Rotations are numbered 1-6, moving counter-clockwise:
- 1 → 6 → 5 → 4 → 3 → 2 → 1

### Rotation Changes
Rotation **only changes** when:
- We **win** a point while **receiving**
- Rotation moves counter-clockwise (setter position advances)

Rotation **does NOT change** when:
- We win a point while serving (rotation stays same)
- We lose a point (rotation stays same, regardless of serving/receiving)

### Set Start
- At the start of each set, rotation resets to the **Setter Start Rotation** (user-specified, 1-6)

## Set Win Conditions

### Standard Sets
- First team to reach **25 points** wins the set
- Must win by **2 points** (e.g., 25-23, 26-24, 27-25, etc.)
- No maximum point limit (continues until 2-point margin achieved)

### Match Win Conditions
- First team to win **3 sets** wins the match
- Match ends immediately when a team wins their 3rd set

## Score Tracking

### Score Updates
- **We win point**: Our score increases by 1
- **We lose point**: Opponent score increases by 1

### Score Confirmation
- After each point, proposed scores are shown for confirmation
- User can manually edit scores if needed (for corrections)
- Scores are used to determine set wins

## Rally Length

Rally length is calculated as:
- Total number of actions/events recorded during the rally
- Includes all actions: serve, receive, set, attack, block, dig, etc.

## Point Type Tracking

### Initial Point Type
- Determined by **Serve Start** setting:
  - **Yes (We Serve)**: First point is "serving"
  - **No (We Receive)**: First point is "receiving"

### Subsequent Point Types
- Automatically determined by previous point outcome:
  - Previous point **won** → Current point type = **serving**
  - Previous point **lost** → Current point type = **receiving**

## Edge Cases and Special Scenarios

### 1. Rally Ends Without Clear Outcome
- If rally ends without a kill/ace/error, system assumes we lost the point
- **TODO**: May need refinement based on actual gameplay scenarios

### 2. Multiple Actions in Sequence
- All actions in a rally are recorded sequentially
- Only the **final action** determines point outcome
- Intermediate actions (e.g., dig, set) don't directly win/lose points

### 3. Attack Types
- **Normal**: Standard attack
- **Tip**: Tip attack (soft placement)
- **After Block**: Attack after blocking opponent's attack
- Attack type doesn't affect point outcome, only used for analytics

### 4. Block Outcomes
- **Kill**: Block results in point (counts as point won)
- **Touch**: Block touches ball but doesn't win point (rally continues)
- **Missed**: Block attempted but didn't touch ball (rally continues)
- **Error**: Block error (counts as point lost)

### 5. Dig Outcomes
- **Perfect**: Dig within 1m of setter (rally continues)
- **Good**: Dig within 3m (rally continues)
- **Poor**: Dig beyond 3m but playable (rally continues)
- **Error**: Dig error (counts as point lost)

### 6. Set Outcomes
- **Exceptional**: Exceptional set (rally continues)
- **Good**: Good set (rally continues)
- **Poor**: Poor set (rally continues)
- **Error**: Set error (counts as point lost)

### 7. Receive Outcomes
- **Perfect**: Reception within 1m of setter (rally continues)
- **Good**: Reception within 3m (rally continues)
- **Poor**: Reception beyond 3m but playable (rally continues)
- **Error**: Reception error (counts as point lost)

## Data Export Format

### Individual Events Sheet
Columns:
- Set, Point, Rotation, Player, Position, Action, Outcome, Attack_Type, Notes

### Team Events Sheet
Columns:
- Set, Point, Rotation, Point_Type, Point Won, Our_Score, Opponent_Score, Rally_Length

## Future Enhancements

### Areas for Refinement:
1. **Opponent Action Tracking**: Currently assumes opponent actions based on our actions. May need explicit opponent action tracking.
2. **Timeout Handling**: No current handling for timeouts (may need to pause rally tracking)
3. **Substitution Tracking**: No current handling for player substitutions
4. **Challenge/Review**: No current handling for video challenges
5. **Free Ball Detection**: May need better detection of free ball situations
6. **Complex Rally Endings**: More sophisticated logic for determining point outcome from rally sequence
7. **Rotation Validation**: Ensure rotation changes align with actual volleyball rules
8. **Set Transition Handling**: Better handling of set transitions and side changes

## Validation Rules

### Action-Outcome Validation
- Each action must have a valid outcome from `ACTION_OUTCOME_MAP`:
  - `attack`: ['kill', 'blocked', 'out', 'net', 'defended', 'error']
  - `serve`: ['ace', 'good', 'error']
  - `receive`: ['perfect', 'good', 'poor', 'error']
  - `block`: ['kill', 'touch', 'missed', 'error']
  - `set`: ['exceptional', 'good', 'poor', 'error']
  - `dig`: ['perfect', 'good', 'poor', 'error']
  - `free_ball`: ['good', 'error']

### Attack Type Requirement
- `Attack_Type` is **required** when `Action = 'attack'`
- Valid values: `['normal', 'tip', 'after_block']`
- `Attack_Type` is **empty** for all other actions

### Position Validation
- Valid positions: `['S', 'OPP', 'MB1', 'MB2', 'OH1', 'OH2', 'L']`
- Each player must be assigned to a position

## Notes

- This logic is based on standard volleyball rules
- Some simplifications have been made for the initial implementation
- User feedback and real-world usage will help refine these rules
- All point outcome determinations should be reviewed and validated with actual match data


