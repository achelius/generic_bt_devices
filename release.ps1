param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

# Path to manifest.json
$manifestPath = "./custom_components/generic_bt/manifest.json"

# Read manifest.json
$manifest = Get-Content $manifestPath | ConvertFrom-Json

# Update version
$manifest.version = $Version

# Write back to manifest.json
$manifest | ConvertTo-Json -Depth 10 | Set-Content $manifestPath -Encoding UTF8

# Commit the change
$commitMsg = "Release version $Version"
git add $manifestPath
git commit -m $commitMsg

# Tag the commit
git tag $Version

# Push commit and tag
git push
git push origin $Version

Write-Host "Released version $Version and pushed to origin."
