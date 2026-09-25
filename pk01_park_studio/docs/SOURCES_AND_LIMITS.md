# PK01 — Kaynaklar, ölçüler ve doğrulama sınırları

Kontrol tarihi: 25 Eylül 2026. Aşağıdaki kaynaklar teknik tasarım için kullanıldı; bunlar PK01 kodunun Blender/Unreal içinde çalıştırılıp doğrulandığı anlamına gelmez.

## Birincil teknik kaynaklar

**Epic, FBX Static Mesh Pipeline (sayfa başlığı UE5.8):**
https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine

Paketin ayrı asset FBX dosyaları, kaynak pivotu, vertex color, UV ve UCX isim eşlemesi tasarımı bu akışı izler. Bir FBX içinde çoklu render mesh + custom collision sınırlaması nedeniyle bir asset bir dosya olarak dışa aktarılır. Blender shader grafiğinin otomatik olarak UE'ye eşdeğer taşınacağı varsayılmaz. Epic FBX 2020.2 pipeline sürümünü belirtir; Blender'ın kendi exporter'ıyla gerçek ithalat yine kullanıcı ortamında denenmelidir.

**Epic, Scripting the Unreal Editor Using Python:**
https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python

Python Editor Script Plugin ve Editor Scripting Utilities kurulumu; editör kapsamı; File → Execute Python Script; AssetTools/EditorAssetLibrary kullanımı. PK01 importer bir gameplay runtime scripti değildir. Unreal assetlerini dosya sisteminden elle düzenlemez; editör API'lerini kullanır. Level otomatik kaydedilmez.

**Epic, Instanced Static Mesh Component:**
https://dev.epicgames.com/documentation/en-us/unreal-engine/instanced-static-mesh-component-in-unreal-engine

Aynı geometriyi paylaşan ayrı aktörlerin hâlâ aktör maliyeti bulunduğu; ISM/Batch gruplamanın bu maliyeti azaltmaya yönelik olduğu dikkate alınmıştır. PK01 ilk ithalatta ayrı, kontrol edilebilir aktörler oluşturur. Otomatik ISM/HISM/Foliage aktörü üretimi bu sürümün özelliği değildir.

**Epic, Water System:**
https://dev.epicgames.com/documentation/en-us/unreal-engine/water-system-in-unreal-engine

Native WaterBody ve su sistemi, düz bir su materyali atanmış mesh'ten farklıdır. PK01'de gölet çanağı, kıyı ve ayrı su yüzeyi vardır; native su aktörü, yüzme, dalga simülasyonu ve otomatik Landscape edit layer kurulumu yoktur.

**Epic, MaterialEditingLibrary:**
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary

Materyal ifade düğümleri ve bağlantıları bu API üzerinden hazırlanır. Bazı ayrıntılı sınıf sayfaları bu ortamdan erişilemedi; runtime property erişimleri kontrollü hata vermek üzere yazılmıştır. UE5.8'in gerçek kurulumunda API/Interchange farklılıkları olabilir.

## Spor geometri referansı ve kullanım sınırı

**FIBA resmî kural portalı:**
https://about.fiba.basketball/en/our-sport/official-basketball-rules

**ITF 2026 Rules of Tennis:**
https://www.itftennis.com/media/7221/2026-rules-of-tennis-english.pdf

ITF metnindeki 23,77 m uzunluk, çiftler için 10,97 m genişlik ve servis/ağ ölçüleri tenis modelinin nominal görsel düzeni için referanstır. Çizgi merkezine yerleştirilmiş geometri ile yarışma ölçümünde kullanılan çizgi dış kenarı aynı şey değildir. Model ve saha kaçış alanı bütünü için yarışma uygunluğu iddia edilmez.

Diğer spor ölçüleri rekreasyon sahnesi konfigürasyonlarıdır. Bütün federasyonların 2026 şartları ve yerel imalat mevzuatı karşılaştırılmadı. Özellikle futbol, futsal, basketbol, voleybol ve raket sporlarında işaretlerin, kaçış mesafelerinin, ağ/armatür/çit yerleşiminin profesyonel maç sertifikasyonu yoktur. 400/200 m pist analitik tur değerleridir; kademeli yarış başlangıçları ve engel çizgileri çizilmez.

## Teslim edilen ile teslim edilmeyen

**Var:** Kurulabilir Blender eklenti kaynak paketi; 3 masterplan; 9 tekil spor türü; 400/200 m rekreasyon pisti; mobilya/bitki üreticileri; seed/exclusion; gerçek SW01 çekirdek çağrıları; port köprüsü; yerel PBR setleri; FBX+manifest export kaynak kodu; Unreal importer kaynak kodu; bağımsız geometri/tekstür/dönüşüm kontrolleri; gerçek modelden önizleme ve GLB.

**Yok:** Blender veya UE uygulama içinde doğrulanmış çalışma sertifikası; üretilmiş .blend/.uasset/.umap/.uplugin dosyaları; çalıştırılmış FBX ithalatı; canlı UE spline/PCG sistemi; fotogrametri bitki/texture kütüphanesi; otomatik HISM, Nanite veya LOD; su/bitki/fizik animasyonları; genel arazi/parsel çözücüsü; gerçek mühendislik projesi; erişilebilirlik/güvenlik standardı onayı.

## Veri kökeni

SW01 çekirdeği ve ortak dokular kullanıcının bu konuşmada yüklediği SW01_Sidewalk_Studio_1_0_1.zip içinden alındı. Çekirdeğin ve 20 ortak PNG dosyasının byte kimliği test raporunda kontrol edilir. Önceki paketin lisans bildirimi vendor/SW01_LICENSE.txt içinde korunur.

PK01'in yeni modelleri ve dokuları burada prosedürel olarak üretildi. Para verilmiş, taranmış veya bir üçüncü taraf siteden indirilmiş profesyonel kütüphane olduğu söylenmez. Yeni dokuların dosya/prosedür bilgisi assets/textures/texture_provenance.json içindedir.

Genel Blender eklenti kurulumu yolu için resmi manual sayfasına erişim bu ortamda başarısız oldu; bu yüzden Blender arayüz kurulum adımları uygulama ekranında teyit edilmiş olarak sunulmaz. Menü adı/dili değişirse Add-ons içindeki yerel .zip kurulum komutunu kullan.
