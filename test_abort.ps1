$payload = '{"model":"nvidia/Qwen3.6-35B-A3B-NVFP4","messages":[{"role":"user","content":"Count from 1 to 1000 slowly, one number per line."}],"stream":true}'
$payloadFile = Join-Path $env:TEMP "abort_test_payload.json"
Set-Content -Path $payloadFile -Value $payload -NoNewline -Encoding utf8

curl.exe -N -X POST https://vllm.itrust.lu/llm/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer $env:LLM_API_KEY" -d "@$payloadFile"
