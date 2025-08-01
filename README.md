# 🐍 Snake Game Web - Çok Oyunculu Web Tabanlı Snake Oyunu

Modern web teknolojileri ile geliştirilmiş, gerçek zamanlı çok oyunculu Snake oyunu. Flask-SocketIO ve HTML5 Canvas kullanılarak oluşturulmuş, hem klasik çok oyunculu mod hem de tek oyunculu Time Attack modu içerir.

## 🎮 Oyun Özellikleri

### 🏆 Ana Oyun Modu (Çok Oyunculu)
- **Maksimum 8 Oyuncu**: Aynı anda 8 oyuncuya kadar destek
- **Gerçek Zamanlı Oyun**: Socket.IO ile anlık iletişim
- **Dinamik Oyun Alanı**: 60x35 hücrelik geniş oyun alanı
- **Otomatik Renk Ataması**: Her oyuncuya benzersiz renk
- **Puan Sistemi**: Oyuncu skorlarının takibi

### ⚡ Power-up Sistemi
- **Hızlandırıcı** (Mavi): Yılanı hızlandırır
- **Zırh** (Siyah): Çarpışmalara karşı koruma
- **Görünmezlik** (Gri): Geçici görünmezlik
- **Ters Kontrol** (Beyaz): Kontrolleri tersine çevirir
- **Dondurma** (Açık Mavi): Rakipleri dondurur
- **Dev Yılan** (Turuncu): Yılanı büyütür
- **Magnet** (Mor): Yiyecekleri çeker
- **İz Bırakıcı** (Turkuaz): Geçici iz bırakır

### 🚧 Engel Sistemi
- **Duvar** (Gri): Geçilemez engel
- **Yavaşlatıcı Çimen** (Yeşil): Hızı azaltır
- **Zehir** (Kırmızı): Anında ölüm
- **Gizli Duvar** (Koyu Gri): Görünmez engel

### 🌟 Özel Özellikler
- **Portal Sistemi**: Oyuncuları farklı konumlara ışınlar
- **Altın Elma**: Özel güçlü yiyecek
- **Dinamik Yiyecek**: Sürekli yenilenen yiyecek sistemi

### ⏱️ Time Attack Modu (Tek Oyunculu)
- **3 Zorluk Seviyesi**: Kolay (2 dk), Orta (1.5 dk), Zor (1 dk)
- **Süre Yönetimi**: Yiyecek yeme ile süre uzatma
- **Yüksek Skor**: En yüksek skorları kaydetme
- **Sınırlı Power-up**: Sadece belirli power-up'lar kullanılabilir
- **Yeniden Doğma**: Ölüm sonrası yeniden başlama

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
- **Python**: 3.7 veya üzeri
- **Flask**: Web framework
- **Flask-SocketIO**: WebSocket desteği
- **eventlet**: Asenkron sunucu

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

### 🐳 Docker ile Kurulum (Opsiyonel)

```bash
# Dockerfile oluşturun
echo "FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ['python', 'server.py']" > Dockerfile

# Docker image oluşturun ve çalıştırın
docker build -t snake-game .
docker run -p 8000:8000 snake-game
```

## 📁 Proje Yapısı

```
Snake_GameWEB/
├── server.py              # Ana Flask-SocketIO sunucu (1133 satır)
├── time_attack_module.py  # Time Attack modu modülü (425 satır)
├── common.py              # Ortak sabitler ve yardımcı fonksiyonlar (102 satır)
├── web_client.html        # Frontend HTML/JS dosyası (1399 satır)
├── requirements.txt       # Python bağımlılıkları
├── assets/                # Oyun görselleri
│   ├── Background.jpg     # Ana menü arka planı
│   ├── elma.png          # Normal yiyecek
│   ├── golden_apple.png  # Altın elma
│   ├── çimen.png         # Yavaşlatıcı çimen
│   ├── kutu.png          # Kutu engeli
│   ├── portal.png        # Portal görseli
│   ├── Eagle_500kg.png   # Kartal karakteri
│   └── yarasa.png        # Yarasa karakteri
└── README.md
```

## 🎯 Oyun Kontrolleri

### Ana Oyun Modu
- **WASD** veya **Ok Tuşları**: Yılanı yönlendirme
- **Enter**: Hazır durumuna geçme / Yeniden başlatma
- **Easter Egg**: Özel komutlar (geliştirici tarafından)

### Time Attack Modu
- **WASD** veya **Ok Tuşları**: Yılanı yönlendirme
- **R**: Yeniden doğma (sınırlı sayıda)
- **Enter**: Oyunu yeniden başlatma

## 🔧 Teknik Detaylar

### Backend (Python/Flask)
- **WebSocket Sunucu**: Flask-SocketIO
- **Oyun Döngüsü**: 20 FPS (0.05 saniye tick rate)
- **Oyun Alanı**: 60x35 hücre
- **Maksimum Oyuncu**: 8
- **Asenkron İşlem**: eventlet ile

### Frontend (HTML5/JavaScript)
- **Canvas API**: Oyun grafikleri
- **Socket.IO Client**: Sunucu iletişimi
- **Responsive Design**: Modern CSS
- **Asset Loading**: Dinamik görsel yükleme
- **Real-time Updates**: Anlık oyun durumu güncellemeleri

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
    "active_powerups": {}, # Aktif power-up'lar
    "trails": {}           # İz bırakıcı power-up
}
```

## 🌐 Hosting ve Deployment

### Render Platformu
Bu proje Render platformunda yayınlanmıştır:
- **Canlı Demo**: https://snakegameweb.onrender.com
- **Platform**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python server.py`
- **Port**: 8000 (otomatik)

### Environment Variables
```bash
PORT=8000          # Render tarafından otomatik atanır
HOST=0.0.0.0      # Tüm IP'lerden erişim
```

### Diğer Platformlar
- **Heroku**: `Procfile` ile deployment
- **Railway**: Otomatik Python deployment
- **Vercel**: Serverless function olarak

## 🎨 Görsel Varlıklar

Proje aşağıdaki görsel varlıkları içerir:
- **Background.jpg**: Ana menü arka planı
- **elma.png**: Normal yiyecek
- **golden_apple.png**: Altın elma (özel güçlü yiyecek)
- **çimen.png**: Yavaşlatıcı çimen engeli
- **kutu.png**: Kutu engeli
- **portal.png**: Portal görseli
- **Eagle_500kg.png**: Kartal karakteri
- **yarasa.png**: Yarasa karakteri

## 🔄 Oyun Döngüsü

### Ana Oyun Modu
1. **Bağlantı**: Oyuncu Socket.IO ile sunucuya bağlanır
2. **Hazırlık**: Oyuncu nickname girer ve hazır durumuna geçer
3. **Oyun Başlangıcı**: Tüm oyuncular hazır olduğunda oyun başlar
4. **Oyun Döngüsü**: 20 FPS ile sürekli güncelleme
5. **Çarpışma Kontrolü**: Yılanlar, engeller ve diğer oyuncularla çarpışma
6. **Power-up Etkileri**: Aktif power-up'ların etkileri uygulanır
7. **Oyun Sonu**: Son oyuncu kaldığında oyun biter

### Time Attack Modu
1. **Mod Seçimi**: Oyuncu zorluk seviyesi seçer
2. **Oyun Başlangıcı**: Süre ile birlikte oyun başlar
3. **Süre Yönetimi**: Yiyecek yeme ile süre uzatma
4. **Yeniden Doğma**: Ölüm sonrası sınırlı yeniden doğma
5. **Skor Kaydetme**: En yüksek skorları kaydetme

## 🛠️ Geliştirme

### Yeni Özellik Ekleme
1. **common.py**: Yeni sabitler ve konfigürasyonlar
2. **server.py**: Ana oyun mantığı ve WebSocket olayları
3. **time_attack_module.py**: Time Attack modu özellikleri
4. **web_client.html**: Frontend arayüzü ve JavaScript
5. **assets/**: Yeni görsel varlıklar

### Debug Modu
Geliştirme sırasında debug modunu aktif etmek için:
```python
# server.py'de
DEBUG = True
```

### Kod Yapısı
- **Modüler Tasarım**: Her özellik ayrı modülde
- **Sabit Yönetimi**: Tüm sabitler `common.py`'de
- **WebSocket Events**: Socket.IO ile gerçek zamanlı iletişim
- **State Management**: Merkezi oyun durumu yönetimi

## 📊 Performans

### Optimizasyonlar
- **Canvas Rendering**: Verimli grafik işleme
- **WebSocket**: Düşük gecikme iletişimi
- **Asset Caching**: Görsel varlıkların önbelleklenmesi
- **Memory Management**: Oyun durumu temizleme

### Ölçeklenebilirlik
- **Çoklu Oyun**: Aynı anda birden fazla oyun
- **Oyuncu Limiti**: Maksimum 8 oyuncu kontrolü
- **Resource Management**: Bellek ve CPU optimizasyonu

## 🤝 Katkıda Bulunma

### Geliştirme Süreci
1. **Fork**: Projeyi fork edin
2. **Branch**: Feature branch oluşturun (`git checkout -b feature/YeniOzellik`)
3. **Commit**: Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. **Push**: Branch'inizi push edin (`git push origin feature/YeniOzellik`)
5. **Pull Request**: Pull Request oluşturun

### Katkı Alanları
- **Yeni Power-up'lar**: Orijinal power-up fikirleri
- **Görsel İyileştirmeler**: UI/UX geliştirmeleri
- **Yeni Oyun Modları**: Farklı oyun modları
- **Performans Optimizasyonu**: Kod iyileştirmeleri
- **Dokümantasyon**: README ve kod yorumları

## 📝 Lisans

Bu proje açık kaynak kodludur. Geliştirme ve katkılarınız beklenmektedir.

## 📞 İletişim ve Destek

- **Issues**: GitHub Issues üzerinden hata bildirimi
- **Pull Requests**: Özellik önerileri ve iyileştirmeler
- **Discussions**: GitHub Discussions ile tartışma

## 🎯 Gelecek Planları

- [ ] Mobil uygulama desteği
- [ ] Yeni oyun modları
- [ ] Daha fazla power-up türü
- [ ] Ses efektleri
- [ ] Çoklu dil desteği
- [ ] Turnuva modu
- [ ] Özelleştirilebilir oyun alanları

---

🎮 **İyi Oyunlar!** 🐍

*Bu proje modern web teknolojileri ile geliştirilmiş, eğlenceli ve rekabetçi bir Snake oyunudur. Hem klasik çok oyunculu deneyim hem de tek oyunculu Time Attack modu ile farklı oyun stilleri sunar.* 