import socket
import struct
import random
import time
import hashlib

from utils import make_packet, unpack_packet, is_corrupted, simulate_loss, simulate_corruption, RDTPacket


HOST = '127.0.0.1'
PORT = 5001
BUFFER_SIZE = 1024
LOSS_PROB = 0.1
CORRUPTION_PROB = 0.1
ALPHA = 0.125
BETA = 0.25

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
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    log_event("Server Started", f"Listening on {HOST}:{PORT}")

    expected_seq_num = 0
    estimated_rtt = None
    dev_rtt = None
    total_bytes = 0
    start_time = time.time()

    while True:
        try:
            packet, client_addr = server_socket.recvfrom(BUFFER_SIZE)
            received_time = time.time()
            log_event("Packet Received", f"From {client_addr}, Size={len(packet)} bytes")

            if simulate_loss():
                log_event("Packet Loss", "Simulated packet loss")
                continue

            pkt = unpack_packet(packet)
            if pkt is None:
                log_event("Invalid Packet", "Failed to unpack packet")
                continue

            corrupted = simulate_corruption()
            if corrupted or is_corrupted(pkt):
                log_event("Packet Corrupted", f"Seq={pkt.seq_num}, Discarded")
                continue

            if pkt.seq_num == expected_seq_num:
                log_event("Packet Delivered", f"Seq={pkt.seq_num}, Data={len(pkt.data)} bytes")
                total_bytes += len(pkt.data)

                ack_packet = struct.pack('!I', pkt.seq_num)
                server_socket.sendto(ack_packet, client_addr)
                log_event("ACK Sent", f"ACK={pkt.seq_num}")

                expected_seq_num = 1 - expected_seq_num

                sample_rtt = 0.1
                estimated_rtt, dev_rtt, timeout = estimate_timeout(sample_rtt, estimated_rtt, dev_rtt)
                log_event("RTT Update", f"Estimated RTT={estimated_rtt:.3f}s, Timeout={timeout:.3f}s")

            else:
                log_event("Duplicate/Out-of-Order Packet", f"Seq={pkt.seq_num}, Expected={expected_seq_num}")
                ack_packet = struct.pack('!I', 1 - expected_seq_num)
                server_socket.sendto(ack_packet, client_addr)
                log_event("ACK Sent", f"ACK={1 - expected_seq_num}")

            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                throughput = (total_bytes * 8) / (elapsed_time * 1_000_000)
                log_event("Throughput", f"{throughput:.2f} Mbps")

        except KeyboardInterrupt:
            log_event("Server Shutdown", "Stopping server")
            break
        except Exception as e:
            log_event("Error", str(e))

    server_socket.close()
    log_event("Server Closed", "Socket closed")

if __name__ == "__main__":
    main()