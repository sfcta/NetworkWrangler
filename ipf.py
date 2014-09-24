__author__ = "Michail Xyntarakis"
__company__ = "Parsons Brinckerhoff"
__email__ = "xyntarakis@pbworld.com"
__license__ = "GPL"

import logging
import numpy as np

class IPFError(Exception):
    pass

def ipf(npArray, marginals, threshold, maxIterations):
    """Watch out. it is a reference to the npArray.
    Perhaps you can have two versions of ipf depending on the arguments that go
    into it, npAray or MDArray"""
    
    #check that all the margianls have the same sum


    marginalDims = tuple(len(marginal) for marginal in marginals)
    if npArray.shape != marginalDims:
        raise IPFError("The dimentions of the seeds %s and the marginals %s"
                       "do not match" % (str(npArray.shape), str(marginalDims)))


    
    marginalSum = marginals[0].sum()
    for i, marginal in enumerate(marginals):
        if not abs(marginal.sum() - marginalSum) < 0.000001:
            msg = ('The marginals %f and %f correspoding to dimensions '
                   '%i and %i are not equal' % (marginalSum, marginal.sum(), 0, i))
            
            raise IPFError(msg)
            

    maxRatio = threshold + 2
    maxDiff = 0
    iteration = 0
    numDimentions = len(npArray.shape)
    result = npArray.copy()
    while abs(maxRatio - 1) > threshold:
        
        iteration += 1
        if iteration >= maxIterations:
            msg = ("Ipf algorithm reached maximum iterations: %d "
                   "without convergence. Target marginal divided by "
                   "the caclulated "
                   "marginal is %.6f. Maximum difference between "
                   "target and calculated marginal is %f" % (iteration, maxRatio, maxDiff))
            logging.error(msg)
            print msg
            return result
            break
        maxRatio = 1.0
        maxDiff = 0

        for dimIndex in xrange(len(result.shape)):
            for elemIndex in xrange(result.shape[dimIndex]):
            
                sliceObj = [slice(None, None, None),] * numDimentions
                sliceObj[dimIndex] = elemIndex
                subArray = result[sliceObj]
                currentSum = np.sum(subArray)
                targetSum = marginals[dimIndex][elemIndex]
                if currentSum > 0:
                    ratio = targetSum / currentSum
                else:
                    ratio = 0
                subArray *= ratio
                maxRatio = max(maxRatio, ratio)
                maxDiff = max(maxDiff, abs(targetSum - currentSum))

    logging.info("Ipf algorithm achieved convergence after %d"
                 " iterations" % iteration)
    return result


