import socket
import struct
import time
import hashlib
import sys

HOST = '127.0.0.1'
PORT = 5001
BUFFER_SIZE = 1024
ALPHA = 0.125
BETA = 0.25
DATA_PAYLOAD = b'x' * 512  # exemplo de carga útil (ajustável)

def make_packet(seq_num, data):
    checksum = hashlib.md5(data).hexdigest()
    header = struct.pack('!I', seq_num) + checksum.encode()
    return header + data

def log_event(event, details):
    print(f"[{time.strftime('%H:%M:%S')}] {event}: {details}")

def estimate_timeout(sample_rtt, estimated_rtt, dev_rtt):
    if estimated_rtt is None:
        estimated_rtt = sample_rtt
        dev_rtt = sample_rtt / 2
    else:
        estimated_rtt = (1 - ALPHA) * estimated_rtt + ALPHA * sample_rtt
        dev_rtt = (1 - BETA) * dev_rtt + BETA * abs(sample_rtt - estimated_rtt)
    return estimated_rtt, dev_rtt, estimated_rtt + 4 * dev_rtt

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(1.0)  # valor inicial, será ajustado
    server_addr = (HOST, PORT)

    seq_num = 0
    estimated_rtt = None
    dev_rtt = None
    retries = 0
    max_retries = 10

    total_bytes = 0
    start_time = time.time()

    while True:
        packet = make_packet(seq_num, DATA_PAYLOAD)
        sent_time = time.time()
        client_socket.sendto(packet, server_addr)
        log_event("Packet Sent", f"Seq={seq_num}, Size={len(packet)} bytes")

        try:
            ack_packet, _ = client_socket.recvfrom(4)
            rtt = time.time() - sent_time
            rtt = max(rtt, 0.001)  # garante um RTT mínimo de 1ms
            ack_seq = struct.unpack('!I', ack_packet)[0]

            if ack_seq == seq_num:
                log_event("ACK Received", f"ACK={ack_seq}")
                total_bytes += len(DATA_PAYLOAD)

                estimated_rtt, dev_rtt, timeout = estimate_timeout(rtt, estimated_rtt, dev_rtt)
                timeout = max(timeout, 0.05)  # define um timeout mínimo de 50ms
                client_socket.settimeout(timeout)
                log_event("RTT Update", f"RTT={rtt:.3f}s, Timeout={timeout:.3f}s")

                seq_num = 1 - seq_num
                retries = 0

                time.sleep(0.01)  # controle de envio

            else:
                log_event("Unexpected ACK", f"ACK={ack_seq}, Expected={seq_num}")

        except socket.timeout:
            log_event("Timeout", f"Retransmitting Seq={seq_num}")
            retries += 1
            if retries > max_retries:
                log_event("Abort", "Max retries reached")
                break

        except KeyboardInterrupt:
            log_event("Client Shutdown", "User interruption")
            break

        elapsed_time = time.time() - start_time
        if elapsed_time > 0:
            throughput = (total_bytes * 8) / (elapsed_time * 1_000_000)
            log_event("Throughput", f"{throughput:.2f} Mbps")

    client_socket.close()
    log_event("Client Closed", "Socket closed")

if __name__ == "__main__":
    main()
