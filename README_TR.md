# Park • Sport • Sidewalk Studio

**PK01 Park + Sport Studio 1.0.0 + SW01 1.0.1 entegrasyonu**

![Üretilmiş sahneler](docs/previews/PK01_Design_Board.png)

Blender üzerinden park, spor tesisi, gölet, peyzaj, kent mobilyası ve uyumlu kaldırım bağlantıları oluşturmak için hazırlanmış kaynak kod projesidir.

**Durum:** Blender 4.5 ve UE5.8 hedeflenmiştir; bu uygulamalar içinde çalışma doğrulaması yapılmış değildir. Kaynak/paket testleri, uygulama uyumluluğu testi yerine geçmez. Mevcut geometri kodu bu repo hazırlığında değiştirilmedi.

## Kurulum

Bu kaynak repo ZIP'ini Blender'a doğrudan kurma. Klasörü çıkartıp içinde şu komutu çalıştır:

```powershell
python tools/build_addon.py
```

Python 3.10 veya üzeri gerekir. Üretilen **dist/PK01_ParkSport_Studio_1_0_0.zip** dosyasını Blender'ın **Install from Disk** komutuyla kur. Eklentiyi etkinleştir, **N → PK01** paneline geç. İlk denemeyi yeni bir sahnede **Liva, Draft, 40–60 ağaç, Unit Scale 1.0, Object Mode** ile yap.

**[Ayrıntılı eklenti kullanım rehberi](pk01_park_studio/README_TR.md)**

## SW01 ile ilişki

PK01 içindeki **vendor/sw01_core.py** gerçek SW01 çekirdeğidir. Ortak dokular, UV0_Tile, SW01_Tint ve M_SW01 materyal adları korunur. Tam bağımsız SW01 kitinin kopyası bu repoda yoktur; PK01'in gerektirdiği çekirdek ve kaynaklar vardır. Açık SW01 panelinden stil almak ve var olan kaldırım soketlerine bağlantı üretmek eklenti rehberinde anlatılır.

## Test ve yayın

```powershell
python -m unittest discover -s tests -v
```

Bu komut mevcut repo için yeniden çalıştırılabilir küçük test kümesidir. Eski **127 kontrol** raporu aynı kapsamda tekrar çalıştırılmış gibi sunulmaz; orijinal rapor **pk01_park_studio/docs/validation_report.json** içinde saklanır.

**[GitHub'a ilk public yayınlama rehberi](docs/PUBLISH_TR.md)**

## Lisans

Önceki paketin MIT kaynak kod ve CC0 özgün varlık bildirimleri değiştirilmeden korunmuştur. Ayrıntılar **LICENSE.txt** ve **vendor/SW01_LICENSE.txt** içindedir. Harici satın alınmış modeller ve dokular bu lisanslardan otomatik yararlanmaz.
