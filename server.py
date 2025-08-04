# --- En üstteki importlar ---
import random
import time
import copy
import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, disconnect
from common import MSG_MOVE, MSG_STATE, MSG_RESTART, create_state_message, MAX_PLAYERS, get_snake_color, OBSTACLE_TYPES, POWERUP_TYPES, INITIAL_FOOD_COUNT

# Time Attack modülünü import et
import time_attack_module

# Capture the Flag modülünü import et
import capture_the_flag_module

BOARD_WIDTH = 60   # Enine daha geniş
BOARD_HEIGHT = 35 # 700/20 = 35 satır
TICK_RATE = 0.05  # saniye, 30 FPS

# Power-up türleri ve renkleri:
#   speed      : Mavi        (0, 0, 255)
#   shield     : Siyah       (0, 0, 0)
#   invisible  : Gri         (128, 128, 128)
#   reverse    : Beyaz       (255, 255, 255)
#   freeze     : Açık Mavi   (0, 200, 255)
#   giant      : Turuncu     (255, 128, 0)
#   magnet     : Mor         (180, 0, 255)
# POWERUP_TYPES artık common.py'den geliyor

def random_powerup(snakes, foods, obstacles, portals, powerups):
    occupied = set()
    for snake in snakes.values():
        occupied.update(snake)
    occupied.update(foods)
    for obs in obstacles:
        occupied.add(tuple(obs["pos"]))
    for portal in portals:
        occupied.add(portal[0])
        occupied.add(portal[1])
    for p in powerups:
        occupied.add(tuple(p["pos"]))
    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT) if (x, y) not in occupied]
    if not empty:
        return {"pos": (0, 0), "type": "speed"}
    x, y = random.choice(empty)
    ptype = random.choice(POWERUP_TYPES)
    return {"pos": (x, y), "type": ptype["type"]}

def random_food(snakes, foods, obstacles=None, portals=None, powerups=None, golden_food=None):
    occupied = set()
    for snake in snakes.values():
        occupied.update(snake)
    occupied.update(foods)
    if golden_food:
        if isinstance(golden_food, (list, tuple)) and len(golden_food) == 2:
            occupied.add(tuple(golden_food))
    if obstacles:
        for obs in obstacles:
            occupied.add(tuple(obs["pos"]))
    if portals:
        for portal in portals:
            occupied.add(portal[0])
            occupied.add(portal[1])
    if powerups:
        for pu in powerups:
            occupied.add(tuple(pu["pos"]))
    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT) if (x, y) not in occupied]
    if not empty:
        return (0, 0)
    return random.choice(empty)

# --- Mermi sistemi ve ilgili alanlar kaldırıldı ---

# --- OYUN DURUMU ---
game_state = {
    "snakes": {},
    "directions": {},
    "food": [(5, 5 + i*2) for i in range(INITIAL_FOOD_COUNT)],
    "golden_food": None,
    "active": {},
    "colors": {},
    "obstacles": [],
    "scores": {},
    "portals": [],
    "powerups": [],
    "active_powerups": {},
    "trails": {},  # İz bırakıcı power-up için: {client_id: [(x, y), ...]}
}

def get_all_empty_cells():
    occupied = set()
    for snake in game_state["snakes"].values():
        occupied.update(snake)
    occupied.update(game_state["food"])
    if "obstacles" in game_state:
        for obs in game_state["obstacles"]:
            occupied.add(tuple(obs["pos"]))
    if "portals" in game_state:
        for portal in game_state["portals"]:
            occupied.add(portal[0])
            occupied.add(portal[1])
    if "powerups" in game_state:
        for pu in game_state["powerups"]:
            occupied.add(tuple(pu["pos"]))
    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT) if (x, y) not in occupied]
    random.shuffle(empty)
    return empty

def place_obstacles():
    obstacles = []
    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT)]
    random.shuffle(empty)
    idx = 0
    for _ in range(15):  # Çimen (slow) - sayıyı artırdık
        pos = empty[idx]; idx += 1
        obstacles.append({"pos": pos, "type": "slow"})
    for _ in range(7):  # Kutu (poison)
        pos = empty[idx]; idx += 1
        obstacles.append({"pos": pos, "type": "poison"})
    for _ in range(7):  # Gizli duvar
        pos = empty[idx]; idx += 1
        obstacles.append({"pos": pos, "type": "hidden_wall"})
    return obstacles

def place_portals():
    empty = get_all_empty_cells()
    if len(empty) < 2:
        return []
    import random
    min_dist = 8  # Minimum Manhattan mesafesi
    tries = 20
    for _ in range(tries):
        a = random.choice(empty)
        far_cells = [cell for cell in empty if abs(cell[0]-a[0]) + abs(cell[1]-a[1]) >= min_dist]
        if far_cells:
            b = random.choice(far_cells)
            return [(a, b)]
    # Eğer yeterince uzak hücre bulunamazsa, en uzak olanı seç
    a = random.choice(empty)
    b = max(empty, key=lambda cell: abs(cell[0]-a[0]) + abs(cell[1]-a[1]))
    return [(a, b)]

def reset_snake(client_id):
    # Maksimum oyuncu kontrolü
    if len(game_state["snakes"]) >= MAX_PLAYERS and client_id not in game_state["snakes"]:
        return  # Yeni oyuncu kabul etme
    x = random.randint(2, BOARD_WIDTH-3)
    y = random.randint(6, BOARD_HEIGHT-1)  # Y koordinatı 6 ve üzeri, ilk 5 satırda doğmaz
    snake = [(x, y)]
    for i in range(1, 3): # START_LENGTH yerine 3 kullanıldı
        snake.append((x, y+i))
    game_state["snakes"][client_id] = snake
    game_state["directions"][client_id] = "UP"
    game_state["active"][client_id] = True
    # Kullanılan renkleri bul ve çakışmayı engelle
    used_colors = set(game_state["colors"].values())
    all_colors = [
        (0, 255, 0),    # Yeşil
        (255, 255, 0),  # Sarı
        (0, 255, 255),  # Camgöbeği
        (255, 0, 255),  # Mor
        (255, 128, 0),  # Turuncu
        (128, 0, 255),  # Mavi-mor
        (255, 0, 0),    # Kırmızı
        (0, 128, 255),  # Açık mavi
    ]
    color = next((c for c in all_colors if c not in used_colors), get_snake_color(client_id))
    game_state["colors"][client_id] = color
    if client_id not in game_state["scores"]:
        game_state["scores"][client_id] = 0
    if client_id not in game_state["active_powerups"]:
        game_state["active_powerups"][client_id] = []
    if len(game_state["snakes"]) == 1:
        game_state["obstacles"] = place_obstacles()  # Sadece ilk oyuncu girince engelleri yerleştir
        game_state["portals"] = place_portals()      # Sadece ilk oyuncu girince portalları yerleştir

# --- Power-up süreleri ---
POWERUP_DURATIONS = {"speed": 10, "shield": 10, "invisible": 10, "reverse": 5, "freeze": 5, "giant": 10, "trail": 10, "magnet": 10}

def has_powerup(cid, ptype):
    now = time.time()
    for p in game_state.get("active_powerups", {}).get(cid, []):
        if p["type"] == ptype and now - p["tick"] < POWERUP_DURATIONS.get(ptype, 10):
            return True
    return False

def has_powerup_time_attack(cid, ptype, ta_game_state):
    now = time.time()
    for p in ta_game_state.get("active_powerups", {}).get(cid, []):
        if p["type"] == ptype and now - p["tick"] < time_attack_module.TIME_ATTACK_CONSTANTS["POWERUP_DURATION"]:
            return True
    return False

def clear_expired_time_attack_powerups():
    now = time.time()
    for client_id in list(time_attack_module.time_attack_games.keys()):
        ta_game_state = time_attack_module.time_attack_games[client_id]
        if client_id in ta_game_state.get("active_powerups", {}):
            expired = []
            for p in ta_game_state["active_powerups"][client_id]:
                if now - p["tick"] >= time_attack_module.TIME_ATTACK_CONSTANTS["POWERUP_DURATION"]:
                    expired.append(p["type"])
            for ptype in expired:
                ta_game_state["active_powerups"][client_id] = [p for p in ta_game_state["active_powerups"][client_id] if p["type"] != ptype]

def get_powerup_timeleft(cid, ptype):
    now = time.time()
    for p in game_state.get("active_powerups", {}).get(cid, []):
        if p["type"] == ptype and now - p["tick"] < POWERUP_DURATIONS.get(ptype, 10):
            return max(0, POWERUP_DURATIONS.get(ptype, 10) - (now - p["tick"]))
    return 0

def clear_expired_powerups():
    now = time.time()
    expired = []
    for cid, powers in list(game_state.get("active_powerups", {}).items()):
        for p in list(powers):
            if now - p["tick"] >= POWERUP_DURATIONS.get(p["type"], 10):
                expired.append((cid, p["type"]))
    for cid, ptype in expired:
        game_state["active_powerups"][cid] = [p for p in game_state["active_powerups"][cid] if p["type"] != ptype]
        # Eğer biten power-up trail ise izleri de sil
        if ptype == "trail" and cid in game_state["trails"]:
            del game_state["trails"][cid]

def eliminate_snake(client_id):
    game_state["active"][client_id] = False
    # Elenince power-up'ları temizle
    if "active_powerups" in game_state and client_id in game_state["active_powerups"]:
        del game_state["active_powerups"][client_id]
    # Skoru sıfırlama kaldırıldı
    # Yılanı haritada tutmaya devam edelim ama hareket etmesin

# --- Oyun döngüsünde power-up etkilerini uygula ---
GAME_DURATION = 120  # saniye (2 dakika)
game_timer = None
waiting_for_restart = False
winner_id = None

def all_players_ready():
    # Tüm aktif olmayan oyuncular hazır komutu gönderdiyse True döner
    if not game_state["snakes"]:
        return False
    for cid in game_state["snakes"]:
        if not game_state["active"].get(cid, True):
            if not game_state.get("ready", {}).get(cid, False):
                return False
    return True

def reset_game():
    global game_timer, waiting_for_restart, winner_id
    # Tüm oyuncuları yeniden başlat
    for cid in list(game_state["snakes"].keys()):
        reset_snake(cid)
        game_state["scores"][cid] = 0  # Skorları burada sıfırla
    # --- YEMLERİ RASTGELE YERLEŞTİR ---
    game_state["food"] = []
    for _ in range(INITIAL_FOOD_COUNT):
        pos = random_food(game_state["snakes"], game_state["food"], game_state["obstacles"], game_state["portals"], game_state["powerups"], game_state["golden_food"])
        game_state["food"].append(pos)
    game_state["ready"] = {}
    game_timer = time.time()
    print(f"[DEBUG] reset_game: game_timer set to {game_timer}")
    waiting_for_restart = False
    winner_id = None

# --- Oyun döngüsünde süre ve bitiş kontrolü ---
async def game_loop():
    global game_timer, waiting_for_restart, winner_id
    last_state_msg = None
    powerup_spawn_chance = 0.01
    max_powerups = 4
    tick_count = 0
    waiting_for_restart = False
    winner_id = None
    game_started = False
    while True:
        # Oyun hiç başlamadıysa ve en az bir oyuncu varsa, sadece bir kez başlat
        if not game_started and game_timer is None and len(game_state["snakes"]) > 0:
            print("[DEBUG] game_loop: Oyun başlatılıyor, reset_game çağrılıyor.")
            reset_game()
            game_started = True
        # Oyun bittiğinde (tüm oyuncular elendiğinde veya süre bittiğinde) tekrar başlatmak için flag'i sıfırla
        if game_timer is None:
            game_started = False
        clear_expired_powerups()
        global move_queue
        new_queue = []
        now = time.time()
        # Oyun süresi kontrolü
        if not waiting_for_restart and game_timer is not None and now - game_timer >= GAME_DURATION:
            # Süre bitti, kazananı belirle
            max_score = -1
            winner_id = None
            for cid, score in game_state["scores"].items():
                if score > max_score:
                    max_score = score
                    winner_id = cid
            waiting_for_restart = True
            # Tüm oyuncuları pasif yap
            for cid in game_state["snakes"]:
                game_state["active"][cid] = False
        # Oyuncular hazırsa oyunu tekrar başlat
        if waiting_for_restart and all_players_ready():
            reset_game()
        # Normal oyun akışı
        if not waiting_for_restart:
            for msg in move_queue:
                cid = msg["client_id"]
                direction = msg["direction"]
                if has_powerup(cid, "reverse"):
                    OPP = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}
                    direction = OPP.get(direction, direction)
                msg["direction"] = direction
                new_queue.append(msg)
            move_queue = new_queue
            while move_queue:
                msg = move_queue.pop(0)
                client_id = msg["client_id"]
                direction = msg["direction"]
                current_dir = game_state["directions"].get(client_id)
                OPPOSITE_DIRECTIONS = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
                if current_dir and OPPOSITE_DIRECTIONS.get(current_dir) == direction:
                    continue
                if client_id in game_state["snakes"]:
                    game_state["directions"][client_id] = direction
                else:
                    reset_snake(client_id)
            # Power-up, golden apple, yılan hareketi vs. aynı şekilde devam
            if len(game_state["powerups"]) < max_powerups and random.random() < powerup_spawn_chance:
                pu = random_powerup(
                    game_state["snakes"],
                    game_state["food"],
                    game_state["obstacles"],
                    game_state["portals"],
                    game_state["powerups"]
                )
                # --- Aynı türden 2'den fazla power-up kontrolü ---
                same_type_count = sum(1 for p in game_state["powerups"] if p["type"] == pu["type"])
                if same_type_count < 2:
                    game_state["powerups"].append(pu)
            # Altın elma üretimi
            if game_state["golden_food"] is None and random.random() < 0.01:
                game_state["golden_food"] = random_food(
                    game_state["snakes"],
                    game_state["food"],
                    game_state["obstacles"],
                    game_state["portals"],
                    game_state["powerups"],
                    None
                )
            for client_id in list(game_state["snakes"].keys()):
                # Eğer oyuncu dondurulmuşsa hareket ettirme
                if has_powerup(client_id, "frozen"):
                    continue
                if has_powerup(client_id, "speed"):
                    move_snake(client_id)
                else:
                    if tick_count % 2 == 0:
                        move_snake(client_id)
        # --- Magnet power-up aktifse, sadece normal elmalar çekilsin ---
        for cid, snake in game_state["snakes"].items():
            if has_powerup(cid, "magnet") and len(snake) > 0:
                head = snake[0]
                new_foods = []
                for fx, fy in game_state["food"]:
                    dist = abs(fx - head[0]) + abs(fy - head[1])
                    if dist <= 5:
                        dx = 1 if head[0] > fx else -1 if head[0] < fx else 0
                        dy = 1 if head[1] > fy else -1 if head[1] < fy else 0
                        new_fx = fx + dx
                        new_fy = fy + dy
                        occupied = set()
                        for s in game_state["snakes"].values():
                            occupied.update(s)
                        if (new_fx, new_fy) not in occupied:
                            new_foods.append((new_fx, new_fy))
                        else:
                            new_foods.append((fx, fy))
                    else:
                        new_foods.append((fx, fy))
                game_state["food"] = new_foods
        # Altın elma için magnet etkisi yok!
        # Her client için özel state gönder
        for client_id in list(game_state["snakes"].keys()):
            state_copy = copy.deepcopy(game_state)
            if game_timer is not None and not waiting_for_restart:
                state_copy["time_left"] = max(0, int(GAME_DURATION - (now - game_timer)))
            else:
                state_copy["time_left"] = 0
            state_copy["winner_id"] = winner_id
            state_copy["waiting_for_restart"] = waiting_for_restart
            state_copy["powerup_timers"] = {}
            for cid in state_copy["snakes"].keys():
                timers = {}
                for ptype in ["speed","shield","invisible","reverse","magnet"]:
                    tleft = get_powerup_timeleft(cid, ptype)
                    if tleft > 0:
                        timers[ptype] = tleft
                if timers:
                    state_copy["powerup_timers"][cid] = timers
            state_copy["golden_food"] = game_state["golden_food"]
            for cid in list(state_copy["snakes"].keys()):
                if has_powerup(cid, "invisible") and cid != client_id:
                    state_copy["snakes"][cid] = []
            state_msg = create_state_message(state_copy)
            # Her client'a güncel state'i gönder
            for ws, pid in list(clients.items()):
                if pid == client_id:
                    try:
                        await ws.send(state_msg)
                    except:
                        pass
        # CTF oyun güncellemesi
        ctf_update_result = capture_the_flag_module.update_ctf_game()
        if ctf_update_result.get("game_over"):
            winner = ctf_update_result.get("winner")
            print(f"[DEBUG] CTF oyunu bitti! Kazanan: {winner}")
            # CTF oyun durumunu tüm oyunculara gönder
            ctf_state = capture_the_flag_module.get_ctf_game_state()
            for ws, pid in list(clients.items()):
                try:
                    await ws.send(create_state_message({
                        "type": "ctf_game_over",
                        "winner": winner,
                        "game_state": ctf_state
                    }))
                except:
                    pass
        
        tick_count += 1
        await asyncio.sleep(TICK_RATE)

# --- Zırh etkisi: move_snake içinde çarpışma kontrolünde uygula ---
MAX_SNAKE_LENGTH = 10
def move_snake(client_id):
    if not game_state["active"].get(client_id, True):
        return
    direction = game_state["directions"].get(client_id)
    if not direction:
        return  # Direction gelmeden yılanı hareket ettirme
    snake = game_state["snakes"].get(client_id)
    if not snake:
        reset_snake(client_id)
        snake = game_state["snakes"][client_id]
    head_x, head_y = snake[0]
    if direction == "UP":
        head_y -= 1
    elif direction == "DOWN":
        head_y += 1
    elif direction == "LEFT":
        head_x -= 1
    elif direction == "RIGHT":
        head_x += 1
    new_head = (head_x, head_y)
    # --- Altın elma kontrolü ---
    if game_state.get("golden_food") and new_head == tuple(game_state["golden_food"]):
        snake.insert(0, new_head)
        game_state["golden_food"] = None
        game_state["scores"][client_id] = game_state["scores"].get(client_id, 0) + 5
        return
    # --- POWER-UP KONTROLÜ ---
    # Magnet etkisi artık burada uygulanmıyor, sadece power-up'ı sil
    for pu in list(game_state.get("powerups", [])):
        if new_head == tuple(pu["pos"]):
            if "active_powerups" not in game_state:
                game_state["active_powerups"] = {}
            if client_id not in game_state["active_powerups"]:
                game_state["active_powerups"][client_id] = []
            game_state["active_powerups"][client_id].append({"type": pu["type"], "tick": time.time()})
            # Freeze ve giant etkileri burada kalacak
            if pu["type"] == "freeze":
                for other_id in game_state["snakes"]:
                    if other_id != client_id:
                        game_state["active_powerups"].setdefault(other_id, []).append({"type": "frozen", "tick": time.time()})
            if pu["type"] == "giant":
                snake = game_state["snakes"][client_id]
                for _ in range(3): # START_LENGTH yerine 3 kullanıldı
                    snake.append(snake[-1])
            game_state["powerups"].remove(pu)
    # --- PORTAL KONTROLÜ ---
    for portal_a, portal_b in game_state.get("portals", []):
        if new_head == portal_a:
            new_head = portal_b
            break
        elif new_head == portal_b:
            new_head = portal_a
            break
    # Engel kontrolü
    shielded = has_powerup(client_id, "shield")
    if not shielded:
        for obs in game_state.get("obstacles", []):
            if new_head == tuple(obs["pos"]):
                if obs["type"] == "slow":
                    # Çalı engelleri sadece yavaşlatma yapar, elenme yapmaz
                    pass
                elif obs["type"] == "poison":
                    if len(snake) > 1:
                        snake.pop()
                    else:
                        eliminate_snake(client_id)
                        return
                elif obs["type"] == "wall":
                    eliminate_snake(client_id)
                    return
                elif obs["type"] == "hidden_wall":
                    # Gizli duvarlar elenme yapar
                    eliminate_snake(client_id)
                    return
                break
    # Çarpışma kontrolü (zırh etkisi ve duvardan geçiş)
    shielded = has_powerup(client_id, "shield")
    out_of_bounds = not (0 <= new_head[0] < BOARD_WIDTH and 0 <= new_head[1] < BOARD_HEIGHT)
    if out_of_bounds:
        if shielded:
            game_state["active_powerups"][client_id] = [p for p in game_state["active_powerups"][client_id] if p["type"] != "shield"]
            nx, ny = new_head
            if nx < 0:
                nx = BOARD_WIDTH - 1
            elif nx >= BOARD_WIDTH:
                nx = 0
            if ny < 0:
                ny = BOARD_HEIGHT - 1
            elif ny >= BOARD_HEIGHT:
                ny = 0
            new_head = (nx, ny)
        else:
            eliminate_snake(client_id)
            return
    for other_id, other_snake in game_state["snakes"].items():
        if other_id != client_id and new_head in other_snake:
            if shielded:
                game_state["active_powerups"][client_id] = [p for p in game_state["active_powerups"][client_id] if p["type"] != "shield"]
                break
            else:
                eliminate_snake(client_id)
                return
    # Kendine çarpma kontrolü - yılanın kuyruğu hariç kontrol et
    if new_head in snake[:-1]:  # Son eleman (kuyruk) hariç kontrol et
        if shielded:
            game_state["active_powerups"][client_id] = [p for p in game_state["active_powerups"][client_id] if p["type"] != "shield"]
        else:
            eliminate_snake(client_id)
            return
    # --- Hareketli yem kontrolü ---
    # Büyüme kontrolü
    ate_food = False
    for i, food in enumerate(game_state["food"]):
        if new_head == food:
            snake.insert(0, new_head)
            game_state["food"][i] = random_food(
                game_state["snakes"],
                game_state["food"],
                game_state["obstacles"],
                game_state["portals"],
                game_state["powerups"],
                game_state["golden_food"]
            )
            ate_food = True
            game_state["scores"][client_id] = game_state["scores"].get(client_id, 0) + 1
            break
    if not ate_food:
        snake.insert(0, new_head)
        snake.pop()
    else:
        snake.insert(0, new_head)
    # Uzunluk sınırı uygula
    if len(snake) > MAX_SNAKE_LENGTH:
        snake = snake[:MAX_SNAKE_LENGTH]
    game_state["snakes"][client_id] = snake
    # --- TRAIL POWER-UP GÜNCELLEME ---
    # Eğer oyuncuda trail power-up varsa, iz güncelle
    if has_powerup(client_id, "trail"):
        trail = game_state["trails"].setdefault(client_id, [])
        # Yılanın son bloğu iz olarak eklenir
        if len(snake) > 0:
            trail.append(snake[-1])
        # İz uzunluğu 6'yı geçmesin
        if len(trail) > 6:
            trail = trail[-6:]
        game_state["trails"][client_id] = trail
    else:
        # Power-up yoksa izleri temizle
        if client_id in game_state["trails"]:
            del game_state["trails"][client_id]
    # --- İZ ÇARPIŞMA KONTROLÜ ---
    # Kendi izine veya başkasının izine çarparsa elenir
    head = snake[0]
    for trail_owner, trail_blocks in game_state["trails"].items():
        if head in trail_blocks:
            eliminate_snake(client_id)
            return

move_queue = []
clients = {}  # sid: client_id

READY_MSG = "ready"

def enqueue_move(msg):
    move_queue.append(msg)

def enqueue_control(msg):
    if msg.get("type") == MSG_RESTART:
        client_id = msg["client_id"]
        reset_snake(client_id)
    elif msg.get("type") == 'disconnect':
        client_id = msg["client_id"]
        game_state["snakes"].pop(client_id, None)
        game_state["directions"].pop(client_id, None)
        game_state["active"].pop(client_id, None)
        game_state["colors"].pop(client_id, None)
        game_state["scores"].pop(client_id, None)
        if "active_powerups" in game_state:
            game_state["active_powerups"].pop(client_id, None)
    elif msg.get("type") == READY_MSG:
        client_id = msg["client_id"]
        if "ready" not in game_state:
            game_state["ready"] = {}
        game_state["ready"][client_id] = True

# ws_handler fonksiyonunun doğru tanımı:
async def ws_handler(websocket):
    print("ws_handler ÇAĞRILDI", websocket)
    client_id = None
    try:
        async for message in websocket:
            msg = json.loads(message)
            if msg.get("type") == "join":
                client_id = msg.get("client_id")
                # Aynı isimle giriş engeli
                if client_id in game_state["snakes"]:
                    await websocket.send(json.dumps({"type": "error", "message": "Bu kullanıcı adı zaten oyunda!"}))
                    break  # Bağlantıyı kapat
                reset_snake(client_id)
                clients[websocket] = client_id
            elif msg.get("type") == MSG_MOVE:
                enqueue_move(msg)
                client_id = msg.get("client_id")
                clients[websocket] = client_id
            elif msg.get("type") in [MSG_RESTART, 'disconnect', READY_MSG]:
                enqueue_control(msg)
                client_id = msg.get("client_id")
                clients[websocket] = client_id
            elif msg.get("type") == "easteregg":
                # Tüm oyuncuları elendir
                for cid in list(game_state["snakes"].keys()):
                    eliminate_snake(cid)
                print("Easter egg tetiklendi! Tüm oyuncular elendi.")
    except Exception as e:
        print("WebSocket bağlantı hatası:", e)
    finally:
        if client_id:
            enqueue_control({"type": 'disconnect', "client_id": client_id})
        if websocket in clients:
            del clients[websocket]

# --- Oyun döngüsü ve oyuncu yönetimi ---
move_queue = []
clients = {}  # sid: client_id
import threading

def game_loop():
    global game_timer, waiting_for_restart, winner_id, game_state
    last_state_msg = None
    powerup_spawn_chance = 0.01
    max_powerups = 4
    tick_count = 0
    waiting_for_restart = False
    winner_id = None
    game_started = False
    while True:
        # Time Attack modülünü güncelle
        time_attack_module.update_all_time_attack_games()
        clear_expired_time_attack_powerups()
        
        # Klasik mod güncellemeleri
        clear_expired_powerups()
        new_queue = []
        now = time.time()
        if not game_started and game_timer is None and len(game_state["snakes"]) > 0:
            print("[DEBUG] game_loop: Oyun başlatılıyor, reset_game çağrılıyor.")
            reset_game()
            game_started = True
        if game_timer is None:
            game_started = False
        if not waiting_for_restart and game_timer is not None and now - game_timer >= GAME_DURATION:
            max_score = -1
            winner_id = None
            for cid, score in game_state["scores"].items():
                if score > max_score:
                    max_score = score
                    winner_id = cid
            waiting_for_restart = True
            for cid in game_state["snakes"]:
                game_state["active"][cid] = False
        if waiting_for_restart and all_players_ready():
            reset_game()
        if not waiting_for_restart:
            for msg in move_queue:
                cid = msg["client_id"]
                direction = msg["direction"]
                if has_powerup(cid, "reverse"):
                    OPP = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}
                    direction = OPP.get(direction, direction)
                msg["direction"] = direction
                new_queue.append(msg)
            move_queue[:] = new_queue
            while move_queue:
                msg = move_queue.pop(0)
                client_id = msg["client_id"]
                direction = msg["direction"]
                current_dir = game_state["directions"].get(client_id)
                OPPOSITE_DIRECTIONS = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
                if current_dir and OPPOSITE_DIRECTIONS.get(current_dir) == direction:
                    continue
                if client_id in game_state["snakes"]:
                    game_state["directions"][client_id] = direction
                else:
                    reset_snake(client_id)
            if len(game_state["powerups"]) < max_powerups and random.random() < powerup_spawn_chance:
                pu = random_powerup(
                    game_state["snakes"],
                    game_state["food"],
                    game_state["obstacles"],
                    game_state["portals"],
                    game_state["powerups"]
                )
                same_type_count = sum(1 for p in game_state["powerups"] if p["type"] == pu["type"])
                if same_type_count < 2:
                    game_state["powerups"].append(pu)
            if game_state["golden_food"] is None and random.random() < 0.01:
                game_state["golden_food"] = random_food(
                    game_state["snakes"],
                    game_state["food"],
                    game_state["obstacles"],
                    game_state["portals"],
                    game_state["powerups"],
                    None
                )
            for client_id in list(game_state["snakes"].keys()):
                if has_powerup(client_id, "frozen"):
                    continue
                if has_powerup(client_id, "speed"):
                    move_snake(client_id)
                else:
                    if tick_count % 2 == 0:
                        move_snake(client_id)
        
        # Time Attack yılanlarını hareket ettir
        for client_id in list(time_attack_module.time_attack_games.keys()):
            ta_game_state = time_attack_module.time_attack_games[client_id]
            if ta_game_state["game_active"]:
                # Yılan hız kontrolü - klasik moddaki gibi
                if has_powerup_time_attack(client_id, "speed", ta_game_state):
                    # Speed power-up varsa her tick'te hareket et
                    pass
                else:
                    # Speed power-up yoksa her 2 tick'te bir hareket et
                    if tick_count % 2 != 0:
                        continue
                # Yılan hareketi
                head = ta_game_state["snake"][0]
                direction = ta_game_state["direction"]
                
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
                    continue
                
                # Çarpışma kontrolü (zırh etkisi ve duvardan geçiş)
                shielded = has_powerup_time_attack(client_id, "shield", ta_game_state)
                out_of_bounds = not (0 <= new_head[0] < BOARD_WIDTH and 0 <= new_head[1] < BOARD_HEIGHT)
                if out_of_bounds:
                    if shielded:
                        # Zırh varsa duvardan geç
                        if client_id in ta_game_state["active_powerups"]:
                            ta_game_state["active_powerups"][client_id] = [p for p in ta_game_state["active_powerups"][client_id] if p["type"] != "shield"]
                        nx, ny = new_head
                        if nx < 0:
                            nx = BOARD_WIDTH - 1
                        elif nx >= BOARD_WIDTH:
                            nx = 0
                        if ny < 0:
                            ny = BOARD_HEIGHT - 1
                        elif ny >= BOARD_HEIGHT:
                            ny = 0
                        new_head = (nx, ny)
                    else:
                        # Zırh yoksa elen
                        ta_game_state["game_active"] = False
                        continue
                
                # Kendine çarpma kontrolü - yılanın kuyruğu hariç kontrol et
                if new_head in ta_game_state["snake"][:-1]:  # Son eleman (kuyruk) hariç kontrol et
                    if shielded:
                        # Zırh varsa zırhı kullan ve devam et
                        if client_id in ta_game_state["active_powerups"]:
                            ta_game_state["active_powerups"][client_id] = [p for p in ta_game_state["active_powerups"][client_id] if p["type"] != "shield"]
                    else:
                        # Zırh yoksa elen
                        ta_game_state["game_active"] = False
                        continue
                
                # Engel kontrolü
                shielded = has_powerup_time_attack(client_id, "shield", ta_game_state)
                if not shielded:
                    for obs in ta_game_state["obstacles"]:
                        if new_head == tuple(obs["pos"]):
                            if obs["type"] == "hidden_wall":
                                # Gizli duvar - elen
                                ta_game_state["game_active"] = False
                                continue
                            elif obs["type"] == "grass":
                                # Normal çalı - elen
                                ta_game_state["game_active"] = False
                                continue
                
                # Portal kontrolü
                if ta_game_state.get("portals"):
                    for portal in ta_game_state["portals"]:
                        if new_head == portal[0]:
                            # Portal A'dan B'ye ışınla
                            new_head = portal[1]
                            break
                        elif new_head == portal[1]:
                            # Portal B'den A'ya ışınla
                            new_head = portal[0]
                            break
                
                # Yem kontrolü
                food_eaten = False
                for i, food_pos in enumerate(ta_game_state["food"]):
                    if new_head == food_pos:
                        ta_game_state["score"] += 10
                        ta_game_state["time_left"] += time_attack_module.TIME_ATTACK_CONSTANTS["FOOD_BONUS_TIME"]
                        ta_game_state["food"].pop(i)
                        food_eaten = True
                        break
                
                # Altın elma kontrolü
                if ta_game_state["golden_food"] and new_head == ta_game_state["golden_food"]:
                    ta_game_state["score"] += 50
                    ta_game_state["time_left"] += time_attack_module.TIME_ATTACK_CONSTANTS["GOLDEN_FOOD_BONUS_TIME"]
                    ta_game_state["golden_food"] = None
                
                # Magnet power-up etkisi
                if has_powerup_time_attack(client_id, "magnet", ta_game_state) and len(ta_game_state["snake"]) > 0:
                    head = ta_game_state["snake"][0]
                    # En yakın yemi bul ve çek
                    closest_food = None
                    min_dist = float('inf')
                    for food_pos in ta_game_state["food"]:
                        dist = abs(head[0] - food_pos[0]) + abs(head[1] - food_pos[1])
                        if dist < min_dist:
                            min_dist = dist
                            closest_food = food_pos
                    
                    # En yakın yemi yılanın başına doğru hareket ettir
                    if closest_food and min_dist > 1:
                        dx = 0
                        dy = 0
                        if closest_food[0] > head[0]:
                            dx = -1
                        elif closest_food[0] < head[0]:
                            dx = 1
                        if closest_food[1] > head[1]:
                            dy = -1
                        elif closest_food[1] < head[1]:
                            dy = 1
                        
                        new_food_pos = (closest_food[0] + dx, closest_food[1] + dy)
                        # Yeni pozisyonun boş olduğunu kontrol et
                        occupied = set()
                        occupied.update(ta_game_state["snake"])
                        occupied.update(ta_game_state["food"])
                        for obs in ta_game_state["obstacles"]:
                            occupied.add(tuple(obs["pos"]))
                        for pu in ta_game_state["powerups"]:
                            occupied.add(tuple(pu["pos"]))
                        
                        if new_food_pos not in occupied and 0 <= new_food_pos[0] < BOARD_WIDTH and 0 <= new_food_pos[1] < BOARD_HEIGHT:
                            # Yemi yeni pozisyona taşı
                            food_index = ta_game_state["food"].index(closest_food)
                            ta_game_state["food"][food_index] = new_food_pos
                
                # Power-up kontrolü
                for i, powerup in enumerate(ta_game_state["powerups"]):
                    if new_head == tuple(powerup["pos"]):
                        # Power-up aktivasyonu
                        if client_id not in ta_game_state["active_powerups"]:
                            ta_game_state["active_powerups"][client_id] = []
                        ta_game_state["active_powerups"][client_id].append({"type": powerup["type"], "tick": time.time()})
                        ta_game_state["powerups"].pop(i)
                        ta_game_state["time_left"] += time_attack_module.TIME_ATTACK_CONSTANTS["POWERUP_BONUS_TIME"]
                        break
                
                # Yılanı güncelle
                ta_game_state["snake"].insert(0, new_head)
                if not food_eaten:
                    ta_game_state["snake"].pop()
                
                # Yılan uzunluğu kontrolü
                if len(ta_game_state["snake"]) > time_attack_module.TIME_ATTACK_CONSTANTS["MAX_SNAKE_LENGTH"]:
                    ta_game_state["snake"] = ta_game_state["snake"][:time_attack_module.TIME_ATTACK_CONSTANTS["MAX_SNAKE_LENGTH"]]
                
                # Yeni yem ekle
                if food_eaten and len(ta_game_state["food"]) < time_attack_module.TIME_ATTACK_CONFIG["food_count"]:
                    # Rastgele yem pozisyonu
                    occupied = set()
                    occupied.update(ta_game_state["snake"])
                    occupied.update(ta_game_state["food"])
                    for obs in ta_game_state["obstacles"]:
                        occupied.add(tuple(obs["pos"]))
                    for pu in ta_game_state["powerups"]:
                        occupied.add(tuple(pu["pos"]))
                    
                    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT) if (x, y) not in occupied]
                    if empty:
                        new_food = random.choice(empty)
                        ta_game_state["food"].append(new_food)
                
                # Altın elma olasılığı
                if random.random() < time_attack_module.TIME_ATTACK_CONFIG["golden_food_chance"] and not ta_game_state["golden_food"]:
                    occupied = set()
                    occupied.update(ta_game_state["snake"])
                    occupied.update(ta_game_state["food"])
                    for obs in ta_game_state["obstacles"]:
                        occupied.add(tuple(obs["pos"]))
                    for pu in ta_game_state["powerups"]:
                        occupied.add(tuple(pu["pos"]))
                    
                    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT) if (x, y) not in occupied]
                    if empty:
                        ta_game_state["golden_food"] = random.choice(empty)
                
                # Power-up olasılığı
                if (len(ta_game_state["powerups"]) < time_attack_module.TIME_ATTACK_CONFIG["max_powerups"] and 
                    random.random() < time_attack_module.TIME_ATTACK_CONSTANTS["POWERUP_SPAWN_CHANCE"]):  # %5 olasılık
                    powerup_type = random.choice(time_attack_module.TIME_ATTACK_CONFIG["allowed_powerups"])
                    occupied = set()
                    occupied.update(ta_game_state["snake"])
                    occupied.update(ta_game_state["food"])
                    for obs in ta_game_state["obstacles"]:
                        occupied.add(tuple(obs["pos"]))
                    for pu in ta_game_state["powerups"]:
                        occupied.add(tuple(pu["pos"]))
                    
                    empty = [(x, y) for x in range(BOARD_WIDTH) for y in range(BOARD_HEIGHT) if (x, y) not in occupied]
                    if empty:
                        powerup_pos = random.choice(empty)
                        ta_game_state["powerups"].append({"pos": powerup_pos, "type": powerup_type})
                        print(f"[DEBUG] Time Attack power-up oluşturuldu: {powerup_type} pozisyon: {powerup_pos}")
                    else:
                        print(f"[DEBUG] Time Attack power-up için boş alan bulunamadı")
                else:
                    if len(ta_game_state["powerups"]) >= time_attack_module.TIME_ATTACK_CONFIG["max_powerups"]:
                        print(f"[DEBUG] Time Attack maksimum power-up sayısına ulaşıldı: {len(ta_game_state['powerups'])}")
                    elif random.random() >= time_attack_module.TIME_ATTACK_CONSTANTS["POWERUP_SPAWN_CHANCE"]:
                        print(f"[DEBUG] Time Attack power-up olasılığı düşük: {random.random():.3f} >= {time_attack_module.TIME_ATTACK_CONSTANTS['POWERUP_SPAWN_CHANCE']}")
        
        # State'leri gönder
        for sid, client_id in list(clients.items()):
            # Klasik mod state'i
            state_copy = copy.deepcopy(game_state)
            # Geri sayım süresi her zaman set edilmeli
            if game_timer is not None and not waiting_for_restart:
                state_copy["time_left"] = max(0, int(GAME_DURATION - (now - game_timer)))
            else:
                state_copy["time_left"] = 0
            print(f"[DEBUG] game_loop: time_left={state_copy['time_left']} game_timer={game_timer}")
            state_copy["winner_id"] = winner_id
            state_copy["waiting_for_restart"] = waiting_for_restart
            state_copy["powerup_timers"] = {}
            for cid2 in state_copy["snakes"].keys():
                timers = {}
                for ptype in ["speed","shield","invisible","reverse"]:
                    tleft = get_powerup_timeleft(cid2, ptype)
                    if tleft > 0:
                        timers[ptype] = tleft
                if timers:
                    state_copy["powerup_timers"][cid2] = timers
            state_copy["golden_food"] = game_state["golden_food"]
            for cid2 in list(state_copy["snakes"].keys()):
                if has_powerup(cid2, "invisible") and cid2 != client_id:
                    state_copy["snakes"][cid2] = []
            socketio.emit('state', state_copy, room=sid)
            
            # Time Attack state'i
            if client_id in time_attack_module.time_attack_games:
                ta_state = copy.deepcopy(time_attack_module.time_attack_games[client_id])
                print(f"[DEBUG] Time Attack state gönderiliyor: {client_id}")
                print(f"[DEBUG] Power-up sayısı: {len(ta_state.get('powerups', []))}")
                if ta_state.get('powerups'):
                    for i, pu in enumerate(ta_state['powerups']):
                        print(f"[DEBUG] Power-up {i}: {pu['type']} pozisyon: {pu['pos']}")
                socketio.emit('time_attack_state', ta_state, room=sid)
        
        # CTF modunu güncelle
        capture_the_flag_module.update_ctf_game()
        
        # CTF oyuncularını hareket ettir
        for client_id in list(capture_the_flag_module.ctf_game_state.snakes.keys()):
            if (client_id in capture_the_flag_module.ctf_game_state.directions and 
                client_id in capture_the_flag_module.ctf_game_state.active and 
                capture_the_flag_module.ctf_game_state.active[client_id]):
                
                direction = capture_the_flag_module.ctf_game_state.directions[client_id]
                capture_the_flag_module.ctf_game_state.move_snake(client_id, direction)
                
                # Bayrak teslim kontrolü
                deliver_result = capture_the_flag_module.ctf_game_state.deliver_flag(client_id)
                if deliver_result and isinstance(deliver_result, dict):
                    if deliver_result.get("round_won"):
                        # Round kazanıldı
                        winning_team = deliver_result["winning_team"]
                        winning_player = deliver_result["winning_player"]
                        print(f"[DEBUG] {winning_team} takımı round'u kazandı! Oyuncu: {winning_player}")
                        socketio.emit('ctf_round_won', {
                            "winning_team": winning_team,
                            "winning_player": winning_player,
                            "message": f"{winning_team} takımı round'u kazandı!"
                        }, broadcast=True)
                    elif deliver_result.get("flag_delivered"):
                        # Normal bayrak teslimi
                        print(f"[DEBUG] {client_id} bayrak teslim etti!")
                        socketio.emit('ctf_flag_delivered', {"message": "Bayrak teslim edildi!"}, broadcast=True)
        
        # CTF durumunu tüm oyunculara gönder
        if len(capture_the_flag_module.ctf_game_state.snakes) > 0:
            ctf_state = capture_the_flag_module.get_ctf_game_state()
            socketio.emit('ctf_state', ctf_state)
            
            # Round countdown kontrolü
            if ctf_state.get('round_phase') == 'round_end':
                socketio.emit('ctf_round_countdown', {
                    "countdown": ctf_state.get('round_countdown', 0)
                }, broadcast=True)
            
            # Oyun bitti mi kontrol et
            if capture_the_flag_module.ctf_game_state.game_phase == "finished":
                winner = capture_the_flag_module.ctf_game_state.get_winner()
                socketio.emit('ctf_game_over', {
                    "winner": winner,
                    "team_scores": capture_the_flag_module.ctf_game_state.team_scores,
                    "individual_scores": capture_the_flag_module.ctf_game_state.individual_scores
                })
        
        tick_count += 1
        socketio.sleep(TICK_RATE)

# --- Flask ve SocketIO sunucu kurulumu ---
app = Flask(__name__, static_folder='.', static_url_path='')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    return send_from_directory('.', 'web_client.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('assets', path)

# --- Flask-SocketIO event handler'ları ---
@socketio.on('join')
def on_join(data):
    client_id = data.get('client_id')
    sid = request.sid
    if client_id in game_state["snakes"]:
        emit('error', {"message": "Bu kullanıcı adı zaten oyunda!"})
        disconnect()
        return
    reset_snake(client_id)
    clients[sid] = client_id

@socketio.on('move')
def on_move(data):
    client_id = data.get('client_id')
    direction = data.get('direction')
    move_queue.append({"client_id": client_id, "direction": direction})

@socketio.on('restart')
def on_restart(data):
    client_id = data.get('client_id')
    reset_snake(client_id)
    # Oyun durumunu hemen güncelle
    if client_id in game_state["active"]:
        game_state["active"][client_id] = True

@socketio.on('ready')
def on_ready(data):
    client_id = data.get('client_id')
    if "ready" not in game_state:
        game_state["ready"] = {}
    game_state["ready"][client_id] = True

@socketio.on('easteregg')
def on_easteregg(data):
    print('[DEBUG] Easter egg tetiklendi! Tüm oyuncular eleniyor.')
    for cid in list(game_state["snakes"].keys()):
        eliminate_snake(cid)

# --- Time Attack Event Handler'ları ---
@socketio.on('start_time_attack')
def on_start_time_attack(data):
    client_id = data.get('client_id')
    difficulty = data.get('difficulty')
    sid = request.sid  # sid'yi burada tanımla
    
    # Client ID kontrolü
    if not client_id or client_id == 'null' or client_id == '':
        emit('error', {"message": "Geçersiz kullanıcı adı!"})
        return
    
    if difficulty not in time_attack_module.TIME_ATTACK_CONFIG["difficulties"]:
        emit('error', {"message": "Geçersiz zorluk seviyesi!"})
        return
    
    # Time Attack oyunu oluştur
    time_attack_module.create_time_attack_game(client_id, difficulty, BOARD_WIDTH, BOARD_HEIGHT)
    clients[sid] = client_id  # clients dictionary'sine ekle
    print(f"[DEBUG] {client_id} Time Attack başlattı: {difficulty}")
    print(f"[DEBUG] Time Attack games: {list(time_attack_module.time_attack_games.keys())}")
    emit('time_attack_started', {"difficulty": difficulty, "time": time_attack_module.TIME_ATTACK_CONFIG["difficulties"][difficulty]["time"]})

@socketio.on('time_attack_move')
def on_time_attack_move(data):
    client_id = data.get('client_id')
    direction = data.get('direction')
    
    if client_id not in time_attack_module.time_attack_games:
        return
    
    game_state = time_attack_module.time_attack_games[client_id]
    
    # Ters kontrol power-up kontrolü
    if has_powerup_time_attack(client_id, "reverse", game_state):
        OPP = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}
        direction = OPP.get(direction, direction)
    
    # Yön kontrolü
    current_dir = game_state["direction"]
    OPPOSITE_DIRECTIONS = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
    if OPPOSITE_DIRECTIONS.get(current_dir) == direction:
        return
    
    game_state["direction"] = direction

@socketio.on('time_attack_respawn')
def on_time_attack_respawn(data):
    client_id = data.get('client_id')
    
    if client_id not in time_attack_module.time_attack_games:
        return
    
    game_state = time_attack_module.time_attack_games[client_id]
    
    # Canlanma - 3 blok uzunluğunda yılan
    center_x = BOARD_WIDTH//2
    center_y = BOARD_HEIGHT//2
    game_state["snake"] = [
        (center_x, center_y),
        (center_x-1, center_y),
        (center_x-2, center_y)
    ]
    game_state["direction"] = "RIGHT"
    game_state["respawn_count"] += 1
    game_state["game_active"] = True  # Oyunu tekrar aktif hale getir
    print(f"[DEBUG] {client_id} manuel canlanma! Canlanma sayısı: {game_state['respawn_count']}")

# --- Capture the Flag Event Handler'ları ---
@socketio.on('start_capture_the_flag')
def on_start_capture_the_flag(data):
    client_id = data.get('client_id')
    sid = request.sid
    
    # Client ID kontrolü
    if not client_id or client_id == 'null' or client_id == '':
        emit('error', {"message": "Geçersiz kullanıcı adı!"})
        return
    
    # CTF oyununu sıfırla
    capture_the_flag_module.reset_ctf_game()
    clients[sid] = client_id
    print(f"[DEBUG] {client_id} Capture the Flag başlattı")
    
    # Oyun başladığını bildir
    emit('capture_the_flag_started', {"game_time": 300})
    
    # Tüm bağlı oyunculara oyunun yeniden başladığını bildir
    emit('ctf_game_restarted', {"message": "Oyun yeniden başlatıldı"}, broadcast=True)

@socketio.on('ctf_join')
def on_ctf_join(data):
    client_id = data.get('client_id')
    nickname = data.get('nickname', client_id)
    selected_team = data.get('team')
    
    if not client_id:
        emit('error', {"message": "Geçersiz kullanıcı!"})
        return
    
    # Oyuncuyu takıma ata
    team = capture_the_flag_module.ctf_game_state.assign_team(client_id, selected_team)
    
    if team is None:
        emit('error', {"message": "Seçilen takım dolu!"})
        return
    
    # Yılan oluştur - takım bazlı spawn pozisyonları
    if team == capture_the_flag_module.RED_TEAM:
        # Kırmızı takım için rastgele spawn pozisyonu
        spawn_pos = random.choice(capture_the_flag_module.RED_SPAWN_POSITIONS)
        start_x, start_y = spawn_pos
        # Kırmızı takım sağa doğru başlar
        capture_the_flag_module.ctf_game_state.snakes[client_id] = [
            (start_x, start_y),
            (start_x-1, start_y),
            (start_x-2, start_y)
        ]
        capture_the_flag_module.ctf_game_state.directions[client_id] = "RIGHT"
    else:
        # Mavi takım için rastgele spawn pozisyonu
        spawn_pos = random.choice(capture_the_flag_module.BLUE_SPAWN_POSITIONS)
        start_x, start_y = spawn_pos
        # Mavi takım sola doğru başlar
        capture_the_flag_module.ctf_game_state.snakes[client_id] = [
            (start_x, start_y),
            (start_x+1, start_y),
            (start_x+2, start_y)
        ]
        capture_the_flag_module.ctf_game_state.directions[client_id] = "LEFT"
    
    capture_the_flag_module.ctf_game_state.colors[client_id] = get_snake_color(client_id)
    capture_the_flag_module.ctf_game_state.active[client_id] = True
    
    print(f"[DEBUG] {client_id} CTF'ye katıldı, takım: {team}")
    
    emit('ctf_joined', {
        "team": team,
        "position": [start_x, start_y],
        "game_state": capture_the_flag_module.get_ctf_game_state()
    })

@socketio.on('ctf_move')
def on_ctf_move(data):
    client_id = data.get('client_id')
    direction = data.get('direction')
    
    if not client_id or client_id not in capture_the_flag_module.ctf_game_state.snakes:
        return
    
    # Yön kontrolü
    current_dir = capture_the_flag_module.ctf_game_state.directions.get(client_id, "RIGHT")
    OPPOSITE_DIRECTIONS = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
    if OPPOSITE_DIRECTIONS.get(current_dir) == direction:
        return
    
    # Ters hareket power-up kontrolü
    if capture_the_flag_module.ctf_game_state.has_powerup(client_id, "reverse"):
        OPP = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}
        direction = OPP.get(direction, direction)
    
    capture_the_flag_module.ctf_game_state.directions[client_id] = direction

@socketio.on('ctf_ready')
def on_ctf_ready(data):
    client_id = data.get('client_id')
    
    if not client_id:
        return
    
    # Oyuncuyu hazır olarak işaretle
    capture_the_flag_module.ctf_game_state.set_player_ready(client_id)
    print(f"[DEBUG] {client_id} CTF'de hazır")
    
    # Tüm oyuncular hazır mı kontrol et
    if capture_the_flag_module.ctf_game_state.all_players_ready():
        print(f"[DEBUG] Tüm oyuncular hazır, sayım başlıyor")
        emit('ctf_countdown_started', {"countdown": 3}, broadcast=True)

@socketio.on('ctf_respawn')
def on_ctf_respawn(data):
    client_id = data.get('client_id')
    
    if not client_id:
        return
    
    # Oyuncuyu respawn et (5 saniye bekleme süresi kontrolü CTF modülünde yapılır)
    if client_id in capture_the_flag_module.ctf_game_state.respawn_timers:
        print(f"[DEBUG] {client_id} CTF'de manuel respawn istedi")
        
        # Respawn dene (5 saniye bekleme süresi kontrolü yapılır)
        if capture_the_flag_module.ctf_game_state.respawn_player(client_id):
            print(f"[DEBUG] {client_id} CTF'de respawn edildi")
            emit('ctf_respawned', {"client_id": client_id})
        else:
            print(f"[DEBUG] {client_id} CTF'de henüz respawn olamaz (5 saniye bekleme süresi)")
            # Kalan süreyi hesapla ve client'a bildir
            current_time = time.time()
            respawn_time = capture_the_flag_module.ctf_game_state.respawn_timers[client_id]
            remaining_time = respawn_time - current_time
            emit('ctf_respawn_failed', {"client_id": client_id, "remaining_time": remaining_time})
    else:
        print(f"[DEBUG] {client_id} CTF'de respawn timer'ı yok")

@socketio.on('ctf_restart')
def on_ctf_restart(data):
    client_id = data.get('client_id')
    
    if not client_id:
        return
    
    # CTF oyununu yeniden başlat
    capture_the_flag_module.reset_ctf_game()
    capture_the_flag_module.start_ctf_game()
    print(f"[DEBUG] {client_id} CTF'yi yeniden başlattı")
    
    # Tüm bağlı oyunculara oyunun yeniden başladığını bildir
    emit('ctf_game_restarted', {"message": "Oyun yeniden başlatıldı"}, broadcast=True)

@socketio.on('ctf_flag_delivered')
def on_ctf_flag_delivered(data):
    """Bayrak teslim edildiğinde çağrılır"""
    print(f"[DEBUG] Bayrak teslim edildi, oyun yeniden başlatılıyor")
    
    # Tüm oyuncuları yeniden spawn et
    for client_id in list(capture_the_flag_module.ctf_game_state.snakes.keys()):
        capture_the_flag_module.ctf_game_state.respawn_player(client_id)
    
    # Tüm bağlı oyunculara oyunun yeniden başladığını bildir
    emit('ctf_flag_delivered', {"message": "Bayrak teslim edildi! Oyun yeniden başlatılıyor"}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    client_id = clients.get(sid)
    if client_id:
        # Klasik mod temizliği
        game_state["snakes"].pop(client_id, None)
        game_state["directions"].pop(client_id, None)
        game_state["active"].pop(client_id, None)
        game_state["colors"].pop(client_id, None)
        game_state["scores"].pop(client_id, None)
        if "active_powerups" in game_state:
            game_state["active_powerups"].pop(client_id, None)
        
        # Time Attack temizliği
        time_attack_module.remove_time_attack_game(client_id)
        
        # CTF temizliği
        capture_the_flag_module.ctf_game_state.eliminate_player(client_id)
    
    clients.pop(sid, None)

# --- Oyun döngüsünü başlat ---
def start_game_loop():
    socketio.start_background_task(game_loop)

if __name__ == "__main__":
    start_game_loop()
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host="0.0.0.0", port=port) 