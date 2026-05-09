# Samedi 9/05 — Migration WP -> Shopify pipeline runner
#
# Usage (PowerShell):
#   d:\be-yours-mylab\docs\migration\samedi_run.ps1
#
# Steps:
#   1. Find latest order_export_*.csv and user_export_*.csv in ~\Downloads
#   2. Create timestamped output dir under docs/migration/runs/
#   3. Run transform_wc_to_matrixify.py with the standard params
#   4. Show summary + open output folder in Explorer
#
# After this script: upload to Shopify Matrixify in this order:
#   1) matrixify_customers.csv  (creates new customers)
#   2) matrixify_orders.csv     (creates orders, links to customers by email)
#   3) matrixify_customers_tags_abo.csv  (already in docs/migration/, MERGE tags abo)

$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
$env:PYTHONIOENCODING = 'utf-8'

$projectRoot = 'd:\be-yours-mylab'
$migrationDir = Join-Path $projectRoot 'docs\migration'
$transformScript = Join-Path $migrationDir 'transform_wc_to_matrixify.py'
$abosCsv = Join-Path $migrationDir 'matrixify_customers_tags_abo.csv'
$downloadsDir = [Environment]::GetFolderPath('UserProfile') + '\Downloads'

Write-Host ''
Write-Host '=== MIGRATION WP -> Shopify : runner samedi ===' -ForegroundColor Cyan
Write-Host ''

# 1. Find latest CSV files
$ordersCsv = Get-ChildItem -Path $downloadsDir -Filter 'order_export_*.csv' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
$usersCsv = Get-ChildItem -Path $downloadsDir -Filter 'user_export_*.csv' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $ordersCsv) {
    Write-Host "ERREUR : Aucun fichier order_export_*.csv trouve dans $downloadsDir" -ForegroundColor Red
    Write-Host '  -> Va dans WP Admin -> WebToffee -> Export -> WooCommerce Orders -> CSV -> sauve dans Telechargements' -ForegroundColor Yellow
    exit 1
}
if (-not $usersCsv) {
    Write-Host "ERREUR : Aucun fichier user_export_*.csv trouve dans $downloadsDir" -ForegroundColor Red
    Write-Host '  -> Va dans WP Admin -> WebToffee -> Export -> WooCommerce Users -> CSV -> sauve dans Telechargements' -ForegroundColor Yellow
    exit 1
}

$ordersAge = (Get-Date) - $ordersCsv.LastWriteTime
$usersAge = (Get-Date) - $usersCsv.LastWriteTime

Write-Host "Orders source : $($ordersCsv.Name)" -ForegroundColor Green
Write-Host "  -> derniere modif : $($ordersCsv.LastWriteTime)  ($([int]$ordersAge.TotalMinutes) min)"
Write-Host "Users source  : $($usersCsv.Name)" -ForegroundColor Green
Write-Host "  -> derniere modif : $($usersCsv.LastWriteTime)  ($([int]$usersAge.TotalMinutes) min)"

if ($ordersAge.TotalHours -gt 1) {
    Write-Host ''
    Write-Host "ATTENTION : l'export Orders date de plus d'1h. Tu veux vraiment continuer avec ce fichier ?" -ForegroundColor Yellow
    $reply = Read-Host '  Tape O pour continuer, autre touche pour annuler'
    if ($reply -ne 'O' -and $reply -ne 'o') { exit 1 }
}

# 2. Output dir timestamped
$ts = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$outDir = Join-Path $migrationDir "runs\$ts"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Write-Host ''
Write-Host "Output : $outDir" -ForegroundColor Cyan

# 3. Run transform
Write-Host ''
Write-Host '=== Transformation WC -> Matrixify ===' -ForegroundColor Cyan
$pythonArgs = @(
    $transformScript,
    '--orders', $ordersCsv.FullName,
    '--users', $usersCsv.FullName,
    '--out', $outDir,
    '--cutoff', '2026-02-26',
    '--shopify-existing-orders', '#3356,#3357'
)
& python @pythonArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host 'ERREUR Python (voir messages au-dessus)' -ForegroundColor Red
    exit $LASTEXITCODE
}

# 4. Copy abos CSV next to outputs for convenience
Copy-Item -Path $abosCsv -Destination $outDir -Force

# 5. Summary
Write-Host ''
Write-Host '=== Fichiers prets pour Matrixify ===' -ForegroundColor Cyan
Get-ChildItem -Path $outDir | ForEach-Object {
    $sizeKb = [math]::Round($_.Length / 1KB, 1)
    Write-Host ("  {0,-45} {1,8} KB" -f $_.Name, $sizeKb)
}

Write-Host ''
Write-Host '=== Ordre d''upload Matrixify (IMPORTANT) ===' -ForegroundColor Yellow
Write-Host '  1. matrixify_customers.csv             -> cree les nouveaux clients WC'
Write-Host '  2. matrixify_orders.csv                -> cree les commandes (link customer par email)'
Write-Host '  3. matrixify_customers_tags_abo.csv    -> ajoute les tags abo en MERGE'
Write-Host ''
Write-Host 'AVANT chaque import : Mode "Dry Run" puis verifier 0 erreur, puis Live.' -ForegroundColor Yellow
Write-Host ''
Write-Host 'AVANT TOUT : as-tu deja desactive ?' -ForegroundColor Yellow
Write-Host '  - Settings -> Notifications -> Staff Order Notifications (decocher tous)'
Write-Host '  - Apps -> Flow -> les 6 flows (Desactiver le flux de travail)'

# 6. Open output folder
Start-Process explorer.exe $outDir
