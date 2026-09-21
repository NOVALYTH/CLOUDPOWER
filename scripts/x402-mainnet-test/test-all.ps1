# Lance test-payment.mjs sur plusieurs produits a la suite (paiement mainnet reel a chaque fois).
#
# Usage :
#   $env:X402_PRIVATE_KEY="0x..."; .\test-all.ps1
#   $env:X402_PRIVATE_KEY="0x..."; .\test-all.ps1 -Targets p1,p3,p4
#
# Defaut : les 4 produits (p1,p2,p3,p4). Continue meme si l'un des appels echoue -- chaque
# node test-payment.mjs est un process separe, tu verras les 4 resultats a la suite.

param(
	[string[]]$Targets = @("p1", "p2", "p3", "p4")
)

if (-not $env:X402_PRIVATE_KEY) {
	Write-Error "X402_PRIVATE_KEY n'est pas definie. Lance d'abord : `$env:X402_PRIVATE_KEY='0x...'"
	exit 1
}

foreach ($t in $Targets) {
	Write-Host "`n=== $t ===" -ForegroundColor Cyan
	$env:TARGET = $t
	node test-payment.mjs
}
