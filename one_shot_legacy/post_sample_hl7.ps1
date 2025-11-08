$payload = Get-Content -Raw .\sample_hl7.txt
$kv = @{ payload = $payload; kind = 'MLLP' }
$form = $kv.GetEnumerator() | ForEach-Object { [System.Uri]::EscapeDataString($_.Key) + '=' + [System.Uri]::EscapeDataString($_.Value) } -join '&'
Invoke-RestMethod -Uri http://127.0.0.1:8001/messages/send -Method Post -Body $form -ContentType 'application/x-www-form-urlencoded' -UseBasicParsing
Write-Output "Posted sample HL7"