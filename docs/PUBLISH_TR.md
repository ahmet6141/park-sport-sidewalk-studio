# GitHub'a ilk public yayın

## Şu anki durum

Bu paket hazırlanırken GitHub'da repo oluşturulmadı ve dosya gönderilmedi. Bağlı GitHub hesabı **ahmet6141** olarak doğrulandı; sohbet oturumundaki araçlar repo oluşturma/push işlemi sunmadı. Bu paketin amacı, işlemi kendi bilgisayarındaki GitHub CLI oturumunla yapmanı sağlamaktır.

**Varsayılan hedef:** `ahmet6141/park-sport-sidewalk-studio` — **PUBLIC**.

`Publish-GitHub.ps1` ilk yayın içindir; var olan repoları dönüştürmez veya silmez. Bu script hazırlama ortamında Windows PowerShell/GitHub oturumuyla uçtan uca çalıştırılmamıştır.

## Başlangıç

1. ZIP'in tamamını normal bir klasöre çıkar. **YAYINLA.cmd**, **Publish-GitHub.ps1**, **PUBLISH_MANIFEST.json** ve **pk01_park_studio** aynı üst klasörde bulunmalı.
2. Bilgisayarında Git ve GitHub CLI yoksa PowerShell'de kur:

```powershell
winget install --id Git.Git -e --source winget
winget install --id GitHub.cli -e --source winget
```

Kurulum izin istemi gösterebilir. Sonra terminali kapatıp yeniden aç. `winget` mevcut değilse Git ve GitHub CLI resmi kurulum paketlerini kullan.

3. **YAYINLA.cmd** dosyasını çift tıkla. Script GitHub oturumu yoksa `gh auth login --hostname github.com --git-protocol https --web` komutunu açar. Tarayıcıda **ahmet6141** hesabınla giriş yap. Şifreni veya erişim token'ını sohbetle paylaşma.
4. Hedef hesap, public görünürlük ve dosya sayısını kontrol et; scriptte **YAYINLA** yaz.

Alternatif olarak kaynak klasöründe terminalden:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Publish-GitHub.ps1
```

`ExecutionPolicy Bypass` yalnızca bu yeni PowerShell işlemi içindir; kalıcı ExecutionPolicy değişikliği yapılmaz. Kurumsal politika daha yüksek öncelikle engelliyorsa onu atlatmaya çalışma; sistem yöneticinin izin verdiği yöntemi kullan.

## Scriptin yaptıkları

Paket manifestindeki dosyaları SHA256 ile doğrular; farklılık varsa otomatik yayın yapmaz. GitHub hesabını kontrol eder. Kullanıcı onayından sonra yeni yerel `main` repo oluşturur, yalnızca manifestteki dosyaları commit eder ve şu mantıkla yeni remote açıp gönderir:

```powershell
gh repo create ahmet6141/park-sport-sidewalk-studio --public --source . --remote origin --push
```

İlk commit için yerel Git kimliği `ahmet6141` ve GitHub noreply adresidir; global Git ayarları değiştirilmez. Asıl komut ayrıca açıklama ekler. Sonunda public durumunu ve GitHub'daki `main` commit SHA'sını yerelle karşılaştırır. Ancak bu kontroller tamamlanınca başarı mesajı verir.

Manifest dışında sonradan eklediğin dosyalar yüklenmez. Kaynakları kasıtlı değiştirdiysen manifest doğrulaması durur; bilinçli geliştirmeler için normal Git akışını kullan. Üçüncü taraf varlıkları lisans kontrolü olmadan yükleme.

## Büyük dosyalar

Orijinal 107,6 MB eklenti ZIP'i yaklaşık 102,65 MiB'dir ve normal Git'in 100 MiB tek dosya sınırını aşar. Bu nedenle ZIP'in kendisini commit etmek yerine **açılmış kaynak dosyaları ve PNG'ler** paketlendi. Bu repodaki her kaynak dosyası sınırın altındadır; `dist` ve üretilen ZIP'ler `.gitignore` içindedir. Kurulum ZIP'ini `python tools/build_addon.py` ile tekrar üretebilirsin. Daha sonra dağıtım için GitHub Releases'e ekleyebilirsin; bu ilk yayın scripti otomatik release oluşturmaz.

## Kısmi başarısızlık

Repo oluşturulmuş ama push başarısız olmuş olabilir; script bunu başarı diye raporlamaz. Tekrar çift tıklamak mevcut `.git` nedeniyle durur; yanlışlıkla başka bir Git deposuna işlem yapmasını önler.

Önce bu klasördeki **.pk01-publish-state.json**, `git remote -v` ve aşağıdaki sonuçlarla hedefi kontrol et:

```powershell
gh repo view ahmet6141/park-sport-sidewalk-studio --json nameWithOwner,isPrivate,url
git status
git remote -v
```

Hesap/repo seninse, public durum doğruysa ve `origin` gerçekten bu hedefi gösteriyorsa, başarısız ilk push'u yeniden dene:

```powershell
git push --set-upstream origin main
```

GitHub'da repo hiç oluşmadıysa ve bu paketin doğru yerel deposunda olduğunu doğruladıysan yukarıdaki `gh repo create ... --public --source . --remote origin --push` komutunu yeniden çalıştır. Aynı isimli başka bir repo varsa otomatik silme, private repoyu public yapma veya force-push kullanma. Farklı bir ad seçerek temiz paket üzerinde ilk yayın scriptini o adla başlat:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Publish-GitHub.ps1 -RepoName park-sport-sidewalk-studio-dev
```

## Resmî kaynaklar

- Repo oluşturma ve --public/--source/--push: https://cli.github.com/manual/gh_repo_create
- Tarayıcıyla kimlik doğrulama: https://cli.github.com/manual/gh_auth_login
- Git dosya boyutu sınırları ve Releases: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- GitHub CLI kurulumu: https://cli.github.com/
- Git Windows kurulumu: https://git-scm.com/install/windows
