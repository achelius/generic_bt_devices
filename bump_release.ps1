param(
    [ValidateSet("patch", "minor", "major")]
    [string]$Type = "patch"
)

# Path to manifest.json
$manifestPath = "./custom_components/generic_bt/manifest.json"

# Read manifest.json
$manifest = Get-Content $manifestPath | ConvertFrom-Json

# Parse current version
$currentVersion = $manifest.version -replace "[vV]", ""
$versionParts = $currentVersion.Split('.')
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]
$patch = [int]$versionParts[2]

switch ($Type) {
    "major" { $major++; $minor = 0; $patch = 0 }
    "minor" { $minor++; $patch = 0 }
    "patch" { $patch++ }
}

$newVersion = "$major.$minor.$patch"

# Call release.ps1 with new version
. ./release.ps1 -Version $newVersion
