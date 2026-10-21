NK2 – Arbeidskrav 2: Automatisering

Dette repositoryet inneholder løsningen min på Arbeidskrav 2 – Automatisering i Nettverk 2.

Målet med arbeidskravet er å bruke to forskjellige metoder for å automatisere konfigurasjon av Cisco-utstyr:

1. Python og PySerial via konsollkabel
2. Ansible via SSH

Python brukes først til å gjøre Cisco-enhetene tilgjengelige via SSH. Når SSH fungerer, brukes Ansible til videre konfigurasjon av nettverket.

---

# Utstyr

Følgende Cisco-utstyr er brukt:

- Cisco ISR 4221
- Cisco ISR 2901
- Cisco Catalyst 3650
- Cisco Catalyst 2960
- Cisco Catalyst 1000 Series

Administrasjonsmaskinen er en Windows-PC med Ubuntu/WSL.

---

# Topologi

Labben er koblet omtrent slik:

```text
                         PC
                          |
                       Gi1/0/1
                          |
                   Catalyst 3650
                    /           \
             Gi1/0/2             Gi1/0/3
                |                   |
             Gi0/0/1              Gi0/1
                |                   |
             ISR 4221            ISR 2901
                |                   |
             Gi0/0/0              Gi0/0
                |                   |
              Fa0/1               Fa0/2
                 \                 /
                  \               /
                   Catalyst 2960
                        |
                      Fa0/3
                        |
                 Catalyst 1000
                        |
                   EtherChannel
```

Management bruker **VLAN 106**.

---

# Kort forklaring – Python

Python-scriptet brukes når Cisco-enheten ennå ikke er tilgjengelig over nettverket.

PC-en kobles til Cisco-enheten med konsollkabel, og Python bruker biblioteket **PySerial** til å sende Cisco-kommandoer gjennom COM-porten.

Scriptet gjør blant annet følgende:

- finner tilgjengelige COM-porter
- kobler til Cisco-enheten via konsoll
- setter hostname
- setter nødvendig management-IP
- oppretter lokal bruker
- setter enable secret
- setter domain name
- genererer RSA-nøkkel
- aktiverer SSH versjon 2
- konfigurerer VTY-linjer med `login local`
- lagrer konfigurasjonen

Scriptet støtter alle Cisco-modellene som brukes i oppgaven.

Variabler som hostname, IP-adresse, interface, brukernavn og passord blir skrevet inn når scriptet kjøres og er derfor ikke hardkodet.

Når Python-scriptet er ferdig skal enheten kunne nås med:

```bash
ssh <brukernavn>@<management-IP>
```

---

# How-to – Python

## 1. Installer Python

Kontroller at Python er installert:

```powershell
python --version
```

Hvis Python ikke er installert må Python 3 installeres først.

---

## 2. Installer PySerial

```powershell
python -m pip install pyserial
```

Kontroller:

```powershell
python -m pip show pyserial
```

---

## 3. Koble konsollkabel

Koble PC-en til console-porten på Cisco-enheten.

På Windows kan COM-porten kontrolleres i:

```text
Enhetsbehandling
→ Porter (COM og LPT)
```

Python-scriptet viser også tilgjengelige COM-porter automatisk.

> PuTTY eller andre programmer som bruker samme COM-port må være lukket før Python-scriptet kjøres.

---

## 4. Kjør scriptet

Gå til mappen der scriptet ligger:

```powershell
cd <sti-til-python-mappen>
```

Kjør:

```powershell
python setup_ssh.py
```

---

## 5. Velg enhet

Scriptet spør hvilken Cisco-modell som skal konfigureres.

Eksempel:

```text
1 - Cisco ISR 4221
2 - Cisco ISR 2901
3 - Cisco Catalyst 3650
4 - Cisco Catalyst 2960
5 - Cisco Catalyst 1000
```

Velg riktig modell.

---

## 6. Velg COM-port

Scriptet viser tilgjengelige COM-porter.

Eksempel:

```text
1: COM3
2: COM5 - USB Serial Port
```

Velg nummeret foran riktig port.

---

## 7. Oppgi konfigurasjon

Scriptet spør blant annet etter:

```text
Hostname
Domain name
SSH-brukernavn
SSH-passord
Enable secret
Management-IP
Subnettmaske
Interface
```

På switchene spør scriptet også etter management-VLAN og nødvendige management-porter.

Management-VLAN som brukes i denne labben er:

```text
VLAN 106
```

---

## 8. Test SSH

Når scriptet er ferdig testes først ping:

```powershell
ping <management-IP>
```

Deretter SSH:

```powershell
ssh <brukernavn>@<management-IP>
```

Python-delen er ferdig når alle Cisco-enhetene kan nås via SSH.

---

# Management-IP-er

Management-oppsettet som ble brukt i labben:

| Enhet | Management-IP |
|---|---|
| ISR 4221 | `192.168.106.1` |
| ISR 2901 | `192.168.106.2` |
| Catalyst 3650 | `192.168.106.3` |
| Catalyst 2960 | `192.168.106.131` |
| Catalyst 1000 | `192.168.106.132` |

PC-en bruker:

```text
IP:      192.168.106.10
VLAN:    106
```

---

# Kort forklaring – Ansible

Når SSH fungerer brukes Ansible til videre konfigurasjon.

Ansible kjører fra Ubuntu/WSL på PC-en og kobler seg til Cisco-enhetene via SSH.

Ansible-konfigurasjonen er delt opp i flere playbooks slik at oppsettet er enklere å forstå, endre og gjenbruke.

Ansible brukes blant annet til:

- teste SSH-forbindelse
- kontrollere interfaces før konfigurasjon
- ta backup av running-config
- opprette VLAN
- konfigurere routere
- konfigurere access- og trunkporter
- konfigurere EtherChannel
- konfigurere DHCP
- kontrollere sluttresultatet

Enhetsspesifikke verdier ligger i `host_vars`, slik at playbookene ikke trenger å inneholde alle portnummer, IP-adresser og VLAN direkte.

---

# Ansible-struktur

```text
ansible/
│
├── ansible.cfg
├── requirements.yml
│
├── inventory/
│   ├── hosts.yml
│   │
│   └── host_vars/
│       ├── R4221.yml
│       ├── R2901.yml
│       ├── SW3650.yml
│       ├── SW2960.yml
│       └── SWC1000.yml
│
└── playbooks/
    ├── 01_test_connection.yml
    ├── 02_precheck.yml
    ├── 03_backup.yml
    ├── 04_vlans.yml
    ├── 05_router_config.yml
    ├── 06_switch_ports.yml
    ├── 07_etherchannel.yml
    ├── 08_dhcp.yml
    ├── 09_verify.yml
    └── site.yml
```

---

# Hva playbookene gjør

| Playbook | Funksjon |
|---|---|
| `01_test_connection.yml` | Tester SSH mot alle enhetene |
| `02_precheck.yml` | Kontrollerer at forventede interface finnes |
| `03_backup.yml` | Tar backup av running-config |
| `04_vlans.yml` | Oppretter VLAN |
| `05_router_config.yml` | Konfigurerer routere og routing |
| `06_switch_ports.yml` | Konfigurerer access- og trunkporter |
| `07_etherchannel.yml` | Konfigurerer LACP EtherChannel |
| `08_dhcp.yml` | Konfigurerer DHCP på routerne |
| `09_verify.yml` | Kontrollerer sluttresultatet |
| `site.yml` | Kjører alle playbookene i riktig rekkefølge |

---

# How-to – Ansible

## 1. SSH må fungere først

Før Ansible kan brukes må Python-delen være ferdig.

Fra PC/WSL må det være mulig å nå Cisco-enhetene.

Eksempel:

```bash
ping 192.168.106.3
```

og:

```bash
ssh admin@192.168.106.3
```

Dette må fungere mot alle enhetene.

---

## 2. Installer WSL/Ubuntu

På Windows:

```powershell
wsl --install -d Ubuntu
```

Start Ubuntu:

```powershell
wsl
