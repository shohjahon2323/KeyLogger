#!/bin/bash

# CYBER RANGE LAB 4: Privilege Escalation (SUID / Wildcard Injection)
echo "[*] Cyber Range Backup Utility"
echo "[*] Running as root..."

# VULNERABILITY: Using wildcard in tar command allows for arbitrary command execution
# if a file named '--checkpoint-action=exec=sh' exists in the directory.

cd /tmp/backup_dir
tar cf /var/backups/data.tar *

echo "[+] Backup complete."
