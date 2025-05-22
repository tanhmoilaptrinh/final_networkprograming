# Networked Word Chain Game

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

## Build and run instructions

**Requirements**
- Python 3
- Server.py, Client.py and Dictionary.txt in the same directory

**Run instructions**
- Open 2 terminals to play
    - Start the Server in one terminal window
    ```
    python3 server.py
    ```
    - Open a second terminal window and run the Client
    ```
    python3 client.py
    ```


## Challenges encountered and solutions
| Challenges     | Solutions     
|----------------|--------------------|
| Switching the programming language from C to Python         | Python provides higher-level abstractions, simpler syntax, and built-in libraries, making development faster and less error-prone.      |
| Managing sockets and threads (multithreading) in Python          | Python simplifies socket programming with fewer lines of code and easier thread management using the `threading` module. |
| Lack of strong data processing support in C                      | Python has powerful libraries like `pandas` and `numpy` for efficient data handling and analysis, which are not available in C. |
| Invalid/malicious inputs	JSON | Parsing guarded with try/except. |
| Turn fairness and latency |	Server timestamps stored for every response.|
| Difficulty formatting and exporting data for reports             | Python can export data directly to CSV, Excel, or JSON formats with minimal code using `pandas`, streamlining reporting tasks. |

## Group Members and Contributions
| Student ID     | Student name       | Contributions       |
|----------------|--------------------|---------------------|
| 23BI14030      | Tran Thuc Anh      | Leader & Create Server|
| 22BA13001      | Bui Truong An      | Making slide   |
| 22BA13020      | Nguyen Phuong Anh  | Create Client    |
| 22BA13032      | Tran Thuong Nam Anh| Making report   |
| 22BA13102      | Nguyen Tien Duy    | Making Client  |
| 23BI14032      | Nguyen Thi Vang Anh| Making Server   |
| 23BI14356      | Luong Quynh Nhi    | Analysis data|
