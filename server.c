#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <ctype.h>
#include <netinet/in.h>
#include <sys/time.h>
#include <time.h>
#include "uthash.h"
#include <fcntl.h>
#include <errno.h>

#define PORT 12345
#define MAX_PLAYERS 5
#define MAX_WORD 64
#define TIMEOUT_SEC 30
#define TIMEOUT_PENALTY -2
#define WIN_SCORE 50
#define JSON_FILE "game_log.json"
// Add these safety checks at the top with other defines
#define MAX_MSG_LEN 512
#define MAX_BUF_LEN 256
#define MAX_NAME_LEN 32

typedef struct {
    char word[MAX_WORD];   // key
    UT_hash_handle hh;     // makes this struct hashable
} DictEntry;

DictEntry *dict_hash = NULL;

typedef struct {
    int socket;
    char name[32];
    int is_host;
    int score;
    int ready;
} Player;

void *game_loop(void *arg); 

Player players[MAX_PLAYERS];
int player_count = 0;
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
char used_words[1000][MAX_WORD];
int used_count = 0;
char current_letter = '\0';
int game_active = 0;

void load_dictionary(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { 
        perror("Dictionary file error"); 
        exit(1); 
    }
    
    char buf[MAX_WORD];
    while (fgets(buf, sizeof buf, f)) {
        buf[strcspn(buf, "\r\n")] = '\0';
        DictEntry *e = malloc(sizeof *e);
        strcpy(e->word, buf);
        HASH_ADD_STR(dict_hash, word, e);
    }
    fclose(f);
    printf("Dictionary loaded successfully\n");
}

int validate_word(const char *word, char expected) {
    if (tolower(word[0]) != tolower(expected)) return 0;

    DictEntry *e;
    HASH_FIND_STR(dict_hash, word, e);
    if (!e) return 0;  // word not in dictionary

    // Check against used words
    for (int i = 0; i < used_count; i++)
        if (strcasecmp(used_words[i], word) == 0)
            return 0;

    return 1;
}

void log_word_submission(const char* player_name, const char* word, int score) {
    time_t now;
    struct tm *tm_info;
    char timestamp[30];
    
    time(&now);
    tm_info = localtime(&now);
    strftime(timestamp, 30, "%H:%M:%S %d/%m/%Y", tm_info);
    
    FILE *f = fopen(JSON_FILE, "a");
    if (f) {
        fprintf(f, "{\n  \"player\": \"%s\",\n  \"word\": \"%s\",\n  \"score\": %d,\n  \"timestamp\": \"%s\"\n}\n",
                player_name, word, score, timestamp);
        fclose(f);
    }
}

int send_with_timeout(int sock, const char *buf, size_t len, int timeout_ms) {
    fd_set wfds;
    struct timeval tv;
    
    FD_ZERO(&wfds);
    FD_SET(sock, &wfds);
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    
    if (select(sock + 1, NULL, &wfds, NULL, &tv) <= 0) {
        return -1;
    }
    return send(sock, buf, len, MSG_DONTWAIT);
}

void broadcast(const char *msg) {
    if (!msg) return;
    char full_msg[MAX_MSG_LEN];
    if (snprintf(full_msg, sizeof(full_msg), "%s\n", msg) >= sizeof(full_msg)) {
        printf("[Warning] Message truncated in broadcast\n");
    }
    pthread_mutex_lock(&lock);
    for (int i = 0; i < player_count; i++) {
        if (send_with_timeout(players[i].socket, full_msg, strlen(full_msg), 100) < 0) {
            printf("Warning: Failed to send to player %s\n", players[i].name);
        }
    }
    pthread_mutex_unlock(&lock);
}

void broadcast_chat(const char *name, const char *msg) {
    if (!name || !msg) return;
    char full_msg[MAX_MSG_LEN];
    if (snprintf(full_msg, sizeof(full_msg), "CHAT [%.*s]: %.*s\n", 
                MAX_NAME_LEN, name, MAX_BUF_LEN, msg) >= sizeof(full_msg)) {
        printf("[Warning] Chat message truncated\n");
    }
    for (int i = 0; i < player_count; i++) {
        send(players[i].socket, full_msg, strlen(full_msg), 0);
    }
}


void *handle_player(void *arg) {
    int idx = *(int *)arg;
    free(arg);
    char buf[MAX_BUF_LEN];
    printf("New player connected: %d\n", idx+1);

    // Initialize player name as empty
    players[idx].name[0] = '\0';

    // Set send timeout only
    struct timeval tv = { .tv_sec = 1, .tv_usec = 0 };
    setsockopt(players[idx].socket, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    while (1) {
        // Use blocking recv() for first message
        int n = recv(players[idx].socket, buf, sizeof(buf) - 1, 0);
        if (n <= 0) {
            pthread_mutex_lock(&lock);
            printf("\nPlayer disconnected before registration\n");
            printf("Current players: %d\n", player_count - 1);
            
            close(players[idx].socket);
            for (int i = idx; i < player_count - 1; i++) {
                players[i] = players[i + 1];
            }
            player_count--;
            pthread_mutex_unlock(&lock);
            pthread_exit(NULL);
            break;
        }
        buf[n] = 0;
        buf[strcspn(buf, "\n")] = 0;

        printf("Received command: %s\n", buf);  // Debug print

        if (strncmp(buf, "REGISTER ", 9) == 0) {
            strncpy(players[idx].name, buf + 9, MAX_NAME_LEN - 1);
            players[idx].name[MAX_NAME_LEN - 1] = 0;
            players[idx].ready = 1;
            
            char msg[MAX_MSG_LEN];
            snprintf(msg, sizeof(msg), "Player %s joined the game", players[idx].name);
            broadcast(msg);

            if (players[idx].is_host) {
                printf("Sending host status to player %s\n", players[idx].name);  // Debug print
                send(players[idx].socket, "You are the host.\n", 17, 0);
            }
        }
        else if (strncmp(buf, "START", 5) == 0) {
            printf("Received START command from player %s (is_host: %d)\n", 
                   players[idx].name, players[idx].is_host);  // Debug print
            
            pthread_mutex_lock(&lock);
            if (!players[idx].is_host) {
                send(players[idx].socket, "ERROR: Only the host can start the game.\n", 40, 0);
            } else if (game_active) {
                send(players[idx].socket, "ERROR: Game already in progress.\n", 33, 0);
            } else {
                int ready_count = 0;
                for (int i = 0; i < player_count; i++) {
                    if (players[i].ready) ready_count++;
                }
                if (ready_count < 2) {
                    send(players[idx].socket, "ERROR: Need at least 2 players.\n", 32, 0);
                } else {
                    printf("Starting game...\n");  // Debug print
                    game_active = 1;
                    pthread_t game_tid;
                    pthread_create(&game_tid, NULL, game_loop, NULL);
                }
            }
            pthread_mutex_unlock(&lock);
        }

    }
    
    close(players[idx].socket);
    pthread_exit(NULL);
}

void broadcast_scores() {
    char score_msg[512] = "SCORES ";
    int offset = 7;  // length of "SCORES "
    
    for (int i = 0; i < player_count; i++) {
        offset += snprintf(score_msg + offset, sizeof(score_msg) - offset,
                         "%s%s:%d", 
                         i > 0 ? "," : "", 
                         players[i].name, 
                         players[i].score);
    }
    strcat(score_msg, "\n");
    broadcast(score_msg);
}

#define READ_BUF 512

void *game_loop(void *arg) {
    char msg[MAX_MSG_LEN];
    char raw[READ_BUF];
    char linebuf[READ_BUF];
    int linepos = 0;
    
    srand(time(NULL));
    current_letter = 'a' + rand() % 26;
    snprintf(msg, sizeof(msg), "Game starting! First letter: %c", current_letter);
    broadcast(msg);

    int turn = 0;
    while (1) {
        Player *p = &players[turn];
        snprintf(msg, sizeof(msg), "PROMPT %c\n", current_letter);
        send(p->socket, msg, strlen(msg), 0);

        int got_valid_word = 0;
        int should_continue = 1;
        time_t start = time(NULL);

        // Process player input with timeout
        while (should_continue) {
            fd_set rfds;
            FD_ZERO(&rfds);
            FD_SET(p->socket, &rfds);
            struct timeval tv = {TIMEOUT_SEC, 0};

            int sel = select(p->socket + 1, &rfds, NULL, NULL, &tv);
            if (sel < 0 && errno != EINTR) {
                goto disconnect;
            }
            if (sel == 0) {
                // Timeout only if no word was processed
                if (!got_valid_word) {
                    p->score += TIMEOUT_PENALTY;
                    snprintf(msg, sizeof(msg), "%s ran out of time (%d points)", p->name, TIMEOUT_PENALTY);
                    broadcast(msg);
                    broadcast_scores();
                }
                break;  // Next turn
            }

            // Socket is readable
            int n = recv(p->socket, raw, sizeof(raw), 0);
            if (n < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    continue;
                }
                goto disconnect;
            }
            if (n == 0) {
                goto disconnect;
            }

            // Process received data
            for (int i = 0; i < n; i++) {
                if (raw[i] == '\n' || linepos + 1 >= READ_BUF) {
                    linebuf[linepos] = '\0';
                    
                    if (strncmp(linebuf, "WORD ", 5) == 0) {
                        char *word = linebuf + 5;
                        int early = (time(NULL) - start) <= 5;

                        // Check for duplicate with last word
                        int is_duplicate = (used_count > 0 && 
                            strcasecmp(word, used_words[used_count-1]) == 0);

                        if (validate_word(word, current_letter) && !is_duplicate) {
                            strcpy(used_words[used_count++], word);
                            int gained = strlen(word) + (early ? 2 : 0);
                            p->score += gained;
                            
                            send(p->socket, "VALID\n", 6, 0);
                            snprintf(msg, sizeof(msg), "%s played '%s' (+%d points)", 
                                    p->name, word, gained);
                            broadcast(msg);
                            current_letter = tolower(word[strlen(word) - 1]);
                            broadcast_scores();
                            got_valid_word = 1;
                            should_continue = 0;  // End turn after valid word
                        } else {
                            p->score -= 1;
                            if (is_duplicate) {
                                snprintf(msg, sizeof(msg), "INVALID Word '%s' was already used\n", word);
                            } else {
                                snprintf(msg, sizeof(msg), "INVALID Word '%s' is not valid\n", word);
                            }
                            send(p->socket, msg, strlen(msg), 0);
                            broadcast_scores();
                            should_continue = 0;  // End turn after invalid word
                        }
                    }
                    linepos = 0;
                } else {
                    linebuf[linepos++] = raw[i];
                }
            }

            if (!should_continue) break;
        }

        // Check for win condition
        if (p->score >= WIN_SCORE) {
            char endgame[512];
            snprintf(endgame, sizeof(endgame), "ENDGAME %s: %d points", p->name, p->score);
            for (int i = 0; i < player_count; i++) {
                if (i != turn) {
                    snprintf(endgame + strlen(endgame), sizeof(endgame) - strlen(endgame),
                            ",%s: %d points", players[i].name, players[i].score);
                }
            }
            strcat(endgame, "\n");
            broadcast(endgame);
            break;
        }

        turn = (turn + 1) % player_count;
        continue;

disconnect:
        // Handle disconnection
        pthread_mutex_lock(&lock);
        broadcast(msg);
        pthread_mutex_unlock(&lock);
        break;
    }
    
    game_active = 0;
    return NULL;
}

void cleanup_dictionary() {
    DictEntry *current, *tmp;
    HASH_ITER(hh, dict_hash, current, tmp) {
        HASH_DEL(dict_hash, current);
        free(current);
    }
}

int main() {
    // Load dictionary before creating socket
    load_dictionary("dictionary.txt");

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    // Add socket options to allow address reuse
    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt failed");
        exit(1);
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("Bind failed");
        exit(1);
    }

    if (listen(server_fd, MAX_PLAYERS) < 0) {
        perror("Listen failed");
        exit(1);
    }

    printf("Server listening on port %d...\n", PORT);

    while (1) {
        struct sockaddr_in cli_addr;
        socklen_t clilen = sizeof(cli_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&cli_addr, &clilen);

        pthread_mutex_lock(&lock);
        if (player_count < MAX_PLAYERS) {
            // Remove set_nonblocking call here
            int *idx = malloc(sizeof(int));
            *idx = player_count;
            players[*idx].socket = client_fd;            
            players[*idx].score = 0;
            players[*idx].ready = 0;
            players[*idx].is_host = (player_count == 0) ? 1 : 0;

            pthread_t tid;
            pthread_create(&tid, NULL, handle_player, idx);
            usleep(100000); 
            player_count++;
        } else {
            send(client_fd, "Server full.\n", 13, 0);
            close(client_fd);
        }
        pthread_mutex_unlock(&lock);
    }
    close(server_fd);
    cleanup_dictionary();
    return 0;
}
