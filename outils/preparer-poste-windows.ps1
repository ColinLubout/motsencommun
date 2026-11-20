<#
.SYNOPSIS
    Prépare un poste Windows pour travailler sur Mots en commun.

.DESCRIPTION
    Installe Git, GitHub CLI, WSL2 et Debian, puis uv dans Debian ; clone le
    dépôt et lance les tests. Python et les outils du projet tournent dans
    Debian : sous Windows, Smart App Control bloque souvent les programmes non
    signés (Python, ruff, extensions compilées).

    Le script peut être relancé sans risque : chaque étape déjà faite est
    sautée. Sur un poste neuf, il faut le lancer deux fois, car l'installation
    de WSL demande de redémarrer l'ordinateur.

    À lancer depuis PowerShell, sans être administrateur (Windows demande
    l'autorisation quand il le faut) :

        powershell -ExecutionPolicy Bypass -File .\preparer-poste-windows.ps1

.PARAMETER Dossier
    Dossier où cloner le dépôt. Par défaut : C:\Projects\motsencommun.
#>
param(
    [string]$Dossier = "C:\Projects\motsencommun"
)

$ErrorActionPreference = "Stop"
$env:WSL_UTF8 = "1"  # sortie de wsl.exe en UTF-8 plutôt qu'en UTF-16

$Depot = "https://github.com/ColinLubout/motsencommun.git"
$Distribution = "Debian"
$VersionUv = "0.13.9"  # la même que dans .github/workflows/verifications.yml


function Write-Etape {
    param([string]$Texte)
    Write-Host ""
    Write-Host "==> $Texte" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Texte)
    Write-Host "    $Texte"
}

function Test-Commande {
    param([string]$Nom)
    return [bool](Get-Command $Nom -ErrorAction SilentlyContinue)
}

function Test-Reussite {
    # Lance une commande sans afficher sa sortie ; renvoie vrai si elle réussit.
    param([scriptblock]$Commande)
    $ancien = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Commande *> $null
    $reussi = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $ancien
    return $reussi
}

function Update-Chemin {
    # Relit le PATH enregistré, pour trouver les programmes qui viennent d'être installés.
    $cle = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    $machine = (Get-ItemProperty -Path $cle).Path
    $utilisateur = (Get-ItemProperty -Path "HKCU:\Environment").Path
    $env:Path = "$machine;$utilisateur"
}

function Install-Programme {
    param([string]$Commande, [string]$IdWinget, [string]$Nom)
    Write-Etape $Nom
    if (Test-Commande $Commande) {
        Write-Info "déjà installé"
        return
    }
    winget install --id $IdWinget --exact --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "L'installation de $Nom a échoué (winget, code $LASTEXITCODE)."
    }
    Update-Chemin
    if (-not (Test-Commande $Commande)) {
        throw "$Nom est installé mais introuvable : ouvrez un nouveau terminal et relancez le script."
    }
}

function Get-Distributions {
    # Noms des distributions Linux installées dans WSL.
    $ancien = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $liste = wsl.exe --list --quiet 2> $null
    $ErrorActionPreference = $ancien
    return @($liste | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
}

function Get-UidParDefaut {
    # Identifiant de l'utilisateur par défaut de Debian (0 : root, pas encore d'utilisateur).
    return "$(wsl.exe -d $Distribution --exec id -u)".Trim()
}

function Invoke-Debian {
    # Exécute un script sh dans Debian, sans passer par le shell par défaut de WSL.
    param([string]$Script, [switch]$Root, [string]$Repertoire)
    $arguments = @("-d", $Distribution)
    if ($Root) { $arguments += @("-u", "root") }
    if ($Repertoire) { $arguments += @("--cd", $Repertoire) }
    $arguments += @("--exec", "sh", "-c", ($Script -replace "`r", ""))
    & wsl.exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Une commande lancée dans Debian a échoué (code $LASTEXITCODE)."
    }
}


Write-Host "Préparation du poste pour Mots en commun" -ForegroundColor Cyan

Install-Programme -Commande git -IdWinget Git.Git -Nom "Git"
Install-Programme -Commande gh -IdWinget GitHub.cli -Nom "GitHub CLI"

Write-Etape "Identité git (nom et adresse des commits)"
$nom = git config --global user.name
if (-not $nom) {
    $nom = Read-Host "    Votre nom"
    git config --global user.name $nom
}
$adresse = git config --global user.email
if (-not $adresse) {
    $adresse = Read-Host "    Votre adresse e-mail (celle de GitHub, ou son adresse noreply)"
    git config --global user.email $adresse
}
Write-Info "$nom <$adresse>"

Write-Etape "WSL2"
if (Test-Reussite { wsl.exe --status }) {
    Write-Info "déjà installé"
} else {
    Write-Info "Windows va demander l'autorisation d'administrateur."
    Start-Process -FilePath wsl.exe -ArgumentList "--install", "-d", $Distribution, "--no-launch" -Verb RunAs -Wait
    Write-Host ""
    Write-Host "WSL est installé. Redémarrez l'ordinateur, puis relancez ce script." -ForegroundColor Yellow
    exit 0
}

Write-Etape "Debian dans WSL"
if ((Get-Distributions) -notcontains $Distribution) {
    Write-Info "Debian va s'installer, puis demander un nom d'utilisateur et un mot de passe Linux."
    Write-Info "Ils ne servent que sur ce poste. Quand l'invite de Debian s'affiche, tapez exit."
    wsl.exe --install -d $Distribution
    if ($LASTEXITCODE -ne 0) {
        throw "L'installation de Debian a échoué. Si WSL vient d'être installé, redémarrez d'abord l'ordinateur."
    }
}
if ((Get-UidParDefaut) -eq "0") {
    Write-Info "Debian n'a pas encore d'utilisateur : créez-le, puis tapez exit."
    wsl.exe -d $Distribution
    if ((Get-UidParDefaut) -eq "0") {
        throw "Debian n'a toujours pas d'utilisateur ordinaire. Lancez « wsl -d $Distribution », créez-en un, puis relancez ce script."
    }
}
Write-Info "prête"

Write-Etape "Paquets de base dans Debian"
Invoke-Debian -Root -Script @'
set -eu
if dpkg -s curl ca-certificates >/dev/null 2>&1; then
  echo '    déjà installés'
else
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates
fi
'@

Write-Etape "uv $VersionUv dans Debian"
$scriptUv = @'
set -eu
version=VERSION_UV
uv=$HOME/.local/bin/uv
if [ -x $uv ] && [ $($uv --version | cut -d ' ' -f 2) = $version ]; then
  echo '    déjà installé'
else
  case $(uname -m) in
    x86_64) archive=uv-x86_64-unknown-linux-gnu ;;
    aarch64) archive=uv-aarch64-unknown-linux-gnu ;;
    *) echo 'Processeur non pris en charge.' >&2; exit 1 ;;
  esac
  adresse=https://github.com/astral-sh/uv/releases/download/$version/$archive.tar.gz
  temporaire=$(mktemp -d)
  cd $temporaire
  curl -fsSL -o $archive.tar.gz $adresse
  curl -fsSL -o $archive.tar.gz.sha256 $adresse.sha256
  sha256sum --check --quiet $archive.tar.gz.sha256
  tar -xzf $archive.tar.gz
  mkdir -p $HOME/.local/bin
  install -m 0755 $archive/uv $archive/uvx $HOME/.local/bin/
  cd /
  rm -rf $temporaire
  $uv --version
fi
# Le dépôt est sur le disque Windows : uv y copie les fichiers au lieu de les lier.
if ! grep -q UV_LINK_MODE $HOME/.profile 2>/dev/null; then
  printf '\nexport UV_LINK_MODE=copy\n' >> $HOME/.profile
fi
'@
Invoke-Debian -Script ($scriptUv -replace "VERSION_UV", $VersionUv)

Write-Etape "Dépôt Mots en commun"
if (Test-Path (Join-Path $Dossier ".git")) {
    Write-Info "déjà cloné dans $Dossier"
} else {
    $parent = Split-Path -Parent $Dossier
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    git clone $Depot $Dossier
    if ($LASTEXITCODE -ne 0) {
        throw "Le clonage du dépôt a échoué."
    }
}

Write-Etape "Connexion de GitHub CLI à GitHub"
if (Test-Reussite { gh auth status }) {
    Write-Info "déjà connecté"
} else {
    Write-Info "Le navigateur va s'ouvrir : connectez-vous, puis saisissez le code affiché ici."
    gh auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) {
        throw "La connexion à GitHub a échoué."
    }
}

Write-Etape "Vérification : les tests du projet, dans Debian"
if (Test-Path (Join-Path $Dossier "uv.lock")) {
    Invoke-Debian -Repertoire $Dossier -Script @'
set -eu
export UV_LINK_MODE=copy
$HOME/.local/bin/uv sync --locked
$HOME/.local/bin/uv run pytest -q
'@
} else {
    Write-Info "pas encore de uv.lock sur cette branche : vérification sautée"
}

Write-Host ""
Write-Host "Le poste est prêt." -ForegroundColor Green
Write-Host "Pour travailler sur le projet, ouvrez Debian dans le dossier du dépôt :"
Write-Host "    wsl -d $Distribution --cd $Dossier"
Write-Host "puis lancez par exemple : uv run pytest"
