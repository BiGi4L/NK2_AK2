# NK2 AK2 - Automatisering

Dette repoet inneholder løsningen min på arbeidskrav 2 i Nettverk 2.

Oppgaven går ut på å bruke Python og Ansible til å automatisere konfigurasjon av Cisco-utstyr.

Python brukes først via konsollkabel for å sette opp SSH på enhetene. Når SSH fungerer på alle enhetene brukes Ansible til resten av konfigurasjonen.

# Utstyr

Utstyret som er brukt:

- Cisco ISR 4221
- Cisco ISR 2901
- Cisco Catalyst 3650
- Cisco Catalyst 2960
- Cisco Catalyst 1000 Series
- Windows-PC med WSL/Ubuntu
- Konsollkabel
- Ethernet-kabler

# Kobling

Oppsettet i labben er koblet slik:

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

Catalyst 1000 brukes også videre mot klienter og EtherChannel.

Management bruker VLAN 106.

# Management IP-adresser

IP-adressene som brukes til management er:

```text
4221:            192.168.106.1
2901:            192.168.106.2
3650:            192.168.106.3
2960:            192.168.106.131
Catalyst 1000:   192.168.106.132
PC:              192.168.106.10
```

Management-nettet er delt i to /25-nett.

4221 og 2901 er koblet til begge nettene slik at trafikken kan routes mellom dem.

# Python-scriptet

Python-scriptet brukes til å gjøre Cisco-enhetene klare for SSH.

PC-en kobles til enheten med konsollkabel og scriptet bruker PySerial til å sende Cisco-kommandoer gjennom COM-porten.

Scriptet gjør blant annet dette:

- finner tilgjengelige COM-porter
- lar brukeren velge Cisco-modell
- setter hostname
- setter nødvendig management-IP
- oppretter lokal bruker
- setter enable secret
- setter domain name
- genererer RSA-nøkkel
- aktiverer SSH versjon 2
- konfigurerer VTY-linjene
- lagrer konfigurasjonen

Verdier som IP-adresse, interface, brukernavn og passord blir skrevet inn når scriptet kjøres og er derfor ikke hardkodet.

Python-scriptet støtter utstyret som brukes i oppgaven:

```text
Cisco 4221
Cisco 2901
Cisco 3650
Cisco 2960
Catalyst 1000
```

Målet med Python-scriptet er kun å få SSH til å fungere. Resten av konfigurasjonen gjøres med Ansible.

# How to - Python

## 1. Installer Python

Kontroller først om Python er installert:

```powershell
python --version
```

Hvis Python ikke er installert må Python 3 installeres.

## 2. Installer PySerial

Kjør:

```powershell
python -m pip install pyserial
```

PySerial kan kontrolleres med:

```powershell
python -m pip show pyserial
```

## 3. Koble til Cisco-enheten

Koble konsollkabelen mellom PC-en og Cisco-enheten.

COM-porten kan sees i Enhetsbehandling i Windows, men scriptet finner også tilgjengelige COM-porter automatisk.

PuTTY eller andre programmer som bruker samme COM-port må være lukket før scriptet kjøres.

## 4. Kjør Python-scriptet

Gå til mappen der scriptet ligger og kjør:

```powershell
python setup_ssh.py
```

## 5. Velg enhet og COM-port

Scriptet spør først hvilken Cisco-modell som brukes.

Deretter vises tilgjengelige COM-porter.

Eksempel:

```text
1: COM3
2: COM5 - USB Serial Port
```

Velg nummeret som tilhører riktig konsollkabel.

## 6. Fyll inn informasjonen scriptet spør etter

Scriptet spør blant annet etter:

```text
Hostname
Domain
SSH-brukernavn
SSH-passord
Enable secret
Management-IP
Subnettmaske
Interface
```

På switchene brukes VLAN 106 til management.

## 7. Test at SSH fungerer

Når scriptet er ferdig kan enheten først pinges:

```powershell
ping <IP-adresse>
```

Deretter testes SSH:

```powershell
ssh admin@<IP-adresse>
```

Eksempel:

```powershell
ssh admin@192.168.106.3
```

Når SSH fungerer er enheten klar til å brukes med Ansible.

# Ansible

Ansible brukes etter at SSH fungerer på alle Cisco-enhetene.

Ansible kjører fra Ubuntu i WSL på Windows-PC-en og kobler seg til Cisco-enhetene over SSH.

I dette oppsettet brukes Ansible til:

- å teste SSH-forbindelsen
- å kontrollere at riktige interfaces finnes
- å ta backup av running-config
- å opprette VLAN
- å konfigurere routerne
- å konfigurere access- og trunkporter
- å konfigurere EtherChannel
- å konfigurere DHCP
- å kontrollere konfigurasjonen etterpå

Konfigurasjonen er delt opp i flere playbooks. Det gjør det lettere å finne feil og endre deler av oppsettet senere.

Verdier som er forskjellige mellom enhetene ligger i host_vars. Dette gjelder for eksempel interface, VLAN og IP-adresser.

# Ansible-oppsettet

Mappene er satt opp omtrent slik:

```text
ansible/
|
├── ansible.cfg
├── requirements.yml
|
├── inventory/
│   ├── hosts.yml
│   |
│   └── host_vars/
│       ├── R4221.yml
│       ├── R2901.yml
│       ├── SW3650.yml
│       ├── SW2960.yml
│       └── SWC1000.yml
|
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

# Playbooks

01_test_connection.yml

Tester at Ansible får kontakt med alle enhetene over SSH.

02_precheck.yml

Sjekker at interfaces som skal brukes faktisk finnes før Ansible begynner å konfigurere.

03_backup.yml

Tar backup av running-config fra enhetene.

04_vlans.yml

Oppretter VLAN som skal brukes på switchene.

05_router_config.yml

Konfigurerer routerinterfaces, subinterfaces, IP-adresser og routing.

06_switch_ports.yml

Konfigurerer access- og trunkporter.

07_etherchannel.yml

Konfigurerer EtherChannel med LACP.

08_dhcp.yml

Setter opp DHCP på routerne.

09_verify.yml

Kjører show-kommandoer for å kontrollere konfigurasjonen.

site.yml

Kjører alle playbookene i riktig rekkefølge.

# How to - Ansible

## 1. Python-delen må være ferdig først

Ansible er avhengig av SSH.

Før Ansible brukes må alle Cisco-enhetene derfor ha:

```text
Management-IP
SSH-bruker
SSH versjon 2
RSA-nøkkel
VTY konfigurert for SSH
```

Test gjerne først fra PC-en:

```bash
ssh admin@192.168.106.3
```

Det må være mulig å logge inn før Ansible kan brukes.

## 2. Installer WSL og Ubuntu

Hvis WSL ikke allerede er installert kan det gjøres fra PowerShell:

```powershell
wsl --install -d Ubuntu
```

Start Ubuntu etter installasjonen.

## 3. Installer Ansible

I Ubuntu:

```bash
sudo apt update
sudo apt install ansible python3 python3-pip python3-paramiko git -y
```

Kontroller at Ansible er installert:

```bash
ansible --version
```

## 4. Installer Cisco Collections

Gå til prosjektmappen:

```bash
cd ~/NK2_AK2
```

Installer nødvendige collections:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

Prosjektet bruker:

```text
cisco.ios
ansible.netcommon
```

## 5. Kontroller at PC-en når alle enhetene

Fra WSL kan IP-adressene testes:

```bash
ping -c 2 192.168.106.1
ping -c 2 192.168.106.2
ping -c 2 192.168.106.3
ping -c 2 192.168.106.131
ping -c 2 192.168.106.132
```

Hvis en enhet ikke svarer må nettverk eller routing sjekkes før Ansible kjøres.

## 6. Gå til Ansible-mappen

```bash
cd ~/NK2_AK2/ansible
```

## 7. Kontroller inventory

Kjør:

```bash
ansible-inventory --graph
```

Alle fem Cisco-enhetene skal vises.

De er delt i routere og switcher:

```text
routers
  R4221
  R2901

switches
  SW3650
  SW2960
  SWC1000
```

## 8. Test Ansible-forbindelsen

Kjør:

```bash
ansible-playbook playbooks/01_test_connection.yml -k
```

`-k` gjør at Ansible spør etter SSH-passord.

Hvis alt fungerer skal alle enhetene ende med:

```text
failed=0
unreachable=0
```

## 9. Sjekk syntaks

Før hele oppsettet kjøres kan syntaksen testes:

```bash
ansible-playbook playbooks/site.yml --syntax-check
```

Hvis det ikke kommer noen feil er playbookene klare til å kjøres.

## 10. Kjør hele Ansible-oppsettet

Kjør:

```bash
ansible-playbook playbooks/site.yml -k
```

site.yml kjører playbookene i denne rekkefølgen:

```text
Test SSH
Precheck
Backup
VLAN
Router-konfigurasjon
Switchporter
EtherChannel
DHCP
Verifisering
```

## 11. Kontroller resultatet

Verifiseringsplaybooken kan kjøres alene:

```bash
ansible-playbook playbooks/09_verify.yml -k
```

Den kjører blant annet:

```text
show vlan brief
show interfaces trunk
show etherchannel summary
show ip interface brief
show ip route
show ip dhcp pool
show ip dhcp binding
```

# VLAN og DHCP

I oppsettet brukes:

```text
VLAN 10
Nettverk: 192.168.10.0/24
Gateway: 192.168.10.1
```

```text
VLAN 20
Nettverk: 192.168.20.0/24
Gateway: 192.168.20.1
```

```text
VLAN 106
Management
```

DHCP blir konfigurert på routerne gjennom Ansible.

# Testing

Etter at site.yml er kjørt har jeg kontrollert at Ansible får kontakt med alle enhetene.

Et vellykket resultat skal blant annet vise:

```text
R2901    failed=0  unreachable=0
R4221    failed=0  unreachable=0
SW2960   failed=0  unreachable=0
SW3650   failed=0  unreachable=0
SWC1000  failed=0  unreachable=0
```

Andre ting som bør sjekkes etter kjøring:

- SSH fungerer fortsatt på alle enhetene
- VLAN 10, 20 og 106 finnes
- trunkene er oppe
- native VLAN er likt på begge sider
- EtherChannel er oppe
- DHCP-poolene finnes
- klientene får riktig IP-adresse
- klientene kan nå gatewayen sin

# Ting jeg måtte feilsøke

Det oppstod noen problemer underveis.

Python fikk først problemer med COM-porten. Scriptet ble derfor endret slik at tilgjengelige COM-porter blir funnet automatisk.

Ansible forsøkte først å bruke vanlig SSH i stedet for network_cli. Dette ble løst ved å bruke:

```yaml
ansible_connection: ansible.netcommon.network_cli
ansible_network_os: cisco.ios.ios
```

Paramiko manglet også i WSL og ble installert med:

```bash
sudo apt install python3-paramiko
```

Det oppstod også native VLAN mismatch mellom 2960 og Catalyst 1000. Den ene siden brukte VLAN 1 mens den andre brukte VLAN 106.

Dette ble løst ved å bruke VLAN 106 som native VLAN på begge sider av trunkforbindelsen.

# Passord og backup

Passord er ikke lagret i GitHub-repoet.

Python-scriptet spør etter passord når det kjøres.

Ansible kjøres med:

```bash
-k
```

og spør derfor etter SSH-passord ved kjøring.

Backup av running-config blir lagret lokalt i:

```text
ansible/backups/
```

Denne mappen er lagt til i .gitignore og blir derfor ikke lastet opp til GitHub.

# Kort oppsummering

Python brukes til å sette opp SSH via konsoll.

Når SSH fungerer tar Ansible over og gjør resten av nettverkskonfigurasjonen.

Oppsettet blir derfor:

```text
Konsollkabel
     |
   Python
     |
SSH blir satt opp
     |
   Ansible
     |
VLAN, routing, porter,
EtherChannel og DHCP
```

På denne måten kan utstyret først klargjøres via konsoll og deretter administreres videre over nettverket.
