param(
    [string]$Repository = 'Abdealmalk007/ProTech-Stone-Manager',
    [string]$Tag = 'v2.0.0'
)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if (!(Get-Command gh.exe -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI is required. Install it with: winget install GitHub.cli'
}
& gh auth status
if ($LASTEXITCODE -ne 0) {
    throw 'Sign in using gh auth login before publishing. No credentials are stored in this script.'
}
if (!(Test-Path '.git')) { & git init -b main }
& git add .gitignore .github README_AR.md THIRD_PARTY_NOTICES.md requirements-build.txt build_windows.ps1 installer.iss src PUBLISH_GITHUB.ps1
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    & git -c user.name='Abu Omar' -c user.email='protech.2025.2026@gmail.com' commit -m 'Public release: ProTech Marble & Porcelain Manager 2.0.0'
}
& gh repo view $Repository --json name 2>$null
if ($LASTEXITCODE -ne 0) {
    & gh repo create $Repository --public --source . --remote origin --push
    if ($LASTEXITCODE -ne 0) { throw 'Creating GitHub repository failed' }
} else {
    $remote=& git remote get-url origin 2>$null
    if (!$remote) { & git remote add origin "https://github.com/$Repository.git" }
    & git push -u origin main
    if ($LASTEXITCODE -ne 0) { throw 'GitHub push failed' }
}
if (!(Test-Path '.\Release\Setup.exe')) { throw 'Setup.exe is missing; build it first' }
$release=& gh release view $Tag --repo $Repository --json tagName 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "Release tag $Tag already exists; do not overwrite without reviewing its artifacts."
}
& gh release create $Tag ".\Release\Setup.exe" ".\Release\SHA256SUMS.txt" ".\Release\ProTechStoneManager_Source_v2.0.0.zip" --repo $Repository --target main --title "ProTech Marble & Porcelain Manager $Tag" --notes-file '.\RELEASE_NOTES_AR.md'
if ($LASTEXITCODE -ne 0) { throw 'Release publishing failed' }
Write-Output "Published: https://github.com/$Repository/releases/tag/$Tag"
