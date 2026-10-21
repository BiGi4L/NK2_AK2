import serial
import time
import getpass
from serial.tools import list_ports


# ============================================================
# HJELPEFUNKSJONER
# ============================================================

def read_output(connection, wait=1):
    """
    Venter litt og leser output fra Cisco-enheten.
    """
    time.sleep(wait)

    output = ""

    while connection.in_waiting > 0:
        output += connection.read(
            connection.in_waiting
        ).decode("utf-8", errors="ignore")

        time.sleep(0.2)

    return output


def send_command(connection, command, wait=1, hide=False):
    """
    Sender én kommando til Cisco-enheten.
    hide=True brukes for kommandoer som inneholder passord.
    """

    if hide:
        print("\n>>> [sensitiv kommando skjult]")
    else:
        print(f"\n>>> {command}")

    connection.write(
        (command + "\r\n").encode()
    )

    output = read_output(connection, wait)

    if output:
        # Vi skriver ikke output fra sensitive kommandoer,
        # siden Cisco kan ekko passordet tilbake.
        if not hide:
            print(output, end="")

    return output


def has_error(output):
    """
    Ser etter vanlige Cisco CLI-feil.
    """

    if not output:
        return False

    errors = [
        "% Invalid input",
        "% Incomplete command",
        "% Ambiguous command",
        "% Unknown command",
        "% Unrecognized command"
    ]

    return any(
        error.lower() in output.lower()
        for error in errors
    )


# ============================================================
# COM-PORT
# ============================================================

def select_com_port():
    """
    Finner COM-porter automatisk og lar brukeren
    velge med nummer.
    """

    ports = list(list_ports.comports())

    if not ports:
        print("\nIngen COM-porter ble funnet.")
        print("Kontroller consolekabel og driver.")
        return None

    print("\n" + "=" * 60)
    print(" TILGJENGELIGE COM-PORTER")
    print("=" * 60)

    for index, port in enumerate(ports, start=1):
        print(
            f"{index}: {port.device} - {port.description}"
        )

    while True:

        choice = input(
            "\nVelg COM-port med nummer: "
        ).strip()

        try:
            choice = int(choice)

            if 1 <= choice <= len(ports):

                selected_port = ports[
                    choice - 1
                ].device

                print(
                    f"Valgt COM-port: {selected_port}"
                )

                return selected_port

            print("Ugyldig valg.")

        except ValueError:
            print(
                "Skriv nummeret foran COM-porten."
            )


def open_console(com_port):
    """
    Åpner Cisco console:
    9600 baud, 8N1, ingen flow control.
    """

    print(
        f"\nForsøker å åpne {com_port}..."
    )

    connection = serial.Serial(
        port=com_port,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        write_timeout=2,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )

    print(
        f"{com_port} åpnet OK!"
    )

    return connection


# ============================================================
# KLARGJØR CONSOLE
# ============================================================

def prepare_console(connection):
    """
    Vekker Cisco-enheten og håndterer
    initial configuration dialog.
    """

    print("\nKlargjør Cisco-console...")

    connection.write(b"\r\n")

    output = read_output(
        connection,
        3
    )

    if output:
        print(output, end="")

    if "initial configuration dialog" in output.lower():

        print(
            "\nFørstegangsoppsett oppdaget."
        )

        send_command(
            connection,
            "no",
            wait=3
        )

        # Cisco ber ofte om RETURN etterpå.
        connection.write(b"\r\n")

        output = read_output(
            connection,
            3
        )

        if output:
            print(output, end="")

    # Ctrl+Z for å forsøke å stå i vanlig EXEC-mode.
    connection.write(
        b"\x1a\r\n"
    )

    read_output(
        connection,
        1
    )


# ============================================================
# ENABLE
# ============================================================

def enter_enable(connection):
    """
    Går til privileged EXEC mode.
    Dersom enheten allerede har enable-passord,
    spør scriptet etter det.
    """

    output = send_command(
        connection,
        "enable"
    )

    if "password" in output.lower():

        old_password = getpass.getpass(
            "Eksisterende enable-passord: "
        )

        send_command(
            connection,
            old_password,
            wait=2,
            hide=True
        )


# ============================================================
# RSA
# ============================================================

def generate_rsa(connection):
    """
    Genererer RSA-nøkkel.
    Forsøker alternativ syntaks dersom nødvendig.
    """

    print("\nOppretter RSA-nøkkel...")

    output = send_command(
        connection,
        "crypto key generate rsa modulus 2048",
        wait=5
    )

    # Noen IOS-versjoner spør etter størrelse separat.
    if "how many bits" in output.lower():

        send_command(
            connection,
            "2048",
            wait=5
        )

        return

    # Hvis nøkkel allerede finnes.
    if "replace" in output.lower():

        send_command(
            connection,
            "no",
            wait=2
        )

        return

    # Alternativ syntaks for enkelte IOS-versjoner.
    if has_error(output):

        print(
            "\nPrøver alternativ RSA-kommando..."
        )

        output = send_command(
            connection,
            "crypto key generate rsa general-keys modulus 2048",
            wait=5
        )

        if "how many bits" in output.lower():

            send_command(
                connection,
                "2048",
                wait=5
            )


# ============================================================
# SSH
# ============================================================

def configure_ssh(
    connection,
    domain,
    username,
    password
):
    """
    SSH-konfigurasjon som er felles
    for routere og switcher.
    """

    print("\n" + "=" * 60)
    print(" KONFIGURERER SSH")
    print("=" * 60)

    send_command(
        connection,
        f"ip domain-name {domain}"
    )

    send_command(
        connection,
        f"username {username} privilege 15 secret {password}",
        hide=True
    )

    generate_rsa(
        connection
    )

    send_command(
        connection,
        "ip ssh version 2"
    )

    # Prøv først 16 VTY-linjer.
    output = send_command(
        connection,
        "line vty 0 15"
    )

    # Noen eldre modeller/IOS-versjoner bruker bare 0-4.
    if has_error(output):

        print(
            "\nVTY 0-15 støttes ikke. "
            "Prøver VTY 0-4."
        )

        send_command(
            connection,
            "line vty 0 4"
        )

    send_command(
        connection,
        "login local"
    )

    send_command(
        connection,
        "transport input ssh"
    )

    send_command(
        connection,
        "exit"
    )


# ============================================================
# SWITCH
# ============================================================

def configure_switch_management(
    connection,
    vlan_id,
    ip_address,
    subnet_mask,
    gateway,
    ports
):
    """
    Minimal management-konfigurasjon for:
    - Catalyst 3650
    - Catalyst 2960
    - Catalyst 1000

    Dette er kun for å gjøre SSH tilgjengelig.
    """

    print("\n" + "=" * 60)
    print(" KONFIGURERER MANAGEMENT-IP")
    print("=" * 60)

    # Opprett management-VLAN.
    send_command(
        connection,
        f"vlan {vlan_id}"
    )

    send_command(
        connection,
        "exit"
    )

    # Management-SVI.
    send_command(
        connection,
        f"interface vlan {vlan_id}"
    )

    send_command(
        connection,
        f"ip address {ip_address} {subnet_mask}"
    )

    send_command(
        connection,
        "no shutdown"
    )

    send_command(
        connection,
        "exit"
    )

    # Legg nødvendige fysiske porter i management-VLAN.
    for port in ports:

        output = send_command(
            connection,
            f"interface {port}"
        )

        if has_error(output):
            raise RuntimeError(
                f"Interface {port} finnes ikke."
            )

        # Sikrer Layer 2-modus på switcher som støtter routed ports.
        send_command(
            connection,
            "switchport"
        )

        send_command(
            connection,
            "switchport mode access"
        )

        send_command(
            connection,
            f"switchport access vlan {vlan_id}"
        )

        send_command(
            connection,
            "no shutdown"
        )

        send_command(
            connection,
            "exit"
        )

    if gateway:

        send_command(
            connection,
            f"ip default-gateway {gateway}"
        )


# ============================================================
# ROUTER
# ============================================================

def configure_router_management(
    connection,
    interfaces
):
    """
    Minimal IP-konfigurasjon på routerinterface.

    Flere interface kan legges inn fordi 4221 og 2901
    i topologien ligger mellom to management-nett.
    """

    print("\n" + "=" * 60)
    print(" KONFIGURERER MANAGEMENT-IP")
    print("=" * 60)

    for interface in interfaces:

        name = interface["name"]
        ip_address = interface["ip"]
        mask = interface["mask"]

        output = send_command(
            connection,
            f"interface {name}"
        )

        if has_error(output):
            raise RuntimeError(
                f"Interface {name} finnes ikke."
            )

        send_command(
            connection,
            f"ip address {ip_address} {mask}"
        )

        send_command(
            connection,
            "no shutdown"
        )

        send_command(
            connection,
            "exit"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 60)
    print(" NK2 - PYTHON SSH BOOTSTRAP")
    print("=" * 60)

    print(
        "\nDette scriptet gjør kun enheten klar "
        "for administrasjon over SSH."
    )

    print(
        "\nVelg Cisco-enhet:"
        "\n"
        "\n1 - Cisco ISR 4221"
        "\n2 - Cisco ISR 2901"
        "\n3 - Cisco Catalyst 3650"
        "\n4 - Cisco Catalyst 2960"
        "\n5 - Cisco Catalyst 1000 Series"
    )

    choice = input(
        "\nVelg [1/2/3/4/5]: "
    ).strip()

    # --------------------------------------------------------
    # ENHETSTYPE
    # --------------------------------------------------------

    if choice == "1":

        model = "Cisco ISR 4221"
        device_type = "router"
        default_hostname = "R4221"

    elif choice == "2":

        model = "Cisco ISR 2901"
        device_type = "router"
        default_hostname = "R2901"

    elif choice == "3":

        model = "Cisco Catalyst 3650"
        device_type = "switch"
        default_hostname = "SW3650"

    elif choice == "4":

        model = "Cisco Catalyst 2960"
        device_type = "switch"
        default_hostname = "SW2960"

    elif choice == "5":

        model = "Cisco Catalyst 1000"
        device_type = "switch"
        default_hostname = "SWC1000"

    else:

        print("\nUgyldig valg.")
        return

    # --------------------------------------------------------
    # COM
    # --------------------------------------------------------

    com_port = select_com_port()

    if com_port is None:
        return

    # --------------------------------------------------------
    # FELLES INPUT
    # --------------------------------------------------------

    hostname = input(
        f"\nHostname [{default_hostname}]: "
    ).strip() or default_hostname

    domain = input(
        "Domain name [lab.local]: "
    ).strip() or "lab.local"

    username = input(
        "SSH-brukernavn [admin]: "
    ).strip() or "admin"

    password = getpass.getpass(
        "SSH-passord: "
    )

    enable_secret = getpass.getpass(
        "Enable secret: "
    )

    # ========================================================
    # SWITCH
    # ========================================================

    if device_type == "switch":

        vlan_id = input(
            "\nManagement VLAN [99]: "
        ).strip() or "99"

        management_ip = input(
            "Management IP: "
        ).strip()

        subnet_mask = input(
            "Subnettmaske [255.255.255.0]: "
        ).strip() or "255.255.255.0"

        gateway = input(
            "Default gateway "
            "(Enter hvis ikke nødvendig): "
        ).strip()

        print(
            "\nOppgi bare portene som akkurat nå "
            "må være i management-nettet."
        )

        print(
            "Skill flere porter med komma."
        )

        print(
            "Eksempel: "
            "GigabitEthernet1/0/1,"
            "GigabitEthernet1/0/2"
        )

        ports_input = input(
            "\nManagement-porter: "
        ).strip()

        ports = [
            port.strip()
            for port in ports_input.split(",")
            if port.strip()
        ]

        if not ports:
            print(
                "\nMinst én port må oppgis."
            )
            return

        ssh_ip = management_ip

    # ========================================================
    # ROUTER
    # ========================================================

    else:

        try:

            interface_count = int(
                input(
                    "\nHvor mange router-interface "
                    "skal få management-IP? [1]: "
                ).strip() or "1"
            )

        except ValueError:

            print("\nUgyldig antall.")
            return

        interfaces = []

        for number in range(
            interface_count
        ):

            print(
                f"\nInterface {number + 1}:"
            )

            interface_name = input(
                "Interface-navn: "
            ).strip()

            ip_address = input(
                "IP-adresse: "
            ).strip()

            subnet_mask = input(
                "Subnettmaske [255.255.255.0]: "
            ).strip() or "255.255.255.0"

            interfaces.append(
                {
                    "name": interface_name,
                    "ip": ip_address,
                    "mask": subnet_mask
                }
            )

        ssh_ip = interfaces[0]["ip"]

    # ========================================================
    # OPPSUMMERING
    # ========================================================

    print("\n" + "=" * 60)
    print(" OPPSUMMERING")
    print("=" * 60)

    print(f"Modell:      {model}")
    print(f"COM-port:    {com_port}")
    print(f"Hostname:    {hostname}")
    print(f"SSH-bruker: {username}")

    if device_type == "switch":

        print(
            f"Management IP: {management_ip}"
        )

        print(
            f"Management VLAN: {vlan_id}"
        )

    else:

        for interface in interfaces:
            print(
                f"{interface['name']}: "
                f"{interface['ip']}"
            )

    confirm = input(
        "\nSkriv JA for å starte: "
    ).strip().lower()

    if confirm != "ja":
        print("\nAvbrutt.")
        return

    connection = None

    try:

        # ====================================================
        # ÅPNE CONSOLE
        # ====================================================

        connection = open_console(
            com_port
        )

        time.sleep(2)

        prepare_console(
            connection
        )

        # ====================================================
        # ENABLE
        # ====================================================

        enter_enable(
            connection
        )

        send_command(
            connection,
            "terminal length 0"
        )

        # ====================================================
        # CONFIG MODE
        # ====================================================

        output = send_command(
            connection,
            "configure terminal"
        )

        if has_error(output):
            raise RuntimeError(
                "Kunne ikke gå inn i configuration mode."
            )

        # ====================================================
        # HOSTNAME
        # ====================================================

        send_command(
            connection,
            f"hostname {hostname}"
        )

        # ====================================================
        # ENABLE SECRET
        # ====================================================

        send_command(
            connection,
            f"enable secret {enable_secret}",
            hide=True
        )

        # ====================================================
        # MINIMAL MANAGEMENT-IP
        # ====================================================

        if device_type == "switch":

            configure_switch_management(
                connection,
                vlan_id,
                management_ip,
                subnet_mask,
                gateway,
                ports
            )

        else:

            configure_router_management(
                connection,
                interfaces
            )

        # ====================================================
        # SSH
        # ====================================================

        configure_ssh(
            connection,
            domain,
            username,
            password
        )

        # ====================================================
        # LAGRE
        # ====================================================

        send_command(
            connection,
            "end"
        )

        send_command(
            connection,
            "write memory",
            wait=4
        )

        # ====================================================
        # ENKEL VERIFISERING
        # ====================================================

        print("\n" + "=" * 60)
        print(" VERIFISERING")
        print("=" * 60)

        send_command(
            connection,
            "show ip interface brief",
            wait=2
        )

        send_command(
            connection,
            "show ip ssh",
            wait=2
        )

        print("\n" + "=" * 60)
        print(" FERDIG")
        print("=" * 60)

        print(
            "\nEnheten skal nå være klar for SSH."
        )

        print(
            "\nTest fra management-PC:"
        )

        print(
            f"ping {ssh_ip}"
        )

        print(
            f"ssh {username}@{ssh_ip}"
        )

    # ========================================================
    # FEILHÅNDTERING
    # ========================================================

    except serial.SerialException as error:

        print("\n" + "=" * 60)
        print(" COM-FEIL")
        print("=" * 60)

        print(error)

        print(
            "\nKontroller at:"
            "\nPuTTY/Tera Term er helt lukket,"
            "\nconsolekabelen er koblet til,"
            "\nog ingen andre programmer bruker COM-porten."
        )

    except RuntimeError as error:

        print("\n" + "=" * 60)
        print(" KONFIGURASJONSFEIL")
        print("=" * 60)

        print(error)

    except KeyboardInterrupt:

        print(
            "\n\nScriptet ble avbrutt."
        )

    except Exception as error:

        print(
            f"\nUventet feil: "
            f"{type(error).__name__}: {error}"
        )

    finally:

        if (
            connection is not None
            and connection.is_open
        ):

            connection.close()

            print(
                "\nConsole-forbindelsen er lukket."
            )


if __name__ == "__main__":
    main()