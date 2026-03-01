#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import signal
from datetime import datetime
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.log import setLogLevel

RATE_MBIT = 735
BURST = "1mbit"
TBF_LATENCY = "50ms"
NETEM_LIMIT = 10000

PARALLEL_FLOWS = 8      # TCP multi-flux
IPERF_TIME = 20         # secondes
PING_INTERVAL = 0.2     # ping toutes les 200ms
PING_TIME = IPERF_TIME + 2

class LanTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        r1 = self.addHost('r1')
        self.addLink(h1, r1, cls=TCLink)
        self.addLink(h2, r1, cls=TCLink)

def sh(node, cmd):
    return node.cmd(cmd)

def setup_ip(net):
    h1, h2, r1 = net.get('h1', 'h2', 'r1')

    sh(r1, "ip addr flush dev r1-eth0")
    sh(r1, "ip addr flush dev r1-eth1")
    sh(h1, "ip addr flush dev h1-eth0")
    sh(h2, "ip addr flush dev h2-eth0")

    sh(r1, "ip addr add 192.168.1.1/24 dev r1-eth0")
    sh(r1, "ip addr add 192.168.2.1/24 dev r1-eth1")
    sh(r1, "sysctl -w net.ipv4.ip_forward=1")

    sh(h1, "ip addr add 192.168.1.100/24 dev h1-eth0")
    sh(h1, "ip route replace default via 192.168.1.1")

    sh(h2, "ip addr add 192.168.2.100/24 dev h2-eth0")
    sh(h2, "ip route replace default via 192.168.2.1")

def tc_reset(r1, dev):
    sh(r1, f"tc qdisc del dev {dev} root 2>/dev/null || true")

def apply_stack(r1, dev, delay_ms, mode):
    """
    root tbf -> netem -> (pfifo ou fq_codel)
    """
    tc_reset(r1, dev)

    # Root TBF
    sh(r1,
       f"tc qdisc add dev {dev} root handle 1: "
       f"tbf rate {RATE_MBIT}mbit burst {BURST} latency {TBF_LATENCY}"
    )

    # Netem child
    sh(r1,
       f"tc qdisc add dev {dev} parent 1:1 handle 10: "
       f"netem delay {delay_ms}ms limit {NETEM_LIMIT}"
    )

    # Leaf qdisc
    if mode == "pfifo":
        sh(r1, f"tc qdisc add dev {dev} parent 10:1 handle 20: pfifo limit 10000")
    elif mode == "fq_codel":
        sh(r1,
           f"tc qdisc add dev {dev} parent 10:1 handle 20: "
           f"fq_codel limit 10240p flows 1024 target 5ms interval 100ms"
        )
    else:
        raise ValueError("mode must be 'pfifo' or 'fq_codel'")

def dump_tc(r1, dev, path):
    with open(path, "w") as f:
        f.write(sh(r1, f"tc -s qdisc show dev {dev}"))

def start_iperf_server(h2):
    sh(h2, "pkill -f 'iperf3 -s' 2>/dev/null || true")
    sh(h2, "iperf3 -s -D")

def stop_iperf_server(h2):
    sh(h2, "pkill -f 'iperf3 -s' 2>/dev/null || true")

def run_iperf_client_tcp(h1, dst_ip, out_path):
    cmd = f"iperf3 -c {dst_ip} -t {IPERF_TIME} -P {PARALLEL_FLOWS} -i 1 --get-server-output"
    out = sh(h1, cmd)
    with open(out_path, "w") as f:
        f.write(out)

def start_ping_bg(h1, dst_ip, out_path):
    # ping en background pendant la charge (timestamp intégré via -D si dispo; sinon on garde brut)
    # Busybox ping sur certains systèmes n’a pas -D; Mininet utilise ping iputils généralement.
    cmd = f"ping -i {PING_INTERVAL} -w {PING_TIME} {dst_ip} > {out_path} 2>&1 & echo $!"
    pid = sh(h1, cmd).strip()
    return pid

def stop_pid(h1, pid):
    if pid.isdigit():
        sh(h1, f"kill {pid} 2>/dev/null || true")

def run_scenario(delay_ms, mode):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = f"results_t4_tcp_{mode}_{PARALLEL_FLOWS}flows_{delay_ms}ms_{ts}"
    os.makedirs(outdir, exist_ok=True)

    net = Mininet(topo=LanTopo(), link=TCLink)
    net.start()

    h1, h2, r1 = net.get('h1', 'h2', 'r1')
    setup_ip(net)

    # Apply tc on router interfaces (bottleneck + delay)
    apply_stack(r1, "r1-eth0", delay_ms, mode)
    apply_stack(r1, "r1-eth1", delay_ms, mode)

    dump_tc(r1, "r1-eth1", os.path.join(outdir, "tc_before_r1-eth1.txt"))

    # Start iperf server
    start_iperf_server(h2)
    time.sleep(0.5)

    # Start ping in background (measure RTT under load)
    ping_path = os.path.join(outdir, "ping_under_load.txt")
    ping_pid = start_ping_bg(h1, "192.168.2.100", ping_path)

    # Run iperf client
    iperf_path = os.path.join(outdir, "iperf3_tcp_client.txt")
    run_iperf_client_tcp(h1, "192.168.2.100", iperf_path)

    # Stop ping if still running
    stop_pid(h1, ping_pid)
    time.sleep(0.2)

    # Stop server and dump tc after
    stop_iperf_server(h2)
    dump_tc(r1, "r1-eth1", os.path.join(outdir, "tc_after_r1-eth1.txt"))

    net.stop()
    print(f"[OK] Scénario terminé : {outdir}")

if __name__ == "__main__":
    setLogLevel("info")

    # 1.6 ms
    run_scenario(1.6, "pfifo")
    run_scenario(1.6, "fq_codel")

    # 50 ms
    run_scenario(50, "pfifo")
    run_scenario(50, "fq_codel")
