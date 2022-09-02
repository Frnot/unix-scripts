#v0.1

import re
from shutil import which
import subprocess

try:
    import segno
except ModuleNotFoundError:
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "segno"])
    import segno


server_address = ""
server_pubkey = ""

tunnel_ipv6_net = "fdff::/64"
tunnel_ipv4_net = "10.0.255.0/24"
dns = ["fddd::1", "10.0.221.1"]

routed_nets = [""]

def main():
    # Check that required program exists
    if which("wg") is None:
        print("Error: command 'wg' is not found. Is wireguard installed?")
        exit(1)

    index = None
    while not index:
        inp = input("Enter client index: ")
        try:
            index = int(inp)
        except:
            print("Please enter a number")


    ipv4_re = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}(\/\d{1,2})$")
    if ipv4_re.match(tunnel_ipv4_net):
        ipv4_address = ipv4_re.sub(fr"\g<1>{index}\g<2>", tunnel_ipv4_net)
        ipv4_address_uni = ipv4_re.sub(fr"\g<1>{index}\\32", tunnel_ipv4_net)
    else:
        print("Invalid IPv4 network address")
        exit(1)
    
    ipv6_re = re.compile(r"([a-f0-9:]+:)\d*(/\d{1,2})")
    if ipv6_re.match(tunnel_ipv6_net):
        ipv6_address = ipv6_re.sub(fr"\g<1>{index}\g<2>", tunnel_ipv6_net)
        ipv6_address_uni = ipv6_re.sub(fr"\g<1>{index}\\128", tunnel_ipv6_net)
    else:
        print("Invalid IPv6 network address")
        exit(1)
    

    public_key, private_key, psk = generate_keyset()

    client_conf = build_client_config(ipv6_address, ipv4_address, dns, routed_nets, server_address, private_key, psk, server_pubkey)
    server_entry = build_server_config(ipv6_address_uni, ipv4_address_uni, psk, public_key)

    print("Client config QR code:")
    stringy = segno.make(client_conf)
    stringy.terminal(compact=True)

    print("Add this to server config:")
    print(server_entry)

    input("Press any key to exit")


def generate_keyset():
    private_key = execute("wg genkey")

    # TODO: check if works on both windows and linux
    public_key = execute("wg pubkey", input=private_key)

    psk = execute("wg genpsk")

    return (public_key, private_key, psk)


def build_client_config(ipv6_addr, ipv4_addr, dns, routed_nets, server_addr, privatekey, psk, server_pubkey):
    config = "[Interface]\n"
    config += f"Address = {', '.join([ip for ip in [ipv6_addr, ipv4_addr] if ip])}\n"
    config += f"DNS = {', '.join(dns)}\n"
    config += f"PrivateKey = {privatekey}\n"
    config += "\n[Peer]\n"
    config += f"AllowedIPs = {', '.join(routed_nets)}\n"
    config += f"Endpoint = {server_addr}\n"
    config += f"PreSharedKey = {psk}\n"
    config += f"PublicKey = {server_pubkey}\n"
    return config


def build_server_config(ipv6_addr, ipv4_addr, psk, pubkey):
    config = "[Peer]\n"
    config += f"PublicKey = {pubkey}\n"
    config += f"PreSharedKey = {psk}\n"
    config += f"AllowedIPs = {', '.join([ip for ip in [ipv6_addr, ipv4_addr] if ip])}\n"
    return config


def execute(command, input=None, return_rc=False):
    cmdarr = command.split()
    result = subprocess.run(cmdarr, input=input, text=True, capture_output=True)

    if return_rc:
        return result.returncode
    else:
        return result.stdout.strip()

main()
