from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.node import OVSController
from mininet.cli import CLI

class LanTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        r1 = self.addHost('r1')

        # Lien sans paramètres — tout sera fait avec tc
        self.addLink(h1, r1, cls=TCLink)
        self.addLink(h2, r1, cls=TCLink)

def run():
    net = Mininet(topo=LanTopo(), controller=OVSController, link=TCLink)
    net.start()

    h1, h2, r1 = net.get('h1', 'h2', 'r1')

    # -----------------------------
    # CONFIG IP
    # -----------------------------
    r1.cmd("ifconfig r1-eth0 192.168.1.1/24")
    r1.cmd("ifconfig r1-eth1 192.168.2.1/24")
    r1.cmd("sysctl -w net.ipv4.ip_forward=1")

    h1.cmd("ifconfig h1-eth0 192.168.1.100/24")
    h1.cmd("route add default gw 192.168.1.1")

    h2.cmd("ifconfig h2-eth0 192.168.2.100/24")
    h2.cmd("route add default gw 192.168.2.1")

    h1.cmd("route add -net 192.168.2.0/24 gw 192.168.1.1")
    h2.cmd("route add -net 192.168.1.0/24 gw 192.168.2.1")

    # -----------------------------
    # TC : CONFIGURATION DES LIENS
    # -----------------------------

    # h1 <-> r1
    r1.cmd("tc qdisc add dev r1-eth0 root handle 1: netem delay 1ms 0.4ms")
    r1.cmd("tc qdisc add dev r1-eth0 parent 1: tbf rate 600mbit burst 1mbit latency 50ms")

    h1.cmd("tc qdisc add dev h1-eth0 root handle 1: netem delay 1ms 0.4ms")
    h1.cmd("tc qdisc add dev h1-eth0 parent 1: tbf rate 600mbit burst 1mbit latency 50ms")

    # h2 <-> r1
    r1.cmd("tc qdisc add dev r1-eth1 root handle 1: netem delay 1ms 0.4ms")
    r1.cmd("tc qdisc add dev r1-eth1 parent 1: tbf rate 600mbit burst 1mbit latency 50ms")

    h2.cmd("tc qdisc add dev h2-eth0 root handle 1: netem delay 1ms 0.4ms")
    h2.cmd("tc qdisc add dev h2-eth0 parent 1: tbf rate 600mbit burst 1mbit latency 50ms")

    
    CLI(net)

    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

