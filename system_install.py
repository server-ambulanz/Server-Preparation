import os
import getpass
import subprocess

# Prüfen, ob das Skript als Root ausgeführt wird
if os.geteuid() != 0:
   print("Dieses Skript muss als Root ausgeführt werden (nicht mit sudo)")
   exit(1)

# Linux-Distribution prüfen
dist = subprocess.run(["lsb_release", "-ds"], capture_output=True, text=True).stdout.strip()

# Paketquellen aktualisieren
if "Ubuntu" in dist:
   subprocess.run(["apt", "update"])
elif "Debian" in dist:
   subprocess.run(["apt", "update"])
elif "CentOS" in dist or "Red Hat" in dist:
   subprocess.run(["yum", "check-update"])
else:
   print(f"Nicht unterstützte Distribution: {dist}")
   exit(1)

# Updates installieren
if "Ubuntu" in dist or "Debian" in dist:
   subprocess.run(["apt", "upgrade", "-y"])
elif "CentOS" in dist or "Red Hat" in dist:
   subprocess.run(["yum", "update", "-y"])

# Pakete installieren
pakete = ["sudo", "aptitude", "curl", "mc"]
if "Ubuntu" in dist or "Debian" in dist:
   subprocess.run(["apt", "install", "-y"] + pakete)
elif "CentOS" in dist or "Red Hat" in dist:
   subprocess.run(["yum", "install", "-y"] + pakete)

# Neuen SSH-Port abfragen
neuer_ssh_port = input("Geben Sie den neuen SSH-Port ein: ")

# SSH-Port in /etc/ssh/sshd_config ändern
with open("/etc/ssh/sshd_config", "r") as f:
   zeilen = f.readlines()
with open("/etc/ssh/sshd_config", "w") as f:
   for zeile in zeilen:
       if zeile.startswith("Port "):
           f.write(f"Port {neuer_ssh_port}\n")
       else:
           f.write(zeile)

# SSH-Dienst neu starten
if "Ubuntu" in dist or "Debian" in dist:
   subprocess.run(["systemctl", "restart", "sshd"])
elif "CentOS" in dist or "Red Hat" in dist:
   subprocess.run(["systemctl", "restart", "sshd"])

# Benutzer admjsentuerk mit Passwort erstellen und zur sudo-Gruppe hinzufügen
passwort = getpass.getpass("Geben Sie das Passwort für admjsentuerk ein: ")
subprocess.run(["useradd", "-m", "-p", passwort, "admjsentuerk"])
subprocess.run(["usermod", "-aG", "sudo", "admjsentuerk"])

# Benutzer admapp-agent ohne Home-Verzeichnis und Passwort erstellen
subprocess.run(["useradd", "-r", "admapp-agent"])

# Verzeichnis /opt/adm-agent/.ssh erstellen und Zugriff auf admapp-agent beschränken
os.makedirs("/opt/adm-agent/.ssh", mode=0o700, exist_ok=True)
subprocess.run(["chown", "-R", "admapp-agent:admapp-agent", "/opt/adm-agent/.ssh"])