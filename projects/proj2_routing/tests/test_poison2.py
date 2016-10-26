"""
test_poison2
Tests that the router performs route poisoning.

Creates a topology like the following:

h1 --s6-- s1 --c1--s4--s3-- h2
       \-- s2 --c2--s5--/

First send ping from h1 to h2, which should be received, then break the through
c1 which is the shorter path. then unlink s4 from s3 and send another ping from
h1 to h2 which should propogate through the second path. Then unlink both paths
but don't wait long enough for routes to time out, and send another ping from h1
to h2, which should be dropped.

"""

import sim
import sim.api as api
import sim.basics as basics
import sys

from tests.test_simple import GetPacketHost, NoPacketHost
from tests.test_link_weights import CountingHub


def launch():
    h1 = NoPacketHost.create('h1')
    h2 = GetPacketHost.create('h2')
    s1 = sim.config.default_switch_type.create('s1')
    s2 = sim.config.default_switch_type.create('s2')
    s3 = sim.config.default_switch_type.create('s3')
    s4 = sim.config.default_switch_type.create('s4')
    s5 = sim.config.default_switch_type.create('s5')
    s6 = sim.config.default_switch_type.create('s6')
    c1 = CountingHub.create('c1')
    c2 = CountingHub.create('c2')
    h1.linkTo(s6, latency=1)
    s6.linkTo(s1, latency=1)
    s6.linkTo(s2, latency=2)
    s1.linkTo(c1, latency=1)
    s2.linkTo(c2, latency=3)
    c1.linkTo(s4, latency=1)
    c2.linkTo(s5, latency=1)
    s4.linkTo(s3, latency=1)
    s5.linkTo(s3, latency=1)
    s3.linkTo(h2, latency=1)

    def test_tasklet():
        yield 25

        api.userlog.debug('Sending ping from h1 to h2 - it should get through')
        h1.ping(h2)

        yield 20

        if c1.pings != 1:
            api.userlog.error(str(c1.pings)+" first ping not received through c1  "+str(c2.pings))
            sys.exit(1)

        api.userlog.debug('Disconnecting s1 path')
        s4.unlinkTo(s3)


        yield 15

        api.userlog.debug('Sending ping from h1 to h2 again - it should get through')
        h1.ping(h2)

        yield 10

        if c2.pings != 1:
            api.userlog.error("The second ping didn't get through from s2")
            sys.exit(1)

        api.userlog.debug('Disconnecting both paths')
        s5.unlinkTo(s3)




        api.userlog.debug(
            'Waiting for poison to propagate, but not long enough ' +
            'for routes to time out')
        yield 10

        api.userlog.debug(
            'Sending ping from h1 to h2 - it should be dropped at s1')
        h1.ping(h2)

        yield 5

        if c1.pings != 1 or c2.pings != 1:
            api.userlog.error(
                'h1 forwarded the ping when it should have dropped it')
            sys.exit(1)
        else:
            api.userlog.debug('h1 dropped the ping as expected')
            sys.exit(0)

    api.run_tasklet(test_tasklet)
