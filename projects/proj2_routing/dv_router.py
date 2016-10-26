"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics

# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter(basics.DVRouterBase):
    # NO_LOG = True # Set to True on an instance to disable its logging
    # POISON_MODE = True # Can override POISON_MODE here
    # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.

        """
        self.start_timer()  # Starts calling handle_timer() at correct rate
        self.neighbors = {} # {port => node}
        self.ports = set()
        self.latencies = {} # {port => link_latency}
        self.routing_table = {} # {destination => {port => latency_cost, time}}

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.latencies[port] = latency
        self.ports.add(port)
        self.send_update()

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        del self.latencies[port]
        self.ports.remove(port)
        to_delete = []
        if port in self.neighbors:
            del self.neighbors[port]
        for destination, inside_dict in self.routing_table.items():
            if port in inside_dict.keys(): #if not POISON_MODE it will just expire on its own
                if self.POISON_MODE:
                    inside_dict[port] = (INFINITY + 1, api.current_time())  #route poisoning for whoever was using this route earlier
                else:
                    to_delete.append((port, destination))
        for port, destination in to_delete:
            del self.routing_table[destination][port]
            if len(self.routing_table[destination]) == 0:
                del self.routing_table[destination]


        # self.send_update()

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        #self.log("RX %s on %s (%s)", packet, port, api.current_time())
        if isinstance(packet, basics.RoutePacket):
            self.handle_update(packet, port, api.current_time())

        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.neighbors[port] = packet.src
            self.routing_table[packet.src] = {}
            self.routing_table[packet.src][port] = self.latencies[port], api.current_time()

        else: # Therefore it must be a forwarding packet
            # print(api.current_time())
            # print(self)
            # print(packet.dst)
            if packet.dst == self:
                return
            if packet.dst not in self.routing_table: #if we don't know where to forward
                return
            new_port, (distance, time) = min(self.routing_table[packet.dst].items(), key = lambda x: x[1][0])
            if self.routing_table[packet.dst][new_port][0] > INFINITY:
                return
            else:
                # print("woohooo")
                # print(new_port)
                # print(port)
                if new_port != port:
                    return self.send(packet, new_port, False)
        #send update to everyone

    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbors.  It
        also might not be a bad place to check for whether any entries
        have expired.

        """
        to_delete = []
        # print(api.current_time())
        for dest, inside_dict in self.routing_table.items():
            for port, (dist, time) in inside_dict.items():
                if api.current_time() - time >= self.ROUTE_TIMEOUT:
                    to_delete.append((dest, port))
        for dest, port in to_delete:
            if port not in self.neighbors:
                del self.routing_table[dest][port]
                if len(self.routing_table[dest]) == 0:
                    del self.routing_table[dest]
        # print(api.current_time())
        self.send_update()
        pass

    def send_update(self):
        for port in self.ports: #send update to all neighbors
            for dest in self.routing_table: #send update for all the destinations that I am aware of
                smallest_port, (smallest_latency, time) = min(self.routing_table[dest].items(), key = lambda x: x[1][0])

                if smallest_port == port: #and not (port in self.neighbors and dest == self.neighbors[port]): #same port not my neighboor though
                    # del self.routing_table[dest][smallest_port]
                    if self.POISON_MODE:
                        packet = basics.RoutePacket(dest, INFINITY + 1)
                        self.send(packet, port, False)
                    # elif len(self.routing_table[dest].items()) > 0:
                    #     new_smallest_port, (new_smallest_latency, new_time) = min(self.routing_table[dest].items(), key = lambda x: x[1][0])
                    #     packet = basics.RoutePacket(dest, new_smallest_latency) #send best latency for this destination
                    #     self.send(packet, port, False)
                    # self.routing_table[dest][smallest_port] = smallest_latency, time
                else:
                    packet = basics.RoutePacket(dest, smallest_latency) #send best latency for this destination
                    self.send(packet, port, False)
        # print("afer update")
        # print(self)
        # print(self.routing_table)
                # print("port of my neighboor " + str(port))
                # print("port of my neighboor " + str(smallest_port))


    def handle_update(self, packet, port, time):
        latency = packet.latency
        if packet.destination in self.routing_table.keys():
            self.routing_table[packet.destination][port] = latency + self.latencies[port], time
        else:
            self.routing_table[packet.destination] = {}
            self.routing_table[packet.destination][port] = latency + self.latencies[port], time
