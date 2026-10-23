# PK01 — Teknik sözleşme ve modüler yapı

## Dizin mimarisi

```text
pk01_park_studio/
  __init__.py          Blender register/unregister giriş noktası
  ui.py                PK01 sidebar, özellik grupları ve operatörler
  geometry.py          Saf Python mesh/scene/port veri modeli
  planner.py           Üç yerleşim, SW01 yolları, dışlama ve ağaç dağıtımı
  sports.py            Tesis tabanı/çizgileri ve pist
  props.py             Ekipman, mobilya, ağaç ve peyzaj geometri üreticileri
  surfaces.py          Ortak materyal anahtarları ve üç palet
  materials.py         Blender PBR image shader kurulum yolu
  runtime.py           Staging koleksiyonu, sahiplik, instance mesh'leri
  bridge.py            PK01/SW01 soket bilgisi ve kavisli yol bağlantısı
  curves.py            Catmull-Rom, fillet, dalga (meander), uyarlamalı örnekleme
  modeling.py          Profil süpürme (sweep) ve torna (lathe), sert/yumuşak kenar grupları
  flow.py              FLOW kaldırım: eksen takipli döşeme, profilli bordür, yuvarlak kavşak
  contracts.py         Saf Python matris/eksen/ölçek doğrulaması
  exporter.py          FBX başına tek asset + yerleşim manifesti
  unreal/PK01_Import.py UE editörü için export klasörüne kopyalanan importer
  vendor/sw01_core.py  Yüklenen SW01 1.0.1 çekirdeği, değiştirilmedi
  assets/textures/     Beş ortak + dokuz yeni PBR ailesi
  docs/                Kullanım rehberi ve teknik belgeler
```

Runtime için kullanıcıya pip kurulumu yaptırılmaz. Saf geometri bölümü stdlib kullanır. Blender tarafı bpy/mathutils; Unreal tarafı kendi unreal modülünü kullanır. Geliştirme ortamındaki bağımsız görsel/test araçları NumPy, Pillow, SciPy, trimesh ve VTK kullanmıştır; bunlar eklentinin bağımlılıkları değildir.

## Geometri ve yerleşim sözleşmesi

Mesh verisi üçgenler, yüz başına UV koordinatları, materyal indisleri, vertex renkleri ve smooth bayraklarından oluşur. Obje/zone/root dönüşümleri ayrı tutulur. Ağaç/mobilya kopyaları aynı mesh datablock'ını kullanır. UV veya smooth değişimi mesh cache hash'ine dahildir; eski UV düzeninin yanlışlıkla cache'den alınması önlenir.

Üretim parametreleri önce saf Python'da kontrol edilir. Yeni park bir staging collection içinde oluşturulur; eski PK01 proje grubu ancak yeni geometri ve materyal işlemleri tamamlanınca yenilenir. Kaynak SW01 nesneleri aynı silme etiketiyle işaretlenmez. Blender'da bir işlem ortasında oluşabilecek GPU, disk, API veya bellek hatasının uygulama içinde bütün yan etkileri test edilmiş değildir; düzenli dosya yedeği gerekir.

Yol kavşakları bir ortak genişlikte açık kenarlı kare döşeme pad'leri ve bunların kenarlarında biten ortogonal yollarla oluşur. Bu, bir kavşak üzerinde üç üst üste kaldırım mesh'i bırakmaktan kaçınır. Bağımsız modüllerde desen fazı değişebilir; kaynak SW01 sınırlaması korunur. Çok yakın hero çekimde kavşak derzlerini elle düzenlemek gerekebilir.

Köprü, iki portun konumu/yönü arasında kübik Bezier örnekleri üretir ve bu örnekleri **gerçek SW01 mesh üreticisine** verir. Tek bir dikdörtgen kaldırım mesh'i tüm eğri boyunca bükülmez. Farklı genişlikler için sessiz non-uniform scale uygulanmaz.

## Unreal koordinat sözleşmesi

FBX dosyalarının yerel pivotu korunur. Objenin world matrix'i Blender'da metre cinsinden JSON'a kaydedilir. `SM_PK01_CalX` 2 m ve `SM_PK01_CalY` 3 m yönlü asimetrik kutular olarak dışa aktarılır. Unreal'daki sınırları, XY eksen işaretleri/dönüşümü ve 100× cm ölçeğini ölçmek için kullanılır; level'a yerleştirilmezler.

Ölçülen ortonormal dönüşüm B, kaynak affine dönüşüm A ve konum t için:

```text
A_UE = B · A · transpose(B)
t_UE = 100 · B · t
```

Dönüşüm quaternion + pozitif scale olarak ayrıştırılır. Negatif scale/mirror ve shear varsayımla düzeltilmek yerine reddedilir. Böylece yanlış eksen tahminiyle bütün parkı döndürme veya aynalama ihtimali azaltılır. Yine de gerçek FBX ithalatı runtime doğrulaması gerektirir.

Unreal actor'ları paylaşılmış StaticMesh assetlerine referans verir; bu ilk sürüm ISM/HISM component üretmez. Yerleşim editörde kolayca kontrol edildikten sonra kullanıcı tarafından batch/foliage optimizasyonu yapılır. Bağlantı geometrilerinde SW01_IN/OUT socket bilgisi yeniden oluşturulur.

## Materyal ve görüntü farkları

Blender: UV0_Tile, SW01_Tint, sRGB BaseColor, doğrusal ORM, OpenGL tangent normal; su/cam için Principled transmission.

Unreal: UV0, vertex color, sRGB BaseColor, maske sıkıştırmalı ORM, DirectX normal veya GL normal için yeşil kanal terslemesi. Native su/cam shader'ları eşdeğer çözücü değildir: geçici translucency materyali hazırlanır; mevcut UE materyaline override önerilir. Karmaşık kullanıcı materyalleri çevrilmez.

GLB örneği: Saf çekirdeğin bir planından üretildi. Kaynak Z-up, glTF Y-up kök dönüşümüyle verilir. Mesh'ler paylaşılır; doku dosyaları gömülür. Örnek dosyada dokular en fazla 1K kopyalardır; bu, kurulumdaki orijinal ortak SW01 2K kaynaklarını değiştirmez. Dokunun base/normal/ORM kanalları glTF'de taşınır. GLB, kurulum eklentisinin parametrik arayüzünü veya UE import manifestini içermez.

VTK önizlemeleri: Gerçek model/doku verisi üzerinden aydınlatılmış raster render. Kamera, ışık ve anti-alias farklıdır; Blender/UE'de birebir aynı piksel görünümü sözü yoktur. Önizleme suyu, Blender transmission'ının tam fiziksel eşdeğeri değildir.

## Ölçek ve sınırlar

Masterplan yol genişliği 2–5 m; kaldırım üst yüzeyi .08–.40 m; ağaç sayısı 0–550; merkez aralığı 3–15 m; ağaç ölçeği .5–1.6; gölet derinliği .6–4 m. Değer kombinasyonları geometri sınırlarını aşarsa hata oluşabilir. Planın alan sınırı keyfi L biçimli arsa veya eğimli arazi değildir; yalnızca gölet çanağı düşey deformasyon içerir.

DRAFT/BALANCED/HERO yalnızca belirli geometri detay seviyeleridir; final render kalitesinin otomatik üç seviyesi değildir. Material bake, displacement, ray-tracing ayarı, ağaç rüzgârı, LOD/Nanite ve yerleşim bazlı light bake ayrıca ele alınır.

## FLOW kaldırım sözleşmesi (1.1.0)

`flow.build_flow_module` SW01'in `build_module` fonksiyonuyla aynı girdileri (sw.Path, sw.Config) alır ve aynı metadata anahtarlarını (`config`, `path`, `in`, `out`, `collision`) döndürür; ek olarak `builder='PK01_FLOW'` ve `curb_profile` yazar. Vendored `sw01_core.py` değiştirilmez; FLOW yalnızca onun Path, prism, clip ve materyal sözleşmesini kullanır.

Taşlar yol ekseninde (s, lateral) uzayında yerleştirilir: lateral sıralar simetrik kesimli, boyuna kesimler koşu bağında yarım taş kaydırmalıdır. Her taş `path.strip` ile üretildiği için eğride kenarları eksene paraleldir. Bordür taşları kapalı, saat yönü tersine (CCW) bir kesit profilinin süpürülmesidir; yuvarlatılmış kenar yüzleri köşe paylaşarak yumuşak, keskin kenarlar köşe çoğaltılarak sert gölgelenir. Her katı parça su geçirmez ve pozitif hacimlidir (testler bunu tüm stil ve kavşak kombinasyonlarında denetler).

Örneklenmiş eğrilerde uç kesitler, tasarım teğetine dik olacak şekilde sabitlenir (`flow.make_path`). Böylece dalgalı bir yol ile kavşak ağzı arasında kıl payı kama boşluğu oluşmaz. Kavşak dış hattı CCW çokgendir; iç köşeler bordür dönüş yarıçapıyla, açıkta kalan dış köşeler yarım yol genişliğiyle yuvarlatılır, ağız kenarları keskin kalır. Döşeme alanı bordür + kenar şeridi kadar içeri ofsetlenir ve SW01 desen ızgarasıyla kırpılır. Collision: merkez kare, kol dikdörtgenleri ve her bordür dönüşü için iki konveks kama.
