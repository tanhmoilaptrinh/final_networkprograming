import socket
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys

# Client configuration
HOST = 'localhost'
PORT = 12345
BUFFER_SIZE = 1024

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Nối Từ Game")
        self.client_socket = None
        self.name = ""
        self.timer_running = False
        self.time_left = 30  # Update to 30 seconds
        self.timer_id = None
        self.is_host = False  # Add host status flag
        self.scores = {}
        self.current_player = ""
        self.current_letter = ""
        self.my_turn = False
        self.setup_gui()

        # GUI components
        self.setup_gui()

        # Connect to server
        self.connect_to_server()

        # Start receiving thread
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        self.my_turn = False
        self.word_entry.config(state='disabled')  # Disable word entry by default

    def setup_gui(self):
        # Name entry
        tk.Label(self.root, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(self.root)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Register", command=self.register).grid(row=0, column=2, padx=5, pady=5)

        self.host_label = tk.Label(self.root, text="", fg="blue")
        self.host_label.grid(row=0, column=3, padx=5, pady=5)
        
        self.start_button = tk.Button(self.root, text="Start Game", command=self.start_game, state='disabled')
        self.start_button.grid(row=0, column=4, padx=5, pady=5)

        # Game info display
        self.info_display = scrolledtext.ScrolledText(self.root, height=15, width=50, state='disabled')
        self.info_display.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

        # Word entry
        tk.Label(self.root, text="Word:").grid(row=2, column=0, padx=5, pady=5)
        self.word_entry = tk.Entry(self.root)
        self.word_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Send Word", command=self.send_word).grid(row=2, column=2, padx=5, pady=5)

        # Chat entry
        tk.Label(self.root, text="Chat:").grid(row=3, column=0, padx=5, pady=5)
        self.chat_entry = tk.Entry(self.root)
        self.chat_entry.grid(row=3, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Send Chat", command=self.send_chat).grid(row=3, column=2, padx=5, pady=5)

        # Timer display
        self.timer_label = tk.Label(self.root, text="Time: 20")
        self.timer_label.grid(row=4, column=0, columnspan=3, pady=5)

        # Bind Enter key
        self.word_entry.bind('<Return>', lambda event: self.send_word())
        self.chat_entry.bind('<Return>', lambda event: self.send_chat())

         # Add score display frame
        self.score_frame = tk.LabelFrame(self.root, text="Player Scores")
        self.score_frame.grid(row=1, column=3, columnspan=2, rowspan=3, padx=5, pady=5, sticky='nsew')
        
        # Score display will be dynamically updated
        self.score_labels = {}
        self.info_display.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

    def update_score_display(self):
        # Clear existing score labels
        for label in self.score_labels.values():
            label.destroy()
        self.score_labels.clear()

        # Create new labels for each player's score
        for i, (player, score) in enumerate(self.scores.items()):
            label_text = f"{player}: {score} points"
            if player == self.name:
                label_text += " (You)"
            label = tk.Label(self.score_frame, text=label_text, font=('Arial', 10))
            label.grid(row=i, column=0, padx=5, pady=2, sticky='w')
            self.score_labels[player] = label

    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to server: {e}")
            self.root.quit()


    def register(self):
        self.name = self.name_entry.get().strip()
        if not self.name:
            messagebox.showwarning("Warning", "Please enter a name")
            return
        self.client_socket.send(f"REGISTER {self.name}".encode('utf-8'))
        self.name_entry.config(state='disabled')
        self.display_message("Waiting for server confirmation...")

    def start_timer(self):
        if self.timer_running:
            return
        self.timer_running = True
        self.time_left = 30  # Set to 30 seconds
        self.update_timer()

    def update_timer(self):
        if self.time_left > 0 and self.timer_running:
            self.timer_label.config(text=f"Time: {self.time_left}")
            self.time_left -= 1
            self.timer_id = self.root.after(1000, self.update_timer)
        else:
            self.timer_running = False
            self.timer_label.config(text="Time: 0")

    def stop_timer(self):
        self.timer_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.timer_label.config(text="Time: 20")

    def format_game_message(self, message):
        if "Game starting" in message:
            return f"\n{message}"
        elif "played" in message:
            # Format: "player played 'word' (+N points)"
            parts = message.split("'")
            player = parts[0].split()[0]
            word = parts[1]
            next_letter = word[-1]
            next_player = self.get_next_player(player)
            return f"\nValid! {next_player}'s turn (word must start with '{next_letter}')"
        elif "INVALID" in message:
            return f"[Invalid! next turn]"
        elif "ran out of time" in message:
            return f"[timeout - {self.current_player} loses a point]"
        return message

    def get_next_player(self, current_player):
        players = list(self.scores.keys())
        if not players:
            return "Next player"
        try:
            idx = players.index(current_player)
            next_idx = (idx + 1) % len(players)
            return players[next_idx]
        except ValueError:
            return "Next player"

    def display_message(self, message):
        self.info_display.config(state='normal')
        formatted_msg = self.format_game_message(message)
        self.info_display.insert(tk.END, formatted_msg + '\n')
        self.info_display.see(tk.END)
        self.info_display.config(state='disabled')

    def start_game(self):
        if self.is_host:
            self.client_socket.send("START".encode('utf-8'))
            self.start_button.config(state='disabled')

    def receive_messages(self):
        while True:
            try:
                # Read all available data
                data = b""
                while True:
                    chunk = self.client_socket.recv(BUFFER_SIZE)
                    data += chunk
                    if len(chunk) < BUFFER_SIZE:
                        break
                messages = data.decode('utf-8', errors='ignore').split('\n')
                for message in messages:
                    message = message.strip()
                    if not message:
                        continue

                    print(f"Received: {message}")  # Debug print

                    if "Game starting" in message:
                        self.display_message(f"Game starting! First player's turn.")
                        self.word_entry.config(state='disabled')
                        
                    elif message.startswith('PROMPT'):
                        letter = message.split()[1]
                        self.my_turn = True
                        self.word_entry.config(state='normal')
                        self.display_message(f"\nYOUR TURN! Enter a word starting with '{letter}':")
                        self.start_timer()
                        
                    elif message.startswith('VALID'):
                        self.stop_timer()
                        self.my_turn = False
                        self.word_entry.config(state='disabled')
                        
                    elif "played" in message:
                        parts = message.split("'")
                        word = parts[1]
                        next_letter = word[-1].lower()
                        self.display_message(f"Valid! Next turn (word must start with '{next_letter}')")
                        
                    elif message.startswith('INVALID'):
                        self.display_message("[Invalid word]")
                        self.stop_timer()
                        self.my_turn = False
                        self.word_entry.config(state='disabled')
                        
                    elif "ran out of time" in message:
                        self.display_message("[Timeout - Player loses a point]")
                        if self.my_turn:
                            self.stop_timer()
                            self.my_turn = False
                            self.word_entry.config(state='disabled')
                    elif message.startswith('INFO'):
                        self.display_message(message)
                    elif "You are the host" in message:
                        self.is_host = True
                        self.host_label.config(text="(Host)")
                        self.start_button.config(state='normal')
                        self.display_message(message)
                    elif message.startswith('SCORE'):
                        # Format: SCORE player1:score1,player2:score2,...
                        score_data = message.split(' ', 1)[1]
                        self.scores.clear()
                        for item in score_data.split(','):
                            player, score = item.split(':')
                            self.scores[player] = int(score)
                        self.root.after(0, self.update_score_display)
                    elif message.startswith('TIMEOUT'):
                        self.display_message(message)
                        if self.my_turn:
                            self.stop_timer()
                            self.my_turn = False
                    elif message.startswith('CHAT'):
                        self.display_message(message.split(' ', 1)[1])
                    elif message.startswith('ENDGAME'):
                        self.display_message("")  # Add a blank line before endgame
                        self.display_message("Game Over! Final Scores:")
                        scores = message.split(' ', 1)[1].split(',')
                        for score in scores:
                            self.display_message(score)
                        self.root.after(0, lambda: messagebox.showinfo("Game Over", "Game has ended"))
                        break
            except:
                break

        # Clean up
        try:
            self.client_socket.close()
            self.root.after(0, self.root.quit)
        except:
            pass

    def send_word(self):
        if not self.my_turn:
            self.display_message("Not your turn!")
            return
        word = self.word_entry.get().strip()
        if word:
            self.client_socket.send(f"WORD {word}\n".encode('utf-8'))
            self.word_entry.delete(0, tk.END)
            self.word_entry.config(state='disabled')  # Disable after sending
            self.my_turn = False

    def send_chat(self):
        message = self.chat_entry.get().strip()
        if message:
            self.client_socket.send(f"CHAT {message}".encode('utf-8'))
            self.chat_entry.delete(0, tk.END)

    def on_closing(self):
        try:
            self.client_socket.close()
        except:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = GameClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
