"""INTERNAL/AI_AUTHORED: closed structural-count polynomial and moment sharpness.
Abstract finite words of length five, with nonempty quotient fibers.
Expansion of the V3.8.15 partition-lattice expression yields G and L below.
A counts fine graph cycle rank one; G and L count rank gain and loss.
After five power sums are available, evaluation needs fixed arithmetic work
(excluding integer bit complexity). This is not a measured runtime claim.
"""
from math import comb
import unittest
from moment_quotient_count_v3815 import counts as moment_counts, integer_partitions, moments
from nonuniform_quotient_count_v3814 import counts as subset_counts


def closed(s):
    n,b,c,d,e=s
    a=3*n**4-11*n**3+12*n*n-4*n
    loss=-8*n**3+8*n*n*b+12*n*n-9*n*b-4*n*c-4*n+b*b+6*c-2*d
    gain=(-3*n**4+3*n**3*b+3*n**3+8*n*n*b-7*n*n*c-4*n*b*b
          -9*n*b-4*n*c+9*n*d+b*b+3*b*c+6*c-2*d-4*e)
    return n**5-a-gain,gain,loss,a-loss


def witness():
    return tuple(tuple(i+1 for i in range(6) if i%2==p
                       for _ in range(comb(5,i))) for p in (0,1))


class Tests(unittest.TestCase):
    def test_partitions(self):
        k=0
        for n in range(1,13):
            for f in integer_partitions(n):
                self.assertEqual(closed(moments(f)),moment_counts(f))
                self.assertEqual(closed(moments(f)),subset_counts(f))
                k+=1
        self.assertEqual(k,271)

    def test_sharpness(self):
        a,b=witness()
        x,y=moments(a),moments(b)
        self.assertEqual(x[:4],y[:4])
        self.assertEqual(y[4]-x[4],120)
        for f in (a,b):
            self.assertEqual(closed(moments(f)),subset_counts(f))
        self.assertEqual(tuple(v-u for u,v in zip(closed(x),closed(y))),
                         (480,-480,0,0))

    def test_edges(self):
        for f in ((1,),(1,)*100,(1000,), (1,2,3,100,1000)*10,(2,)*5):
            self.assertEqual(closed(moments(f)),subset_counts(f))


if __name__=='__main__':
    unittest.main()
