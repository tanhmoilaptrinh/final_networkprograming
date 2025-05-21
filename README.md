# Networked Word Chain Game

## Group Members and Contributions
| Student ID     | Student name       | Contributions       |
|----------------|--------------------|---------------------|
| 23BI14030      | Tran Thuc Anh      | Leader & Making Server|
| 22BA13001      | Bui Truong An      | Making slide   |
| 22BA13020      | Nguyen Phuong Anh  | Making Client    |
| 22BA13032      | Tran Thuong Nam Anh| Making report   |
| 22BA13102      | Nguyen Tien Duy    | Making Client  |
| 23BI14032      | Nguyen Thi Vang Anh| Making Server   |
| 23BI14356      | Luong Quynh Nhi    | Analysis data|

## Description
- Implement a multiplayer word chain game where each player must provide a word starting with the last letter of the previous player's word.

## Requirements
- Multiplayer word chain game for 2-5 players per session
- Players provide word starting with the last letter of previous word
- Dictionary validation ensures legitimate words
- 30-second turn timer with timeout penalties
- Detection of repeated words
- Score tracking based on word length and speed
- Simple client interface for word submission
- Chat functionality between turns

## Input/Output
- Player registration and game joining interface
- Current game state display (last word, current player, time remaining)
- Word submission input
- Server validation feedback
- End game results with scores

## Game rules
- The first player to join becomes the host and starts the game.
- The first player to reach 50 points wins the game.
- The word must start with the last letter of the previous one.
- The word must be valid (checked against the dictionary).
- No repeated words are allowed during the game.

**Scoring System**
- Correct word → +1 point per character
    - Example: elephant → +8 points
- Fast answer (<5s) → +2 bonus points
- Invalid word → -1 point
- Timeout (no answer) → -2 points

## Example game flow
```
Game starting! Player 1 goes first.
Player 1:
> apple
Valid! Player 2's turn (word must start with 'e'):
> elephant
Valid! Player 3's turn (word must start with 't'):
> tiger
Valid! Player 1's turn (word must start with 'r'):
> rain
Valid! Player 2's turn (word must start with 'n'):
> [timeout - Player 2 loses a point]
```
## Challenges encountered and solutions