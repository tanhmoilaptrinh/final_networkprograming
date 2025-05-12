import socket
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import datetime

# Client configuration
HOST = 'localhost'
PORT = 12345
BUFFER_SIZE = 1024
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Nối Từ Game")
        self.client_socket = None
        self.name = ""
        self.timer_running = False
        self.time_left = 30
        self.timer_id = None
        self.is_host = False
        self.scores = {}
        self.current_player = ""
        self.current_letter = ""
        self.my_turn = False
        self.current_cycle = 1
        self.setup_gui()
        self.connect_to_server()
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        self.my_turn = False
        self.word_entry.config(state='disabled')

    def setup_gui(self):
        tk.Label(self.root, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(self.root)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Register", command=self.register).grid(row=0, column=2, padx=5, pady=5)

        self.host_label = tk.Label(self.root, text="", fg="blue")
        self.host_label.grid(row=0, column=3, padx=5, pady=5)
        
        self.start_button = tk.Button(self.root, text="Start Game", command=self.start_game, state='disabled')
        self.start_button.grid(row=0, column=4, padx=5, pady=5)

        self.info_display = scrolledtext.ScrolledText(self.root, height=15, width=50, state='disabled')
        self.info_display.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

        tk.Label(self.root, text="Word:").grid(row=2, column=0, padx=5, pady=5)
        self.word_entry = tk.Entry(self.root)
        self.word_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Send Word", command=self.send_word).grid(row=2, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Chat:").grid(row=3, column=0, padx=5, pady=5)
        self.chat_entry = tk.Entry(self.root)
        self.chat_entry.grid(row=3, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Send Chat", command=self.send_chat).grid(row=3, column=2, padx=5, pady=5)

        self.timer_label = tk.Label(self.root, text="Time: 30")
        self.timer_label.grid(row=4, column=0, columnspan=3, pady=5)

        self.score_frame = tk.LabelFrame(self.root, text="Player Scores")
        self.score_frame.grid(row=1, column=3, columnspan=2, rowspan=3, padx=5, pady=5, sticky='nsew')
        
        self.score_labels = {}
        self.word_entry.bind('<Return>', lambda event: self.send_word())
        self.chat_entry.bind('<Return>', lambda event: self.send_chat())

    def update_score_display(self):
        for label in self.score_labels.values():
            label.destroy()
        self.score_labels.clear()

        for i, (player, score) in enumerate(self.scores.items()):
            label_text = f"{player}: {score} points"
            if player == self.name:
                label_text += " (You)"
            label = tk.Label(self.score_frame, text=label_text, font=('Arial', 10))
            label.grid(row=i, column=0, padx=5, pady=2, sticky='w')
            self.score_labels[player] = label

    def connect_to_server(self):
        for attempt in range(RETRY_ATTEMPTS):
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(5)  # Timeout for connection attempt
                self.client_socket.connect((HOST, PORT))
                self.client_socket.settimeout(None)  # Remove timeout after connection
                self.display_message("Connected to server")
                return
            except Exception as e:
                self.display_message(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY)
        messagebox.showerror("Error", "Failed to connect to server after multiple attempts")
        self.root.quit()

    def register(self):
        self.name = self.name_entry.get().strip()
        if not self.name:
            messagebox.showwarning("Warning", "Please enter a name")
            return
        try:
            self.client_socket.send(f"REGISTER {self.name}".encode('utf-8'))
            self.name_entry.config(state='disabled')
            self.display_message("Waiting for server confirmation...")
        except Exception as e:
            self.display_message(f"Error sending registration: {e}")

    def start_timer(self):
        if self.timer_running:
            return
        self.timer_running = True
        self.time_left = 30
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
        self.timer_label.config(text="Time: 30")

    def format_game_message(self, message):
        if "Game starting" in message:
            return f"\n{message}"
        elif "played" in message:
            parts = message.split("'")
            player = parts[0].split()[1]  # Lấy tên người chơi sau "INFO"
            word = parts[1]
            next_letter = word[-1].lower()
            next_player = self.get_next_player(player)
            return f"\nValid! {next_player}'s turn (word must start with '{next_letter}')"
        elif "not valid" in message or "already used" in message:
            return f"[Invalid! next turn]"
        elif "ran out of time" in message:
            return f"[Timeout - {self.current_player} loses points]"
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
            try:
                self.client_socket.send("START".encode('utf-8'))
                self.start_button.config(state='disabled')
            except Exception as e:
                self.display_message(f"Error starting game: {e}")

    def receive_messages(self):
        while True:
            try:
                # Đọc dữ liệu cho đến khi nhận được dấu xuống dòng
                data = b""
                while True:
                    chunk = self.client_socket.recv(BUFFER_SIZE)
                    if not chunk:
                        raise ConnectionError("Server disconnected")
                    data += chunk
                    if b'\n' in chunk:
                        break
                
                messages = data.decode('utf-8', errors='ignore').split('\n')
                for message in messages:
                    message = message.strip()
                    if not message:
                        continue

                    print(f"Received: {message}")

                    if message.startswith('{'):
                        try:
                            json_data = json.loads(message)
                            cycle = json_data.get("Cycle")
                            player = json_data.get("player")
                            word = json_data.get("word")
                            state = json_data.get("state")
                            score_change = json_data.get("score_change")
                            current_score = json_data.get("current_score")
                            timestamp = json_data.get("server_timestamp") or json_data.get("player_timestamp")

                            self.current_cycle = int(cycle)
                            self.scores[player] = current_score
                            self.update_score_display()

                            if state == "accept":
                                self.display_message(f"INFO {player} played '{word}' (+{score_change} points)")
                            elif state == "bonus":
                                self.display_message(f"INFO {player} played '{word}' (+{score_change} points) [Bonus]")
                            elif state == "invalid":
                                self.display_message(f"INFO Word '{word}' is not valid")
                            elif state == "timeout":
                                self.display_message(f"INFO {player} ran out of time ({score_change} points)")

                            # Chỉ log khi nhận phản hồi từ server, và chỉ log lượt của mình
                            if player == self.name:
                                self.stop_timer()
                                self.my_turn = False
                                self.word_entry.config(state='disabled')
                                self.log_play(cycle, player, word, timestamp)

                        except json.JSONDecodeError:
                            self.display_message("Invalid JSON received")
                        continue

                    if "Game starting" in message:
                        self.display_message("Game starting! First player's turn.")
                        self.word_entry.config(state='disabled')
                    
                    elif message.startswith('PROMPT'):
                        letter = message.split()[1]
                        self.my_turn = True
                        self.current_letter = letter
                        self.word_entry.config(state='normal')
                        self.display_message(f"\nYOUR TURN! Enter a word starting with '{letter}':")
                        self.start_timer()
                    
                    elif "You are the host" in message:
                        self.is_host = True
                        self.host_label.config(text="(Host)")
                        self.start_button.config(state='normal')
                        self.display_message("You are the host")
                    
                    elif message.startswith('SCORES'):
                        score_data = message.split(' ', 1)[1]
                        self.scores.clear()
                        for item in score_data.split(','):
                            player, score = item.split(':')
                            self.scores[player] = int(score)
                        self.root.after(0, self.update_score_display)
                    
                    elif message.startswith('CHAT'):
                        self.display_message(message.split(' ', 1)[1])
                    
                    elif message.startswith('ENDGAME'):
                        self.display_message("")
                        self.display_message("Game Over! Final Scores:")
                        scores = message.split(' ', 1)[1].split(',')
                        for score in scores:
                            self.display_message(score)
                        self.root.after(0, lambda: messagebox.showinfo("Game Over", "Game has ended"))
                        break
                    
                    elif message.startswith('INFO'):
                        self.display_message(message[5:])  # Bỏ prefix "INFO"

            except ConnectionError as e:
                self.display_message(f"Error: {e}")
                break
            except Exception as e:
                self.display_message(f"Error receiving message: {e}")
                break

        try:
            self.client_socket.close()
            self.root.after(0, lambda: messagebox.showerror("Connection Lost", "Disconnected from server"))
            self.root.after(0, self.root.quit)
        except:
            pass

    def log_play(self, cycle, player, word, timestamp):
        log_data = {
            "Cycle": str(cycle),
            "player": player,
            "word": word,
            "player_timestamp": timestamp
        }
        try:
            with open("client_log.json", "a") as f:
                json.dump(log_data, f, indent=2)
                f.write("\n")
        except Exception as e:
            self.display_message(f"Error logging play: {e}")

    def send_word(self):
        if not self.my_turn:
            self.display_message("Not your turn!")
            return
        word = self.word_entry.get().strip()
        if word:
            json_data = {
                "Cycle": str(self.current_cycle),
                "player": self.name,
                "word": word,
                "player_timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"
            }
            try:
                json_str = json.dumps(json_data)
                self.client_socket.send(f"{json_str}\n".encode('utf-8'))
                self.log_play(word)
                self.word_entry.delete(0, tk.END)
                self.word_entry.config(state='disabled')
                self.my_turn = False
            except Exception as e:
                self.display_message(f"Error sending word: {e}")

    def send_chat(self):
        message = self.chat_entry.get().strip()
        if message:
            try:
                self.client_socket.send(f"CHAT {message}".encode('utf-8'))
                self.chat_entry.delete(0, tk.END)
            except Exception as e:
                self.display_message(f"Error sending chat: {e}")

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