import logging
import os.path
from .Network import Network
from .Logger import WranglerLogger

class PlanSpecs:
    """ Simple class to read in the plan specifications from a CSV file.
    """
    
    def __init__(self,champVersion,basedir,networkdir,plansubdir,projectsubdir=None,tag=None,tempdir=None, **kwargs):
        """
        Read specs file, check out projects and check the network type and project year
        """
        self.projects           = [] # list of projects included in the plan
        self.projectdict        = {} # plan name => dictionary of attributes
        #network is necessary to check out projects
        self.network            = Network(champVersion=champVersion,
                                          networkBaseDir=basedir,
                                          networkPlanSubdir=plansubdir,
                                          networkProjectSubdir=projectsubdir)
        self.plan_tag           = None
        self.override           = []
        self.modelyear          = None
        if kwargs:
            if 'modelyear' in kwargs.keys():
                self.modelyear = kwargs['modelyear']
            #These next two don't do anything now.
            if 'plan_tag' in kwargs.keys():
                self.plan_tag = kwargs['plan_tag']
            if 'override' in kwargs.keys():
                self.override = kwargs['override']
        
        specs = open(os.path.join(tempdir,plansubdir,networkdir,'planSpecs.csv'),'r')
        i=0
        for line in specs:
            i+=1
            if i==1:
                header=line.strip().split(',')
            else:
                l = line.strip().split(',')

                project_name = l[header.index("projectname")]
                projType = l[header.index("type")]
                self.projectdict[project_name] = {}
                self.projects.append(project_name)

                self.projectdict[project_name]["name"]=project_name
                self.projectdict[project_name]["projtype"]=projType
                if kwargs:
                    self.projectdict[project_name]["kwargs"]=kwargs
                    
                # if project = "dir1/dir2" assume dir1 is git, dir2 is the projectsubdir
                (head,tail) = os.path.split(project_name)
                if head:
                    applied_SHA1 = self.network.cloneProject(networkdir=head, projectsubdir=tail, tag=tag,
                                                                     projtype=projType, tempdir=tempdir)
                    (parentdir, networkdir, gitdir, projectsubdir) = self.network.getClonedProjectArgs(head, tail, projType, tempdir)
                    self.projectdict[project_name]["nettypes"]=self.network.getNetTypes(tempdir,head,tail)
                else:
                    applied_SHA1 = self.network.cloneProject(networkdir=project_name, tag=tag,
                                                                     projtype=projType, tempdir=tempdir)
                    (parentdir, networkdir, gitdir, projectsubdir) = self.network.getClonedProjectArgs(project_name, None, projType, tempdir)
                    self.projectdict[project_name]["nettypes"]=self.network.getNetTypes(tempdir,project_name)
                self.projectdict[project_name]["year"]= self.network.getAttr('year',parentdir, networkdir, gitdir, projectsubdir)

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
                if not self.modelyear or self.modelyear >= self.projectdict[proj]["year"]:
                    projectlist.append(self.projectAsDict(proj))
                else:
                    WranglerLogger.warn("not applying %s, projectyear %d >= modelyear %d" % (proj, self.projectdict[proj]["year"], self.modelyear))
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

