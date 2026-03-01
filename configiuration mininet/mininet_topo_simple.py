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
        

        self.addLink(h1, r1, cls=TCLink, bw=735, delay='0.4ms')
        
        self.addLink(h2, r1, cls=TCLink, bw=735, delay='0.4ms')

def run():
    net = Mininet(topo=LanTopo(), controller=OVSController, link=TCLink)
    net.start()
    
    h1, h2, r1 = net.get('h1', 'h2', 'r1')
    
    
    r1.cmd("ifconfig r1-eth0 192.168.1.1/24") 
    r1.cmd("ifconfig r1-eth1 192.168.2.1/24") 
    

    r1.cmd("sysctl -w net.ipv4.ip_forward=1")
    
    
    h1.cmd("ifconfig h1-eth0 192.168.1.100/24")
    h1.cmd("route add default gw 192.168.1.1")
    
    h2.cmd("ifconfig h2-eth0 192.168.2.100/24")
    h2.cmd("route add default gw 192.168.2.1")
    

    h1.cmd("route add -net 192.168.2.0/24 gw 192.168.1.1")#ip route  
    h2.cmd("route add -net 192.168.1.0/24 gw 192.168.2.1")
    CLI(net)
  
    #print("\n=== Test Ping ===")
    #print(h1.cmd("ping -c 10 192.168.2.100"))
    
    #print("\n=== Test iperf3 ===")
    #h2.cmd("iperf3 -s -D")  # -D pour exécuter en arrière-plan
    #print(h1.cmd("iperf3 -c 192.168.2.100 -t 10"))
    
    #h2.cmd("pkill iperf3")
    
    #print("\n=== Test HTTP avec ApacheBench ===")
    #h2.cmd("pkill -f http.server") nginx 
    #h2.cmd("nohup python3 -m http.server 8080 &")

    #result_ab = h1.cmd("ab -n 1000 -c 50 http://192.168.2.100:8080/")
    #print(result_ab)
    #h2.cmd("pkill -f http.server")
    
    
    net.stop()

if __name__ == '__main__':
    setLogLevel('debug')
    run()
