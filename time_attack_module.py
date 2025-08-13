# --- TIME ATTACK MODU MODÜLÜ ---
import random
import time
import copy

# Time Attack konfigürasyonu (common.py'dan alınacak)
from common import TIME_ATTACK_DIFFICULTIES, TIME_ATTACK_CONSTANTS, TIME_ATTACK_ALLOWED_POWERUPS, get_snake_color_info

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
        
        # Renk bilgisi al (klasik moddaki gibi)
        color_info = get_snake_color_info(client_id)
        
        # Oyun durumu
        # Rastgele güvenli başlangıç pozisyonu bul
        start_pos = self._find_safe_start_position()
        initial_snake = [
            start_pos,                    # Baş
            (start_pos[0]-1, start_pos[1]),    # İkinci blok
            (start_pos[0]-2, start_pos[1])     # Üçüncü blok
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
            "respawn_count": 0,
            # Klasik moddaki renk sistemi
            "color": color_info["color"],
            "color_info": color_info,
            "trails": []  # İz bırakıcı power-up için
        }
        
        # Start the game
        self._place_food()
        self._place_obstacles()
        self._place_portals()
        time_attack_games[client_id] = self.game_state
    
    def _find_safe_start_position(self):
        """Güvenli başlangıç pozisyonu bul"""
        # Kenarlardan uzak pozisyonlar (en az 5 hücre içeride)
        safe_margin = 5
        safe_x_range = range(safe_margin, self.board_width - safe_margin)
        safe_y_range = range(safe_margin, self.board_height - safe_margin)
        
        # Rastgele pozisyonlar dene
        for _ in range(50):  # 50 deneme
            x = random.choice(safe_x_range)
            y = random.choice(safe_y_range)
            
            # Bu pozisyon ve sağındaki 2 hücrenin boş olduğunu kontrol et
            positions = [(x, y), (x-1, y), (x-2, y)]
            if all(0 <= px < self.board_width and 0 <= py < self.board_height 
                   for px, py in positions):
                return (x, y)
        
        # Eğer güvenli pozisyon bulunamazsa, merkeze yakın bir yer
        return (self.board_width//2, self.board_height//2)
    
    def _place_food(self):
        """Yemleri yerleştir"""
        for _ in range(TIME_ATTACK_CONFIG["food_count"]):
            food_pos = self._random_food()
            self.game_state["food"].append(food_pos)
    
    def _place_obstacles(self):
        """Engelleri yerleştir"""
        # Sabit engel sayıları: 11 çalı, 9 enemy
        slow_count = 11
        enemy_count = 9
        
        # Çalı engelleri yerleştir
        for _ in range(slow_count):
            occupied = set()
            occupied.update(self.game_state["snake"])
            occupied.update(self.game_state["food"])
            for obs in self.game_state["obstacles"]:
                occupied.add(tuple(obs["pos"]))
            
            empty = [(x, y) for x in range(self.board_width) for y in range(self.board_height) 
                    if (x, y) not in occupied]
            if empty:
                pos = random.choice(empty)
                self.game_state["obstacles"].append({"pos": pos, "type": "slow"})
        
        # Enemy engelleri yerleştir
        for _ in range(enemy_count):
            occupied = set()
            occupied.update(self.game_state["snake"])
            occupied.update(self.game_state["food"])
            for obs in self.game_state["obstacles"]:
                occupied.add(tuple(obs["pos"]))
            
            empty = [(x, y) for x in range(self.board_width) for y in range(self.board_height) 
                    if (x, y) not in occupied]
            if empty:
                pos = random.choice(empty)
                self.game_state["obstacles"].append({"pos": pos, "type": "enemy"})
    
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
        
        # Engel kontrolü - klasik moddaki gibi
        for obs in self.game_state["obstacles"]:
            if new_head == tuple(obs["pos"]):
                if obs["type"] == "slow":
                    # Çalı engelleri yavaşlatma yapar (klasik moddaki gibi)
                    # Yavaşlatma etkisi için hareket hızını azalt
                    # Bu etki client tarafında işlenecek
                    pass
                elif obs["type"] == "enemy":
                    # Enemy engelleri yılanı kısaltır
                    if len(self.game_state["snake"]) > 1:
                        self.game_state["snake"].pop()
                    else:
                        self.eliminate_snake()
                        return
                # Wall tipi engeller kaldırıldı
                # elif obs["type"] == "wall":
                #     # Normal duvarlar elenme yapar
                #     self.eliminate_snake()
                #     return
                elif obs["type"] == "hidden_wall":
                    # Gizli duvarlar elenme yapar
                    self.eliminate_snake()
                    return
                else:
                    # Diğer engeller de elenme yapar
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
                break
        
        # Trail sistemi (klasik moddaki gibi)
        # Trail power-up aktifse iz bırak
        if self.has_powerup("trail"):
            # Son pozisyonu trail'e ekle
            if len(self.game_state["trails"]) >= 10:  # Maksimum 10 trail
                self.game_state["trails"].pop(0)
            self.game_state["trails"].append(head)
        
        # Yeni başı ekle
        self.game_state["snake"].insert(0, new_head)
        
        # Yem yemediyse kuyruğu kısalt
        if not food_eaten:
            self.game_state["snake"].pop()
        
        # Yeni yem yerleştir
        if not food_eaten:
            new_food = self._random_food()
            if new_food:
                self.game_state["food"].append(new_food)
        
        # Altın elma üretimi (klasik moddaki gibi)
        if (self.game_state["golden_food"] is None and 
            random.random() < TIME_ATTACK_CONFIG["golden_food_chance"]):
            self.game_state["golden_food"] = self._random_food()
        
        # Power-up üretimi
        if (len(self.game_state["powerups"]) < TIME_ATTACK_CONFIG["max_powerups"] and 
            random.random() < 0.01):  # %1 şans
            powerup_pos = self._random_food()
            if powerup_pos:
                powerup_type = random.choice(TIME_ATTACK_CONFIG["allowed_powerups"])
                self.game_state["powerups"].append({
                    "pos": powerup_pos,
                    "type": powerup_type
                })
    
    def eliminate_snake(self):
        """Yılanı ele"""
        if TIME_ATTACK_CONFIG["respawn_allowed"]:
            # Canlanma - rastgele güvenli pozisyonda
            start_pos = self._find_safe_start_position()
            self.game_state["snake"] = [start_pos]
            self.game_state["direction"] = "RIGHT"
            self.game_state["respawn_count"] += 1
            pass
        else:
            # Oyun biter
            self.game_state["game_active"] = False
    
    def activate_powerup(self, powerup_type):
        """Power-up aktivasyonu"""
        if self.client_id not in self.game_state["active_powerups"]:
            self.game_state["active_powerups"][self.client_id] = {}
        
        self.game_state["active_powerups"][self.client_id][powerup_type] = time.time() + TIME_ATTACK_CONSTANTS["POWERUP_DURATION"]
        
        # Trail power-up için özel işlem
        if powerup_type == "trail":
            # Clear trail (start new trail)
            self.game_state["trails"] = []
    
    def has_powerup(self, powerup_type):
        """Power-up kontrolü"""
        if self.client_id not in self.game_state["active_powerups"]:
            return False
        
        if powerup_type not in self.game_state["active_powerups"][self.client_id]:
            return False
        
        return time.time() < self.game_state["active_powerups"][self.client_id][powerup_type]
    
    def update_time(self):
        """Update time"""
        current_time = time.time()
        elapsed = current_time - self.game_state["start_time"]
        self.game_state["time_left"] = max(0, self.game_state["time_left"] - elapsed)
        self.game_state["start_time"] = current_time
        
        # End game if time is up
        if self.game_state["time_left"] <= 0:
            self.game_state["game_active"] = False
            # Update high score
            if self.game_state["score"] > self.game_state["high_score"]:
                self.game_state["high_score"] = self.game_state["score"]
    
    def clear_expired_powerups(self):
        """Clear expired power-ups"""
        current_time = time.time()
        if self.client_id in self.game_state["active_powerups"]:
            expired = []
            for powerup_type, expiry_time in self.game_state["active_powerups"][self.client_id].items():
                if current_time >= expiry_time:
                    expired.append(powerup_type)
            for powerup_type in expired:
                del self.game_state["active_powerups"][self.client_id][powerup_type]
                # Clear trail if trail power-up expired
                if powerup_type == "trail":
                    self.game_state["trails"] = []
    
    def set_direction(self, direction):
        """Set direction"""
        # Reverse control power-up check
        if self.has_powerup("reverse"):
            OPP = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}
            direction = OPP.get(direction, direction)
        
        # Direction control - ters yön kontrolü
        current_dir = self.game_state["direction"]
        OPPOSITE_DIRECTIONS = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        if OPPOSITE_DIRECTIONS.get(current_dir) == direction:
            return
        
        # Kendine çarpma kontrolü - yeni yön yılanın kendi vücuduna çarpar mı?
        snake = self.game_state["snake"]
        if len(snake) > 1:
            head_x, head_y = snake[0]
            if direction == "UP":
                new_head = (head_x, head_y - 1)
            elif direction == "DOWN":
                new_head = (head_x, head_y + 1)
            elif direction == "LEFT":
                new_head = (head_x - 1, head_y)
            elif direction == "RIGHT":
                new_head = (head_x + 1, head_y)
            
            # Yeni baş pozisyonu yılanın mevcut vücuduyla çakışıyor mu?
            if new_head in snake[1:]:
                return  # Bu hareketi atla, yılan kendine çarpar
        
        self.game_state["direction"] = direction
    
    def manual_respawn(self):
        """Manual respawn"""
        if not self.game_state["game_active"]:
            return
        
        # Respawn at random safe position
        start_pos = self._find_safe_start_position()
        self.game_state["snake"] = [start_pos]
        self.game_state["direction"] = "RIGHT"
        self.game_state["respawn_count"] += 1

# --- Modül fonksiyonları ---
def create_time_attack_game(client_id, difficulty, board_width, board_height):
    """Create Time Attack game"""
    return TimeAttackGame(client_id, difficulty, board_width, board_height)

def get_time_attack_game(client_id):
    """Get Time Attack game"""
    if client_id in time_attack_games:
        # Return game state, not class instance
        return time_attack_games[client_id]
    return None

def remove_time_attack_game(client_id):
    """Remove Time Attack game"""
    if client_id in time_attack_games:
        del time_attack_games[client_id]

def update_all_time_attack_games():
    """Update all Time Attack games"""
    for client_id, game_state in list(time_attack_games.items()):
        if game_state["game_active"]:
            # Update time
            current_time = time.time()
            elapsed = current_time - game_state["start_time"]
            game_state["time_left"] = max(0, game_state["time_left"] - elapsed)
            game_state["start_time"] = current_time
            
            # End game if time is up
            if game_state["time_left"] <= 0:
                game_state["game_active"] = False
                # Update high score
                if game_state["score"] > game_state["high_score"]:
                    game_state["high_score"] = game_state["score"]

def clear_expired_powerups_all():
    """Clear all expired power-ups"""
    current_time = time.time()
    for client_id, game_state in time_attack_games.items():
        if client_id in game_state["active_powerups"]:
            expired = []
            for powerup_type, expiry_time in game_state["active_powerups"][client_id].items():
                if current_time >= expiry_time:
                    expired.append(powerup_type)
            for powerup_type in expired:
                del game_state["active_powerups"][client_id][powerup_type] 