# --- TIME ATTACK MODU MODÜLÜ ---
import random
import time
import copy

# Time Attack konfigürasyonu (common.py'dan alınacak)
from common import TIME_ATTACK_DIFFICULTIES, TIME_ATTACK_CONSTANTS, TIME_ATTACK_ALLOWED_POWERUPS

TIME_ATTACK_CONFIG = {
    "difficulties": TIME_ATTACK_DIFFICULTIES,
    "food_count": TIME_ATTACK_CONSTANTS["FOOD_COUNT"],
    "max_powerups": TIME_ATTACK_CONSTANTS["MAX_POWERUPS"],
    "golden_food_chance": TIME_ATTACK_CONSTANTS["GOLDEN_FOOD_CHANCE"],
    "allowed_powerups": TIME_ATTACK_ALLOWED_POWERUPS,
    "respawn_allowed": True
}

# Time Attack oyun durumları
time_attack_games = {}  # {client_id: game_state}

class TimeAttackGame:
    def __init__(self, client_id, difficulty, board_width, board_height):
        self.client_id = client_id
        self.difficulty = difficulty
        self.board_width = board_width
        self.board_height = board_height
        self.config = TIME_ATTACK_CONFIG["difficulties"][difficulty]
        
        # Oyun durumu
        # Başlangıç yılanı 3 blok uzunluğunda olsun
        center_x = board_width//2
        center_y = board_height//2
        initial_snake = [
            (center_x, center_y),      # Baş
            (center_x-1, center_y),    # İkinci blok
            (center_x-2, center_y)     # Üçüncü blok
        ]
        
        self.game_state = {
            "snake": initial_snake,
            "direction": "RIGHT",
            "food": [],
            "golden_food": None,
            "obstacles": [],
            "portals": [],
            "powerups": [],
            "active_powerups": {},
            "score": 0,
            "time_left": self.config["time"],
            "difficulty": difficulty,
            "start_time": time.time(),
            "game_active": True,
            "high_score": 0,
            "respawn_count": 0
        }
        
        # Oyunu başlat
        self._place_food()
        self._place_obstacles()
        self._place_portals()
        time_attack_games[client_id] = self.game_state
    
    def _place_food(self):
        """Yemleri yerleştir"""
        for _ in range(TIME_ATTACK_CONFIG["food_count"]):
            food_pos = self._random_food()
            self.game_state["food"].append(food_pos)
    
    def _place_obstacles(self):
        """Engelleri yerleştir"""
        base_obstacles = 8
        obstacle_count = int(base_obstacles * self.config["obstacle_multiplier"])
        
        # Engel türleri - klasik oyundaki gibi slow tipi
        obstacle_types = ["slow"]
        
        for _ in range(obstacle_count):
            occupied = set()
            occupied.update(self.game_state["snake"])
            occupied.update(self.game_state["food"])
            for obs in self.game_state["obstacles"]:
                occupied.add(tuple(obs["pos"]))
            
            empty = [(x, y) for x in range(self.board_width) for y in range(self.board_height) 
                    if (x, y) not in occupied]
            if empty:
                pos = random.choice(empty)
                obstacle_type = random.choice(obstacle_types)
                self.game_state["obstacles"].append({"pos": pos, "type": obstacle_type})
    
    def _place_portals(self):
        """Portalları yerleştir"""
        # Boş hücreleri bul
        occupied = set()
        occupied.update(self.game_state["snake"])
        occupied.update(self.game_state["food"])
        for obs in self.game_state["obstacles"]:
            occupied.add(tuple(obs["pos"]))
        
        empty = [(x, y) for x in range(self.board_width) for y in range(self.board_height) 
                if (x, y) not in occupied]
        
        if len(empty) < 2:
            return
        
        # Minimum Manhattan mesafesi
        min_dist = 8
        tries = 20
        
        for _ in range(tries):
            a = random.choice(empty)
            far_cells = [cell for cell in empty if abs(cell[0]-a[0]) + abs(cell[1]-a[1]) >= min_dist]
            if far_cells:
                b = random.choice(far_cells)
                self.game_state["portals"] = [(a, b)]
                return
        
        # Eğer yeterince uzak hücre bulunamazsa, en uzak olanı seç
        a = random.choice(empty)
        b = max(empty, key=lambda cell: abs(cell[0]-a[0]) + abs(cell[1]-a[1]))
        self.game_state["portals"] = [(a, b)]
    
    def _random_food(self):
        """Rastgele yem pozisyonu"""
        occupied = set()
        occupied.update(self.game_state["snake"])
        occupied.update(self.game_state["food"])
        for obs in self.game_state["obstacles"]:
            occupied.add(tuple(obs["pos"]))
        for pu in self.game_state["powerups"]:
            occupied.add(tuple(pu["pos"]))
        
        empty = [(x, y) for x in range(self.board_width) for y in range(self.board_height) 
                if (x, y) not in occupied]
        if not empty:
            return (0, 0)
        return random.choice(empty)
    
    def move_snake(self):
        """Yılanı hareket ettir"""
        if not self.game_state["game_active"]:
            return
        
        head = self.game_state["snake"][0]
        direction = self.game_state["direction"]
        
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
            return
        
        # Sınır kontrolü
        if (new_head[0] < 0 or new_head[0] >= self.board_width or 
            new_head[1] < 0 or new_head[1] >= self.board_height):
            self.eliminate_snake()
            return
        
        # Kendine çarpma kontrolü
        if new_head in self.game_state["snake"]:
            self.eliminate_snake()
            return
        
        # Engel kontrolü
        for obs in self.game_state["obstacles"]:
            if new_head == tuple(obs["pos"]):
                if obs["type"] == "grass":
                    # Çalı engelleri sadece yavaşlatma yapar, elenme yapmaz
                    # Klasik oyundaki gibi slow tipi olarak işle
                    pass
                elif obs["type"] == "slow":
                    # Çalı engelleri sadece yavaşlatma yapar, elenme yapmaz
                    pass
                else:
                    self.eliminate_snake()
                    return
        
        # Portal kontrolü
        if self.game_state.get("portals"):
            for portal in self.game_state["portals"]:
                if new_head == portal[0]:
                    # Portal A'dan B'ye ışınla
                    self.game_state["snake"][0] = portal[1]
                    break
                elif new_head == portal[1]:
                    # Portal B'den A'ya ışınla
                    self.game_state["snake"][0] = portal[0]
                    break
        
        # Yem kontrolü
        food_eaten = False
        for i, food_pos in enumerate(self.game_state["food"]):
            if new_head == food_pos:
                self.game_state["score"] += 10
                self.game_state["time_left"] += TIME_ATTACK_CONSTANTS["FOOD_BONUS_TIME"]
                self.game_state["food"].pop(i)
                food_eaten = True
                break
        
        # Altın elma kontrolü
        if self.game_state["golden_food"] and new_head == self.game_state["golden_food"]:
            self.game_state["score"] += 50
            self.game_state["time_left"] += TIME_ATTACK_CONSTANTS["GOLDEN_FOOD_BONUS_TIME"]
            self.game_state["golden_food"] = None
        
        # Power-up kontrolü
        for i, powerup in enumerate(self.game_state["powerups"]):
            if new_head == tuple(powerup["pos"]):
                self.activate_powerup(powerup["type"])
                self.game_state["powerups"].pop(i)
                self.game_state["time_left"] += TIME_ATTACK_CONSTANTS["POWERUP_BONUS_TIME"]
                break
        
        # Yılanı güncelle
        self.game_state["snake"].insert(0, new_head)
        if not food_eaten:
            self.game_state["snake"].pop()
        
        # Yılan uzunluğu kontrolü
        if len(self.game_state["snake"]) > TIME_ATTACK_CONSTANTS["MAX_SNAKE_LENGTH"]:
            self.game_state["snake"] = self.game_state["snake"][:TIME_ATTACK_CONSTANTS["MAX_SNAKE_LENGTH"]]
        
        # Yeni yem ekle
        if food_eaten and len(self.game_state["food"]) < TIME_ATTACK_CONFIG["food_count"]:
            new_food = self._random_food()
            self.game_state["food"].append(new_food)
        
        # Altın elma olasılığı
        if random.random() < TIME_ATTACK_CONFIG["golden_food_chance"] and not self.game_state["golden_food"]:
            self.game_state["golden_food"] = self._random_food()
        
        # Power-up olasılığı
        if (len(self.game_state["powerups"]) < TIME_ATTACK_CONFIG["max_powerups"] and 
            random.random() < 0.01):  # %1 olasılık
            powerup_type = random.choice(TIME_ATTACK_CONFIG["allowed_powerups"])
            powerup_pos = self._random_food()
            self.game_state["powerups"].append({"pos": powerup_pos, "type": powerup_type})
    
    def eliminate_snake(self):
        """Yılanı ele"""
        if TIME_ATTACK_CONFIG["respawn_allowed"]:
            # Canlanma
            self.game_state["snake"] = [(self.board_width//2, self.board_height//2)]
            self.game_state["direction"] = "RIGHT"
            self.game_state["respawn_count"] += 1
            print(f"[DEBUG] {self.client_id} canlandı! Canlanma sayısı: {self.game_state['respawn_count']}")
        else:
            # Oyun biter
            self.game_state["game_active"] = False
            print(f"[DEBUG] {self.client_id} Time Attack oyunu bitti!")
    
    def activate_powerup(self, powerup_type):
        """Power-up aktivasyonu"""
        if self.client_id not in self.game_state["active_powerups"]:
            self.game_state["active_powerups"][self.client_id] = {}
        
        self.game_state["active_powerups"][self.client_id][powerup_type] = time.time() + TIME_ATTACK_CONSTANTS["POWERUP_DURATION"]
    
    def has_powerup(self, powerup_type):
        """Power-up kontrolü"""
        if self.client_id not in self.game_state["active_powerups"]:
            return False
        
        if powerup_type not in self.game_state["active_powerups"][self.client_id]:
            return False
        
        return time.time() < self.game_state["active_powerups"][self.client_id][powerup_type]
    
    def update_time(self):
        """Süreyi güncelle"""
        current_time = time.time()
        elapsed = current_time - self.game_state["start_time"]
        self.game_state["time_left"] = max(0, self.game_state["time_left"] - elapsed)
        self.game_state["start_time"] = current_time
        
        # Süre bittiyse oyunu bitir
        if self.game_state["time_left"] <= 0:
            self.game_state["game_active"] = False
            # En yüksek skoru güncelle
            if self.game_state["score"] > self.game_state["high_score"]:
                self.game_state["high_score"] = self.game_state["score"]
            print(f"[DEBUG] {self.client_id} Time Attack süresi bitti! Skor: {self.game_state['score']}")
    
    def clear_expired_powerups(self):
        """Süresi dolmuş power-up'ları temizle"""
        current_time = time.time()
        if self.client_id in self.game_state["active_powerups"]:
            expired = []
            for powerup_type, expiry_time in self.game_state["active_powerups"][self.client_id].items():
                if current_time >= expiry_time:
                    expired.append(powerup_type)
            for powerup_type in expired:
                del self.game_state["active_powerups"][self.client_id][powerup_type]
    
    def set_direction(self, direction):
        """Yön ayarla"""
        # Ters kontrol power-up kontrolü
        if self.has_powerup("reverse"):
            OPP = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}
            direction = OPP.get(direction, direction)
        
        # Yön kontrolü
        current_dir = self.game_state["direction"]
        OPPOSITE_DIRECTIONS = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        if OPPOSITE_DIRECTIONS.get(current_dir) == direction:
            return
        
        self.game_state["direction"] = direction
    
    def manual_respawn(self):
        """Manuel canlanma"""
        if not self.game_state["game_active"]:
            return
        
        self.game_state["snake"] = [(self.board_width//2, self.board_height//2)]
        self.game_state["direction"] = "RIGHT"
        self.game_state["respawn_count"] += 1
        print(f"[DEBUG] {self.client_id} manuel canlanma! Canlanma sayısı: {self.game_state['respawn_count']}")

# --- Modül fonksiyonları ---
def create_time_attack_game(client_id, difficulty, board_width, board_height):
    """Time Attack oyunu oluştur"""
    return TimeAttackGame(client_id, difficulty, board_width, board_height)

def get_time_attack_game(client_id):
    """Time Attack oyununu getir"""
    if client_id in time_attack_games:
        # Game state'i döndür, class instance'ı değil
        return time_attack_games[client_id]
    return None

def remove_time_attack_game(client_id):
    """Time Attack oyununu kaldır"""
    if client_id in time_attack_games:
        del time_attack_games[client_id]

def update_all_time_attack_games():
    """Tüm Time Attack oyunlarını güncelle"""
    for client_id, game_state in list(time_attack_games.items()):
        if game_state["game_active"]:
            # Süreyi güncelle
            current_time = time.time()
            elapsed = current_time - game_state["start_time"]
            game_state["time_left"] = max(0, game_state["time_left"] - elapsed)
            game_state["start_time"] = current_time
            
            # Süre bittiyse oyunu bitir
            if game_state["time_left"] <= 0:
                game_state["game_active"] = False
                # En yüksek skoru güncelle
                if game_state["score"] > game_state["high_score"]:
                    game_state["high_score"] = game_state["score"]
                print(f"[DEBUG] {client_id} Time Attack süresi bitti! Skor: {game_state['score']}")

def clear_expired_powerups_all():
    """Tüm süresi dolmuş power-up'ları temizle"""
    current_time = time.time()
    for client_id, game_state in time_attack_games.items():
        if client_id in game_state["active_powerups"]:
            expired = []
            for powerup_type, expiry_time in game_state["active_powerups"][client_id].items():
                if current_time >= expiry_time:
                    expired.append(powerup_type)
            for powerup_type in expired:
                del game_state["active_powerups"][client_id][powerup_type] 