from itertools import izip, count, tee
from collections import defaultdict
from odict import OrderedDict
import numpy as np
import csv, decimal, datetime

from struct import unpack, pack, calcsize 

print "Importing ", __file__

class DataTableError(Exception):
    pass

class DataTableKeyError(DataTableError):
    pass

class DataTableValueError(DataTableError):
    pass

class DataTable(object):
    """A DataTable wrapper around a numpy array class"""

    def __init__(self, numRecords, header=None, fieldNames=None, numpyFieldTypes=None):
        """Constuct a new DataTable. 
        Inputs: numRecords : a positive integer
                dtype : a dictionary containing the names and
                        types of the fields
        """
        if header:
            fieldNames, numpyFieldTypes = convertDbfToNumpyDataTypes(header)
            npDtype = np.dtype({"names":self.fixFieldNames(fieldNames), "formats":numpyFieldTypes})
            self.header = header
        elif fieldNames and numpyFieldTypes:
            npDtype = np.dtype({"names":self.fixFieldNames(fieldNames), "formats":numpyFieldTypes})
            self.header = ()
        else:
            raise ValueError("You have to provide either the header or the field "
                             "names along with their types to instantiate a new "
                             "data table")
            
        self.fields = np.zeros((numRecords,), npDtype)
        self._index = dict(izip(range(self.fields.size), range(self.fields.size)))
        self._hasIndex = False
        self._indexFunction = None
#        self._updateAttributes()

    def fixFieldNames(self, fieldNames):
        """
        For a given list of fieldNames, ensures that
        1) every name is 10 chars or less
        2) every name is unique (errors if not)
        """
        returnlist      = []
        for fieldname in fieldNames:
            # first truncate to 10
            if len(fieldname) > 10: fieldname = fieldname[:10]
            
            # check uniqueness
            if fieldname in returnlist:
                raise DataTableKeyError("Two fields are both called %s - unsupported." % fieldname)
            
            returnlist.append(fieldname)
            
        # print "fixFieldNames: fieldNames=(%d) %s returnlist=(%d) %s" % (len(fieldNames), str(fieldNames), len(returnlist), str(returnlist))
        return returnlist
            
    def __str__(self):
        """Return the numpy representation of the table"""
        return str(self.fields)

    def __getitem__(self, key):
        """Allow the datatable to be accessed as a dictionary"""
        try:
            return self.fields[self._index[key]]
        except KeyError:
            raise DataTableKeyError("Key %s does not exist" % str(key))

    def __contains__(self, key):
        
        try:
            self.__getitem__(key)
        except DataTableKeyError:
            return False
        return True
    
    def __setitem__(self, key, value):
        """Alow the user to set a row or a field in a row the same way one
        would use if the datatable was a dictionary"""
#        raise DataTableError("There is a bug here")
        try:
            self.fields[self._index[key]] = value
        except KeyError:
            raise DataTableKeyError("Key %s does not exist" % str(key))
        except ValueError, e:
            raise DataTableValueError(str(e))
        return self

    def __iter__(self):
        """Return a row iterator"""
        return self.fields.flat

    def __len__(self):
        """Return the number of records in the table"""
        return self.getNumRecords()

    def getNumpyArray(self):
        """Return the underlying numpy array"""
        return self.fields
    
    def _updateAttributes(self):
        """Set the field names as attributes"""
        for name in self.fields.dtype.names:
            setattr(self, name, self.fields[name])

    def getNumRecords(self):
        """Return the number of records in the data table"""
        return self.fields.size

    def getFieldNames(self):
        """Return the field names of the datatable"""
        return self.fields.dtype.names

    def setIndex(self, fieldName = None, indexFunction = None):
        """Define a fieldName the values of which will serve as the index 
        of the table. Alternativly, you can define a fucntion that takes a
        row as an input and returns a value serving as the index"""
        if fieldName:
            if fieldName not in self.fields.dtype.names:
                raise DataTableError("The field: %d does not exist" % str(fieldName))

            newIndex = self._createIndex(fieldName)
            self._index = newIndex
            #TODO you can simplify this
            self._hasIndex = True
            self._indexField = fieldName
            self._indexFunction = None
        elif indexFunction:
            newIndex = self._createIndex(indexFunction=indexFunction)
            self._index = newIndex
            self._hasIndex = True
            self._indexField = None
            self._indexFunction = indexFunction
        else:
            self._index = dict(izip(range(self.fields.size), range(self.fields.size)))
            self._hasIndex = False
            self._indexFunction = None
            self._indexField = None

    def _createIndex(self, fieldName=None, indexFunction=None):
        """Create a dictionary the keys of which will serve as the new
        indices for accessing table elements"""
        newIndex = {}
        if fieldName:
            #check the uniqueness of the fields values
            if len(set(self.fields[fieldName])) != self.getNumRecords():
                raise DataTableError("The field: %s contains non unique values and therefore"
                                     "canot be set as the index" % fieldName)
            for i, record in enumerate(self):
                newIndex[record[fieldName]] = i
        elif indexFunction:
            for i, record in enumerate(self):
                newIndex[indexFunction(record)] = i
            #check if the generated keys are unique
            if not len(set(newIndex.keys())) == self.getNumRecords():
                numKeys = defaultdict(int)
                for record in self:
                    numKeys[indexFunction(record)] += 1

                duplicateKeys = [str(key) for key, count in numKeys.iteritems() if count > 1]
                raise DataTableError("The provided index function does not generate"
                                     "unique keys and therefore cannot be applied.\nDuplicate keys %s" 
                                     % str(duplicateKeys))                              
        else:
            raise DataTableError("A fieldName or an indexFunction have to be"
                                 "provided to index the features")        
        return newIndex
    
    def getFieldInfo(self):
        """Return a string with info about field names
        and their data types"""
        raise DataTableError("Not implemented yet")
    
    def addField(self, newFieldName=None, dtype=None):
        """Add a field to the existing ones"""
        #TODO the header needs to be updated
        self.header = ()
        fnames = list(self.getFieldNames())
        ftypes = [self.fields.dtype[fname] for fname in fnames]        
        fnames.append(newFieldName)
        ftypes.append(dtype)

        dt = np.zeros((self.getNumRecords(),), dtype={"names":fnames, "formats":ftypes})
        #copy the data
        for fname in fnames:
            if fname is newFieldName:
                continue
            dt[fname] = self.fields[fname]
            
        self.fields = dt
#        self._updateAttributes()

    def addIntegerField(self, fieldName):
        """Add an interger field to the table with the provided field name"""
        self.addField(newFieldName=fieldName, dtype="i")

    def addDoubleField(self, fieldName):
        """Add a field with type double to the table with the
        given field name"""
        self.addField(newFieldName=fieldName, dtype="d")

    def addStringField(self, fieldName, numCharacters):
        """Add a string field with the given name and number 
        of charaters length"""
        self.addField(newFieldName=fieldName, dtype="S%d" % numCharacters)
        
    def sort(self, fieldNames):
        """Sort the records based on the index?"""
        self.fields.sort(order=fieldNames)
        if self._hasIndex:
            if self._indexField:
                self._index = self._createIndex(fieldName=self._indexField)
            else:
                self._index = self._createIndex(indexFunction=self._indexFunction)

    def writeAsDbf(self, fileName):
        """Write the table in a dbf file"""
        
        if self.header == ():
            raise ValueError("Not implemented yet")
        dbfWriter = DbfDictWriter(fileName, self.header, self.getNumRecords())
        for record in self:
            dbfWriter.writeRecord(record)

    def writeAsCsv(self, fileName):
        """Write the table as a csv file"""
        import csv 
        dialect = csv.excel
        dialect.lineterminator = "\n"
        outputStream = open(fileName, "w")
        writer = csv.writer(outputStream, dialect=dialect)
        writer.writerow(self.getFieldNames())
        for record in self:
            writer.writerow(record)
        outputStream.close()

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
    # truncate field names to 10
    if fieldType.name > 10: fieldType.name = fieldType.name[:10]
    
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
    
class DbfDictReader(object):
    """Iterator over the records of a DBF III file
    for each record in the file an OrderedDict is returned 
    """
    def __init__(self, bfstream):
        """Input: a binary sream"""
        self.bfstream = bfstream
        self.numrec, lenheader = unpack('<xxxxLH22x', self.bfstream.read(32))    
        numfields = (lenheader - 33) // 32

        # get the header.
        # for each field you have name, type, size, decimals

        header = [list(unpack('<11sc4xBB14x', self.bfstream.read(32))) for i in xrange(numfields)]

        # remove the "\0" from the field Names
        for fieldInfo in header:
            fieldInfo[0] = fieldInfo[0].replace('\0', '')       # eliminate NULs from string   

        self.header = tuple([FieldType(*fieldInfo) for fieldInfo in header])
        self.fieldNames = tuple([fType.name for fType in self.header])
        self.recNo = 0

        terminator = self.bfstream.read(1)
        assert terminator == '\r'

    def __iter__(self):
        return self

    def next(self):
        
        header = [fType.toTuple() for fType in self.header]
        header.insert(0, ('DeletionFlag', 'C', 1, 0))

        # read the string as a bunch of characters eg. 2s4s5s 
        fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in header])
        
        self.recNo += 1
        if self.recNo == self.numrec + 1:
            raise StopIteration

        fieldValues = unpack(fmt, self.bfstream.read(calcsize(fmt))) # the field values are stores as an array
        if fieldValues[0] != ' ': # deleted record
            return {}

        finalValues = []
        for (name, typ, size, deci), value in izip(header, fieldValues):

            if name == 'DeletionFlag':
                continue
            try:
                if typ == "N" or typ == "F":
                    value = value.replace('\0', '').lstrip()
                    if value == '':
                        value = 0
                    elif deci:
                        value = decimal.Decimal(value)
                    elif value=='*'*size:
                        value = 0 # unknown!!
                    else:
                        value = int(value)
                elif typ == 'D':
                    y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                    value = datetime.date(y, m, d)
                elif typ == 'L':
                    value = (value in 'YyTt' and 'T') or (value in 'NnFf' and 'F') or '?'
            except:
                print "Exception caught with name %s type %s value %s" % (name, typ, str(value))
                raise
            
            finalValues.append(value)
        return OrderedDict(izip(self.fieldNames, finalValues))   

def dbfTableReader(fileName):
    """Read a dbf table and return a DataTable"""
    
    binaryStream = open(fileName, "rb")
    dictReader = DbfDictReader(binaryStream)
    numRecords = dictReader.numrec

    #create an approximate numpy dtype object

    # the dbf header is looks like
    #(['ID', 'N', 10, 0], ['AREA', 'N', 11, 2], ['DISTRICT_N', 'C', 25, 0])
    #then the dtype header should look 
    # {"names":["ID", "AREA", "DISTRICT_N"], "formats":["i", "d", "S25"]}
    names = []
    formats = []

    dt = DataTable(numRecords, header=dictReader.header)
    index = 0
    try:
        for record in dictReader:
            dt[index] = tuple(record.values())
            index += 1
    except:
        print "Failed reading dbf table; index=%d" % index
        raise
    return dt

class DbfDictWriter(object):
    """Writes a datatable to the disk
    Not individual records"""

    def __init__(self, fileName, header, numRecords):
        
        self.header = header
        self._bfstream = open(fileName, "wb")
        self._numRecords = numRecords
        self._currentRecord = 0
        self._writeHeader()

    def _writeHeader(self):
        """Write the header of the dbf file"""
        # header info
        ver = 3
        now = datetime.datetime.now()
        yr, mon, day = now.year-1900, now.month, now.day
        numrec = self._numRecords
        numfields = len(self.header)
        lenheader = numfields * 32 + 33
        lenrecord = sum(fType.length for fType in self.header) + 1

        hdr = pack('<BBBBLHH20x', ver, yr, mon, day, numrec, lenheader, lenrecord)
        self._bfstream.write(hdr)

        # field specs
        for fieldType in self.header:
            name = fieldType.name
            typ = fieldType.type
            size = fieldType.length
            deci = fieldType.numDecimals

            name = name.ljust(11, '\x00')
            fld = pack('<11sc4xBB14x', name, typ, size, deci)
            self._bfstream.write(fld)

        # terminator
        self._bfstream.write('\r')
                
    def writeRecord(self, record):
        """Write a record that can be accessed as a dictionary to the 
        dbf file"""
        if self._currentRecord > self._numRecords:
            raise DbfWriteError("The number of records that can be writen to the file "
                                "%s cannot exceed %d" % (self._fileName, self._numRecords))
        self._bfstream.write(" ")
        for fType in self.header:
            name = fType.name
            typ = fType.type
            size = fType.length
            deci = fType.numDecimals
            value = record.__getitem__(name)
            if (fType.type == FieldType.TYPE_INT or 
                fType.type == FieldType.TYPE_DECIMAL or 
                fType.type == FieldType.TYPE_FLOAT):
                if deci == 0:
                    fmtstr = "%" + str(size)+"d"
                    value = fmtstr % value
                else:
                    fmtstr = "%" + str(size) + "." + str(deci) + "f"
                    value = fmtstr % value
            elif fType.type == 'D':
                value = value.strftime('%Y%m%d')
            elif fType.type == 'L':
                value = str(value)[0].upper()
            else:
                value = str(value)[:size].ljust(size, ' ')
            if len(value) != size: print "Mismatch for "+name+"; "+str(len(value))+" != "+str(size)+"; val="+str(value)
            assert len(value) == size

            self._bfstream.write(value)

        self._currentRecord += 1
        if self._currentRecord == self._numRecords:
            self._bfstream.write('\x1A')
            self._bfstream.close()
        
    def __del__(self):
        #TODO should I close the binary stream? 
        pass
    
