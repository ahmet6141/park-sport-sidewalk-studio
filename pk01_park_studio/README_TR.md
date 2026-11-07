# PK / 01 — PARK + SPORT STUDIO
## Blender 4.5 için parametrik park üretimi • SW01 1.0.1 köprüsü • UE5.8 hedefli aktarım

**Sürüm:** 1.1.0 • 25 Eylül 2026  
**Kurulum tipi:** Blender'a kurulan çok dosyalı Python add-on; Text Editor'e yapıştırılacak tek script değildir.  
**Önemli doğrulama sınırı:** Saf geometri çekirdeği, dokular, koordinat dönüşümleri ve örnek GLB dosyası bağımsız olarak kontrol edildi. Geliştirme ortamında Blender ve Unreal çalıştırılamadı. Kurulum, Blender API çağrıları, FBX exporter ve UE5.8 importer henüz bu uygulamaların içinde çalıştırılarak doğrulanmış değildir. İlk kullanım boş bir test sahnesinde yapılmalıdır.

---

## 1. Neler teslim edildi?

PK01, birbirine kaldırım ağıyla bağlanan spor sahaları ve peyzaj alanları oluşturmak için yazıldı. Üç tasarlanmış masterplan; tekil spor tesisi ekleme; kent mobilyaları; gölet ve iskele; kontrollü ağaç yerleşimi; SW01 soket bağlantısı; materyal kaynakları; benzersiz mesh kütüphanesi ve yerleşim manifesti içeren FBX dışa aktarma yolu bulunur.

Bu paket, Blender veya Unreal için piyasada denenmiş bir ticari ürün değildir. Eklenti kaynak kodu teslimidir. Ayrıca UE içinde spline sürükleyince parkı canlı yeniden üreten bir C++/Blueprint/PCG eklentisi değildir. Üretim Blender'da; UE tarafı editör içe aktarma ve yerleşim otomasyonudur.

**Kurulum ZIP'i:** `PK01_ParkSport_Studio_1_1_0.zip`  
**Ayrı örnek:** `PK01_Garden_Demo.glb` — gömülü dokularla gerçek geometri; Blender'dan export edildiği iddia edilmez.  
**Testler:** `Tests/validation_report.json`  
**Önizlemeler:** Gerçek kaynak mesh ve dokulardan alınan VTK/EGL renderları; Blender/Cycles/UE ekran görüntüleri değildir.

Kurulum ZIP'i üretici eklentiyi içerir. Örnek GLB, büyük önizlemeler ve dış test raporu ayrıca verilen dosyalardır.

## 2. Blender 4.5'te kurulum

1. Önce açık çalışmanı kaydet. İlk denemeyi yeni bir dosyada yap.
2. `Edit → Preferences → Add-ons` bölümünü aç. Sağ üst menüdeki **Install from Disk** komutunu kullan; menü dili farklıysa `.zip`/`.py` seçtiren yerel kurulum komutunu bul.
3. **ZIP'i açmadan** `PK01_ParkSport_Studio_1_1_0.zip` dosyasını seç. Listede **PK01 | Park + Sport Studio (SW01 Bridge)** eklentisini etkinleştir.
4. `Layout` görünümünde, imleç 3D alanının üzerindeyken `N` tuşuna bas. Sağ kenardaki **PK01** sekmesini aç.
5. `Yerleşim` bölümünde **Liva / Gölet Bahçesi**, **Draft / hızlı**, 40–60 ağaç gibi hafif bir başlangıç seç. Ağaç ayarları **Peyzaj** bölümündedir.
6. **Parkı Oluştur / Yeniden Üret** düğmesine bas. Materyalleri görmek için Material Preview veya Rendered görünümüne geç.

**Alt+P ile çalıştırma:** Bu paketin `__init__.py` dosyasını Text Editor'de çalıştırma. Eklenti, kurulum yolundan modül olarak yüklenir; önceki SW01 scriptindeki kısa `__file__` / `parents[1]` yol sorununa dayanmaz. Paket içindeki kaynak klasörlerini ayırma.

**Birimler:** Scene Properties → Units → **Unit Scale = 1.0**. Kod metre cinsinden geometri oluşturur; birimi gizlice değiştirmek yerine yanlış ölçek varsa durur. Blender'ın varsayılan `None` birim sistemi, Scale 1.0 ile sayısal metre düzeninde kullanılabilir. Eklentiyi Object Mode'da çalıştır.

**SW01 gerekli mi?** İlk parkı oluşturmak için orijinal SW01 scriptini ayrıca açmak gerekmez: yüklediğin 1.0.1 paketinin değişmemiş geometri çekirdeği ve gereken ortak dokuları PK01 içinde bulunur. Açık SW01 panelinden ayar kopyalamak için orijinal SW01 scripti bir kez çalıştırılmış olmalıdır.

## 3. Üç başlangıç masterplanı

| Plan | Alan | Ana içerik |
|---|---:|---|
| **Aster / Spor Kampüsü** | 270 × 224 m | 400 m nominal pist, futbol iç sahası, basketbol, tenis, futsal, voleybol, badminton, pickleball, masa tenisi, fitness, gölet ve peyzaj |
| **Mira / Mahalle Parkı** | 164 × 144 m | 200 m rekreasyon pisti, basketbol, tenis, voleybol, fitness, gölet ve gezinti yolları |
| **Liva / Gölet Bahçesi** | 142 × 112 m | Gölet/iskele, basketbol, tenis, kavisli bahçe gezinti yolu, ağaçlar ve oturma alanları |

Bunlar sabit ana bölge yerleşimleri olan parametreli tasarımlardır. Herhangi bir arazi poligonuna otomatik sığdırma, GIS parsel optimizasyonu, yol mühendisliği veya kent planlama çözücüsü değildir. Spor seçimleri, içinde bulunduğun planın ayrılan tesis alanları için çalışır. Örneğin Liva'da futbol kutusu gösterilmez; ayrı futbol tesisi eklenebilir.

Ana ölçekte sarı/grafit/beton taş detayları, ahşap ve metal kent mobilyaları, petrole yakın mavi-yeşil ve kiremit spor yüzeyleri ortak bir malzeme dili oluşturur. **Coastal, Woodland, Urban** paletleri spor zemini ve vurgu renklerini değiştirir. Ortak SW01 materyalleri ayrı bir temayla izinsiz değiştirilmez.

## 4. Spor alanları

Tekil tesis menüsünde **9 tür** vardır: basketbol, tenis, futbol, futsal, voleybol, badminton, pickleball, masa tenisi ve açık hava fitness. Spor tesisini 3D Cursor konumuna ekleyebilirsin. Dönüş açısı `Yerleşim → Yön / derece` değerini kullanır.

Sahalarda ayrı taban ve çizgi geometrisi; ilgili dallarda pota, kale, ağ ve kapı açıklıklı çevre teli bulunur. Tesisler, bir **Zone Empty** altında gruplanır. Tam sahayı taşımak için bu Empty'yi taşı/döndür; yalnızca zemini taşırsan çizgiler ve ekipmanlar geride kalır.

**Aktif parka bağla** açıksa yeni tesis, seçili parkın altına eklenir ve onun aktarımına dahil edilir. Kapalıysa bağımsız bir PK01 proje grubu olur. Sonradan eklediğin bir tesise kaldırım bağlantısı `SW01` bölümündeki port aracıyla oluşturulur.

**Ölçü sınırı:** Basketbol 28 × 15 m, çiftler tenis 23,77 × 10,97 m ve futbol 105 × 68 m gibi nominal oyun alanları kodda kullanılır. Bunlar her sporun bütün yarışma/aydınlatma/kaçış/güvenlik koşullarını sağlayan sertifikalı tesisler değildir. Futsal ceza alanı basitleştirilmiştir. Pistte nominal tur geometrisi ve şerit çizgileri vardır; kulvarlı çıkışların kademeleri, engel işaretleri ve yarışma homologasyonu yoktur. `400 m`, 0,30 m referans uzaklığındaki analitik güzergâhın hedef uzunluğunu ifade eder.

Mira'nın 200 m halkası en fazla dört şerit kullanır; Aster 2–8 şerit sağlar. Saha boylarını farklı spor ölçülerine sınırsız ölçeklemek yerine kendi parametreli tesis üreticisini düzenlemek gerekir. Özellikle sahayı non-uniform Scale ile uzatmak, daire ve çizgi oranlarını bozar.

## 5. SW01 ile birlikte kullanım

### Aynı geometri ve yüzey düzeni

`vendor/sw01_core.py`, yüklediğin SW01 paketindeki çekirdekle byte düzeyinde aynıdır. PK01 kaldırım yolları bu fonksiyonları gerçekten çağırır. Ortak kaynaklar:

```text
UV seti        : UV0_Tile
Vertex color   : SW01_Tint
Materyaller    : M_SW01_Mortar / Pavers / Curb / Border / Tactile / Metal
Koordinatlar   : metre, +Z yukarı, +X ileri, +Y sol
```

Blender'da bu SW01 materyalleri zaten varsa mevcut datablock'lar yeniden kullanılır. PK01, eski SW01 nesnelerini `sw01_generated` olarak işaretlemez veya temizlemez. Kendi nesneleri ayrı PK01 sahiplik etiketi taşır.

### Var olan kaldırıma bağlama

Önce iki uçtaki **genişlik ve yüzey yüksekliğini eşitle**. PK01 varsayılanı 3,2 m; SW01 varsayılanı 2,4 m olabilir. `Açık SW01 Panelinden Stili Al` düğmesi boyutları/deseni/taş renklerini kopyalar; bu işlem daha önce oluşturulmuş parka kendiliğinden uygulanmaz, yeniden üretim gerekir.

`SW01` sekmesinde:

- Başlangıç portu: orijinal kaldırımın `SOCKET_..._OUT` Empty'si.
- Bitiş portu: parkın `...ENTRY` veya uygun `...IN` Empty'si.
- `Kavis kolu`: 0 otomatik; farklı dönüş biçimleri için metre cinsinden değer.
- Yanlış yöne kıvrılıyorsa başlangıç/bitiş yönü tersleme kutularını kontrol et.
- **Portları SW01 Kaldırımla Birleştir** düğmesini çalıştır.

Bağlantı yeni bir SW01 geometrisi olarak eklenir; iki kaynak modül değiştirilmez. Portları daha sonra taşırsan köprü canlı güncellenmez: eski bağlantıyı kaldırıp yeniden oluştur. Hata veren çok dar/kendi üzerine dönen bir eğriyi zorlamak yerine port yönlerini, kavis kolunu veya tesis konumunu düzenle.

Uçlarda eşit genişlik/yükseklik, Scale 1 ve XY düzlemine paralel yön beklenir. İki port arasında .5–250 m mesafe sınırı vardır. Farklı taban kotları arasında doğrusal kot geçişi desteklenir; farklı genişlikler için otomatik sıkıştırma yapılmaz. Köprü üzerindeki tactile çizgiler tasarım amaçlıdır; erişilebilirlik sertifikası değildir.

### Unreal'da ortak materyaller

PK01 importer, varsayılan olarak `/Game/SW01/Materials/MI_SW01_*` materyallerini bulursa **yeniden kullanır ve değiştirmez**. SW01 başka klasöre alındıysa export edilen `PK01_Import.py` içindeki `SW01_CONTENT_ROOT` değerini değiştir. Mevcut materyal yoksa PK01 kendi klasöründe aynı kaynaklardan yeni materyal üretir.

### FLOW kavisli kaldırımlar (1.1.0)

`SW01` sekmesindeki **Kaldırım stili** iki seçenek sunar:

- **Flow / kavisli + yuvarlak kavşak** (varsayılan): Döşeme taşları yol eksenini takip eden sıralar halinde döşenir; kavislerde taşlar hafif yamuk (radyal) olur, kenar kesimleri iki yanda simetrik ve en az yarım taş genişliğindedir, modül uçlarında 12 cm'den kısa şerit kesim bırakılmaz. Bordürler profil süpürme (sweep) ile üretilir ve derzli taşlara bölünür; dar kavislerde taş boyu otomatik kısalır. Kavşaklar kare pad yerine **bordür dönüşlü (curb return)** yuvarlatılmış köşelerle, çıkmaz uçlar yarım daire ile biter. Kenar şeridi (border) kavşak dönüşü boyunca devam eder.
- **Classic / SW01 1.0.1**: Orijinal SW01 çekirdeği ve kare kavşak pad'leri. Bu mod 1.0.0 ile birebir aynı kaldırım geometrisini üretir (testlerle doğrulanır).

FLOW ayarları:

```text
Bordur profili            : BULLNOSE (dış üst kenar yuvarlatılmış), CHAMFER (45° pah), SQUARE
Kavsak donus yaricapi / m : 0..6, varsayılan 2.5; yakın kavşaklarda otomatik küçültülür
Yol kivrimi / m           : 0..4, düz bağlantı yollarına verilen yumuşak dalga genliği
```

Kıvrım, iki uçta sıfır sapma ve sıfır eğimle başlar/biter; böylece yol kavşak ağzına her zaman dik ve kesintisiz oturur. Genlik, merkez hattı dönüş yarıçapı yol genişliğinin en az üç katı kalacak şekilde otomatik sınırlandırılır. Aydınlatma direkleri eğri boyunca gerçek yol eksenine göre konumlanır. En az üç kollu kavşaklarda, bordür dönüşünün çim tarafına kavisli banklar yerleşir (başka rezervasyonlarla çakışan köşeler atlanır).

Soket bağlama köprüsü de FLOW modunda aynı üreticiyi kullanır. FLOW modülleri SW01 materyal slotlarını, `UV0_Tile`, `SW01_Tint`, port verisini ve konveks collision gövdelerini korur; FBX/UE aktarımı değişmez. Aynı kol düzenine sahip kavşaklar tek mesh olarak örneklenir (instance).

Sınırlar: Kavşak ağ yapısı ortogonaldir (hazır masterplanlar gibi). Kavşak pad'lerine ek port üretilmez; yeni bağlantıları yol uçlarındaki IN/OUT soketlerine yap. Rampa (kot farkı) FLOW'da desteklenir ancak çok uzun eğimli yollarda üretim süresi artar.

## 6. Peyzaj, gölet ve kent mobilyaları

Ağaç dağıtımı bir `seed` ile tekrarlanabilir. Yollar, sahalar, pist, gölet, iskele ve ayrılmış mobilya alanları dışlama bölgeleridir. Prosedürel ağaç tacının hesaplanan yarıçapı bu bölgelere göre kontrol edilir; minimum ağaç aralığı korunur. İstenen sayı alana sığmazsa kısıtları bozmak yerine daha az ağaç yerleştirip not düşer.

Paket üç biçim ailesinde dört ağaç prototipi, çalı/çiçek, saz ve kıyı kayası üretir. Aynı ağacın kopyaları Blender'da aynı mesh verisini paylaşır. **Bunlar fotoğraf taraması veya botanikal açıdan birebir tür rekonstrüksiyonu değildir.** Yakın çekimin önem kazandığı yerlerde `Harici ağaç mesh` alanından kendi lisanslı kaliteli ağacını seçip değiştirme düğmesini kullan.

Kaynak ağaç tek Mesh olmalı; gerekirse kendi ağacının parçalarını bir kopya üzerinde birleştir. Araç kaynak modelin dönüş/ölçeğini değerlendirir, alt-merkez pivotu hesaplar ve mevcut yerleşimleri korur. Bu değiştirme sonrası kendi ağacının UE materyallerini ayrıca ataman gerekir; rastgele karmaşık Blender shader'ı dönüştürülmez. Yeniden park üretimi bu elle değiştirmeyi sıfırlar. Rüzgâr animasyonu, otomatik bitki LOD'ları ve impostor atlası bu sürümde yoktur.

Gölet bir çukur arazi yüzeyi, ayrı su yüzeyi, kıyı kayaları/sazlar ve ahşap seyir iskelesinden oluşur. Su, UE'nin native WaterBody nesnesi değildir; simülasyon ve yüzme fiziği oluşturulmaz. Gerekirse UE'deki su materyalini `WATER_MATERIAL_PATH` ile mevcut bir materyale yönlendir.

Kent mobilyaları: yuvarlatılmış kesitli ahşap çıtalı ve döküm yan ayaklı banklar, kavisli banklar, pergola, piknik masası, çiçeklikler, çöp kutuları, bisiklet parkı ve aydınlatma direkleri. Direkler torna (lathe) profilli flanş ve konik gövde, kuğu boynu kol ve disk armatür ile emissive lens içerir; her armatüre otomatik UE ışık aktörü konulmaz. Gece çekimi için sahneye uygun gerçek ışıkları Unreal'da kur.

## 7. PBR dokular

**14 doku ailesi** paket içinde yerel dosya olarak bulunur: SW01'den aynen korunan beş ortak aile ve PK01 için üretilmiş dokuz aile. SW01'in Asphalt seti bu eklenti için gerekli olmadığından yeniden paketlenmez.

Yeni setler: EPDM, Grass, Timber, Bark, Mulch, Stone, Gravel, Leaf ve Water. Bunlar 1024 × 1024 orijinal prosedürel setlerdir. Her yeni sette BaseColor, ORM, NormalGL, NormalDX ve 16-bit Height vardır. Ortak SW01 dokuları orijinal çözünürlüklerinde korunmuştur.

```text
BaseColor : sRGB
ORM       : doğrusal / R=AO, G=Roughness, B=Metallic
NormalGL  : Blender için +Y normal
NormalDX  : Unreal için -Y normal
Height    : 16-bit kaynak; varsayılan shader'da displacement bağlı değildir
```

Hiçbiri satın alınmış veya indirilmiş fotogrametri paketinin yerine geçmez. Yakın plan gerçekçiliği için kendi taranmış beton/ahşap/çim yüzeylerini şu düzenle ekleyebilirsin:

```text
D:/PBR_Overrides/
  Timber/Timber_BaseColor.png
         Timber_ORM.png
         Timber_NormalGL.png
         Timber_NormalDX.png     # önerilir
```

`Aktarım → Harici PBR klasörü` bu üst klasörü gösterir. Aynı şema diğer etiketlerde de kullanılır. Eksik override dosyası için paket kaynağına dönülür. Tam eşleşmiş set kullanmak, örneğin yeni albedo ile eski yüzeyin normalinin istemeden karışmasını önler. Modellerde gerçek derzler olduğu için taş başına tekrar bütün derzli kaldırım dokusu yerleştirme.

## 8. Blender'dan Unreal'a

Önce `.blend` dosyanı kaydet veya mutlak bir export yolu seç. `//PK01_Export` göreli yolu, kaydedilmemiş dosyada bilinçli olarak reddedilir.

`PK01 → Aktarım → Aktif park` alanında doğru kökü seç. **UE Kütüphanesi + Yerleşimi Export Et** düğmesi her denemede ayrı tarih/saat/revizyon klasörü oluşturur; eski export klasörü üzerine yazmaz.

Üretilen çıktı:

```text
PK01_Proje_Tarih_Revizyon/
  Meshes/*.fbx
  Textures/...
  PK01_scene.json
  PK01_Import.py
  pk01_contracts.py
  START_HERE.txt
```

Mesh'ler her varlık için yerel pivotlarında ayrı FBX olarak dışa aktarılır. Instance yerleşimleri tam dünya matrisleri olarak JSON'dadır. SW01 bağlantı/soket bilgileri de taşınır. **Hazır FBX dosyaları kurulum ZIP'inde bulunmaz; Blender export düğmesi bunları üretir.**

Unreal test projesinde **Python Editor Script Plugin** ve **Editor Scripting Utilities** eklentilerini aç; editörü yeniden başlat. Boş bir level aç. **File → Execute Python Script** komutuyla yalnızca **export klasöründeki** `PK01_Import.py` dosyasını çalıştır. Add-on'un kaynak içindeki aynı adlı dosyası henüz JSON olmadığı için doğrudan çalıştırılmaz.

Importer önce iki asimetrik referans mesh'i alır. Birim, XY eksen yönleri ve pivotu ölçer; beklenen 200/300 cm değerleri tutmazsa parkı yerleştirmeden durur. Sonra PBR materyallerini kurar/ortak SW01 materyalini bulursa kullanır, FBX kütüphanesini alır ve instance matrislerini uygular.

Varsayılan içerik klasörü `/Game/PK01`'dir. Yeni büyük revizyonu test ederken örneğin `/Game/PK01_Test02` kullan. Aynı klasörde önceki kaynaktan farklı dosyayı sessizce ezmek yerine hata verir. Kasıtlı yeniden aktarım için `REIMPORT_OWN_ASSETS=True` gereklidir; script kendi sahiplik etiketi olmayan assetleri değiştirmez.

**Level otomatik kaydedilmez.** Ölçek, yön, materyal slotları, collision, su ve çizgi görünümünü incele; sonra kendin kaydet. `PK01_last_unreal_run.json` yalnızca script gerçekten başarıyla çalıştığında oluşur. Hazır pakette çalışmış gibi sahte bir UE çalışma raporu yoktur.

## 9. Performans ve collision

Blender'da tekrar eden ağaç/mobilya mesh verileri paylaşılır. Unreal importer ise ilk adımda kontrol edilebilir ayrı StaticMeshActor'lar yerleştirir. **Bu sürüm otomatik HISM/PCG/Foliage dönüşümü yapmaz.** Çok sayıda aynı model için sahneyi kontrol ettikten sonra UE'nin Merge Actors → Batch / ISM veya Foliage iş akışını kullan. Poligon sayısının tek başına FPS garantisi olmadığına dikkat et: materyal sayısı, gölgeler, transparan su ve görüntüleme ayarları da etkilidir.

Gölet suyu, küçük bitkiler ve aydınlatma geometrilerinde gereksiz collision kapatılır. Ağaçta yalnızca gövde için basit kutu; mobilyalarda ve tesislerde seçili gövde/zemin kutuları kullanılır. Kapı/kale boşluklarını tek büyük collision kutusuyla kapatma yaklaşımı kullanılmaz. Terrain ve pist, statik kullanım için complex-as-simple yolunu hedefler; bu mesh'ler fizik simüle eden hareketli nesneler için tasarlanmamıştır.

Varsayılan UV0 tekrarlanan malzeme düzenidir, benzersiz 0–1 boya atlası değildir. UE importer lightmap UV üretimini talep eder; gerçek sonucu Static Mesh Editor'de kontrol et. Nanite, LOD ve çim/orman rüzgârı otomatik uygulanmaz.

## 10. Güvenli yeniden üretim

Model yeni bir staging koleksiyonunda hazırlanır; kurulum tamamlanmadan eski parkı silmemeyi hedefler. Yalnızca aynı PK01 proje adına/sahibine ait nesneler yenilenir. Kullanıcının veya SW01'in diğer nesneleri genel sahne temizliğiyle silinmez.

Ancak **yeniden üretim o parkın üretilmiş nesneleri üzerindeki elle düzenlemeleri sıfırlar**. Düzenlenmiş parçayı saklamak için seçip **Seçilenleri Yeniden Üretimden Koru** komutunu kullan. Bu parçalar `PK01_Preserved` koleksiyonuna ayrılır ve otomatik aktif park export kapsamından çıkar. Ayrıca elle export etmen veya kendi sahne düzenine dahil etmen gerekir. Önemli sahnelerin yedeğini al; staging/Undo bir yedek sistemi değildir.

## 11. Sık karşılaşılan durumlar

**PK01 sekmesi görünmüyor:** Preferences'da eklenti gerçekten etkin mi? 3D Viewport üzerinde `N` açıldı mı? Console'da kayıt hatası var mı? ZIP'in içinde ilk klasör `pk01_park_studio`, onun içinde `__init__.py` olmalı.

**Attempted relative import / no parent package:** `__init__.py` Text Editor'de çalıştırılmıştır. ZIP'i eklenti olarak kur.

**Missing PBR map / texture missing:** Kurulum içindeki assets klasörünü ayırma. Kendi override yolunu geçici boşaltıp paket kaynaklarını dene.

**Unit Scale / Object Mode hatası:** Scale 1.0 ve Object Mode ile yeni bir test sahnesi aç.

**Port mismatch:** SW01 ve PK01 yol genişliği/yüksekliğini eşitle; eğriyi üretmeden doğru Empty'leri seç.

**UE API / Interchange hatası:** Tam traceback'i ve export klasöründeki manifesti sakla. Bu sürümün UE editör testi yapılmadığından bazı property/importer ayrımları uygulama içinde düzeltme gerektirebilir. Bir hata oluşursa tüm işlemin tamamlandığını varsayma; dosyalar teşhis için korunur.

**Yüksek kalite düğmesine rağmen render fotoğraf gibi değil:** Hero geometrinin yaprak yoğunluğunu artırır, aydınlatma ve gerçek tarama materyalleri yerine geçmez. Sinema yakın planı için kendi premium bitkilerin, taranmış malzemelerin, Lumen/Path Tracer ışık düzenin ve son rötuşların gerekir.

## 12. Lisans ve teknik sınırlar

Yeni kaynak kod MIT lisansı; üretilmiş orijinal model/dokular CC0 adamasıyla verilir. SW01 çekirdeğinin lisans bildirimi `vendor/SW01_LICENSE.txt` içinde aynen saklanmıştır. Harici ekleyeceğin modellerin ve dokuların lisansı ayrıca sana aittir. Program, gerçek park/saha imalat projesi veya erişilebilirlik/güvenlik onayı değildir.

Detaylı kaynak ve sınırlar: `docs/SOURCES_AND_LIMITS.md`. Teknik mimari: `docs/TECHNICAL_TR.md`.
