import asyncio
import websockets
import json
import random
import time
from common import MSG_MOVE, MSG_STATE, MSG_RESTART, create_state_message, MAX_PLAYERS, get_snake_color, OBSTACLE_TYPES, POWERUP_TYPES, INITIAL_FOOD_COUNT
import copy
import os
import threading
from flask import Flask, send_from_directory

BOARD_WIDTH = 60   # Enine daha geniş
BOARD_HEIGHT = 35 # 700/20 = 35 satır
START_LENGTH = 3
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
    for _ in range(11):  # Çimen (slow)
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
    for i in range(1, START_LENGTH):
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
POWERUP_DURATIONS = {"speed": 10, "shield": 10, "invisible": 10, "reverse": 5, "freeze": 5, "giant": 10, "trail": 10}

def has_powerup(cid, ptype):
    now = time.time()
    for p in game_state.get("active_powerups", {}).get(cid, []):
        if p["type"] == ptype and now - p["tick"] < POWERUP_DURATIONS.get(ptype, 10):
            return True
    return False

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
    while True:
        # Oyun hiç başlamadıysa ve en az bir oyuncu varsa, oyunu başlat
        if game_timer is None and len(game_state["snakes"]) > 0:
            reset_game()
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
        # --- Magnet power-up aktifse, elmalar sürekli çekilsin ---
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
                for ptype in ["speed","shield","invisible","reverse"]:
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
                for _ in range(START_LENGTH):
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
                    time.sleep(0.2)
                elif obs["type"] == "poison":
                    if len(snake) > 1:
                        snake.pop()
                    else:
                        eliminate_snake(client_id)
                        return
                elif obs["type"] in ("wall", "hidden_wall"):
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
    if new_head in snake:
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
clients = {}  # websocket: client_id

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

PORT = int(os.environ.get("PORT", 10000))

async def main():
    async with websockets.serve(ws_handler, "0.0.0.0", PORT):
        await game_loop()

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'web_client.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('assets', path)

def run_flask():
    app.run(host='0.0.0.0', port=8000)

if __name__ == "__main__":
    print("[*] WebSocket tabanlı Snake sunucusu başlatıldı ")
    print("ÇALIŞAN DOSYA:", __file__)
    # Flask'ı ayrı bir thread'de başlat
    threading.Thread(target=run_flask, daemon=True).start()
    # WebSocket sunucusunu başlat
    asyncio.run(main()) 