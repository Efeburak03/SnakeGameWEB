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