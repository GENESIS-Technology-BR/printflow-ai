import socket


def discover():

    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    print(f"Computador: {hostname}")
    print(f"IP Local: {ip}")

    return [
        {
            "ip": "10.2.0.124",
            "name": "HP Laser MFP 432",
            "manufacturer": "HP",
            "model": "Laser MFP 432",
            "status": "online",
            "source": "agent",
            "page_count": None
        }
    ]
