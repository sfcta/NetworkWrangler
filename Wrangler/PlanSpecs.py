import logging
import os.path
from .Network import Network

class PlanSpecs:
    """ Simple class to read in the plan specifications from a CSV file.
    """
    
    def __init__(self,basedir,networkdir,plansubdir,projectsubdir=None,tag=None,tempdir=None, **kwargs):
        """
        Read specs file, check out projects and check the network type and project year
        """
        self.projects = [] # list of projects included in the plan
        self.projectdict = {} # plan name => dictionary of attributes
        self.network = Network(champVersion=4.3,
                               networkBaseDir=basedir,
                               networkPlanSubdir=plansubdir,
                               networkProjectSubdir=projectsubdir)
        
        specs = open(os.path.join(basedir,plansubdir,networkdir,'planSpecs.csv'),'r')
        i=0
        for line in specs:
            i+=1
            if i==1:
                header=line.strip().split(',')
            else:
                l = line.strip().split(',')
                #print l
                project_name = l[header.index("projectname")]
                projType = l[header.index("type")]
                self.projectdict[project_name] = {}
                self.projects.append(project_name)

                self.projectdict[project_name]["name"]=project_name
                self.projectdict[project_name]["projtype"]=projType
                if kwargs:
                    self.projectdict[project_name]["kwargs"]=kwargs
                else:
                    print "kwargs not coming through.", kwargs
                    assert(1==2)

                # if project = "dir1/dir2" assume dir1 is git, dir2 is the projectsubdir
##                (head,tail) = os.path.split(os.path.join(networkdir,project_name))
##                if head:
##                    applied_SHA1 = self.network.cloneProject(networkdir=head, projectsubdir=tail, tag=tag,
##                                                                     projtype=projType, tempdir=tempdir)
##                    self.projectdict[project_name]["nettypes"]=self.network.getNetTypes(tempdir,head,tail)
##                else:
##                    applied_SHA1 = self.network.cloneProject(networkdir=project_name, tag=tag,
##                                                                     projtype=projType, tempdir=tempdir)
##                    self.projectdict[project_name]["nettypes"]=self.network.getNetTypes(tempdir,project_name)

    def projectAsDict(self,project_name):
        projDict = {}
        projDict['name'] = project_name
        if 'projtype' in self.projectdict[project_name].keys():
            projDict['type'] = self.projectdict[project_name]['projtype']
        if 'kwargs' in self.projectdict[project_name].keys():
            projDict['kwargs'] = self.projectdict[project_name]['kwargs']

        return projDict

    def listOfProjects(self,netType='hwy'):
        """
        Returns a list of project names.
        """
        projectlist = []

        for proj in self.projects:
            if netType in self.projectdict[proj]['nettypes']:
                print "proj: ", proj
                print "projAsDict: ", self.projectAsDict(proj)
                projectlist.append(self.projectAsDict(proj))
        return projectlist
        
    def printProjects(self,fileObj):
        pass
##        fileObj.write("YEAR   PROJECT       HWY    MUNI   RAIL    BUS        \n")
##        fileObj.write("----------------------------------------------------\n")
##        for p in self.projects:
##            fileObj.write( str(p['year'])+" "+p['name']+" "+p['hwy']+" "+p['muni']+" "+p['rail']+" "+p['bus']+"\n")
    
    def logProjects(self, logger):
        pass
##        logger.info("YEAR   PROJECT       HWY    MUNI   RAIL    BUS      \n")
##        logger.info("----------------------------------------------------")
##        for p in self.projects:
##            logger.info( sstr(p['year'])+" "+p['name']+" "+p['hwy']+" "+p['muni']+" "+p['rail']+" "+p['bus'])

