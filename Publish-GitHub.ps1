#requires -Version 5.1
<#
First publication only. Requires Git and GitHub CLI; never requests a pasted token.
No global Git settings, force-pushes, repository deletion or visibility changes.
Only the explicitly listed and SHA256-verified package files are staged.
Run from YAYINLA.cmd, or: powershell -NoProfile -ExecutionPolicy Bypass -File .\Publish-GitHub.ps1
#>
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9-]+$')]
    [string]$Owner = 'ahmet6141',
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$RepoName = 'park-sport-sidewalk-studio'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$FullName = "$Owner/$RepoName"
$Description = 'PK01 procedural parks, sports grounds and landscapes for Blender, with SW01 sidewalks and an Unreal Editor export bridge (UE5.8 target; runtime unverified).'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit $LASTEXITCODE). Publication is not confirmed."
    }
}

function Invoke-Captured {
    param([string]$Program, [string[]]$Arguments)
    $Lines = & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit $LASTEXITCODE). Publication is not confirmed."
    }
    return (($Lines | ForEach-Object { [string]$_ }) -join "`n").Trim()
}

Push-Location -LiteralPath $Root
try {
    foreach ($Program in @('git', 'gh')) {
        if (-not (Get-Command $Program -ErrorAction SilentlyContinue)) {
            Write-Host 'Eksik araci PowerShell uzerinden kur ve sonra terminali yeniden ac:'
            if ($Program -eq 'git') { Write-Host 'winget install --id Git.Git -e --source winget' }
            if ($Program -eq 'gh')  { Write-Host 'winget install --id GitHub.cli -e --source winget' }
            throw "Required command missing: $Program"
        }
    }
    if (Test-Path -LiteralPath (Join-Path $Root '.git')) {
        throw 'This first-publication helper will not reuse an existing .git directory. For recovery after a partial attempt, read docs/PUBLISH_TR.md. No files were uploaded by this run.'
    }

    $ManifestPath = Join-Path $Root 'PUBLISH_MANIFEST.json'
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        throw 'PUBLISH_MANIFEST.json missing. Extract the complete repository package.'
    }
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $FileList = New-Object 'System.Collections.Generic.List[string]'
    [long]$TotalBytes = 0
    $SafeRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    Write-Host 'Paket dosyalari ve SHA256 kayitlari kontrol ediliyor...'
    foreach ($Entry in $Manifest.files.PSObject.Properties) {
        $Relative = [string]$Entry.Name
        $Path = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
        if (-not $Path.StartsWith($SafeRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Unsafe manifest path: $Relative"
        }
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Missing package file: $Relative"
        }
        $Item = Get-Item -LiteralPath $Path
        if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Linked file is not allowed: $Relative"
        }
        if ($Item.Length -ge 100MB) { throw "File exceeds safe Git size: $Relative" }
        if ($Item.Length -ne [long]$Entry.Value.size) { throw "Package file size changed: $Relative" }
        $Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Hash -ne [string]$Entry.Value.sha256) { throw "Package bytes changed: $Relative" }
        $FileList.Add($Relative)
        $TotalBytes += $Item.Length
    }
    $FileList.Add('PUBLISH_MANIFEST.json')

    # An existing login is used; otherwise the user authenticates with GitHub's browser flow.
    $OldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & gh auth status --hostname github.com
        $Authenticated = ($LASTEXITCODE -eq 0)
    } finally { $ErrorActionPreference = $OldPreference }
    if (-not $Authenticated) {
        Invoke-Checked -Program 'gh' -Arguments @('auth','login','--hostname','github.com','--git-protocol','https','--web')
    }
    $Profile = (Invoke-Captured -Program 'gh' -Arguments @('api','--hostname','github.com','user')) | ConvertFrom-Json
    if ($Profile.login -ne $Owner) {
        throw "Wrong active account: $($Profile.login). Expected: $Owner. Switch using: gh auth switch --hostname github.com --user $Owner"
    }

    Write-Host ''
    Write-Host "Hedef: $FullName" -ForegroundColor Cyan
    Write-Host 'Gorunurluk: PUBLIC - kaynaklar ve dokular herkes tarafindan gorulebilir.'
    Write-Host ("Yayinlanacak dosya: {0}, boyut: {1:N1} MB" -f $FileList.Count, ($TotalBytes / 1000000))
    Write-Host 'Bu klasor disindaki dosyalar, fotograflar ve diger projeler eklenmez.'
    $Confirm = Read-Host 'Devam etmek icin YAYINLA yaz; iptal etmek icin Enter'
    if ($Confirm -cne 'YAYINLA') {
        Write-Host 'Iptal edildi. Repo olusturulmadi.'
        exit 0
    }

    Invoke-Checked -Program 'git' -Arguments @('init','-b','main','.')
    # Local-only identity: do not put the user's private email into the public first commit.
    $NoReply = "$($Profile.id)+$($Profile.login)@users.noreply.github.com"
    Invoke-Checked -Program 'git' -Arguments @('config','--local','user.name', $Profile.login)
    Invoke-Checked -Program 'git' -Arguments @('config','--local','user.email', $NoReply)
    Invoke-Checked -Program 'git' -Arguments @('config','--local','core.autocrlf','false')
    # A local Git credential section resets inherited helpers for github.com.
    # Write the empty helper explicitly: Windows PowerShell 5 can omit empty native arguments.
    $CredentialConfig = @'
[credential "https://github.com"]
    helper =
    helper = !gh auth git-credential
'@
    $UTF8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::AppendAllText((Join-Path $Root '.git/config'), "`n$CredentialConfig`n", $UTF8)
    for ($Index = 0; $Index -lt $FileList.Count; $Index += 30) {
        $Last = [Math]::Min($Index + 29, $FileList.Count - 1)
        $Batch = @('add','--') + @($FileList.ToArray()[$Index..$Last])
        Invoke-Checked -Program 'git' -Arguments $Batch
    }
    Invoke-Checked -Program 'git' -Arguments @('commit','-m','Initial source release: PK01 1.0.0 with SW01 1.0.1 bridge')
    $Commit = Invoke-Captured -Program 'git' -Arguments @('rev-parse','HEAD')
    # Record intent only: this is NOT evidence that the remote exists.
    @{ target=$FullName; local_commit=$Commit; publication_verified=$false } |
        ConvertTo-Json | Set-Content -LiteralPath '.pk01-publish-state.json' -Encoding UTF8

    # If the name already exists, gh fails. No existing repository is made public or overwritten.
    Invoke-Checked -Program 'gh' -Arguments @('repo','create', $FullName, '--public', '--description', $Description, '--disable-wiki', '--source','.', '--remote','origin', '--push')
    $Remote = (Invoke-Captured -Program 'gh' -Arguments @('repo','view', $FullName, '--json','nameWithOwner,isPrivate,url')) | ConvertFrom-Json
    if ($Remote.isPrivate -or $Remote.nameWithOwner -ne $FullName) {
        throw 'Remote identity/public visibility check failed; do not treat the publication as complete.'
    }
    $RemoteCommit = Invoke-Captured -Program 'gh' -Arguments @('api','--hostname','github.com', "repos/$FullName/git/ref/heads/main", '--jq','.object.sha')
    if ($RemoteCommit -ne $Commit) { throw 'Remote main commit does not match local HEAD.' }
    @{ target=$FullName; local_commit=$Commit; publication_verified=$true; url=$Remote.url } |
        ConvertTo-Json | Set-Content -LiteralPath '.pk01-publish-state.json' -Encoding UTF8
    Write-Host ''
    Write-Host 'PUBLIC REPO OLUSTURULDU VE MAIN COMMIT DOGRULANDI:' -ForegroundColor Green
    Write-Host $Remote.url
    Write-Host "Commit: $Commit"
    Write-Host 'Blender ve UE uygulama uyumlulugu bu yayin islemiyle test edilmis olmaz.'
} catch {
    Write-Host ''
    Write-Host ("HATA: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Basari dogrulanmadi. Remote create/push asamasina ulasildiysa repo kismen olusmus olabilir.'
    Write-Host 'Mevcut repo silinmedi; force-push yapilmadi. Kurtarma adimlari: docs/PUBLISH_TR.md'
    exit 1
} finally {
    Pop-Location
}
