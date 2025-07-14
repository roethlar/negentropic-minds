# generate_raw_links.ps1
# PowerShell script to generate a manifest of raw GitHub URLs for all files in the local repo.
# Run from the repo's base directory.
# Supports custom Git executable path (e.g., portable Git); falls back to system Git if not set.
# Excludes .git folder and outputs in TXT format, grouped by directory.

# Custom Git path (set to your portable Git; leave empty for system Git)
$gitExe = "H:\onedrive\Apps\GitPortable\bin\git.exe"  # Or '' for normal Git

# Function to run Git command with optional custom exe
function Invoke-Git {
    param (
        [string[]]$arguments
    )
    if ($gitExe) {
        & $gitExe $arguments
    } else {
        git $arguments
    }
}

# Function to get repo details from .git/config
function Get-RepoDetails {
    # Get remote origin URL
    $remoteUrl = Invoke-Git config --get remote.origin.url
    if (-not $remoteUrl) {
        Write-Error "No remote.origin.url found in .git/config. Ensure this is a Git repo with a remote."
        exit 1
    }

    # Parse owner and repo name (supports https and ssh formats)
    if ($remoteUrl -match 'github.com/(.+)/(.+?)(.git)?$') {
        $owner = $Matches[1]
        $repo = $Matches[2]
    } else {
        Write-Error "Unable to parse GitHub owner/repo from remote URL: $remoteUrl"
        exit 1
    }

    # Get current branch
    $branch = Invoke-Git rev-parse --abbrev-ref HEAD
    if (-not $branch) {
        Write-Error "Unable to determine current branch."
        exit 1
    }

    return @{
        Owner = $owner
        Repo = $repo
        Branch = $branch
    }
}

# Main execution
$repoDetails = Get-RepoDetails
$baseUrl = "https://raw.githubusercontent.com/$($repoDetails.Owner)/$($repoDetails.Repo)/$($repoDetails.Branch)/"

# Get all files recursively, exclude .git
$files = Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch '\\\.git\\' }

# Group files by directory for output
$groupedFiles = $files | Group-Object -Property DirectoryName

# Output to console (redirect to file if needed, e.g., .\generate_raw_links.ps1 > raw_links_manifest.txt)
Write-Output "# raw_links_manifest.txt"
Write-Output "# Generated list of raw GitHub links for repo files."
Write-Output "# Base URL: $baseUrl"
Write-Output ""

foreach ($group in $groupedFiles | Sort-Object Name) {
    $dirPath = if ($group.Name -eq (Get-Location).Path) { "Root" } else { $group.Name.Substring((Get-Location).Path.Length + 1).Replace('\', '/') }
    Write-Output "## $dirPath"
    foreach ($file in $group.Group | Sort-Object Name) {
        $relPath = $file.FullName.Substring((Get-Location).Path.Length + 1).Replace('\', '/')
        $rawLink = "$baseUrl$relPath"
        Write-Output "$rawLink"
    }
    Write-Output ""
}

$groupedFiles | set-content .\raw_link_manifest.txt