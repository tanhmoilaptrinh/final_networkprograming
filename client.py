import socket
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import datetime
from PIL import Image, ImageTk
import random
import os


AVATARS = ['avatar1.jpg', 'avatar2.jpg', 'avatar3.jpg', 'avatar4.jpg', 'avatar5.jpg']
HOST = 'localhost'
PORT = 12345
BUFFER_SIZE = 1024
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Networked Word Chain Game")
        self.client_socket = None
        self.name = ""
        self.timer_running = False
        self.time_left = 30
        self.timer_id = None
        self.is_host = False
        self.scores = {}
        self.player_avatars = {}  
        self.current_player = ""
        self.current_letter = ""
        self.my_turn = False
        self.current_cycle = 1
        self.selected_avatar = None  
        self.setup_gui()
        self.connect_to_server()
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        self.my_turn = False
        self.word_entry.config(state='disabled')

    def setup_gui(self):
        # Main frames
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.middle_frame = tk.Frame(self.root)
        self.middle_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        # Top frame - Player info and controls
        tk.Label(self.top_frame, text="Name:").pack(side=tk.LEFT, padx=5)
        self.name_entry = tk.Entry(self.top_frame, width=15)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        
        self.register_button = tk.Button(self.top_frame, text="Register", command=self.register)
        self.register_button.pack(side=tk.LEFT, padx=5)
        
        self.host_label = tk.Label(self.top_frame, text="", fg="blue")
        self.host_label.pack(side=tk.LEFT, padx=5)
        
        self.start_button = tk.Button(self.top_frame, text="Start Game", command=self.start_game, state='disabled')
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.timer_label = tk.Label(self.top_frame, text="Time: 30")
        self.timer_label.pack(side=tk.RIGHT, padx=10)

        # Middle frame - Chat display and scores
        self.chat_frame = tk.Frame(self.middle_frame)
        self.chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.score_frame = tk.LabelFrame(self.middle_frame, text="Player Scores", width=200)
        self.score_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        # Chat display with scrollbar
        self.chat_canvas = tk.Canvas(self.chat_frame, bg='white', width=400)
        self.scrollbar = tk.Scrollbar(self.chat_frame, command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.chat_inner_frame = tk.Frame(self.chat_canvas, bg='white')
        self.chat_canvas.create_window((0, 0), window=self.chat_inner_frame, anchor='nw')
        
        self.chat_inner_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(
            scrollregion=self.chat_canvas.bbox("all")))

        # Bottom frame - Input controls
        tk.Label(self.bottom_frame, text="Word:").pack(side=tk.LEFT, padx=5)
        self.word_entry = tk.Entry(self.bottom_frame, width=25)
        self.word_entry.pack(side=tk.LEFT, padx=5)
        self.word_entry.bind('<Return>', lambda event: self.send_word())
        
        tk.Button(self.bottom_frame, text="Send Word", command=self.send_word).pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.bottom_frame, text="Chat:").pack(side=tk.LEFT, padx=5)
        self.chat_entry = tk.Entry(self.bottom_frame, width=25)
        self.chat_entry.pack(side=tk.LEFT, padx=5)
        self.chat_entry.bind('<Return>', lambda event: self.send_chat())
        
        tk.Button(self.bottom_frame, text="Send Chat", command=self.send_chat).pack(side=tk.LEFT, padx=5)

        # Initialize score labels
        self.score_labels = {}

    def load_avatar(self, image_path, size=(40, 40)):
        try:
            # Create a new image if it doesn't exist
            if not os.path.exists(image_path):
                img = Image.new('RGB', size, color=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))
                img.save(image_path, 'JPEG')
            img = Image.open(image_path)
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading avatar: {e}")
            # Fallback avatar if image loading fails
            img = Image.new('RGB', size, color='gray')
            return ImageTk.PhotoImage(img)

    def assign_avatar(self, player_name, avatar_filename):
        """Assign avatar to client."""
        if player_name not in self.player_avatars and player_name != "System":
            try:
                # Create avatars directory if it doesn't exist
                if not os.path.exists('avatars'):
                    os.makedirs('avatars')
                
                avatar_path = os.path.join('avatars', avatar_filename)
                print(f"Attempting to load avatar: {avatar_path}")
                avatar_image = self.load_avatar(avatar_path, (40, 40))
                if avatar_image:
                    self.player_avatars[player_name] = avatar_image
                    print(f"Successfully assigned avatar {avatar_filename} to {player_name}")
                else:
                    print(f"Failed to load avatar {avatar_filename} for {player_name}")
                # Update score display
                self.root.after(0, self.update_score_display)
            except Exception as e:
                print(f"Error assigning avatar to {player_name}: {e}")
                # Fallback: assign a gray avatar
                img = Image.new('RGB', (40, 40), color='gray')
                self.player_avatars[player_name] = ImageTk.PhotoImage(img)
                self.root.after(0, self.update_score_display)

    def update_score_display(self):
        for widget in self.score_frame.winfo_children():
            widget.destroy()

        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        
        for player, score in sorted_scores:
            frame = tk.Frame(self.score_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            if player in self.player_avatars:
                avatar_label = tk.Label(frame, image=self.player_avatars[player])
                avatar_label.image = self.player_avatars[player]
                avatar_label.pack(side=tk.LEFT)
            
            label_text = f"{player}: {score}"
            if player == self.name:
                label_text += " (You)"
                
            label = tk.Label(frame, text=label_text, font=('Arial', 10))
            label.pack(side=tk.LEFT, padx=5)

    def add_message_to_chat(self, sender, text, is_word=False, is_me=False):
        msg_frame = tk.Frame(self.chat_inner_frame, bg='white')
        msg_frame.pack(fill=tk.X, pady=2)
        
        if sender != "System" and sender in self.player_avatars:
            avatar_frame = tk.Frame(msg_frame, bg='white')
            avatar_frame.pack(side=tk.LEFT, padx=(5, 0))
            
            avatar_label = tk.Label(avatar_frame, image=self.player_avatars[sender], bg='white')
            avatar_label.image = self.player_avatars[sender]
            avatar_label.pack()
        elif sender == "System":
            tk.Frame(msg_frame, width=45, bg='white').pack(side=tk.LEFT)
        
        msg_bg = '#f0f2f5'
        if is_me:
            msg_bg = '#e5f6ff'
        elif sender == "System":
            msg_bg = '#f0f0f0'
            
        msg_container = tk.Frame(msg_frame, bg=msg_bg)
        msg_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        if sender != "System":
            name_label = tk.Label(msg_container, 
                                 text=sender + (" (You)" if is_me else ""), 
                                 bg=msg_container['bg'],
                                 fg='#385898',
                                 font=('Arial', 9, 'bold'),
                                 anchor='w')
            name_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        msg_label = tk.Label(msg_container, 
                            text=text,
                            bg=msg_container['bg'],
                            fg='#1c1e21',
                            font=('Arial', 10),
                            anchor='w',
                            justify='left',
                            wraplength=300)
        msg_label.pack(fill=tk.X, padx=5, pady=(0 if sender == "System" else 5, 5))
        
        self.chat_canvas.yview_moveto(1.0)

    def connect_to_server(self):
        for attempt in range(RETRY_ATTEMPTS):
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(5)
                self.client_socket.connect((HOST, PORT))
                self.client_socket.settimeout(None)
                self.add_message_to_chat("System", "Connected to server")
                return
            except Exception as e:
                self.add_message_to_chat("System", f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY)
        messagebox.showerror("Error", "Failed to connect to server after multiple attempts")
        self.root.quit()

    def register(self):
        self.name = self.name_entry.get().strip()
        if not self.name:
            messagebox.showwarning("Warning", "Please enter a name")
            return
        # Randome avatar
        self.selected_avatar = random.choice(AVATARS)
        try:
            self.client_socket.send(f"REGISTER {self.name} {self.selected_avatar}\n".encode('utf-8'))
            self.name_entry.config(state='disabled')
            self.register_button.config(state='disabled')
            self.assign_avatar(self.name, self.selected_avatar)
            self.add_message_to_chat("System", "Registering name...")
        except Exception as e:
            self.add_message_to_chat("System", f"Error sending registration: {e}")
            self.name_entry.config(state='normal')
            self.register_button.config(state='normal')

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

    def start_game(self):
        if self.is_host:
            try:
                self.client_socket.send("START\n".encode('utf-8'))
                self.start_button.config(state='disabled')
            except Exception as e:
                self.add_message_to_chat("System", f"Error starting game: {e}")
        else:
            self.add_message_to_chat("System", "Only the host can start the game!")

    def receive_messages(self):
        buffer = b""
        while True:
            try:
                chunk = self.client_socket.recv(BUFFER_SIZE)
                if not chunk:
                    raise ConnectionError("Server disconnected")
                buffer += chunk

                while b'\n' in buffer:
                    message, buffer = buffer.split(b'\n', 1)
                    message = message.decode('utf-8', errors='ignore').strip()
                    if not message:
                        continue

                    print(f"Client received: {message}")  # Debug log

                    if message.startswith('INFO Registration successful'):
                        self.root.after(0, lambda: self.add_message_to_chat("System", "Registration successful!"))
                        continue
                        
                    if message.startswith('INFO Name already taken'):
                        self.root.after(0, lambda: self.add_message_to_chat("System", "Name already taken. Please choose another name."))
                        self.root.after(0, lambda: self.name_entry.config(state='normal'))
                        self.root.after(0, lambda: self.register_button.config(state='normal'))
                        continue
                        
                    if message.startswith('INFO Player') and 'joined with avatar' in message:
                        parts = message.split(' ')
                        if len(parts) >= 5:  
                            player_name = parts[2]
                            avatar_filename = parts[-1]
                            print(f"Received avatar assignment: {player_name} -> {avatar_filename}")
                            self.assign_avatar(player_name, avatar_filename)
                            self.root.after(0, lambda pn=player_name: self.add_message_to_chat("System", f"Player {pn} joined the game"))
                        else:
                            print(f"Invalid avatar message format: {message}")
                        continue
                        
                    if message.startswith('CHAT'):
                        parts = message.split(' ', 2)
                        if len(parts) >= 3:
                            player = parts[1][1:-2]  
                            chat_msg = parts[2]
                            self.root.after(0, lambda p=player, m=chat_msg: self.add_message_to_chat(
                                p, m, is_word=False, is_me=(p == self.name)))
                    
                    elif message.startswith('INFO') and 'played' in message:
                        parts = message.split(' ', 3)
                        if len(parts) >= 4:
                            player = parts[1]
                            word = parts[3].split("'")[1]
                            points = parts[3].split('+')[1].split()[0] if '+' in parts[3] else "0"
                            self.root.after(0, lambda p=player, w=word, pts=points: self.add_message_to_chat(
                                p, f"Word : {w} (+{pts} points)", is_word=True, is_me=(p == self.name)))
                    
                    elif message.startswith('{'):
                        try:
                            json_data = json.loads(message)
                            cycle = json_data.get("Cycle")
                            player = json_data.get("player")
                            word = json_data.get("word")
                            state = json_data.get("state")
                            score_change = json_data.get("score_change", 0)
                            current_score = json_data.get("current_score", 0)
                            timestamp = json_data.get("player_timestamp") or json_data.get("server_timestamp")


                            self.current_cycle = int(cycle)
                            self.scores[player] = current_score
                            self.root.after(0, self.update_score_display)

                            if state == "accept":
                                self.root.after(0, lambda: self.add_message_to_chat("System", f"{player} played '{word}' (+{score_change} points)"))
                            elif state == "bonus":
                                self.root.after(0, lambda: self.add_message_to_chat("System", f"{player} played '{word}' (+{score_change} points) [Bonus]"))
                            elif state == "invalid":
                                self.root.after(0, lambda: self.add_message_to_chat("System", f"Word '{word}' is not valid"))
                            elif state == "timeout":
                                self.root.after(0, lambda: self.add_message_to_chat("System", f"{player} ran out of time ({score_change} points)"))

                            if player == self.name:
                                self.root.after(0, self.stop_timer)
                                self.my_turn = False
                                self.root.after(0, lambda: self.word_entry.config(state='disabled'))
                                self.log_play(cycle, player, word, timestamp)

                        except json.JSONDecodeError:
                            self.root.after(0, lambda: self.add_message_to_chat("System", "Invalid JSON received"))
                        continue

                    elif "Game starting" in message:
                        self.root.after(0, lambda: self.add_message_to_chat("System", "Game started! First player's turn."))
                        self.root.after(0, lambda: self.word_entry.config(state='disabled'))
                    
                    elif message.startswith('PROMPT'):
                        letter = message.split()[1]
                        self.my_turn = True
                        self.current_letter = letter
                        self.root.after(0, lambda: self.word_entry.config(state='normal'))
                        self.root.after(0, lambda: self.add_message_to_chat("System", f"Your turn! Enter a word starting with '{letter}':"))
                        self.root.after(0, self.start_timer)
                    
                    elif "You are the host" in message or "You are the new host" in message:
                        self.is_host = True
                        self.root.after(0, lambda: self.host_label.config(text="(Host)"))
                        self.root.after(0, lambda: self.start_button.config(state='normal'))
                        self.root.after(0, lambda: self.add_message_to_chat("System", "You are the host"))
                        print(f"Client {self.name} recognized as host")  
                    
                    elif message.startswith('SCORES'):
                        score_data = message.split(' ', 1)[1]
                        self.scores.clear()
                        for item in score_data.split(','):
                            player, score = item.split(':')
                            self.scores[player] = int(score)
                        self.root.after(0, self.update_score_display)
                    
                    elif message.startswith('ENDGAME'):
                        self.root.after(0, lambda: self.add_message_to_chat("System", "Game Over! Final Scores:"))
                        scores = message.split(' ', 1)[1].split(',')
                        for score in scores:
                            self.root.after(0, lambda s=score: self.add_message_to_chat("System", s))
                        self.root.after(0, lambda: messagebox.showinfo("Game Over", "Game has ended"))
                        break
                    
                    elif message.startswith('INFO'):
                        self.root.after(0, lambda: self.add_message_to_chat("System", message[5:]))

            except ConnectionError as e:
                self.root.after(0, lambda: self.add_message_to_chat("System", f"Error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Connection Lost", "Disconnected from server. Please restart the client."))
                break
            except Exception as e:
                self.root.after(0, lambda: self.add_message_to_chat("System", f"Error receiving message: {e}"))
                continue

        try:
            self.client_socket.close()
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
            self.add_message_to_chat("System", f"Error logging play: {e}")

    def send_word(self):
        if not self.my_turn:
            self.add_message_to_chat("System", "Not your turn!")
            return
        word = self.word_entry.get().strip()
        if not word:
            return

        # 1. Generate timestamp before sending
        ts = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + "Z"

        payload = {
            "Cycle": str(self.current_cycle),
            "player": self.name,
            "word": word,
            "player_timestamp": ts
        }
        try:
            # 2. Send JSON with player_timestamp
            self.client_socket.send((json.dumps(payload) + "\n").encode('utf-8'))

            # 3. Log the timestamp
            self.log_play(self.current_cycle, self.name, word, ts)

            # disable entry after sending
            self.root.after(0, lambda: self.word_entry.delete(0, tk.END))
            self.my_turn = False
            self.root.after(0, lambda: self.word_entry.config(state='disabled'))
        except (ConnectionError, BrokenPipeError) as e:
            self.root.after(0, lambda: self.add_message_to_chat("System", f"Error sending word: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Connection Lost", "Disconnected from server. Please restart the client."))

    def send_chat(self):
        message = self.chat_entry.get().strip()
        if message:
            try:
                self.client_socket.send(f"CHAT {message}\n".encode('utf-8'))
                self.root.after(0, lambda: self.chat_entry.delete(0, tk.END))
            except (ConnectionError, BrokenPipeError) as e:
                self.root.after(0, lambda: self.add_message_to_chat("System", f"Error sending chat: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Connection Lost", "Disconnected from server. Please restart the client."))

    def on_closing(self):
        try:
            self.client_socket.close()
        except:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = GameClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()