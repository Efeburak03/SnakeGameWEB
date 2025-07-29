# 🐍 Snake Game Web

Çok oyunculu, gerçek zamanlı web tabanlı Snake oyunu. WebSocket teknolojisi kullanılarak geliştirilmiş ve Render hosting platformunda yayınlanmıştır.

## 🎮 Oyun Özellikleri

### Temel Özellikler
- **Çok Oyunculu**: Maksimum 8 oyuncu aynı anda oynayabilir
- **Gerçek Zamanlı**: WebSocket bağlantısı ile anlık oyun deneyimi
- **Modern UI**: Responsive tasarım ve modern görsel arayüz
- **Cross-Platform**: Tüm modern web tarayıcılarında çalışır

### Oyun Mekanikleri
- **Farklı Yılan Renkleri**: Her oyuncuya otomatik atanan benzersiz renkler
- **Power-up Sistemi**: 7 farklı power-up türü
  - 🚀 **Speed**: Hızlandırıcı (**Mavi** - (0, 0, 255))
  - 🛡️ **Shield**: Zırh koruması (**Siyah** - (0, 0, 0))
  - 👻 **Invisible**: Görünmezlik (**Gri** - (128, 128, 128))
  - 🔄 **Reverse**: Ters kontrol (**Beyaz** - (255, 255, 255))
  - ❄️ **Freeze**: Rakibi dondurma (**Açık Mavi** - (0, 200, 255))
  - 🐉 **Giant**: Dev yılan (**Turuncu** - (255, 128, 0))
  - 🧲 **Magnet**: Magnet çekimi (**Mor** - (180, 0, 255))
- **Engel Sistemi**: 4 farklı engel türü
  - 🧱 **Wall**: Normal duvar
  - 🌱 **Slow**: Yavaşlatıcı çimen
  - ☠️ **Poison**: Zehirli engel
  - 🕳️ **Hidden Wall**: Gizli duvar
- **Portal Sistemi**: Oyuncuları farklı konumlara ışınlayan portallar
- **Altın Elma**: Özel güçlü yiyecek
- **Puan Sistemi**: Oyuncu skorları takibi

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.7+
- websockets kütüphanesi

### Yerel Kurulum

1. **Projeyi klonlayın:**
```bash
git clone <repository-url>
cd Snake_GameWEB
```

2. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

3. **Sunucuyu başlatın:**
```bash
python server.py
```

4. **Web tarayıcısında açın:**
```
http://localhost:8000
```

### Render Hosting

Bu proje Render platformunda yayınlanmıştır. Canlı demo için:
- **Oyun URL**: https://snakegameweb.onrender.com

## 📁 Proje Yapısı

```
Snake_GameWEB/
├── server.py          # Ana WebSocket sunucu
├── common.py          # Ortak sabitler ve yardımcı fonksiyonlar
├── web_client.html    # Frontend HTML/JS dosyası
├── requirements.txt   # Python bağımlılıkları
├── assets/           # Oyun görselleri
│   ├── Background.jpg
│   ├── elma.png
│   ├── golden_apple.png
│   ├── çimen.png
│   ├── kutu.png
│   ├── portal.png
│   ├── Eagle_500kg.png
│   └── yarasa.png
└── README.md
```

## 🎯 Oyun Kontrolleri

- **WASD** veya **Ok Tuşları**: Yılanı yönlendirme
- **Space**: Oyunu yeniden başlatma (oyun sonunda)
- **Enter**: Hazır durumuna geçme

## 🔧 Teknik Detaylar

### Backend (Python)
- **WebSocket Sunucu**: `websockets` kütüphanesi
- **Oyun Döngüsü**: 20 FPS (0.05 saniye tick rate)
- **Oyun Alanı**: 60x35 hücre
- **Maksimum Oyuncu**: 8

### Frontend (HTML5/JavaScript)
- **Canvas API**: Oyun grafikleri
- **WebSocket Client**: Sunucu iletişimi
- **Responsive Design**: Modern CSS
- **Asset Loading**: Dinamik görsel yükleme

### Oyun Durumu Yönetimi
```python
game_state = {
    "snakes": {},           # Oyuncu yılanları
    "directions": {},       # Yön bilgileri
    "food": [],            # Normal yiyecekler
    "golden_food": None,   # Altın elma
    "obstacles": [],       # Engeller
    "portals": [],         # Portallar
    "powerups": [],        # Power-up'lar
    "scores": {},          # Oyuncu skorları
    "active_powerups": {}  # Aktif power-up'lar
}
```

## 🌐 Hosting (Render)

### Render Konfigürasyonu
- **Platform**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python server.py`
- **Port**: 8000 (otomatik)

### Environment Variables
Render'da aşağıdaki environment variable'ları ayarlayın:
- `PORT`: Render tarafından otomatik atanır
- `HOST`: `0.0.0.0` (tüm IP'lerden erişim)

## 🎨 Görsel Varlıklar

Proje aşağıdaki görsel varlıkları içerir:
- **Background.jpg**: Ana menü arka planı
- **elma.png**: Normal yiyecek
- **golden_apple.png**: Altın elma
- **çimen.png**: Yavaşlatıcı çimen
- **kutu.png**: Kutu engeli
- **portal.png**: Portal görseli
- **Eagle_500kg.png**: Kartal karakteri
- **yarasa.png**: Yarasa karakteri

## 🔄 Oyun Döngüsü

1. **Bağlantı**: Oyuncu WebSocket ile sunucuya bağlanır
2. **Hazırlık**: Oyuncu nickname girer ve hazır durumuna geçer
3. **Oyun Başlangıcı**: Tüm oyuncular hazır olduğunda oyun başlar
4. **Oyun Döngüsü**: 20 FPS ile sürekli güncelleme
5. **Çarpışma Kontrolü**: Yılanlar, engeller ve diğer oyuncularla çarpışma
6. **Power-up Etkileri**: Aktif power-up'ların etkileri uygulanır
7. **Oyun Sonu**: Son oyuncu kaldığında oyun biter

## 🛠️ Geliştirme

### Yeni Özellik Ekleme
1. `common.py`'de yeni sabitler tanımlayın
2. `server.py`'de oyun mantığını güncelleyin
3. `web_client.html`'de frontend'i güncelleyin
4. Gerekirse yeni asset'ler ekleyin

### Debug Modu
Geliştirme sırasında debug modunu aktif etmek için:
```python
# server.py'de
DEBUG = True
```

## 📝 Lisans

Bu proje açık kaynak kodludur. Geliştirme ve katkılarınız beklenmektedir.

## 🤝 Katkıda Bulunma

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## 📞 İletişim

Proje hakkında sorularınız için issue açabilir veya pull request gönderebilirsiniz.

---

**🎮 İyi Oyunlar!** 🐍 