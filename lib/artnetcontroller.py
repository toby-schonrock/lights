import socket
import time


class ArtNetController:
    """Low level art net controller"""

    ARTNET_PORT = 6454

    def __init__(self, target_ip, subnet=0, universe=0, net=0):
        self.target_ip = target_ip
        self.subnet = subnet
        self.universe = universe
        self.net = net

        self.sequence_counter = 1
        self.sock = None

        if not self.__connect():
            raise ConnectionError(f"Failed to connect to {target_ip}")

    def _build_art_poll(self):
        """Constructs an ArtPoll packet (OpCode 0x2000), used as "ping" for artnet"""
        packet = bytearray()
        packet.extend(b'Art-Net\x00')  # ID String
        packet.append(0x00)            # OpCode Low (0x2000)
        packet.append(0x20)            # OpCode High
        packet.append(0x00)            # ProtVer High
        packet.append(0x0E)            # ProtVer Low (Version 14)
        # TalkToMe (Bit 1 set: reply via Unicast)
        packet.append(0x02)
        packet.append(0x00)            # Diagnostics Priority
        return bytes(packet)

    def _build_art_dmx(self, dmx_data):
        """Constructs a standard 530-byte ArtDmx payload frame."""
        header = bytearray()
        header.extend(b'Art-Net\x00')
        header.append(0x00)                     # OpCode Low (0x5000)
        header.append(0x50)                     # OpCode High
        header.append(0x00)                     # ProtVer High
        header.append(0x0E)                     # ProtVer Low
        header.append(self.sequence_counter & 0xFF)
        header.append(0x00)                     # Physical Input Port

        # SubUni computation
        sub_uni_byte = ((self.subnet & 0x0F) << 4) | (self.universe & 0x0F)
        header.append(sub_uni_byte)
        header.append(self.net & 0x7F)          # Net

        # Fixed Universe Length (512 channels = 0x0200)
        header.append(0x02)
        header.append(0x00)

        return header + bytes(dmx_data)

    def __connect(self):
        """
        Initializes the network socket, binds locally to port 6454,
        and runs a handshake verification against the target device.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # Force compliance: Source port must be 6454
            self.sock.bind(("0.0.0.0", self.ARTNET_PORT))
        except PermissionError:
            print(
                f"[ERROR] Port {self.ARTNET_PORT} is locked. Ensure other lighting apps are shut down.")
            return False

        self.sock.settimeout(2.0)
        print("Socket setup")
        print(f"Sending ArtPoll Handshake to {self.target_ip}...")

        try:
            poll_packet = self._build_art_poll()

            responseTime = time.time_ns()
            self.sock.sendto(poll_packet, (self.target_ip, self.ARTNET_PORT))

            data, addr = self.sock.recvfrom(1024)
            responseTime = (time.time_ns() - responseTime) / 1000000
            # ns / 10^6 = ms
            if len(data) >= 10 and data[0:8] == b'Art-Net\x00':
                opcode = (data[9] << 8) | data[8]
                if opcode == 0x2100:  # ArtPollReply
                    short_name = data[26:44].split(
                        b'\x00')[0].decode('ascii', errors='replace')
                    long_name = data[44:108].split(
                        b'\x00')[0].decode('ascii', errors='replace')
                    print("[SUCCESS] Handshake acknowledged by controller!")
                    print(f"    Device Name : {short_name} ({long_name})")
                    print(f"    Response Time : {responseTime}ms")

                    # Connection established, strip timeout bounds for stable execution streaming
                    self.sock.settimeout(None)
                    return True

        except socket.timeout:
            print(
                "[WARNING] Handshake timed out. No response from hardware application layer.")
            print("          Defaulting to blind transmission mode...")
            self.sock.settimeout(None)
            return True
        except Exception as e:
            print(f"[ERROR] Network initialization failed: {e}")
            return False

    def send_packet(self, channel_values: list[int]):
        """
        Sends the channels values via Artnet to the device.
        Warning these values are unchecked!!!
        It is up to you to ensure these are 512 int values between 0-255
        """
        packet_bytes = self._build_art_dmx(channel_values)

        self.sock.sendto(packet_bytes, (self.target_ip, self.ARTNET_PORT))

        self.sequence_counter = 1 if self.sequence_counter >= 255 else self.sequence_counter + 1

    def close(self):
        """Cleanly releases bound networking interfaces."""
        if self.sock:
            self.sock.close()
            print("[*] Art-Net socket interface closed safely.")
