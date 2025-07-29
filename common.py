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
    {"type": "trail", "color": (200, 200, 200, 128)}, # İz bırakıcı (yarı saydam gri)
]

# Oyun başında elma sayısı
INITIAL_FOOD_COUNT = 4 