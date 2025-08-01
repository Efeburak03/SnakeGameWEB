# Capture the Flag Modu
# Bu modül CTF oyun mantığını içerir

import random
import time
import copy
from common import MSG_MOVE, MSG_STATE, MSG_RESTART, create_state_message, MAX_PLAYERS, get_snake_color

# CTF Oyun Sabitleri
CTF_BOARD_WIDTH = 60
CTF_BOARD_HEIGHT = 35
CTF_START_LENGTH = 5
CTF_TICK_RATE = 0.05
CTF_RESPAWN_TIME = 5  # 5 saniye

# Takım Sabitleri
RED_TEAM = "red"
BLUE_TEAM = "blue"
TEAMS = [RED_TEAM, BLUE_TEAM]

# Bayrak Bölgeleri (5x4 alan)
# Kırmızı takım: Sol duvarın ortası
RED_FLAG_AREA = {
    "x": 1,  # Sol duvar
    "y": 15,  # Ortaya yakın (35/2 - 2)
    "width": 4,
    "height": 5
}

# Mavi takım: Sağ duvarın ortası  
BLUE_FLAG_AREA = {
    "x": 55,  # Sağ duvar (60-5)
    "y": 15,  # Ortaya yakın
    "width": 4,
    "height": 5
}

# Takım Doğuş Noktaları
RED_SPAWN_POSITIONS = [
    (10, 10), (10, 15), (10, 20), (10, 25),
    (15, 10), (15, 15), (15, 20), (15, 25),
    (20, 10), (20, 15), (20, 20), (20, 25)
]

BLUE_SPAWN_POSITIONS = [
    (40, 10), (40, 15), (40, 20), (40, 25),
    (45, 10), (45, 15), (45, 20), (45, 25),
    (50, 10), (50, 15), (50, 20), (50, 25)
]

# Skor Sistemi
FLAG_CAPTURE_SCORE = 10
FLAG_DELIVERY_SCORE = 15
KILL_SCORE = 5

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
        self.respawn_timers = {}  # Oyuncuların respawn zamanları
        self.eliminated_snakes = {}  # Elenen oyuncuların yılanları
        self.eliminated_directions = {}  # Elenen oyuncuların yönleri
        
        # Bayraklar - her takımın kendi alanında
        self.flags = {
            RED_TEAM: {
                "pos": [RED_FLAG_AREA["x"] + 2, RED_FLAG_AREA["y"] + 2],  # Alanın ortası
                "captured": False,
                "carrier": None,
                "dropped_pos": None,
                "base_pos": [RED_FLAG_AREA["x"] + 2, RED_FLAG_AREA["y"] + 2]
            },
            BLUE_TEAM: {
                "pos": [BLUE_FLAG_AREA["x"] + 2, BLUE_FLAG_AREA["y"] + 2],  # Alanın ortası
                "captured": False,
                "carrier": None,
                "dropped_pos": None,
                "base_pos": [BLUE_FLAG_AREA["x"] + 2, BLUE_FLAG_AREA["y"] + 2]
            }
        }
        
        self.game_time = 300  # 5 dakika
        self.game_phase = "preparation"  # preparation, active, finished
        self.start_time = None
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
        """Oyuncunun bayrağı yakalayıp yakalayamayacağını kontrol eder"""
        if player_id not in self.snakes:
            return False
        
        player_team = self.get_player_team(player_id)
        if not player_team:
            return False
        
        # Hangi bayrağın pozisyonu olduğunu bul
        flag_team = None
        for team in TEAMS:
            # Bayrak pozisyonunu tuple formatına çevir
            flag_pos_tuple = tuple(self.flags[team]["pos"])
            if flag_pos_tuple == flag_pos:
                flag_team = team
                break
        
        if not flag_team:
            return False
        
        # Kendi bayrağını yakalayamaz
        if player_team == flag_team:
            return False
        
        # Bayrak zaten yakalanmış mı?
        if self.flags[flag_team]["captured"]:
            return False
        
        # Oyuncu aktif mi?
        if player_id not in self.active or not self.active[player_id]:
            return False
        
        print(f"[DEBUG] {player_id} {flag_team} bayrağını yakalayabilir")
        return True
    
    def capture_flag(self, player_id, flag_team):
        """Bayrağı yakalar"""
        if flag_team not in TEAMS:
            return False
        
        self.flags[flag_team]["captured"] = True
        self.flags[flag_team]["carrier"] = player_id
        # Yılanın başını list formatında sakla
        head_pos = list(self.snakes[player_id][0])
        self.flags[flag_team]["pos"] = head_pos
        
        # Skor ver
        self.individual_scores[player_id] += FLAG_CAPTURE_SCORE
        
        print(f"[DEBUG] {player_id} {flag_team} bayrağını yakaladı ve {head_pos} pozisyonuna taşıdı")
        return True
    
    def drop_flag(self, flag_team):
        """Bayrağı düşürür"""
        if flag_team not in TEAMS:
            return
        
        # Bayrağı düşür ve pozisyonunu güncelle
        self.flags[flag_team]["captured"] = False
        self.flags[flag_team]["dropped_pos"] = self.flags[flag_team]["pos"]
        self.flags[flag_team]["pos"] = self.flags[flag_team]["dropped_pos"]  # Ana pozisyonu güncelle
        self.flags[flag_team]["carrier"] = None
        
        print(f"[DEBUG] {flag_team} bayrağı {self.flags[flag_team]['pos']} pozisyonuna düştü")
    
    def deliver_flag(self, player_id):
        """Bayrağı teslim eder"""
        player_team = self.get_player_team(player_id)
        if not player_team:
            return False
        
        # Karşı takımın bayrağını mı taşıyor?
        opponent_team = self.get_opponent_team(player_id)
        if not opponent_team:
            return False
        
        # Oyuncunun pozisyonunu kontrol et
        if player_id not in self.snakes:
            return False
        
        head = self.snakes[player_id][0]
        in_team_area = self.is_in_team_area(player_id, player_team)
        
        print(f"[DEBUG] {player_id} pozisyon: {head}, takım: {player_team}, takım alanında: {in_team_area}")
        print(f"[DEBUG] {opponent_team} bayrağını taşıyor mu: {self.flags[opponent_team]['carrier'] == player_id}")
        
        if (self.flags[opponent_team]["carrier"] == player_id and 
            in_team_area):
            
            print(f"[DEBUG] {player_id} {opponent_team} bayrağını {player_team} alanına teslim etti!")
            
            # Bayrağı teslim et
            self.flags[opponent_team]["captured"] = False
            self.flags[opponent_team]["carrier"] = None
            self.flags[opponent_team]["pos"] = self.flags[opponent_team]["base_pos"]
            
            # Skor ver
            self.individual_scores[player_id] += FLAG_DELIVERY_SCORE
            self.team_scores[player_team] += FLAG_DELIVERY_SCORE
            
            # Round kazanıldı - oyunu yeniden başlat
            print(f"[DEBUG] {player_team} takımı round'u kazandı! Oyun yeniden başlatılıyor...")
            self.reset_round()
            
            # Server'a round kazanma bildirimi gönder
            return {"round_won": True, "winning_team": player_team, "winning_player": player_id}
        
        return False
    
    def reset_round(self):
        """Round sonunda oyunu yeniden başlatır"""
        print("[DEBUG] Round yeniden başlatılıyor...")
        
        # Tüm oyuncuları yeniden spawn et
        for player_id in list(self.snakes.keys()):
            if player_id in self.active:
                self.respawn_player(player_id)
        
        # Bayrakları başlangıç pozisyonlarına getir
        self.flags[RED_TEAM]["pos"] = self.flags[RED_TEAM]["base_pos"]
        self.flags[RED_TEAM]["captured"] = False
        self.flags[RED_TEAM]["carrier"] = None
        
        self.flags[BLUE_TEAM]["pos"] = self.flags[BLUE_TEAM]["base_pos"]
        self.flags[BLUE_TEAM]["captured"] = False
        self.flags[BLUE_TEAM]["carrier"] = None
        
        print("[DEBUG] Round yeniden başlatıldı")
    
    def is_in_team_area(self, player_id, team):
        """Oyuncunun kendi takım alanında olup olmadığını kontrol eder"""
        if player_id not in self.snakes:
            return False
        
        head = self.snakes[player_id][0]
        
        if team == RED_TEAM:
            # Kırmızı takım alanı: sol duvarın ortası (1, 15) - (5, 20)
            return (head[0] >= RED_FLAG_AREA["x"] and 
                   head[0] < RED_FLAG_AREA["x"] + RED_FLAG_AREA["width"] and
                   head[1] >= RED_FLAG_AREA["y"] and 
                   head[1] < RED_FLAG_AREA["y"] + RED_FLAG_AREA["height"])
        elif team == BLUE_TEAM:
            # Mavi takım alanı: sağ duvarın ortası (55, 15) - (59, 20)
            return (head[0] >= BLUE_FLAG_AREA["x"] and 
                   head[0] < BLUE_FLAG_AREA["x"] + BLUE_FLAG_AREA["width"] and
                   head[1] >= BLUE_FLAG_AREA["y"] and 
                   head[1] < BLUE_FLAG_AREA["y"] + BLUE_FLAG_AREA["height"])
        
        return False
    
    def check_collision(self, player_id, new_head):
        """Çarpışma kontrolü"""
        # Duvar çarpışması
        if (new_head[0] < 0 or new_head[0] >= CTF_BOARD_WIDTH or
            new_head[1] < 0 or new_head[1] >= CTF_BOARD_HEIGHT):
            return True
        
        # Diğer yılanlarla çarpışma
        for other_id, snake in self.snakes.items():
            if other_id != player_id and other_id in self.active and self.active[other_id]:
                if new_head in snake:
                    return True
        
        # Kendi yılanıyla çarpışma
        if player_id in self.snakes:
            if new_head in self.snakes[player_id][1:]:  # Baş hariç
                return True
        
        return False
    
    def move_snake(self, player_id, direction):
        """Yılanı hareket ettirir"""
        if player_id not in self.snakes or player_id not in self.directions:
            return False
        
        snake = self.snakes[player_id]
        head = snake[0]
        
        # Yeni baş pozisyonu
        if direction == "UP":
            new_head = (head[0], head[1] - 1)
        elif direction == "DOWN":
            new_head = (head[0], head[1] + 1)
        elif direction == "LEFT":
            new_head = (head[0] - 1, head[1])
        elif direction == "RIGHT":
            new_head = (head[0] + 1, head[1])
        else:
            return False
        
        # Çarpışma kontrolü
        if self.check_collision(player_id, new_head):
            self.eliminate_player(player_id)
            return False
        
        # Yılanı hareket ettir
        snake.insert(0, new_head)
        snake.pop()  # Kuyruğu kaldır
        
        # Bayrak taşıyorsa bayrağı da hareket ettir
        player_team = self.get_player_team(player_id)
        if player_team:
            for team in TEAMS:
                if (self.flags[team]["carrier"] == player_id and 
                    self.flags[team]["captured"]):
                    # Yeni pozisyonu list formatında sakla
                    self.flags[team]["pos"] = list(new_head)
                    print(f"[DEBUG] {player_id} {team} bayrağını {list(new_head)} pozisyonuna taşıdı")
        
        # Bayrak teslim kontrolü
        self.deliver_flag(player_id)
        
        # Bayrak yakalama kontrolü
        for team in TEAMS:
            flag_pos = self.flags[team]["pos"]
            flag_pos_tuple = tuple(flag_pos)
            print(f"[DEBUG] {player_id} yeni pozisyon: {new_head}, {team} bayrak pozisyonu: {flag_pos_tuple}, yakalanmış: {self.flags[team]['captured']}")
            if new_head == flag_pos_tuple and self.can_capture_flag(player_id, flag_pos_tuple):
                print(f"[DEBUG] {player_id} {team} bayrağını yakaladı!")
                self.capture_flag(player_id, team)
        
        return True
    
    def eliminate_player(self, player_id):
        """Oyuncuyu eleme"""
        if player_id not in self.active:
            return
        
        self.active[player_id] = False
        self.respawn_timers[player_id] = time.time() + CTF_RESPAWN_TIME
        
        # Elenen oyuncunun yılanını geçici olarak sil
        if player_id in self.snakes:
            # Yılanı geçici olarak sakla (respawn için)
            self.eliminated_snakes[player_id] = self.snakes[player_id]
            del self.snakes[player_id]
        
        # Yön bilgisini de geçici olarak sakla
        if player_id in self.directions:
            self.eliminated_directions[player_id] = self.directions[player_id]
            del self.directions[player_id]
        
        # Taşıdığı bayrağı düşür
        for team in TEAMS:
            if self.flags[team]["carrier"] == player_id:
                self.drop_flag(team)
        
        print(f"[DEBUG] {player_id} elendi, {CTF_RESPAWN_TIME} saniye sonra manuel respawn mümkün")
    
    def respawn_player(self, player_id):
        """Oyuncuyu yeniden doğur"""
        if player_id not in self.respawn_timers:
            return False
        
        # 5 saniye bekleme süresi kontrolü
        current_time = time.time()
        respawn_time = self.respawn_timers[player_id]
        
        if current_time < respawn_time:
            remaining_time = respawn_time - current_time
            print(f"[DEBUG] {player_id} henüz respawn olamaz, {remaining_time:.1f} saniye kaldı")
            return False
        
        # Oyuncunun takımını bul
        player_team = self.get_player_team(player_id)
        if not player_team:
            return False
        
        # Takım bazlı spawn pozisyonu
        if player_team == RED_TEAM:
            spawn_pos = random.choice(RED_SPAWN_POSITIONS)
            start_x, start_y = spawn_pos
            # Kırmızı takım sağa doğru başlar
            self.snakes[player_id] = [
                (start_x, start_y),
                (start_x-1, start_y),
                (start_x-2, start_y)
            ]
            self.directions[player_id] = "RIGHT"
        else:
            spawn_pos = random.choice(BLUE_SPAWN_POSITIONS)
            start_x, start_y = spawn_pos
            # Mavi takım sola doğru başlar
            self.snakes[player_id] = [
                (start_x, start_y),
                (start_x+1, start_y),
                (start_x+2, start_y)
            ]
            self.directions[player_id] = "LEFT"
        
        self.active[player_id] = True
        self.respawn_timers.pop(player_id, None)
        
        # Elenen yılan ve yön bilgilerini temizle
        self.eliminated_snakes.pop(player_id, None)
        self.eliminated_directions.pop(player_id, None)
        
        print(f"[DEBUG] {player_id} respawn edildi")
        return True
    
    def check_respawns(self):
        """Respawn zamanı gelen oyuncuları yeniden doğur - CTF'de otomatik respawn yok"""
        # CTF modunda otomatik respawn yok, sadece manuel respawn
        return []
    
    def get_game_state(self):
        """Oyun durumunu döndürür"""
        return {
            "snakes": self.snakes,
            "directions": self.directions,
            "colors": self.colors,
            "active": self.active,
            "flags": self.flags,
            "team_scores": self.team_scores,
            "individual_scores": self.individual_scores,
            "game_time": self.game_time,
            "game_phase": self.game_phase,
            "teams": self.teams,
            "respawn_timers": self.respawn_timers,
            "eliminated_snakes": self.eliminated_snakes,
            "eliminated_directions": self.eliminated_directions
        }
    
    def start_game(self):
        """Oyunu başlatır"""
        self.game_phase = "active"
        self.start_time = time.time()
    
    def update_game_time(self):
        """Oyun süresini günceller"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.game_time = max(0, 300 - int(elapsed))
            
            if self.game_time <= 0:
                self.game_phase = "finished"
    
    def get_winner(self):
        """Oyunun kazananını döndürür"""
        if self.team_scores[RED_TEAM] > self.team_scores[BLUE_TEAM]:
            return RED_TEAM
        elif self.team_scores[BLUE_TEAM] > self.team_scores[RED_TEAM]:
            return BLUE_TEAM
        else:
            return "tie"  # Beraberlik

# Global CTF oyun durumu
ctf_game_state = CTFGameState()

# Global fonksiyonlar (server.py tarafından çağrılır)
def reset_ctf_game():
    """CTF oyununu sıfırlar"""
    global ctf_game_state
    ctf_game_state = CTFGameState()

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
    
    # Respawn kontrolü
    respawned_players = ctf_game_state.check_respawns()
    if respawned_players:
        print(f"[DEBUG] CTF respawn: {respawned_players} oyuncuları yeniden doğdu")
    
    return respawned_players 