# Networked Word Chain Game

## Group Members and Contributions
| Student ID     | Student name       | Contributions       |
|----------------|--------------------|---------------------|
| 23BI14030      | Tran Thuc Anh      | Leader &     |
| 22BA13001      | Bui Truong An      | Analysis and Making slide   |
| 22BA13020      | Nguyen Phuong Anh  |    |
| 22BA13032      | Tran Thuong Nam Anh| Analysis and Making report   |
| 22BA13102      | Nguyen Tien Duy    | Dữ liệu D   |
| 23BI14032      | Nguyen Thi Vang Anh| Dữ liệu D   |
| 23BI14356      | Luong Quynh Nhi    | Analysis and Making report   |

## Description
- Implement a multiplayer word chain game where each player must provide a word starting with the last letter of the previous player's word.

## Requirements
- Server managing multiple game rooms with 2-4 players each
- Random number generation (1-100) for each game
- Turn-based gameplay with timeout mechanism
- Scoring system based on number of attempts and speed
- Game chat functionality
- Leaderboard tracking
- Reconnection capability if a player disconnects

## Input/Output
- Player registration and game room selection
- Number guess input
- Server feedback on guess accuracy ("higher", "lower", "correct")
- Game status updates (current player, guesses made)
- Score reporting at the end of each round

## Example game flow
```
Game starting! Secret number is between 1 and 100.
Player 1's turn:
> 50
Too high! Player 2's turn.
> 25
Too low! Player 3's turn.
> 40
Too high! Player 1's turn.
> 30
Correct! Player 1 wins with 2 guesses!
```
## Challenges encountered and solutions