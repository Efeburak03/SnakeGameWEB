# Capture the Flag Modu
# Bu modül CTF oyun mantığını içerir

import random
import time
import copy
from common import MSG_MOVE, MSG_STATE, MSG_RESTART, create_state_message, MAX_PLAYERS, get_snake_color

# CTF Oyun Sabitleri
CTF_BOARD_WIDTH = 60
CTF_BOARD_HEIGHT = 35
CTF_START_LENGTH = 6
CTF_TICK_RATE = 0.05
CTF_RESPAWN_TIME = 5  # 5 saniye
CTF_GAME_TIME = 300  # 5 dakika
CTF_COUNTDOWN_TIME = 3  # Oyun başlama sayımı
CTF_MAX_PLAYERS_PER_TEAM = 3

# CTF Power-up Sabitleri
CTF_POWERUP_TYPES = [
    {"type": "shield", "color": (0, 0, 0), "duration": 10},        # Zırh (siyah) - 10s
    {"type": "reverse", "color": (255, 255, 255), "duration": 5},   # Ters kontrol (beyaz) - 5s
    {"type": "magnet", "color": (180, 0, 255), "duration": 5},      # Magnet (mor) - 5s
    {"type": "freeze", "color": (0, 200, 255), "duration": 5},      # Rakibi dondurma (açık mavi) - 5s
    {"type": "invisible", "color": (128, 128, 128), "duration": 5}, # Görünmezlik (gri) - 5s
]

# CTF Power-up Spawn Olasılığı
CTF_POWERUP_SPAWN_CHANCE = 0.01  # %1

# Takım Sabitleri
RED_TEAM = "red"
BLUE_TEAM = "blue"
TEAMS = [RED_TEAM, BLUE_TEAM]

# Bayrak Bölgeleri (5x4 alan)
RED_FLAG_AREA = {
    "x": 1,  # Sol duvar
    "y": 15,  # Ortaya yakın (35/2 - 2)
    "width": 4,
    "height": 5
}

BLUE_FLAG_AREA = {
    "x": 55,  # Sağ duvar (60-5)
    "y": 15,  # Ortaya yakın
    "width": 4,
    "height": 5
}

# Takım Doğuş Noktaları - Çakışma olmayacak şekilde
RED_SPAWN_POSITIONS = [
    (8, 8), (8, 12), (8, 16), (8, 20), (8, 24), (8, 28),
    (12, 8), (12, 12), (12, 16), (12, 20), (12, 24), (12, 28),
    (16, 8), (16, 12), (16, 16), (16, 20), (16, 24), (16, 28)
]

BLUE_SPAWN_POSITIONS = [
    (42, 8), (42, 12), (42, 16), (42, 20), (42, 24), (42, 28),
    (46, 8), (46, 12), (46, 16), (46, 20), (46, 24), (46, 28),
    (50, 8), (50, 12), (50, 16), (50, 20), (50, 24), (50, 28)
]

# Skor Sistemi
FLAG_CAPTURE_SCORE = 15
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
        self.ready_players = {}  # Hazır olan oyuncular
        
        # Bayraklar - her takımın kendi alanında
        self.flags = {
            RED_TEAM: {
                "pos": [RED_FLAG_AREA["x"] + 2, RED_FLAG_AREA["y"] + 2],  # Alanın ortası
                "captured": False,
                "carrier": None,
                "base_pos": [RED_FLAG_AREA["x"] + 2, RED_FLAG_AREA["y"] + 2]
            },
            BLUE_TEAM: {
                "pos": [BLUE_FLAG_AREA["x"] + 2, BLUE_FLAG_AREA["y"] + 2],  # Alanın ortası
                "captured": False,
                "carrier": None,
                "base_pos": [BLUE_FLAG_AREA["x"] + 2, BLUE_FLAG_AREA["y"] + 2]
            }
        }
        
        self.game_time = CTF_GAME_TIME
        self.game_phase = "waiting"  # waiting, countdown, active, finished
        self.countdown_time = CTF_COUNTDOWN_TIME
        self.start_time = None
        self.active = {}
        
        # Power-up sistemi
        self.powerups = []  # Haritadaki power-up'lar
        self.active_powerups = {}  # Oyuncuların aktif power-up'ları
        
        # Round sistemi
        self.round_countdown = 0  # Round sonrası sayım
        self.round_phase = "normal"  # normal, round_end
        
    def can_join_team(self, team):
        """Takıma katılabilir mi kontrol eder"""
        if team not in TEAMS:
            return False
        return len(self.teams[team]) < CTF_MAX_PLAYERS_PER_TEAM
    
    def assign_team(self, player_id, selected_team=None):
        """Oyuncuyu takıma atar"""
        if selected_team and selected_team in TEAMS:
            if self.can_join_team(selected_team):
                team = selected_team
            else:
                return None  # Takım dolu
        else:
            # Otomatik takım ataması
            if len(self.teams[RED_TEAM]) <= len(self.teams[BLUE_TEAM]):
                team = RED_TEAM
            else:
                team = BLUE_TEAM
        
        self.teams[team].append(player_id)
        self.individual_scores[player_id] = 0
        self.ready_players[player_id] = False
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
    
    def all_players_ready(self):
        """Tüm oyuncular hazır mı kontrol eder"""
        if not self.teams[RED_TEAM] and not self.teams[BLUE_TEAM]:
            return False
        
        for team in TEAMS:
            for player_id in self.teams[team]:
                if not self.ready_players.get(player_id, False):
                    return False
        return True
    
    def set_player_ready(self, player_id):
        """Oyuncuyu hazır olarak işaretler"""
        self.ready_players[player_id] = True
        
        # Tüm oyuncular hazır mı kontrol et
        if self.all_players_ready():
            self.start_countdown()
    
    def start_countdown(self):
        """Oyun başlama sayımını başlatır"""
        self.game_phase = "countdown"
        self.countdown_time = CTF_COUNTDOWN_TIME
        print(f"[DEBUG] Oyun başlama sayımı başladı: {self.countdown_time}")
    
    def update_countdown(self):
        """Sayımı günceller"""
        if self.game_phase == "countdown":
            self.countdown_time -= 1
            if self.countdown_time <= 0:
                self.start_game()
    
    def start_game(self):
        """Oyunu başlatır"""
        self.game_phase = "active"
        self.start_time = time.time()
        print(f"[DEBUG] CTF oyunu başladı!")
    
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
            if self.flags[team]["pos"] and flag_pos == tuple(self.flags[team]["pos"]):
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
        
        # Oyuncu donmuş mu?
        if self.has_powerup(player_id, "frozen"):
            return False
        
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
        
        print(f"[DEBUG] {player_id} {flag_team} bayrağını yakaladı!")
        return True
    
    def drop_flag(self, flag_team):
        """Bayrağı düşürür"""
        if flag_team not in TEAMS:
            return
        
        # Bayrağı düşür ve pozisyonunu güncelle
        self.flags[flag_team]["captured"] = False
        self.flags[flag_team]["pos"] = self.flags[flag_team]["base_pos"]
        self.flags[flag_team]["carrier"] = None
        
        print(f"[DEBUG] {flag_team} bayrağı düştü")
    
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
        
        if (self.flags[opponent_team]["carrier"] == player_id and 
            in_team_area and 
            self.flags[opponent_team]["captured"]):
            
            print(f"[DEBUG] {player_id} {opponent_team} bayrağını {player_team} alanına teslim etti!")
            
            # Bayrağı teslim et
            self.flags[opponent_team]["captured"] = False
            self.flags[opponent_team]["carrier"] = None
            self.flags[opponent_team]["pos"] = self.flags[opponent_team]["base_pos"]
            
            # Skor ver
            self.individual_scores[player_id] += FLAG_CAPTURE_SCORE
            self.team_scores[player_team] += FLAG_CAPTURE_SCORE
            
            # Round sonu - oyunu yeniden başlat
            self.start_round_end()
            
            return {"flag_delivered": True, "winning_team": player_team, "winning_player": player_id, "round_won": True}
        
        return False

    def start_round_end(self):
        """Round sonunu başlatır"""
        self.round_phase = "round_end"
        self.round_countdown = 3  # 3 saniye sayım
        print(f"[DEBUG] Round sonu başladı, 3 saniye sonra yeniden başlayacak")
    
    def update_round_end(self):
        """Round sonu sayımını günceller"""
        if self.round_phase == "round_end":
            self.round_countdown -= 1
            if self.round_countdown <= 0:
                self.reset_round()
    
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
        
        # Power-up'ları temizle
        self.powerups = []
        self.active_powerups = {}
        
        # Round fazını sıfırla
        self.round_phase = "normal"
        
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
        
        # Diğer yılanlarla çarpışma (takım arkadaşları hariç)
        for other_id, snake in self.snakes.items():
            if other_id != player_id and other_id in self.active and self.active[other_id]:
                # Takım arkadaşları arasında çarpışma yok
                if not self.is_teammate(player_id, other_id):
                    if new_head in snake:
                        # Kill puanı ver
                        self.individual_scores[player_id] += KILL_SCORE
                        self.team_scores[self.get_player_team(player_id)] += KILL_SCORE
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
        
        # Freeze kontrolü - sadece karşı takımı etkiler
        if self.has_powerup(player_id, "frozen"):
            return False
        
        snake = self.snakes[player_id]
        head = snake[0]
        
        # Ters hareket kontrolü
        if self.has_powerup(player_id, "reverse"):
            if direction == "UP":
                direction = "DOWN"
            elif direction == "DOWN":
                direction = "UP"
            elif direction == "LEFT":
                direction = "RIGHT"
            elif direction == "RIGHT":
                direction = "LEFT"
        
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
        
        # Çarpışma kontrolü (zırh hariç)
        if not self.has_powerup(player_id, "shield"):
            if self.check_collision(player_id, new_head):
                self.eliminate_player(player_id)
                return False
        
        # Yılanı hareket ettir
        snake.insert(0, new_head)
        snake.pop()  # Kuyruğu kaldır
        
        # Power-up kontrolü
        for powerup in list(self.powerups):
            if new_head == tuple(powerup["pos"]):
                powerup_type = powerup["type"]
                self.add_powerup(player_id, powerup_type)
                
                # Özel power-up etkileri
                if powerup_type == "freeze":
                    # Sadece karşı takımı dondur
                    player_team = self.get_player_team(player_id)
                    if player_team:
                        opponent_team = self.get_opponent_team(player_id)
                        for other_id in self.teams.get(opponent_team, []):
                            if other_id in self.active and self.active[other_id]:
                                self.add_powerup(other_id, "frozen")
                
                # Power-up'ı haritadan kaldır
                self.powerups.remove(powerup)
                break
        
        # Magnet etkisi - bayrakları çek
        if self.has_powerup(player_id, "magnet"):
            for team in TEAMS:
                flag_pos = self.flags[team]["pos"]
                if flag_pos and not self.flags[team]["captured"]:
                    # 2 blok yakınında mı kontrol et
                    distance = abs(new_head[0] - flag_pos[0]) + abs(new_head[1] - flag_pos[1])
                    if distance <= 2:
                        # Bayrağı yılanın yanına çek
                        dx = 1 if new_head[0] > flag_pos[0] else -1 if new_head[0] < flag_pos[0] else 0
                        dy = 1 if new_head[1] > flag_pos[1] else -1 if new_head[1] < flag_pos[1] else 0
                        new_flag_x = flag_pos[0] + dx
                        new_flag_y = flag_pos[1] + dy
                        
                        # Pozisyon boş mu kontrol et
                        occupied = set()
                        for s in self.snakes.values():
                            occupied.update(s)
                        
                        if (new_flag_x, new_flag_y) not in occupied:
                            self.flags[team]["pos"] = [new_flag_x, new_flag_y]
        
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
            if flag_pos and not self.flags[team]["captured"]:  # Bayrak pozisyonu varsa ve yakalanmamışsa
                flag_pos_tuple = tuple(flag_pos)
                if new_head == flag_pos_tuple and self.can_capture_flag(player_id, flag_pos_tuple):
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
        
        print(f"[DEBUG] {player_id} elendi, {CTF_RESPAWN_TIME} saniye sonra respawn")
    
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
            self.snakes[player_id] = [(start_x, start_y)]
            for i in range(1, CTF_START_LENGTH):
                self.snakes[player_id].append((start_x-i, start_y))
            self.directions[player_id] = "RIGHT"
        else:
            spawn_pos = random.choice(BLUE_SPAWN_POSITIONS)
            start_x, start_y = spawn_pos
            # Mavi takım sola doğru başlar
            self.snakes[player_id] = [(start_x, start_y)]
            for i in range(1, CTF_START_LENGTH):
                self.snakes[player_id].append((start_x+i, start_y))
            self.directions[player_id] = "LEFT"
        
        self.active[player_id] = True
        self.respawn_timers.pop(player_id, None)
        
        # Elenen yılan ve yön bilgilerini temizle
        self.eliminated_snakes.pop(player_id, None)
        self.eliminated_directions.pop(player_id, None)
        
        print(f"[DEBUG] {player_id} respawn edildi")
        return True
    
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
            "countdown_time": self.countdown_time,
            "teams": self.teams,
            "ready_players": self.ready_players,
            "respawn_timers": self.respawn_timers,
            "eliminated_snakes": self.eliminated_snakes,
            "eliminated_directions": self.eliminated_directions,
            "powerups": self.powerups,
            "active_powerups": self.active_powerups,
            "round_phase": self.round_phase,
            "round_countdown": self.round_countdown
        }
    
    def update_game_time(self):
        """Oyun süresini günceller"""
        if self.game_phase == "active" and self.game_time > 0:
            self.game_time -= 1
            if self.game_time <= 0:
                self.game_phase = "finished"
    
    def has_powerup(self, player_id, powerup_type):
        """Oyuncunun belirli bir power-up'ı olup olmadığını kontrol eder"""
        if player_id not in self.active_powerups:
            return False
        
        current_time = time.time()
        for powerup in self.active_powerups[player_id]:
            if powerup["type"] == powerup_type:
                duration = next((pu["duration"] for pu in CTF_POWERUP_TYPES if pu["type"] == powerup_type), 5)
                if current_time - powerup["tick"] < duration:
                    return True
        return False
    
    def add_powerup(self, player_id, powerup_type):
        """Oyuncuya power-up ekler"""
        if player_id not in self.active_powerups:
            self.active_powerups[player_id] = []
        
        self.active_powerups[player_id].append({
            "type": powerup_type,
            "tick": time.time()
        })
    
    def spawn_powerup(self):
        """Haritaya rastgele power-up yerleştirir"""
        if len(self.powerups) >= 3:  # Maksimum 3 power-up
            return
        
        # Boş pozisyon bul
        occupied_positions = set()
        
        # Yılanları ekle
        for snake in self.snakes.values():
            occupied_positions.update(snake)
        
        # Bayrakları ekle
        for flag in self.flags.values():
            if flag["pos"]:
                occupied_positions.add(tuple(flag["pos"]))
        
        # Mevcut power-up'ları ekle
        for powerup in self.powerups:
            occupied_positions.add(tuple(powerup["pos"]))
        
        # Boş pozisyon ara
        attempts = 0
        while attempts < 50:
            x = random.randint(5, CTF_BOARD_WIDTH - 6)
            y = random.randint(5, CTF_BOARD_HEIGHT - 6)
            
            # Takım alanlarından uzak dur
            if (x < 10 or x > CTF_BOARD_WIDTH - 11):
                attempts += 1
                continue
            
            if (x, y) not in occupied_positions:
                # Rastgele power-up seç
                powerup_type = random.choice(CTF_POWERUP_TYPES)
                self.powerups.append({
                    "type": powerup_type["type"],
                    "pos": [x, y],
                    "color": powerup_type["color"]
                })
                break
            attempts += 1
    
    def update_powerups(self):
        """Power-up sistemini günceller"""
        current_time = time.time()
        
        # Power-up spawn kontrolü
        if random.random() < CTF_POWERUP_SPAWN_CHANCE:
            self.spawn_powerup()
        
        # Süresi dolmuş power-up'ları temizle
        for player_id in list(self.active_powerups.keys()):
            if player_id not in self.active_powerups:
                continue
            
            self.active_powerups[player_id] = [
                pu for pu in self.active_powerups[player_id]
                if current_time - pu["tick"] < next((p["duration"] for p in CTF_POWERUP_TYPES if p["type"] == pu["type"]), 5)
            ]
    
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
    
    # Sayım güncellemesi
    if ctf_game_state.game_phase == "countdown":
        ctf_game_state.update_countdown()
    
    # Oyun süresi güncellemesi
    if ctf_game_state.game_phase == "active":
        ctf_game_state.update_game_time()
        ctf_game_state.update_powerups()
        ctf_game_state.update_round_end()
    
    return []

def remove_ctf_player(client_id):
    """CTF oyunundan oyuncuyu çıkarır"""
    global ctf_game_state
    if client_id in ctf_game_state.snakes:
        ctf_game_state.eliminate_player(client_id)
    
    # Takımlardan da çıkar
    for team in TEAMS:
        if client_id in ctf_game_state.teams[team]:
            ctf_game_state.teams[team].remove(client_id)
    
    # Diğer verilerden de temizle
    ctf_game_state.snakes.pop(client_id, None)
    ctf_game_state.directions.pop(client_id, None)
    ctf_game_state.colors.pop(client_id, None)
    ctf_game_state.active.pop(client_id, None)
    ctf_game_state.individual_scores.pop(client_id, None)
    ctf_game_state.respawn_timers.pop(client_id, None)
    ctf_game_state.eliminated_snakes.pop(client_id, None)
    ctf_game_state.eliminated_directions.pop(client_id, None)
    ctf_game_state.active_powerups.pop(client_id, None)
    ctf_game_state.ready_players.pop(client_id, None)
    
    print(f"[DEBUG] {client_id} CTF oyunundan çıkarıldı") 