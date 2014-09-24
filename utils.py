__author__ = 'Michail Xyntarakis'
__owner__ = 'San Francisco Transportation Authority'
__email__ = ['billy@sfcta.org', 'xyntarakis@pbworld.com']
__license__ = 'GPL'

from itertools import izip

import tables
import numpy as np
import hdf5

import warnings
warnings.filterwarnings("ignore", category=tables.NaturalNameWarning) # Pytables doesn't like our table numbering scheme

class Utils(object):
    @classmethod
    def readCtl(cls,ctlFile,delim=","):
        F = open(ctlFile, mode='r')
        parameters = {}
        for line in F:
            if line[:2] == '::':
                print "Reading %s Control File from %s" % (ctlFile,line[2:])
            else:
                (param,value) = line.strip().split(delim)
                try:
                    value = float(value)
                except:
                    pass
                param = param.strip()
                parameters[param] = value
        F.close()
        return parameters

    @classmethod
    def areEqual2(cls, array1, array2, decimalPlaces, absDifference=None):

        assert array1.shape == array2.shape

        max1 = np.max(array1 - array2)
        max2 = np.max(array2 - array1)

        if absDifference:
            assert max(max1, max2) < absDifference
        else:
            assert max(max1, max2) < 1.0 / (10 ** decimalPlaces)

    @classmethod
    def printDifferences(cls, numpyArray1, numpyArray2):

        #nose.tools.set_trace()
        print
        print "max:", np.max(numpyArray1), np.max(numpyArray2)
        print "min:", np.min(numpyArray1), np.min(numpyArray2)
        print 'max diff', np.max(numpyArray1 - numpyArray2), np.max(numpyArray2 - numpyArray1)

        numValuesInEachBin, bins = np.histogram(numpyArray1 - numpyArray2)
        print "histogram of the differences\n%s\n%s" % (str(bins), str(numValuesInEachBin))

    @classmethod
    def findDifferenceGreaterThan(cls, array1, array2, diff):

        assert array1.shape == array2.shape
        numRows,numCols = array1.shape
        for i in xrange(numRows):
            for j in xrange(numCols):
                if abs(array1[i, j] - array2[i, j]) > diff:
                    print "Row, col, diff", "%6d %6d    %f" % (i, j, array2[i, j] - array1[i, j])

    @classmethod
    def get3dH5AsNumpy(cls, fileName):
        """
        Reads the cube H5 matrix and returns 
        (3-dimensional zero-based numpy array, list of matrix names)
        """

        h5 = tables.openFile(fileName, 'r')

        allArrays = h5.listNodes('/', classname='CArray')

        numArrays = len(allArrays)
        if numArrays == 0:
            raise Exception("The file %s is emty" % fileName)
        numElements = allArrays[0].shape[0]
        for i in range(numArrays):
            assert allArrays[i].shape == (numElements, numElements)

        cubeMatrix = np.zeros((numArrays, numElements, numElements))
        arrayNames = []
        
        for i in range(numArrays):
            cubeMatrix[i, :, :] = h5.root._f_getChild(str(i + 1)).read()
            arrayNames.append(h5.getNode('/', '%s' % (i+1)).attrs.name)

        h5.close()
        return (cubeMatrix, arrayNames)
    
    @classmethod
    def mtcZonesToSFZones(cls, mtcTrips, FILE_MTC_DISAGGREGATION, FILE_MTC_AGGREGATION=''):
        """Implements what is in the scripts/mtctrips/p2009/aggregateOther"""
        
        if FILE_MTC_AGGREGATION:
            mtcAlphaToBeta = cls.getZeroBasedAlphaToBetaMTCAggregation(FILE_MTC_AGGREGATION)    
            mtcTripsAgg    = cls.aggregateArray(mtcTrips, mtcAlphaToBeta) 
        else:
            mtcTripsAgg = mtcTrips
        sfBetaToAlpha  = cls.getZeroBasedBetaToAlphaMTCDisaggregation(FILE_MTC_DISAGGREGATION)
        sfTrips        = cls.disaggregateArray(mtcTripsAgg, sfBetaToAlpha)

        return sfTrips

    @classmethod
    def getZeroBasedAlphaToBetaMTCAggregation(cls, FILE_MTC_AGGREGATION):
        """Return a dictionary contaning the MTC Aggregation
        One has been substracted from both alpha zones and beta zones"""
        result = {}
        inputStream = open(FILE_MTC_AGGREGATION, 'r')
        for line in inputStream:
            alphaZone, betaZone = map(int, line.strip().split(','))
            result[alphaZone - 1] = betaZone - 1
        inputStream.close()
        return result


    @classmethod
    def getZeroBasedBetaToAlphaMTCDisaggregation(cls, disaggregationFile):

        """
        Read the data similar to the colums below
        the row and col multipliers are in percentages
        and are converted to fractional values

        All Zone ids  are zero based

        alpha   beta  rowMultiplier colMultiplier
        -----   ----  ------------  -------------
        1       1     30           50
        1       2     70           50
        2       3     20           90
        """

        result = {}
        inputStream = open(disaggregationFile, 'r')
        for line in inputStream:
            fields = map(float, line.strip().split(','))
            alphaZone = int(fields[0]) - 1
            betaZone = int(fields[1]) - 1
            rowFactor = fields[2] / 100.0
            colFactor = fields[3] / 100.0

            result[betaZone] = (alphaZone, rowFactor, colFactor)

        inputStream.close()
        return result


    @classmethod
    def getIndexToIndex(cls, alphaToBeta, alphaIndex, betaIndex):

        assert len(alphaToBeta) == len(alphaIndex)
        assert sorted(set(alphaToBeta.keys())) == sorted(set(alphaIndex.keys()))
        assert set(alphaToBeta.values()) <= set(betaIndex.keys())

        assert sorted(set(alphaIndex.values())) == range(len(alphaIndex))
        assert sorted(set(betaIndex.values())) == range(len(betaIndex))

        result = {}
        for alphaZone, betaZone in alphaToBeta.iteritems():
            ai = alphaIndex[alphaZone]
            bi = betaIndex[betaZone]
            result[ai] = bi

        return result

    @classmethod
    def aggregateArray(cls, alphaArray, alphaToBeta):
        """alpha to Beta is a dictionary that maps the alpha zones
        to some beta zones"""
        maxAlphaElement = alphaArray.shape[0]
        assert maxAlphaElement >= max(alphaToBeta.keys())

        maxBetaElement = max(alphaToBeta.values())
        betaArray = np.zeros((maxBetaElement + 1, maxBetaElement + 1))

        for alphaI in alphaToBeta.iterkeys():
            betaI = alphaToBeta[alphaI]
            for alphaJ in alphaToBeta.iterkeys():
                betaJ = alphaToBeta[alphaJ]
                betaArray[betaI, betaJ] += alphaArray[alphaI, alphaJ]
        return betaArray

    @classmethod
    def aggregateConsecutiveArray(cls, numpyArray, alphaToBeta):
        """Aggreate the numpyArray using the alphaToBeta parameters and
        return the result as a numpy array

        alphaToBeta should is a dictionary that returs the beta (zero-based index)
        given the alpha (zero-based) index
        """

        alphaDimension = len(alphaToBeta)
        #the following is right if the beta indices are sequential
        #and zero based. For the MTC aggregation they are not sequential
        #betaDimension = len(set(alphaToBeta.values()))
        betaDimension = max(alphaToBeta.values()) + 1

        assert betaDimension <= alphaDimension
        assert sorted(alphaToBeta.keys()) == \
            range(alphaDimension)

        #the following is an important check. however it does not hold
        #for the MTC aggregation so I have commented it out
        #assert sorted(set(alphaToBeta.values())) == \
        #    range(betaDimension)

        alphaArray = numpyArray
        betaArray = np.zeros((betaDimension, betaDimension))

        for alphaI in xrange(alphaDimension):
            betaI = alphaToBeta[alphaI]
            for alphaJ in xrange(alphaDimension):
                betaJ = alphaToBeta[alphaJ]
                betaArray[betaI, betaJ] += alphaArray[alphaI, alphaJ]
        return betaArray


    @classmethod
    def getBetaIndexToAlphaIndex(cls, betaToAlpha, alphaIndex, betaIndex):

        betaElements = sorted(betaToAlpha.keys())
        alphaElements = sorted(set([b2a[0] for b2a in betaToAlpha.itervalues()]))

        assert betaElements == sorted(betaIndex.keys())
        assert alphaElements == sorted(alphaIndex.keys())

        assert sorted(alphaIndex.values()) == range(len(alphaIndex))
        assert sorted(betaIndex.values()) == range(len(betaIndex))

        result = {}
        for betaZone, (alphaZone, rowM, colM) in betaToAlpha.iteritems():
            betaI = betaIndex[betaZone]
            alphaI = alphaIndex[alphaZone]
            result[betaI] = (alphaI, rowM, colM)

        return result


    @classmethod
    def disaggregateArray(cls, alphaArray, betaToAlpha):
        """Dissagregate the numpyArray using the alphaToBeta parameters
        and return the result as a numpy array

        example
        alpha   beta  rowMultiplier colMultiplier
        -----   ----  ------------  -------------
        0       0     0.3           0.5
        0       1     0.7           0.5
        1       2     0.2           0.9
        1       3     0.8           0.1

        if I sum all the row multipliers of each alpha element i should get 1.0
        same for all colMultipliers
        """
        assert len(alphaArray.shape) == 2
        assert alphaArray.shape[0] == alphaArray.shape[1]

        betaElements = sorted(betaToAlpha.keys())
        alphaElements = sorted(set([b2a[0] for b2a in betaToAlpha.itervalues()]))

        betaDimension = max(betaElements) + 1
        alphaDimension = max(alphaElements) + 1

        assert alphaArray.shape[0] >= alphaDimension

        betaArray = np.zeros((betaDimension, betaDimension))

        for betaI, (alphaI, rowMultI, colMultI) in betaToAlpha.iteritems():
            for betaJ, (alphaJ, rowMultJ, colMultJ) in betaToAlpha.iteritems():

                betaArray[betaI, betaJ] = alphaArray[alphaI, alphaJ] * \
                    rowMultI * colMultJ

        return betaArray

    @classmethod
    def printColumnSums(cls, array1, array2):

        assert array1.shape == array2.shape

        for i in range(array1.shape[1]):
            if abs(round(array1[:, i].sum() - array2[:, i].sum(), 0)) > 0:
                print "%d %10.0f %10.0f" % (i, array1[:, i].sum(), array2[:, i].sum())

    @classmethod
    def disaggregateConsecutiveArray(cls, alphaArray, betaToAlpha):
        """Dissagregate the numpyArray using the alphaToBeta parameters
        and return the result as a numpy array

        example
        alpha   beta  rowMultiplier colMultiplier
        -----   ----  ------------  -------------
        0       0     0.3           0.5
        0       1     0.7           0.5
        1       2     0.2           0.9
        1       3     0.8           0.1

        if I sum all the row multipliers of each alpha element i should get 1.0
        same for all colMultipliers
        """

        betaElements = sorted(betaToAlpha.keys())
        alphaElements = sorted(set([b2a[0] for b2a in betaToAlpha.itervalues()]))

        betaDimension = len(betaElements)
        alphaDimension = len(alphaElements)

        assert betaDimension > alphaDimension
        assert betaElements == range(betaDimension)
        assert alphaElements == range(alphaDimension)

        betaArray = np.zeros((betaDimension, betaDimension))

        for betaI, (alphaI, rowMultI, colMultI) in betaToAlpha.iteritems():
            for betaJ, (alphaJ, rowMultJ, colMultJ) in betaToAlpha.iteritems():
                betaArray[betaI, betaJ] = alphaArray[alphaI, alphaJ] * \
                    rowMultI * colMultJ

        return betaArray

    @classmethod
    def writeNumpyArray(cls, fileName, array):
        """Saves the input array in the numpy native binary format"""
        np.save(fileName, array)

    @classmethod
    def readNumpyArray(cls, fileName):
        """Reads an npz file and returns a numby array"""
        return np.load(fileName)

    @classmethod
    def writeAsHDF5(cls, numpyArray, outFileName, names=None):
        """Save the numpyArray as HDF5 CArray."""
        assert isinstance(numpyArray, np.ndarray)

        dimensions = len(numpyArray.shape)
        zones = int(numpyArray.shape[dimensions-1])
        matrices = dimensions<3 and 1 or int(numpyArray.shape[0])

        h5f = hdf5.H5Matrix.create(outFileName, zones, matrices, names)

        if dimensions == 3:
            for i in range(matrices):
                h5f[i+1][:] = numpyArray[i]
        elif dimensions == 2:
            h5f[1][:] = numpyArray
        else:
            raise Exception("The shape of the numpy array %s is not supported" % str(numpyArray.shape))

        h5f.close()

    @classmethod
    def getSharesAsStr(cls, matrixType, inputArray):

        lines = []
        header = "%15s %10s %10s\n" % ("Mode", "Trips", "Percent")
        lines.append(header)
        for i in range(len(matrixType)):
            name = matrixType[i]
            line = "%15s %10d %10.2f\n" % (name, inputArray[i].sum(), float(inputArray[i].sum()) / inputArray.sum() * 100)
            lines.append(line)
        footer = "%15s %10d %10.2f\n" % ("ALL", inputArray.sum(), 100)
        lines.append(footer)
        return "".join(lines)

def enum(typename, field_names):
    "Create a new enumeration type"

    if isinstance(field_names, str):
        field_names = field_names.replace(',', ' ').split()
    d = dict((reversed(nv) for nv in enumerate(field_names)), __slots__ = ())
    return type(typename, (object,), d)()
