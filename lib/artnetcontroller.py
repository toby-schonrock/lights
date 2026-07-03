import socket
import time

"""Low level art net controller"""


class ArtNetController:
    ARTNET_PORT = 6454

    def __init__(self, target_ip, subnet=0, universe=0, net=0):
        self.target_ip = target_ip
        self.subnet = subnet
        self.universe = universe
        self.net = net

        self.sequence_counter = 1
        self.sock = None
        self.buffer = [0] * 512

        self.__connect()

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

    def flush_buffer(self):
        packet_bytes = self._build_art_dmx(self.buffer)

        self.sock.sendto(packet_bytes, (self.target_ip, self.ARTNET_PORT))

        self.sequence_counter = 1 if self.sequence_counter >= 255 else self.sequence_counter + 1

    def set_buffer(self, dmx_data, flush: bool = False):
        """
        Sets the buffer (an array of up to 512 integers (0-255))
        Note channel 1 is at position 0
        If flush is enabled sends the data to the controller
        """
        # Ensure data is a list or bytes object
        dmx_list = list(dmx_data)

        # Enforce exact 512-byte constraint bounds
        if len(dmx_list) != 512:
            raise RuntimeError("Dmx buffer should have length 512")

        # Clamp individual channel integer values strictly between 0 and 255
        dmx_list = [max(0, min(255, int(val))) for val in dmx_list]

        self.buffer = dmx_list

        if flush:
            self.flush_buffer()

    def set_channel(self, channel: int, value: int, flush: bool = False):
        """
        In the buffer sets the channel = value.
        Note these are DMX channel numbers so 1 - 512 not 0 - 511.
        If flush is enabled sends the resulting buffer to the controller immediately
        """
        if channel < 1 or channel > 512:
            raise ValueError(f"Invalid rchannel number {channel}")

        self.buffer[channel - 1] = max(0, min(255, int(value)))

        if flush:
            self.flush_buffer()

    def set_RGB(self, rchannel: int, r: int, g: int, b: int, flush: bool = False):
        """
        In the buffer sets the rchannel = r, rchannel + 1 = g and rchannel + 2 = b.
        Note these are DMX channel numbers so 1 - 512 not 0 - 511.
        If flush is enabled sends the resulting buffer to the controller immediately
        """
        if rchannel < 1 or rchannel > 512 - 2:
            raise ValueError(f"Invalid rchannel number {rchannel}")

        base_idx = rchannel - 1

        self.buffer[base_idx] = max(0, min(255, int(r)))
        self.buffer[base_idx + 1] = max(0, min(255, int(g)))
        self.buffer[base_idx + 2] = max(0, min(255, int(b)))

        if flush:
            self.flush_buffer()

    def close(self):
        """Cleanly releases bound networking interfaces."""
        if self.sock:
            self.sock.close()
            print("[*] Art-Net socket interface closed safely.")
