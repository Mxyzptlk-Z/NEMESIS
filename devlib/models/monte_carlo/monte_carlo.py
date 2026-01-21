"""
This module creates Monte Carlo engines, which can then
be used to calculate option price and Greek letters.

The engine implements *vectorization*, which significantly
boost algorithm speed."""


import numpy as np
import multiprocessing as mp
from joblib import Parallel, delayed
from joblib import wrap_non_picklable_objects



__docformat__ = "restructuredtext en"

__all__ = ['MonteCarlo']


class MonteCarlo:
    """A Monte Carlo engine for valuing path-dependent options.


    Parameters regarding the simulation are specified here. This engine implements
    vectorization, which significantly enhances algorithm speed.


    :param int batch_size: An integer telling the engine how many paths should
        be generated in each iteration.
    :param int num_iter: Number of iterations. The product of *batch_size* and
        *num_iter* is the total number of paths generated."""


    def __init__(self, batch_size: int, num_iter: int):
        self.batch_size = batch_size
        self.num_iter = num_iter
        self.most_recent_entropy = None


    @staticmethod
    def generate_eps(seed, shape):
        """Draw a random matrix from the standard normal distribution.


        :param seed: Seed of the random number generator.
        :param shape: Shape of the random matrix to generate.
        :return: A matrix of random numbers drawn from the standard normal
            distribution.

        :type seed: int or numpy.random.SeedSequence
        :type shape: tuple[int]"""

        rng = np.random.default_rng(seed)
        eps = rng.normal(0, 1, shape)
        eps = np.concatenate([eps, -eps])
        
        return eps


    def calc(self, option, spot, process, n_knot, is_other_ouput=False, 
             entropy=None, parallel_method='loky', n_jobs=-1, time_out=100):
        """Calculates the requested values of the option.


        :param option: An instance of option(without QuantLib).
        :param process: Used for generating paths and calculating pv.
        :param n_knot: Random numbers count of one path
        :param other_ouput: Some other calculation ouput if useful, calculated by option itself.
        :param entropy: Entropy used to generate random numbers.
        :param parallel_method: One param used in parallel calculation.
        :param n_jobs: One param used in parallel calculation.
        :return: The Monte Carlo result of present value or a dict containing PV and Greek letters.
        
        :type entropy: int"""
        
        n_sim, n_iter = self.batch_size, self.num_iter
        n_sim = int(n_sim / 2)
        
        if n_iter > 1:
            @delayed
            @wrap_non_picklable_objects
            def _calc(seed):
                eps = self.generate_eps(seed, (n_sim, n_knot))
                paths = option.paths_given_eps(spot, process, eps)
                #path 2-D (n_sim * 2, len(dt))
                output = option.pv_paths(paths, process) # 给定路径下的输出
                pv = output['pv']
                if is_other_ouput:
                    other_output = output['others']
                    return pv, other_output
                else:
                    return pv
    
            ss = np.random.SeedSequence(entropy)
            # 创建一系列seed
            # probability of colliding pairs = n^2/(2^128)
            subs = ss.spawn(n_iter)
            # 多个处理器同时计算
            print(f'Parallel method: {parallel_method}, n_jobs: {n_jobs}')
            if n_jobs == 1:
                res = Parallel(n_jobs=n_jobs, backend=parallel_method)(_calc(s) for s in subs)
            else:
                res = Parallel(n_jobs=n_jobs, backend=parallel_method, timeout=time_out)(_calc(s) for s in subs)
            self.most_recent_entropy = ss.entropy

            if is_other_ouput:
                other_outputs = [row[1] for row in res]
                pvs = [row[0] for row in res]
                return np.mean(pvs), other_outputs
                
            else:
                return np.mean(res)
        
        else:
            # 不进行并行计算
            ss = np.random.SeedSequence(entropy)
            self.most_recent_entropy = ss.entropy
            subs = ss.spawn(n_iter)
            eps = self.generate_eps(subs[0], (n_sim, n_knot))
            paths = option.paths_given_eps(spot, process, eps)
            #path 2-D (n_sim * 2, len(dt))
            output = option.pv_paths(paths, process) # 给定路径下的输出
            pv = output['pv']
            if is_other_ouput:
                other_output = output['others']
                return pv, other_output
            else:
                return pv



