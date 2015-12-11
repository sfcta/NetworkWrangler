# some generic helper functions for NetworkWrangler
import copy, xlrd

def openFileOrString(f):
    # check if it's a filename or a file. Open it if it's a filename
    if isinstance(f, str):
        f = open(f, 'w')
    elif isinstance(f, file):
        if f.closed: f = open(f.name)
    return f

def generate_unique_id(seq):
    """
    Generator that yields a number from a passed in sequence
    """
    for x in seq:
        yield x

def getListOverlap(list1, list2):
    '''
    Assumes list1 and list2 are lists of integers where elements are unique within
    each list. Returns left (elements only in list1), right (elements only in list2),
    overlap (elements in both lists)
    '''
    left = removeDuplicatesFromList(list1)
    right = removeDuplicatesFromList(list2)
    overlap = []
    for x in left:
        if x in right:
            if x not in overlap: overlap.append(x)
            right.remove(x)
    for x in overlap:
        left.remove(x)
    left.sort(), right.sort(), overlap.sort()
    return (left, right, overlap)

def boilDown(numbers, left_split, right_split):
    sets = []
    overlap1 = getListOverlap(numbers, left_split)
    overlap2 = getListOverlap(numbers, right_split)
    for x in overlap1:
        if x not in sets and len(x) > 0: sets.append(x)
    for x in overlap2:
        if x not in sets and len(x) > 0: sets.append(x)
    return sets

def isSubset(subset, fullset):
    for i in subset:
        if i not in fullset:
            return False
    return True
def removeDuplicatesFromList(l):
    this_list = copy.deepcopy(l)
    for x in this_list:
        while this_list.count(x) > 1:
            this_list.remove(x)
    return this_list

def getChampNodeNameDictFromFile(filename):
    book = xlrd.open_workbook(filename)
    sh = book.sheet_by_index(0)
    nodeNames = {}
    for rx in range(0,sh.nrows): # skip header
        therow = sh.row(rx)
        nodeNames[int(therow[0].value)] = therow[1].value
    return nodeNames