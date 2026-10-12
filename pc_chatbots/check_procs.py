import subprocess

cmd = """powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'msedge|python' } | Select-Object ProcessId, Name, CommandLine | Format-List" """
p = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
for block in p.stdout.split('\n\n'):
    if 'uvicorn' in block or 'headless' in block or 'gemini' in block or 'data' in block or '11916' in block:
        print(block)
        print('-'*40)
