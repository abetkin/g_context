# coding: utf-8
from applets.base import GreenletWrapper
from applets import from_context, context
from applets.handles import stop_before, stop_after, resume, resume_all
from applets.util import case

class A:
    a = 1

    @GreenletWrapper
    def run(self):
        return B().run()


class B:

    @GreenletWrapper
    def run(self):
        return from_context('a')


o = A()
case.assertEqual(o.run(), 1)

with context({'a': 2}):
    case.assertEqual(B().run(), 2)
    case.assertEqual(A().run(), 1)


stop_after(A.run)
stop_before(B.run)

o = A()
o.run()
# case.assertEqual(resume(), 1)
# case.assertEqual(resume(), 1)
case.assertEqual(resume_all(), 1)
