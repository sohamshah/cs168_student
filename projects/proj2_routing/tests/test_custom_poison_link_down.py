"""
A simple test to test when a link goes down and route poisoning

H1 -- r1 -- C1 -- r2 -- r3 -- H2
        \_______________/
            ^ link goes down later
"""

import sim
import sim.api as api
import sim.basics as basics

class RouteCheckCountingHub(api.Entity):
    pings = 0
    route_packets = []

    def handle_rx(self, packet, in_port):
        self.send(packet, in_port, flood=True)
        if isinstance(packet, basics.Ping):
            api.userlog.debug('%s saw a ping' % (self.name, ))
            self.pings += 1
        if isinstance(packet, basics.RoutePacket):
            self.route_packets.append((packet, api.current_time()))

    def reset_route_packets(self):
        self.route_packets = []


class GetPacketHost(basics.BasicHost):
    """A host that expects to see a ping."""
    pings = 0

    def handle_rx(self, packet, port):
        if isinstance(packet, basics.Ping):
            self.pings += 1


def launch():
    h1 = GetPacketHost.create("h1")
    h2 = GetPacketHost.create("h2")

    r1 = sim.config.default_switch_type.create("r1")
    r2 = sim.config.default_switch_type.create("r2")
    r3 = sim.config.default_switch_type.create("r3")

    RouteCheckCountingHub.create('c1')

    r1.POISON_MODE = True
    r2.POISON_MODE = True

    r1.linkTo(h1, latency=1)
    r1.linkTo(c1, latency=1)
    c1.linkTo(r2, latency=0)
    r2.linkTo(r3, latency=1)
    r1.linkTo(r3, latency=1)
    r3.linkTo(h2, latency=1)

    def test_tasklet():
        yield 5  # Wait five seconds for routing to converge

        api.userlog.debug("Sending test pings")
        h1.ping(h2)

        yield 1  # Wait a bit before sending last ping

        h2.ping(h1)

        yield 5  # Wait five seconds for pings to be delivered

        # Make sure h1 and h2 both get pinged once and c1 gets no pings since
        # no packets should have traveled through it
        good = True
        if h1.pings != 1:
            api.userlog.error("h1 got %s packets instead of 1", h1.pings)
            good = False
        if h2.pings != 1:
            api.userlog.error("h2 got %s packets instead of 1", h2.pings)
            good = False
        # Test to see if route doesn't go through c1
        if c1.pings != 0:
            api.userlog.error("c1 got %s packets instead of 0", c1.pings)
            good = False

        # Break link at time = 11
        r1.unlinkTo(r3)

        yield 1

        # Start tracking route packets that go to c1 a second after the link has been broken
        # so a new RoutePacket has time to get to c1

        c1.reset_route_packets()

        yield 5

        h1.ping(h2)

        yield 1

        # h2 shouldn't have received its second ping by now
        if h2.pings != 1:
            api.userlog.error("h2 got %s packets instead of 1", h2.pings)
            good = False

        yield 4

        # h2 should have received its second ping by now
        if h2.pings != 2:
            api.userlog.error("h2 got %s packets instead of 2", h2.pings)
            good = False
        # Test to see that route now goes through c1 since link between r1 and r2 went down
        if c1.pings != 1:
            api.userlog.error("c1 got %s packets instead of 0", c1.pings)
            good = False

        # Check to see that RoutePackets with destination = h2 that c1 receives should only have latency 16
        # since r1 should be poisoning c1 and latency 2 from r2 (which is latency 2 from h2)
        for packet, time in c1.route_packets:
            if packet.destination == h2 and not (packet.latency == 2 or packet.latency == 16): #infinity
                api.userlog.error("c1 got a RoutePacket to %s with latency %s at time %d", packet.destination, packet.latency, time)
                good = False
            else:
                api.userlog.debug("c1 got a RoutePacket to %s with latency %s at time %d", packet.destination, packet.latency, time)

        if good:
            api.userlog.debug("Test passed successfully!")

        # End the simulation and (if not running in interactive mode) exit.
        import sys
        sys.exit(0 if good else 1)

    api.run_tasklet(test_tasklet)
