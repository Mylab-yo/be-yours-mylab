<#
  download-ref.ps1 — Télécharge une vidéo Instagram (ou autre) et la prépare pour analyse.
  Usage :
    ./download-ref.ps1 "https://www.instagram.com/reel/XXXX/"
    ./download-ref.ps1 "URL1","URL2","URL3"        # plusieurs liens

  Produit, dans refs-video/ :
    - <uploader>_<id>.mp4          la vidéo
    - frames_<id>/f_###.jpg        1 image / seconde (analyse fine)
    - contact_<id>_##.jpg          planches contact 4x4 (vue d'ensemble)
#>
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string[]]$Urls,
  [string]$OutDir = "$PSScriptRoot\..\refs-video"
)

$ErrorActionPreference = 'Stop'

# yt-dlp installé via winget — chemin direct (le PATH n'est pas toujours rechargé)
$ytLink = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\yt-dlp.yt-dlp_Microsoft.Winget.Source_8wekyb3d8bbwe\yt-dlp.exe"
$yt = if (Get-Command yt-dlp -ErrorAction SilentlyContinue) { "yt-dlp" } else { $ytLink }

New-Item -ItemType Directory -Force $OutDir | Out-Null

foreach ($url in $Urls) {
  Write-Host "`n=== $url ===" -ForegroundColor Cyan
  # 1. Télécharger
  & $yt -o "$OutDir\%(uploader)s_%(id)s.%(ext)s" $url
  if ($LASTEXITCODE -ne 0) { Write-Warning "Echec download : $url"; continue }

  # Retrouver l'ID (dernier segment non vide de l'URL)
  $id = ($url.TrimEnd('/') -split '/')[-1]
  $mp4 = Get-ChildItem $OutDir -Filter "*$id*.mp4" | Select-Object -First 1
  if (-not $mp4) { Write-Warning "mp4 introuvable pour $id"; continue }

  # 2. Frames 1 img/s
  $framesDir = "$OutDir\frames_$id"
  New-Item -ItemType Directory -Force $framesDir | Out-Null
  ffmpeg -hide_banner -loglevel error -y -i $mp4.FullName -vf "fps=1,scale=480:-1" "$framesDir\f_%03d.jpg"

  # 3. Planches contact 4x4
  ffmpeg -hide_banner -loglevel error -y -i $mp4.FullName -vf "fps=1,scale=360:-1,tile=4x4" "$OutDir\contact_${id}_%02d.jpg"

  $dur = ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $mp4.FullName
  Write-Host "OK $id — ${dur}s — $(($mp4).Name)" -ForegroundColor Green
}
