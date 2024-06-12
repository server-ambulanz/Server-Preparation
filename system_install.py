import os
import subprocess
import getpass
import re

def is_root():
    return os.geteuid() == 0

def change_root_password():
    if input("Möchten Sie das Root-Passwort ändern? (j/n): ").lower() == 'j':
        while True:
            new_password = getpass.getpass("Neues Root-Passwort: ")
            confirm_password = getpass.getpass("Passwort bestätigen: ")
            if new_password == confirm_password:
                process = subprocess.Popen(['passwd', 'root'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                process.communicate(f"{new_password}\n{new_password}\n")
                print("Root-Passwort geändert.")
                break
            else:
                print("Passwörter stimmen nicht überein. Bitte versuchen Sie es erneut.")

def change_ssh_port():
    ssh_config_path = '/etc/ssh/sshd_config'
    new_port = input("Neuer SSH-Port: ")
    with open(ssh_config_path, 'r') as file:
        config = file.read()

    config = re.sub(r'(#Port|Port) \d+', f'Port {new_port}', config)

    with open(ssh_config_path, 'w') as file:
        file.write(config)

    subprocess.run(['systemctl', 'restart', 'sshd'])
    print(f"SSH-Port zu {new_port} geändert und SSH-Dienst neu gestartet.")

def create_user():
    username = input("Neuen Benutzername: ")
    try:
        subprocess.run(['id', '-u', username], check=True)
        print(f"Benutzer {username} existiert bereits. Fortfahren...")
    except subprocess.CalledProcessError:
        while True:
            password = getpass.getpass("Neues Passwort: ")
            confirm_password = getpass.getpass("Passwort bestätigen: ")
            if password == confirm_password:
                subprocess.run(['useradd', '-m', '-s', '/bin/bash', username])
                process = subprocess.Popen(['passwd', username], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                process.communicate(f"{password}\n{password}\n")
                print(f"Benutzer {username} wurde erstellt.")
                break
            else:
                print("Passwörter stimmen nicht überein. Bitte versuchen Sie es erneut.")

def create_system_user():
    sys_username = input("Neuen Systembenutzername: ")
    try:
        subprocess.run(['id', '-u', sys_username], check=True)
        print(f"Systembenutzer {sys_username} existiert bereits. Fortfahren...")
    except subprocess.CalledProcessError:
        subprocess.run(['useradd', '-r', '-s', '/usr/sbin/nologin', sys_username])
        print(f"Systembenutzer {sys_username} wurde erstellt.")

def get_linux_distro():
    distro = ""
    if os.path.isfile('/etc/os-release'):
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('ID='):
                    distro = line.strip().split('=')[1].strip('"')
                    break
    return distro.lower()

def update_system(distro):
    if 'ubuntu' in distro or 'debian' in distro:
        subprocess.run(['apt', 'update'])
        subprocess.run(['apt', 'upgrade', '-y'])
    elif 'centos' in distro or 'fedora' in distro or 'rhel' in distro:
        subprocess.run(['yum', 'update', '-y'])
    elif 'suse' in distro or 'opensuse' in distro:
        subprocess.run(['zypper', 'refresh'])
        subprocess.run(['zypper', 'update', '-y'])
    else:
        print(f"Distribution {distro} wird nicht unterstützt.")
    print("System wurde aktualisiert.")

def check_and_install_packages(distro, packages):
    install_cmd = []
    if 'ubuntu' in distro or 'debian' in distro:
        install_cmd = ['apt', 'install', '-y']
    elif 'centos' in distro or 'fedora' in distro or 'rhel' in distro:
        install_cmd = ['yum', 'install', '-y']
    elif 'suse' in distro or 'opensuse' in distro:
        install_cmd = ['zypper', 'install', '-y']
    
    for package in packages:
        result = subprocess.run(['which', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"{package} wird installiert...")
            subprocess.run(install_cmd + [package])
        else:
            print(f"{package} ist bereits installiert.")

def main():
    if not is_root():
        print("Das Skript muss als Root ausgeführt werden.")
        return

    change_root_password()
    change_ssh_port()
    create_user()
    create_system_user()
    
    distro = get_linux_distro()
    update_system(distro)

    packages = ['sudo', 'aptitude', 'curl', 'mc']
    check_and_install_packages(distro, packages)

if __name__ == "__main__":
    main()
