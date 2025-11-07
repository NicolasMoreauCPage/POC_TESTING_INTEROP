param($hostname ="127.0.0.1", $port=2000)

# Message HL7 simple (CR = `r)
$msg = "MSH|^~\&|TEST|SRC|DST|DST|" + (Get-Date -Format "yyyyMMddHHmmss") + "||ADT^A01|MSG0001|P|2.5`r" +
       "PID|||12345||DOE^JOHN||19800101|M`r" +
       "PV1||I|WARD^ROOM^BED`r"

# Encadrement MLLP : <VT> message <FS><CR>
$vt  = [char]0x0B
$fs  = [char]0x1C
$cr  = [char]0x0D
$bytes = [System.Text.Encoding]::UTF8.GetBytes("$vt$msg$fs$cr")

$client = New-Object System.Net.Sockets.TcpClient($hostname , $port)
$stream = $client.GetStream()
$stream.Write($bytes, 0, $bytes.Length)

# Lire l'ACK
$buffer = New-Object byte[] 65536
$read = $stream.Read($buffer, 0, $buffer.Length)
$ack = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
$client.Close()

"ACK reçu (brut) :"
$ack
