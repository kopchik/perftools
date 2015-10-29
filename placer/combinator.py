#!/usr/bin/env python3

def rest(l, *exclude):
  return [e for e in l if e not in exclude]

def find_far(cpus, htmap):
  for cpu1 in cpus:
    for cpu2 in cpus:
      if cpu2 != cpu1 and cpu2 not in htmap[cpu1]:
        return (cpu1, cpu2), rest(cpus, cpu1, cpu2)
  return None, cpus


def find_near(cpus, htmap):
  for cpu1 in cpus:
    candidates = htmap[cpu1]
    for cpu2 in candidates:
      if cpu2 in cpus:
        return (cpu1, cpu2), rest(cpus, cpu1, cpu2)
  return None, cpus


def combinator(benches, cpus, htmap, r=[], d=1):
  if not benches:
    yield r
    return
  a,b, *benches = benches
  far, newcpus = find_far(cpus, htmap)
  if far:
    yield from combinator(benches, newcpus, htmap, r+list(zip(far, [a,b])),d+1)
  near, newcpus = find_near(cpus, htmap)
  if near:
    yield from combinator(benches, newcpus, htmap, r+list(zip(near, [a,b])), d+1)


if __name__ == '__main__':
  from perf.numa import topology
  for alloc in combinator("a b c d".split(), [0,1,2,3], topology.ht_map):
    print(alloc)

