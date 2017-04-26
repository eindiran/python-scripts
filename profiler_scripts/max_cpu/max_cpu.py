#!/usr/bin/env python
## Maxes out CPU utilization on all cores without using a singnificant memory footprint
import random
from joblib import Parallel, delayed
import numpy as np

def testfunc(junkint):
    while True:
        l = random.choice([0, 1, 2, 3, 4])

def run(niter=10):
    data = (np.random.randn(2,100) for ii in range(niter))
    pool = Parallel(n_jobs=-1,verbose=1,pre_dispatch='all')
    results = pool(delayed(testfunc)(dd) for dd in data)

# Begin main script execution
if __name__ == "__main__":
    run()
# DONE
