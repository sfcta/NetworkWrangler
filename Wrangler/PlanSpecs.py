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
        self.plan_name          = networkdir 
        self.projects           = [] # list of projects included in the plan
        self.projectdict        = {} # plan name => dictionary of attributes
        #network is necessary to check out projects
        self.network            = Network(champVersion=champVersion,
                                          networkBaseDir=basedir,
                                          networkPlanSubdir=plansubdir,
                                          networkProjectSubdir=projectsubdir)
        self.tag_override       = {}
        self.modelyear          = None
        if kwargs:
            if 'modelyear' in kwargs.keys():
                self.modelyear = kwargs['modelyear']
            #These next two don't do anything now.
            if 'tag_override' in kwargs.keys():
                WranglerLogger.debug('found tag_override: %s' % (kwargs['tag_override']))
                self.tag_override = kwargs['tag_override']
                if not isinstance(self.tag_override, dict):
                    raise NetworkException('when passing tag_override, must be dict type')
        
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
                try:
                    project_tag = self.tag_override[project_name]
                    WranglerLogger.debug('applying project-specific tag %s to project %s within plan %s' %(project_tag, project_name, self.plan_name))
                except:
                    project_tag = tag
                    WranglerLogger.debug('applying general tag %s to project %s within plan %s' %(project_tag, project_name, self.plan_name))
                self.projectdict[project_name] = {}
                self.projects.append(project_name)

                self.projectdict[project_name]["name"]=project_name
                self.projectdict[project_name]["projtype"]=projType

                try:
                    self.projectdict[project_name]["modelyear"] = kwargs['modelyear']
                    #WranglerLogger.debug('project %s using MODELYEAR %s' % (project_name, kwargs['modelyear']))
                except Exception as e:
                    self.projectdict[project_name]["modelyear"] = None #WranglerLogger.debug(
                    #WranglerLogger.debug('project %s: MODELYEAR error: %s' % (project_name, e))
                try:
                    self.projectdict[project_name]['tag'] = kwargs['tag_override'][project_name]
                    #WranglerLogger.debug('project %s using TAG %s' % (project_name, kwargs['tag_override'][project_name]))
                except Exception as e:
                    self.projectdict[project_name]['tag'] = None
                    #WranglerLogger.debug('project %s: TAG error: %s' % (project_name, e))
                    
                # if project = "dir1/dir2" assume dir1 is git, dir2 is the projectsubdir
                (head,tail) = os.path.split(project_name)
                if head:
                    applied_SHA1 = self.network.cloneProject(networkdir=head, projectsubdir=tail, tag=project_tag,
                                                                     projtype=projType, tempdir=tempdir)
                    (parentdir, networkdir, gitdir, projectsubdir) = self.network.getClonedProjectArgs(head, tail, projType, tempdir)
                    self.projectdict[project_name]["nettypes"]=self.network.getNetTypes(tempdir,head,tail)
                else:
                    applied_SHA1 = self.network.cloneProject(networkdir=project_name, tag=project_tag,
                                                                     projtype=projType, tempdir=tempdir)
                    (parentdir, networkdir, gitdir, projectsubdir) = self.network.getClonedProjectArgs(project_name, None, projType, tempdir)
                    self.projectdict[project_name]["nettypes"]=self.network.getNetTypes(tempdir,project_name)
                self.projectdict[project_name]["year"]= self.network.getAttr('year',parentdir, networkdir, gitdir, projectsubdir)

    def projectAsDict(self,project_name):
        projDict = {}
        projDict['name'] = project_name
        projDict['kwargs'] = {}
        if 'projtype' in self.projectdict[project_name].keys():
            projDict['type'] = self.projectdict[project_name]['projtype']
        if 'modelyear' in self.projectdict[project_name].keys():
            projDict['kwargs']['modelyear'] = self.projectdict[project_name]['modelyear']
        if 'tag' in self.projectdict[project_name].keys():
            projDict['tag'] = self.projectdict[project_name]['tag']
##        if 'kwargs' in self.projectdict[project_name].keys():
##            projDict['kwargs'] = self.projectdict[project_name]['kwargs']

        return projDict

    def listOfProjects(self,netType='hwy'):
        """
        Returns a list of project names.
        """
        projectlist = []

        for proj in self.projects:
            if netType in self.projectdict[proj]['nettypes']:
                projectlist.append(self.projectAsDict(proj))
##                if not self.modelyear or self.modelyear >= self.projectdict[proj]["year"]:
##                    projectlist.append(self.projectAsDict(proj))
##                else:
##                    WranglerLogger.warn("not applying %s, projectyear %d >= modelyear %d" % (proj, self.projectdict[proj]["year"], self.modelyear))
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

