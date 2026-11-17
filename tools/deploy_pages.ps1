# 把目前的遊戲發佈到 GitHub Pages（https://<帳號>.github.io/qiku/）。
# 用法：在 七窟_原型 資料夾執行  powershell -File tools\deploy_pages.ps1
# 做的事：play.html 當作首頁，連同 img、voice 推到 gh-pages 分支（每次整個覆蓋）。
# 注意：先確定 play.html 是最新的（改過 index.html 要先重建 play.html）。
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$login = gh api user --jq '.login'
$id = gh api user --jq '.id'
$site = Join-Path $env:TEMP 'qiku_site'
if (Test-Path $site) { Remove-Item -Recurse -Force $site }
New-Item -ItemType Directory -Force $site | Out-Null
Copy-Item -LiteralPath (Join-Path $root 'play.html') -Destination (Join-Path $site 'index.html')
Copy-Item -LiteralPath (Join-Path $root 'img'), (Join-Path $root 'voice') -Destination $site -Recurse
New-Item -ItemType File (Join-Path $site '.nojekyll') | Out-Null
git -C $site init -q -b gh-pages
git -C $site config user.name $login
git -C $site config user.email "$id+$login@users.noreply.github.com"
git -C $site add -A
git -C $site commit -q -m 'Deploy site'
git -C $site push -q --force "https://github.com/$login/qiku.git" gh-pages
Write-Output "已推送，約一兩分鐘後生效：https://$login.github.io/qiku/"
