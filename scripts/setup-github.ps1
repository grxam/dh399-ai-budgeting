<#
.SYNOPSIS
  One-time GitHub setup: creates the repo, pushes, adds labels, enables branch protection.
.EXAMPLE
  .\scripts\setup-github.ps1 -Name dh399-ai-budgeting -Visibility private -Collaborators alice,bob
#>
param(
  [Parameter(Mandatory)] [string] $Name,
  [ValidateSet('private', 'public')] [string] $Visibility = 'private',
  [string[]] $Collaborators = @()
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

gh auth status | Out-Null
$owner = gh api user --jq .login
$repo = "$owner/$Name"

gh repo create $repo --$Visibility --source . --remote origin --push `
  --description "AI budgeting app: vision agent reads receipts, reasoning agent gives advice"

# Labels
Get-Content .github/labels.yml | ForEach-Object {
  if ($_ -match 'name: ([^,]+), color: (\w+), description: (.+?) }') {
    gh label create $Matches[1].Trim() --color $Matches[2] --description $Matches[3] --force --repo $repo
  }
}

# Repo settings: squash-merge only, auto-delete merged branches
gh api -X PATCH "repos/$repo" -F allow_squash_merge=true -F allow_merge_commit=false `
  -F allow_rebase_merge=false -F delete_branch_on_merge=true | Out-Null

# Invite teammates
foreach ($c in $Collaborators) {
  gh api -X PUT "repos/$repo/collaborators/$c" -f permission=push | Out-Null
  Write-Host "Invited $c"
}

# Branch protection (needs a public repo or a paid plan for private repos)
$protection = @{
  required_status_checks = @{ strict = $true; contexts = @('lint', 'test (ubuntu-latest, 3.12)') }
  enforce_admins = $false
  required_pull_request_reviews = @{ required_approving_review_count = 1 }
  restrictions = $null
} | ConvertTo-Json -Depth 5
$protection | gh api -X PUT "repos/$repo/branches/main/protection" --input - | Out-Null

Write-Host "Done: https://github.com/$repo"
Write-Host "Remember to replace OWNER/REPO in README.md and .github/ISSUE_TEMPLATE/config.yml."
