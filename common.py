# common.py

# Mesaj tipleri
MSG_MOVE = 'move'
MSG_STATE = 'state'
MSG_RESTART = 'restart'
READY_MSG = 'ready'

# Maksimum oyuncu sayısı
MAX_PLAYERS = 8

# Oyun alanı sabitleri
BOARD_WIDTH = 60   # Enine daha geniş
BOARD_HEIGHT = 35  # 700/20 = 35 satır
START_LENGTH = 3
TICK_RATE = 0.05   # saniye, 20 FPS
MAX_SNAKE_LENGTH = 10

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

# Gelişmiş renk sistemi - her renk için özel efekt bilgileri
SNAKE_COLORS = [
    {
        "name": "Yeşil",
        "color": (0, 255, 0),
        "hex": "#00ff00",
        "effect": "nature",  # Doğa teması - yaprak efektleri
        "particle_color": "#00ff00",
        "glow_color": "#00ff40"
    },
    {
        "name": "Sarı",
        "color": (255, 255, 0),
        "hex": "#ffff00", 
        "effect": "fire",  # Ateş teması - ateş parçacıkları
        "particle_color": "#ff6600",
        "glow_color": "#ffaa00"
    },
    {
        "name": "Camgöbeği",
        "color": (0, 255, 255),
        "hex": "#00ffff",
        "effect": "ice",  # Buz teması - buz kristalleri
        "particle_color": "#00ccff",
        "glow_color": "#00ffff"
    },
    {
        "name": "Mor",
        "color": (255, 0, 255),
        "hex": "#ff00ff",
        "effect": "magic",  # Sihir teması - büyü parçacıkları
        "particle_color": "#cc00ff",
        "glow_color": "#ff00ff"
    },
    {
        "name": "Turuncu",
        "color": (255, 128, 0),
        "hex": "#ff8000",
        "effect": "energy",  # Enerji teması - enerji dalgaları
        "particle_color": "#ff4400",
        "glow_color": "#ff6600"
    },
    {
        "name": "Mavi-Mor",
        "color": (128, 0, 255),
        "hex": "#8000ff",
        "effect": "cosmic",  # Kozmik tema - yıldız parçacıkları
        "particle_color": "#4400ff",
        "glow_color": "#6600ff"
    },
    {
        "name": "Kırmızı",
        "color": (255, 0, 0),
        "hex": "#ff0000",
        "effect": "blood",  # Kan teması - kan damlaları
        "particle_color": "#cc0000",
        "glow_color": "#ff0000"
    },
    {
        "name": "Açık Mavi",
        "color": (0, 128, 255),
        "hex": "#0080ff",
        "effect": "water",  # Su teması - su damlaları
        "particle_color": "#0066cc",
        "glow_color": "#0080ff"
    },

    {
        "name": "Altın",
        "color": (255, 215, 0),
        "hex": "#ffd700",
        "effect": "gold",  # Altın teması - altın parçacıkları
        "particle_color": "#ffcc00",
        "glow_color": "#ffd700"
    },
    {
        "name": "Gümüş",
        "color": (192, 192, 192),
        "hex": "#c0c0c0",
        "effect": "metal",  # Metal teması - metal parçacıkları
        "particle_color": "#a0a0a0",
        "glow_color": "#c0c0c0"
    },
    {
        "name": "Neon Yeşil",
        "color": (57, 255, 20),
        "hex": "#39ff14",
        "effect": "neon",  # Neon teması - neon ışıkları
        "particle_color": "#00ff00",
        "glow_color": "#39ff14"
    }
]

def get_snake_color_info(client_id):
    """Oyuncuya rastgele renk bilgisi döndürür"""
    idx = abs(hash(str(client_id))) % len(SNAKE_COLORS)
    return SNAKE_COLORS[idx]

def get_snake_color(client_id):
    """Geriye uyumluluk için eski fonksiyon"""
    color_info = get_snake_color_info(client_id)
    return color_info["color"]

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
    "FOOD_COUNT": 3,                  # Time Attack'ta maksimum yem sayısı
    "MAX_POWERUPS": 2,                # Time Attack'ta maksimum power-up sayısı
    "GOLDEN_FOOD_CHANCE": 0.02,       # Altın elma çıkma olasılığı (%2)
    "POWERUP_SPAWN_CHANCE": 0.02,     # Power-up çıkma olasılığı (%2) - artırıldı
    "FOOD_BONUS_TIME": 5,             # Yem yendiğinde +5 saniye
    "GOLDEN_FOOD_BONUS_TIME": 15,     # Altın elma yendiğinde +15 saniye
    "POWERUP_BONUS_TIME": 3,          # Power-up alındığında +3 saniye
    "POWERUP_DURATION": 10,           # Power-up süresi (saniye) - tüm power-up'lar için 10 saniye
    "MOVE_SPEED": 2,                  # Yılan hareket hızı (her X tick'te bir hareket)
}

# Time Attack zorluk seviyeleri
TIME_ATTACK_DIFFICULTIES = {
    "easy": {
        "time": 120,                   # 2 dakika
        "name": "Kolay",
        "obstacle_multiplier": 1.5,    # Engel çoğaltma faktörü artırıldı
        "description": "2 dakika süre"
    },
    "medium": {
        "time": 90,                    # 1.5 dakika
        "name": "Orta", 
        "obstacle_multiplier": 2.0,    # Engel çoğaltma faktörü artırıldı
        "description": "1.5 dakika süre"
    },
    "hard": {
        "time": 60,                    # 1 dakika
        "name": "Zor",
        "obstacle_multiplier": 2.5,    # Engel çoğaltma faktörü artırıldı
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