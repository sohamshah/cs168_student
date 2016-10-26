"""
test_split_horizon
Tests that the router performs route poisoning.

Creates a topology like the following:

h1 --s1--c1 -- s2
     |        |
     s4         c2-- s3 --h2

First send a ping from h1 to h2, it should propogate through s2. then remove
the link between c2->s3 and try sending a ping again from h1 to h2. the packet
should be dropped since s1 will not be advertising its distance to s3 at all when
sending its vector to s2. So s2's route to s3 should eventually just expire, as
under the rules of simple split horizon.

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

    c1 = CountingHub.create('c1')
    c2 = CountingHub.create('c2')
    h1.linkTo(s1, latency=1)
    s1.linkTo(s4, latency=1)
    s1.linkTo(c1, latency=1)
    s2.linkTo(c2, latency=1)
    c1.linkTo(s2, latency=1)
    c2.linkTo(s3, latency=1)
    s3.linkTo(h2, latency=1)

    def test_tasklet():
        yield 15

        api.userlog.debug('Sending ping from h1 to h2 - it should get through')
        h1.ping(h2)

        yield 7

        if c1.pings != 1 and c2.pings != 1:
            api.userlog.error(str(c1.pings)+" first ping not received through c1  "+str(c2.pings))
            sys.exit(1)

        api.userlog.debug('Disconnecting s2 path')
        s2.unlinkTo(c2)


        yield 15

        api.userlog.debug('Waiting for route to expire')
        h1.ping(h2)

        yield 15


        if c2.pings != 1:
            api.userlog.error(
                'h1 forwarded the ping when it should have dropped it')
            sys.exit(1)
        else:
            api.userlog.debug('h1 dropped the ping as expected')
            sys.exit(0)

    api.run_tasklet(test_tasklet)
