# Capture the Flag Modu
# Bu modül CTF oyun mantığını içerir

import random
import time
import copy
from common import MSG_MOVE, MSG_STATE, MSG_RESTART, create_state_message, MAX_PLAYERS, get_snake_color

# CTF Oyun Sabitleri
CTF_BOARD_WIDTH = 60
CTF_BOARD_HEIGHT = 35
CTF_START_LENGTH = 3
CTF_TICK_RATE = 0.05

# Takım Sabitleri
RED_TEAM = "red"
BLUE_TEAM = "blue"
TEAMS = [RED_TEAM, BLUE_TEAM]

# Bayrak Pozisyonları
RED_FLAG_POS = (5, 5)
BLUE_FLAG_POS = (55, 30)

# Skor Sistemi
FLAG_CAPTURE_SCORE = 10
FLAG_DELIVERY_SCORE = 15
KILL_SCORE = 5
DEFENSE_SCORE = 2

class CTFGameState:
    def __init__(self):
        self.reset_game()
    
    def reset_game(self):
        """CTF oyununu sıfırlar"""
        self.teams = {
            RED_TEAM: [],
            BLUE_TEAM: []
        }
        self.team_scores = {
            RED_TEAM: 0,
            BLUE_TEAM: 0
        }
        self.individual_scores = {}
        self.snakes = {}
        self.directions = {}
        self.colors = {}
        self.flags = {
            RED_TEAM: {
                "pos": list(RED_FLAG_POS),
                "captured": False,
                "carrier": None,
                "dropped_pos": None,
                "base_pos": list(RED_FLAG_POS)
            },
            BLUE_TEAM: {
                "pos": list(BLUE_FLAG_POS),
                "captured": False,
                "carrier": None,
                "dropped_pos": None,
                "base_pos": list(BLUE_FLAG_POS)
            }
        }
        self.game_time = 300  # 5 dakika
        self.game_phase = "preparation"  # preparation, active, finished
        self.start_time = None
        self.food = []
        self.obstacles = []
        self.portals = []
        self.powerups = []
        self.active_powerups = {}
        self.trails = {}
        self.scores = {}
        self.active = {}
        
    def assign_team(self, player_id):
        """Oyuncuyu rastgele bir takıma atar"""
        if len(self.teams[RED_TEAM]) <= len(self.teams[BLUE_TEAM]):
            team = RED_TEAM
        else:
            team = BLUE_TEAM
        
        self.teams[team].append(player_id)
        self.individual_scores[player_id] = 0
        return team
    
    def get_player_team(self, player_id):
        """Oyuncunun hangi takımda olduğunu döndürür"""
        for team in TEAMS:
            if player_id in self.teams[team]:
                return team
        return None
    
    def get_opponent_team(self, player_id):
        """Oyuncunun karşı takımını döndürür"""
        player_team = self.get_player_team(player_id)
        if player_team == RED_TEAM:
            return BLUE_TEAM
        elif player_team == BLUE_TEAM:
            return RED_TEAM
        return None
    
    def is_teammate(self, player1_id, player2_id):
        """İki oyuncunun takım arkadaşı olup olmadığını kontrol eder"""
        team1 = self.get_player_team(player1_id)
        team2 = self.get_player_team(player2_id)
        return team1 and team2 and team1 == team2
    
    def can_capture_flag(self, player_id, flag_pos):
        """Oyuncunun bayrak yakalayıp yakalayamayacağını kontrol eder"""
        player_team = self.get_player_team(player_id)
        if not player_team:
            return False
        
        # Kendi bayrağını yakalayamaz
        if player_team == RED_TEAM and flag_pos == self.flags[RED_TEAM]["pos"]:
            return False
        if player_team == BLUE_TEAM and flag_pos == self.flags[BLUE_TEAM]["pos"]:
            return False
        
        return True
    
    def capture_flag(self, player_id, flag_team):
        """Bayrak yakalama işlemi"""
        if self.flags[flag_team]["captured"]:
            return False
        
        self.flags[flag_team]["captured"] = True
        self.flags[flag_team]["carrier"] = player_id
        self.individual_scores[player_id] += FLAG_CAPTURE_SCORE
        
        return True
    
    def drop_flag(self, flag_team):
        """Bayrak düşürme işlemi"""
        if not self.flags[flag_team]["captured"]:
            return
        
        # Bayrak taşıyıcısının son pozisyonuna düşür
        carrier_id = self.flags[flag_team]["carrier"]
        if carrier_id in self.snakes:
            last_pos = self.snakes[carrier_id][-1] if self.snakes[carrier_id] else self.flags[flag_team]["base_pos"]
            self.flags[flag_team]["dropped_pos"] = list(last_pos)
            self.flags[flag_team]["pos"] = list(last_pos)
        
        self.flags[flag_team]["captured"] = False
        self.flags[flag_team]["carrier"] = None
    
    def deliver_flag(self, player_id):
        """Bayrak teslim etme işlemi"""
        player_team = self.get_player_team(player_id)
        if not player_team:
            return False
        
        # Karşı takımın bayrağını taşıyor mu?
        opponent_team = self.get_opponent_team(player_id)
        if not self.flags[opponent_team]["captured"] or self.flags[opponent_team]["carrier"] != player_id:
            return False
        
        # Kendi üssünde mi?
        player_pos = self.snakes[player_id][0] if self.snakes[player_id] else None
        if not player_pos:
            return False
        
        # Üs kontrolü (basit: takım bölgesinde olup olmadığı)
        if player_team == RED_TEAM and player_pos[0] < 30:
            # Kırmızı takım sol tarafta
            self.team_scores[player_team] += FLAG_DELIVERY_SCORE
            self.individual_scores[player_id] += FLAG_DELIVERY_SCORE
            self.flags[opponent_team]["captured"] = False
            self.flags[opponent_team]["carrier"] = None
            self.flags[opponent_team]["pos"] = self.flags[opponent_team]["base_pos"]
            return True
        elif player_team == BLUE_TEAM and player_pos[0] >= 30:
            # Mavi takım sağ tarafta
            self.team_scores[player_team] += FLAG_DELIVERY_SCORE
            self.individual_scores[player_id] += FLAG_DELIVERY_SCORE
            self.flags[opponent_team]["captured"] = False
            self.flags[opponent_team]["carrier"] = None
            self.flags[opponent_team]["pos"] = self.flags[opponent_team]["base_pos"]
            return True
        
        return False
    
    def check_collision(self, player_id, new_head):
        """Çarpışma kontrolü - CTF kurallarına göre"""
        player_team = self.get_player_team(player_id)
        if not player_team:
            return True
        
        # Duvar kontrolü
        if (new_head[0] < 0 or new_head[0] >= CTF_BOARD_WIDTH or 
            new_head[1] < 0 or new_head[1] >= CTF_BOARD_HEIGHT):
            return True
        
        # Diğer oyuncularla çarpışma
        for other_id, snake in self.snakes.items():
            if other_id == player_id:
                continue
            
            # Takım arkadaşı kontrolü
            if self.is_teammate(player_id, other_id):
                # Takım arkadaşına çarpmak = ölüm
                if new_head in snake:
                    return True
            else:
                # Karşı takımla çarpışma = ölüm
                if new_head in snake:
                    # Karşı takım oyuncusunu öldür
                    self.individual_scores[player_id] += KILL_SCORE
                    return False  # Kendisi ölmez, karşı takım ölür
        
        # Kendi vücuduna çarpma
        if new_head in self.snakes[player_id]:
            return True
        
        return False
    
    def move_snake(self, player_id, direction):
        """Yılan hareketi - CTF kurallarına göre"""
        if player_id not in self.snakes or not self.snakes[player_id]:
            return
        
        snake = self.snakes[player_id]
        head = snake[0]
        
        # Yeni baş pozisyonu
        if direction == "up":
            new_head = (head[0], head[1] - 1)
        elif direction == "down":
            new_head = (head[0], head[1] + 1)
        elif direction == "left":
            new_head = (head[0] - 1, head[1])
        elif direction == "right":
            new_head = (head[0] + 1, head[1])
        else:
            return
        
        # Çarpışma kontrolü
        if self.check_collision(player_id, new_head):
            self.eliminate_player(player_id)
            return
        
        # Bayrak taşıma kontrolü
        flag_carrier = None
        for team in TEAMS:
            if (self.flags[team]["captured"] and 
                self.flags[team]["carrier"] == player_id):
                flag_carrier = team
                break
        
        # Bayrak taşıyorsa yavaş hareket
        if flag_carrier:
            # Bayrak taşıyan oyuncu yavaş hareket eder
            # Bu örnekte basit bir yavaşlatma
            pass
        
        # Yılanı hareket ettir
        snake.insert(0, new_head)
        
        # Bayrak yakalama kontrolü
        for team in TEAMS:
            if (not self.flags[team]["captured"] and 
                new_head == tuple(self.flags[team]["pos"]) and
                self.can_capture_flag(player_id, self.flags[team]["pos"])):
                self.capture_flag(player_id, team)
        
        # Bayrak teslim etme kontrolü
        self.deliver_flag(player_id)
        
        # Yemi yeme kontrolü (basit)
        if new_head in self.food:
            self.food.remove(new_head)
            # Yılan büyür (kuyruk kesilmez)
        else:
            # Kuyruk kesilir
            snake.pop()
    
    def eliminate_player(self, player_id):
        """Oyuncuyu oyundan çıkarır"""
        # Taşıdığı bayrağı düşür
        for team in TEAMS:
            if (self.flags[team]["captured"] and 
                self.flags[team]["carrier"] == player_id):
                self.drop_flag(team)
        
        # Oyuncuyu kaldır
        if player_id in self.snakes:
            del self.snakes[player_id]
        if player_id in self.directions:
            del self.directions[player_id]
        if player_id in self.colors:
            del self.colors[player_id]
        if player_id in self.active:
            del self.active[player_id]
        
        # Takımdan çıkar
        for team in TEAMS:
            if player_id in self.teams[team]:
                self.teams[team].remove(player_id)
    
    def get_game_state(self):
        """Oyun durumunu döndürür"""
        return {
            "snakes": self.snakes,
            "colors": self.colors,
            "food": self.food,
            "obstacles": self.obstacles,
            "portals": self.portals,
            "powerups": self.powerups,
            "scores": self.individual_scores,
            "teams": self.teams,
            "team_scores": self.team_scores,
            "flags": self.flags,
            "game_time": self.game_time,
            "game_phase": self.game_phase
        }
    
    def start_game(self):
        """Oyunu başlatır"""
        self.game_phase = "active"
        self.start_time = time.time()
    
    def update_game_time(self):
        """Oyun süresini günceller"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.game_time = max(0, 300 - elapsed)
            
            if self.game_time <= 0:
                self.game_phase = "finished"
    
    def get_winner(self):
        """Kazanan takımı döndürür"""
        if self.team_scores[RED_TEAM] > self.team_scores[BLUE_TEAM]:
            return RED_TEAM
        elif self.team_scores[BLUE_TEAM] > self.team_scores[RED_TEAM]:
            return BLUE_TEAM
        else:
            return "tie"

# Global CTF oyun durumu
ctf_game_state = CTFGameState()

def reset_ctf_game():
    """CTF oyununu sıfırlar"""
    global ctf_game_state
    ctf_game_state.reset_game()

def start_ctf_game():
    """CTF oyununu başlatır"""
    global ctf_game_state
    ctf_game_state.start_game()

def get_ctf_game_state():
    """CTF oyun durumunu döndürür"""
    global ctf_game_state
    return ctf_game_state.get_game_state()

def update_ctf_game():
    """CTF oyununu günceller"""
    global ctf_game_state
    ctf_game_state.update_game_time()
    
    # Tüm oyuncuları hareket ettir
    for player_id in list(ctf_game_state.snakes.keys()):
        if player_id in ctf_game_state.directions:
            direction = ctf_game_state.directions[player_id]
            ctf_game_state.move_snake(player_id, direction)
    
    # Oyun bitişi kontrolü
    if ctf_game_state.game_phase == "finished":
        winner = ctf_game_state.get_winner()
        return {"winner": winner, "game_over": True}
    
    return {"game_over": False} 