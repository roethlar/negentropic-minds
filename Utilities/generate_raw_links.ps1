# generate_raw_links.ps1
# PowerShell script to generate a manifest of raw GitHub URLs for all files in the local repo.
# Run from the repo's base directory.
# Supports custom Git executable path (e.g., portable Git); falls back to system Git if not set.
# If no remote found, prompts for owner/repo/branch.

# Custom Git path (set to your portable Git; leave empty for system Git)
$gitExe = "H:\onedrive\Apps\GitPortable\bin\git.exe"  # Or '' for normal Git

# Function to run Git command with optional custom exe
function Invoke-Git {
    param (
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$arguments
    )
    if ($gitExe) {
        & $gitExe @arguments
    } else {
        git @arguments
    }
}

# Function to get repo details from .git/config or prompt user
function Get-RepoDetails {
    # Try to get remote origin URL
    $remoteUrl = Invoke-Git config --get remote.origin.url

    if ($remoteUrl) {
        # Parse owner and repo name (supports https and ssh formats)
        if ($remoteUrl -match 'github.com/(.+)/(.+?)(.git)?$') {
            $owner = $Matches[1]
            $repo = $Matches[2]
        } else {
            Write-Warning "Unable to parse GitHub owner/repo from remote URL: $remoteUrl. Prompting for manual input."
            $owner = Read-Host "Enter GitHub owner (username)"
            $repo = Read-Host "Enter GitHub repo name"
        }
    } else {
        Write-Warning "No remote.origin.url found in .git/config. Prompting for manual input."
        $owner = Read-Host "Enter GitHub owner (username)"
        $repo = Read-Host "Enter GitHub repo name"
    }

    # Get current branch or prompt
    $branch = Invoke-Git rev-parse --abbrev-ref HEAD
    if (-not $branch) {
        Write-Warning "Unable to determine current branch. Prompting for manual input."
        $branch = Read-Host "Enter GitHub branch name (default: main)"
        if (-not $branch) { $branch = "main" }
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

$outData = foreach ($group in $groupedFiles | Sort-Object Name) {
#    $dirPath = if ($group.Name -eq (Get-Location).Path) { "Root" } else { $group.Name.Substring((Get-Location).Path.Length + 1).Replace('\', '/') }
#    Write-Output "## $dirPath"
    foreach ($file in $group.Group | Sort-Object Name) {
        $relPath = $file.FullName.Substring((Get-Location).Path.Length + 1).Replace('\', '/')
        $rawLink = "$baseUrl$relPath"
        Write-Output "$rawLink"
    }
#    Write-Output ""
}
$outData | set-content .\raw_link_manifest.txt