__author__ = "Michail Xyntarakis"
__company__ = "Parsons Brinckerhoff"
__email__ = "xyntarakis@pbworld.com"
__license__ = "GPL"

from DBFErrors import FieldTypeError, DbfToNumpyError

class FieldType(object):
    """Contains information about the data type of each field"""
    TYPE_INT = "N"
    TYPE_DECIMAL = "N"
    TYPE_STRING = "C"
    TYPE_FLOAT = "F"

    TYPES = [TYPE_INT, TYPE_DECIMAL, TYPE_STRING, TYPE_FLOAT]

    LENGTH_INT = 10
    LENGTH_DECIMAL = 15
    LENGTH_DECIMAL_ = 4
    LENGTH_STRING = 50
    
    __slots__ = ("name", "type", "length", "numDecimals")

    def __init__(self, name, _type, length, numDecimals):

        self.name = name

        if _type not in FieldType.TYPES:
            raise FieldTypeError('Unknown field type %s' % _type)

        self.type = _type
        self.length = length
        self.numDecimals = numDecimals

    def __repr__(self):

        return str((self.name, self.type, self.length, self.numDecimals))
    
    def toTuple(self):

        return (self.name, self.type, self.length, self.numDecimals)

def dbfToNumpyDataType(fieldType):
    """Accept a field type object and return the name and the type(format)
    of the corresponding numpy data type"""
    if fieldType.type == FieldType.TYPE_INT or \
            fieldType.type == fieldType.TYPE_DECIMAL:
        if fieldType.numDecimals == 0:
            return fieldType.name, "i"
        else:
            return fieldType.name, "d"
    elif fieldType.type == FieldType.TYPE_FLOAT:
        return fieldType.name, "d"
    elif fieldType.type == FieldType.TYPE_STRING:
        return fieldType.name, "S"+str(fieldType.length)
    else:
        raise DbfToNumpyError("The field %s has the following type that I do not recognize: %s "
                         % (fieldType.name, str(fieldType.type)))

def numpyToDbfType(name, numpyDataType):
    """Accept the name and the type(format) of a numpy data type and 
    return the corresponding DBF data type based on some assumptions 
    about the length of the elements to be stored"""
    if numpyDataType == "i":
        return FieldType(name, FieldType.TYPE_INT, FieldType.LENGTH_INT, 0) 
    elif numpyDataType == "d":
        return FieldType(name, FieldType.TYPE_DECIMAL, 
                         FieldType.LENGTH_DECIMAL, FieldType.LENGTH_DECIMAL_)
    elif numpyDataType == "S":
        return FieldType(name, FieldType.TYPE_STRING, FieldType.LENGTH_STRING, 0)
    else:
        raise ValueError("I cannot recognize the numpy data type %s" %
                         str(numpyDataType))
        
def convertDbfToNumpyDataTypes(fieldTypes):
    """Accept a sequence of FieldType objects and return the field names and their numpy 
    types"""

    names = []
    formats = []
    for fType in fieldTypes:
        name, format = dbfToNumpyDataType(fType)
        names.append(name)
        formats.append(format)
    return names, formats

