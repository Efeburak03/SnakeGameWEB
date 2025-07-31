# common.py

# Mesaj tipleri
MSG_MOVE = 'move'
MSG_STATE = 'state'
MSG_RESTART = 'restart'
READY_MSG = 'ready'

# Maksimum oyuncu sayısı
MAX_PLAYERS = 8

# Yılan renkleri (her oyuncuya farklı renk)
def get_snake_color(client_id):
    colors = [
        (0, 255, 0),    # Yeşil
        (255, 255, 0),  # Sarı
        (0, 255, 255),  # Camgöbeği
        (255, 0, 255),  # Mor
        (255, 128, 0),  # Turuncu
        (128, 0, 255),  # Mavi-mor
        (255, 0, 0),    # Kırmızı
        (0, 128, 255),  # Açık mavi
    ]
    # client_id string ise hashle, int ise direkt kullan
    idx = abs(hash(str(client_id))) % len(colors)
    return colors[idx]

# Oyun durumu mesajı oluşturucu
def create_state_message(state):
    import json
    return json.dumps(state)

# Engel türleri
OBSTACLE_TYPES = [
    {"type": "wall", "color": (128, 128, 128)},
    {"type": "slow", "color": (0, 255, 0)},
    {"type": "poison", "color": (255, 0, 0)},
    {"type": "hidden_wall", "color": (80, 80, 80)},
]

# Power-up türleri için renkler ve tipler
POWERUP_TYPES = [
    {"type": "speed", "color": (0, 0, 255)},        # Hızlandırıcı (mavi)
    {"type": "shield", "color": (0, 0, 0)},        # Zırh (siyah)
    {"type": "invisible", "color": (128, 128, 128)}, # Görünmezlik (gri)
    {"type": "reverse", "color": (255, 255, 255)},   # Ters kontrol (beyaz)
    {"type": "freeze", "color": (0, 200, 255)},      # Rakibi dondurma (açık mavi)
    {"type": "giant", "color": (255, 128, 0)},       # Dev yılan (turuncu)
    {"type": "magnet", "color": (180, 0, 255)},      # Magnet (mor)
    {"type": "trail", "color": (0, 255, 200, 128)}, # İz bırakıcı (yarı saydam turkuaz)
]

# Oyun başında elma sayısı
INITIAL_FOOD_COUNT = 4

# Time Attack modu sabitleri
TIME_ATTACK_CONSTANTS = {
    "INITIAL_SNAKE_LENGTH": 3,        # Time Attack'ta başlangıç yılan uzunluğu
    "MAX_SNAKE_LENGTH": 10,           # Time Attack'ta maksimum yılan uzunluğu
    "FOOD_COUNT": 2,                  # Time Attack'ta maksimum yem sayısı
    "MAX_POWERUPS": 2,                # Time Attack'ta maksimum power-up sayısı
    "GOLDEN_FOOD_CHANCE": 0.05,       # Altın elma çıkma olasılığı (%5)
    "POWERUP_SPAWN_CHANCE": 0.02,     # Power-up çıkma olasılığı (%2) - artırıldı
    "FOOD_BONUS_TIME": 5,             # Yem yendiğinde +5 saniye
    "GOLDEN_FOOD_BONUS_TIME": 15,     # Altın elma yendiğinde +15 saniye
    "POWERUP_BONUS_TIME": 3,          # Power-up alındığında +3 saniye
    "POWERUP_DURATION": 10,           # Power-up süresi (saniye)
    "MOVE_SPEED": 2,                  # Yılan hareket hızı (her X tick'te bir hareket)
}

# Time Attack zorluk seviyeleri
TIME_ATTACK_DIFFICULTIES = {
    "easy": {
        "time": 120,                   # 2 dakika
        "name": "Kolay",
        "obstacle_multiplier": 1.2,    # Engel çoğaltma faktörü
        "description": "2 dakika süre"
    },
    "medium": {
        "time": 90,                    # 1.5 dakika
        "name": "Orta", 
        "obstacle_multiplier": 1.5,
        "description": "1.5 dakika süre"
    },
    "hard": {
        "time": 60,                    # 1 dakika
        "name": "Zor",
        "obstacle_multiplier": 2.0,
        "description": "1 dakika süre"
    }
}

# Time Attack'ta izin verilen power-up'lar
TIME_ATTACK_ALLOWED_POWERUPS = ["shield", "speed", "reverse", "magnet"]

# Time Attack oyun durumu anahtarları
TIME_ATTACK_STATE_KEYS = [
    "snake", "direction", "food", "golden_food", "obstacles", 
    "powerups", "active_powerups", "score", "time_left", 
    "difficulty", "start_time", "game_active", "high_score", 
    "respawn_count"
] 