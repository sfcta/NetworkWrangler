import os, re, string, subprocess, sys, tempfile
from .Logger import WranglerLogger
from .NetworkException import NetworkException
from .Regexes import git_commit_pattern

__all__ = ['Network']

class Network(object):

    WRANGLER_VERSION        = 2.0
    NETWORK_BASE_DIR        = r"Y:\networks"
    NETWORK_PROJECT_SUBDIR	= ""
    NETWORK_PLAN_SUBDIR     = ""
    NETWORK_SEED_SUBDIR     = ""
    # static variable
    allNetworks = {}

    def __init__(self, champVersion, networkBaseDir=None, networkProjectSubdir=None,
                 networkSeedSubdir=None, networkPlanSubdir=None, networkName=None):
        """
        *champVersion* argument is for compatibility check.
        Currently this should be 4.3 or newer.
        Pass *networkName* to be added to the Networks dictionary
        """
        if type(champVersion) != type(0.0):
            raise NetworkException("Do not understand champVersion %s")

        self.champVersion = champVersion
        self.wranglerVersion = self.WRANGLER_VERSION
        self.appliedProjects = {}
        if networkBaseDir: Network.NETWORK_BASE_DIR = networkBaseDir
        if networkProjectSubdir: Network.NETWORK_PROJECT_SUBDIR = networkProjectSubdir
        if networkSeedSubdir: Network.NETWORK_SEED_SUBDIR = networkSeedSubdir
        if networkPlanSubdir: Network.NETWORK_PLAN_SUBDIR = networkPlanSubdir
        if networkName: Network.allNetworks[networkName] = self

    def _runAndLog(self, cmd, run_dir=".", logStdoutAndStderr=False):
        """
        Runs the given command in the given *run_dir*.  Returns a triple:
         (return code, stdout, stderr)
        where stdout and stderr are lists of strings.
        """
        proc = subprocess.Popen( cmd, cwd = run_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )
        retStdout = []
        for line in proc.stdout:
            line = line.strip('\r\n')
            if logStdoutAndStderr: WranglerLogger.debug("stdout: " + line)
            retStdout.append(line)

        retStderr = []
        for line in proc.stderr:
            line = line.strip('\r\n')
            if logStdoutAndStderr: WranglerLogger.debug("stderr: " + line)
            retStderr.append(line)
        retcode  = proc.wait()
        WranglerLogger.debug("Received %d from [%s] run in [%s]" % (retcode, cmd, run_dir))
        return (retcode, retStdout, retStderr)

    def getReqs(self, networkdir, projectsubdir=None, tag=None, projtype=None, tempdir=None):
        """
        Checks project for pre-requisites, co-requisites, and conflicts

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        (parentdir, networkdir, gitdir, projectsubdir) = self.parseProjArgs(networkdir, projectsubdir, projtype, tempdir)
        prereqs     = self.getAttr('prereqs',parentdir, networkdir, gitdir, projectsubdir)
        coreqs      = self.getAttr('coreqs',parentdir, networkdir, gitdir, projectsubdir)
        conflicts   = self.getAttr('conflicts',parentdir, networkdir, gitdir, projectsubdir)
        return (prereqs, coreqs, conflicts)

    def parseProjArgs(self, networkdir, projectsubdir=None, projtype=None, tempdir=None):
        """
        Gets project arguments to clone and apply projects

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        if tempdir:
            if projtype=='plan':
                joinedBaseDir = os.path.join(Network.NETWORK_BASE_DIR,Network.NETWORK_PLAN_SUBDIR)
                joinedTempDir = os.path.join(tempdir, Network.NETWORK_PLAN_SUBDIR)
            elif projtype=='project':
                joinedBaseDir = os.path.join(Network.NETWORK_BASE_DIR,Network.NETWORK_PROJECT_SUBDIR)
                joinedTempDir = os.path.join(tempdir, Network.NETWORK_PROJECT_SUBDIR)
            elif projtype=='seed':
                joinedBaseDir = os.path.join(Network.NETWORK_BASE_DIR,Network.NETWORK_SEED_SUBDIR)
                joinedTempDir = os.path.join(tempdir, Network.NETWORK_SEED_SUBDIR)
            else:
                joinedBaseDir = Network.NETWORK_BASE_DIR
                joinedTempDir = tempdir
                
            gitdir = os.path.join(joinedTempDir, networkdir)
        else:
            # need if for projtype... and joinedTempDir
            tempdir = tempfile.mkdtemp(prefix="Wrangler_tmp_", dir=".")
            joinedTempDir = tempdir
            WranglerLogger.debug("Using tempdir %s" % tempdir)
            gitdir = os.path.join(tempdir, networkdir)

        try:
            commitstr = self.getCommit(gitdir)
        except:
            gitdir = os.path.join(gitdir, projectsubdir)
            commitstr = self.getCommit(gitdir)
            
        return (joinedTempDir, networkdir, gitdir, projectsubdir)
        
    def getAttr(self, attr_name, parentdir, networkdir, gitdir, projectsubdir=None):
        """        
        Returns attribute for this project based on attr_name
        attr_name: the name of the attribute to get
        parentdir: the directory where the project is found
        networkdir: the directory of the project within parentdir
        gitdir: the checkout location of the network project
        projectsubdir: the subdir if it exists, None otherwise
        """

        if attr_name not in ['year', 'desc', 'champVersion', 'wranglerVersion', 'prereqs', 'coreqs', 'conflicts', 'networks']:
            WranglerLogger.fatal('%s is not a valid attribute type for a network project' % (attr_name))
            return
        
        if projectsubdir:
            projectname = projectsubdir
            sys.path.append(os.path.join(os.getcwd(), parentdir, networkdir))
        else:
            projectname = networkdir
            sys.path.append(os.path.join(os.getcwd(), parentdir))

        try:
            s_projectname = None
            evalstr = "import %s" % projectname
            exec(evalstr)
        except Exception as e:
            #WranglerLogger.debug("error importing module")
            s_projectname = "s"+str(projectname)
            evalstr = "%s = __import__('%s')" % (s_projectname, projectname)
            exec(evalstr)
        evalstr = "dir(%s)" % (projectname if not s_projectname else s_projectname)
        projectdir = eval(evalstr)
        
        # WranglerLogger.debug("projectdir = " + str(projectdir))
        attr_value = (eval("%s.%s()" % ((projectname if not s_projectname else s_projectname),attr_name)))
        return attr_value        
    
    def getChampVersion(self, parentdir, networkdir, gitdir, projectsubdir=None):
        """        
        Returns champVersion range for this project

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        return getAttr('champVersion',parentdir, networkdir,gitdir, projectsubdir)

    def getWranglerVersion(self, parentdir, networkdir, gitdir, projectsubdir=None):
        """        
        Returns wranglerVersion range for this project

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        return getAttr('wranglerVersion',parentdir, networkdir,gitdir, projectsubdir)
    
    def checkVersion(self, version, parentdir, networkdir, gitdir, projectsubdir=None):
        """
        Verifies that this project is compatible with the champVersion or wranglerVersion, raises an exception
          if not

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        if version not in ['champVersion','wranglerVersion']:
            Wrangler.WranglerLogger.fatal("%s is not a valid version.  Must be 'champVersion' or 'wranglerVersion'" % str(version))

        versions = {'champVersion':self.champVersion, 'wranglerVersion':self.wranglerVersion}        
        projVersion = self.getAttr(version, parentdir=parentdir, networkdir=networkdir,
                                   gitdir=gitdir, projectsubdir=projectsubdir)
        WranglerLogger.debug("Checking %s compatibility of project (%s) with requirement (%s)" % 
                             (version, projVersion, versions[version]))

        minVersion = projVersion[0]
        maxVersion = projVersion[1]
        
        if maxVersion == None:
            if versions[version] >= minVersion:
                return
        else:
            if versions[version] >= minVersion and versions[version] <= maxVersion:
                return

        raise NetworkException("Project version range (%d, %d) not compatible with this %s version %d"
                               % (minVersion,maxVersion,version.replace("Version","").upper(),versions[version]))

    def getNetTypes(self, parentdir, networkdir, projectsubdir=None):
        """
        Gets a list of network types for this project

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        if projectsubdir:
            projectname = projectsubdir
            sys.path.append(os.path.join(os.getcwd(), parentdir, networkdir))
        else:
            projectname = networkdir
            sys.path.append(os.path.join(os.getcwd(), parentdir))

        try:
            s_projectname = None
            evalstr = "import %s" % projectname
            exec(evalstr)
        except Exception as e:
            #WranglerLogger.debug("error importing module")
            s_projectname = "s"+str(projectname)
            evalstr = "%s = __import__('%s')" % (s_projectname, projectname)
            exec(evalstr)

        evalstr = "dir(%s)" % (projectname if not s_projectname else s_projectname)
        projectdir = eval(evalstr)
        
        # WranglerLogger.debug("projectdir = " + str(projectdir))
        netTypes = (eval("%s.networks()" % (projectname if not s_projectname else s_projectname)))
        return netTypes
        
    def applyProject(self, parentdir, networkdir, gitdir, projectsubdir=None, **kwargs):
        """
        Implemented by subclasses.  Args are as follows:

        * *parentdir* is the directory we're checking stuff out into (e.g. a temp dir)
        * *networkdir* is the name of the dir within ``Y:\\networks``
        * *gitdir* is the git repo; either the same as *networkdir* if the git repo is at
           that level (the typical case), or it's *networkdir\projectsubdir*
        * *projectsubdir* is an optional subdir of *networkdir*; If the ``apply.s`` or ``__init__.py``
          is in a subdir, this is how it's specified
        * *kwargs* are additional keyword args to pass into the apply()
        
        Returns the SHA1 hash ID of the git commit of the project applied
        """
        pass

    def cloneProject(self, networkdir, projectsubdir=None, tag=None, projtype=None, tempdir=None, **kwargs):
        """
        * *networkdir* corresponds to the dir relative to ``Y:\\networks``
        * *projectsubdir* is a subdir within that, or None if there's no subdir
        * *tag* is "1.0" or "1-latest", or None for just the latest version
        * *tempdir* is the parent dir to put the git clone dir; pass None for python to just choose
        * *kwargs* are additional args for the apply
        
        Returns the SHA1 hash ID of the git commit of the project applied
        """


        if tempdir:
            #gitdir = os.path.join(tempdir, networkdir)

            if projtype=='plan':
                joinedBaseDir = os.path.join(Network.NETWORK_BASE_DIR,Network.NETWORK_PLAN_SUBDIR)
                joinedTempDir = os.path.join(tempdir, Network.NETWORK_PLAN_SUBDIR)
            elif projtype=='project':
                joinedBaseDir = os.path.join(Network.NETWORK_BASE_DIR,Network.NETWORK_PROJECT_SUBDIR)
                joinedTempDir = os.path.join(tempdir, Network.NETWORK_PROJECT_SUBDIR)
            elif projtype=='seed':
                joinedBaseDir = os.path.join(Network.NETWORK_BASE_DIR,Network.NETWORK_SEED_SUBDIR)
                joinedTempDir = os.path.join(tempdir, Network.NETWORK_SEED_SUBDIR)
            else:
                joinedBaseDir = Network.NETWORK_BASE_DIR
                joinedTempDir = tempdir
                
            gitdir = os.path.join(joinedTempDir, networkdir)
            
            if not os.path.exists(joinedTempDir):
                os.makedirs(joinedTempDir)
                
            # if the tempdir exists and it's already here and the projectsubdir is present, 
            # then we already checked it out
            elif projectsubdir and os.path.exists(os.path.join(joinedTempDir,networkdir,projectsubdir)):
                WranglerLogger.debug("Skipping checkout of %s, %s already exists" % 
                                     (networkdir, os.path.join(joinedTempDir,networkdir,projectsubdir)))

                 # verify we didn't require conflicting tags
                try:
                    commitstr = self.getCommit(gitdir)
                except:
                    gitdir = os.path.join(gitdir, projectsubdir)
                    commitstr = self.getCommit(gitdir)

                tags = self.getTags(gitdir, commitstr)
                if tag and (not tags or tag not in tags):
                    # TODO: just checkout to the new tag
                    raise NetworkException("Conflicting tag requirements - FIXME!")

                self.checkVersion(version='champVersion',parentdir=joinedTempDir, networkdir=networkdir,
                                         gitdir=gitdir, projectsubdir=projectsubdir)

                commitstr = self.getCommit(gitdir)
                return commitstr
            
            elif not projectsubdir and os.path.exists(os.path.join(joinedTempDir,networkdir)):
                WranglerLogger.debug("Skipping checkout of %s, %s already exists" % 
                                     (networkdir, os.path.join(joinedTempDir,networkdir)))

                self.checkVersion(version='champVersion',parentdir=joinedTempDir, networkdir=networkdir,
                                         gitdir=gitdir, projectsubdir=projectsubdir)

                # TODO: we should verify we didn't require conflicting tags?
                commitstr = self.getCommit(gitdir)
                return commitstr

        else:
            # need if for projtype... and joinedTempDir
            tempdir = tempfile.mkdtemp(prefix="Wrangler_tmp_", dir=".")
            joinedTempDir = tempdir
            WranglerLogger.debug("Using tempdir %s" % tempdir)
            gitdir = os.path.join(tempdir, networkdir)

        WranglerLogger.debug("Checking out networkdir %s into tempdir %s %s" %
                             (networkdir, joinedTempDir,"for "+projectsubdir if projectsubdir else ""))
        cmd = r"git clone -b master --quiet %s" % os.path.join(joinedBaseDir, networkdir)
        (retcode, retstdout, retstderr) = self._runAndLog(cmd, joinedTempDir)

        if retcode != 0:
            if not projectsubdir:
                raise NetworkException("Git clone failed; see log file")

            # if there was a subdir involved, try checking if the subdir is the git dir
            gitdir = os.path.join(gitdir, projectsubdir)
            newtempdir = os.path.join(joinedTempDir,networkdir)
            if not os.path.exists(newtempdir):
                os.makedirs(newtempdir)

            cmd = r"git clone  -b master --quiet %s" % os.path.join(joinedBaseDir, networkdir, projectsubdir)
            (retcode, retstdout, retstderr) = self._runAndLog(cmd, newtempdir)

        if tag != None:
            cmd = r"git checkout %s" % tag
            print "cmd: %s" % cmd
            print "gitdir: %s" % gitdir
            (retcode, retstdout, retstderr) = self._runAndLog(cmd, gitdir)
            if retcode != 0:
                raise NetworkException("Git checkout failed; see log file")

        self.checkVersion(version='champVersion',parentdir=joinedTempDir, networkdir=networkdir,
                                 gitdir=gitdir, projectsubdir=projectsubdir)

        commitstr = self.getCommit(gitdir)
        return commitstr

    def cloneAndApplyProject(self, networkdir, projectsubdir=None, tag=None, projtype=None, tempdir=None, **kwargs):
        """
        * *networkdir* corresponds to the dir relative to ``Y:\\networks``
        * *projectsubdir* is a subdir within that, or None if there's no subdir
        * *tag* is "1.0" or "1-latest", or None for just the latest version
        * *tempdir* is the parent dir to put the git clone dir; pass None for python to just choose
        * *kwargs* are additional args for the apply
        
        Returns the SHA1 hash ID of the git commit of the project applied
        """
        self.cloneProject(networkdir, projectsubdir, tag, projtype, tempdir, **kwargs)
        (joinedTempDir, networkdir, gitdir, projectsubdir) = self.parseProjArgs(networkdir, projectsubdir, projtype, tempdir)
        return self.applyProject(parentdir=joinedTempDir, networkdir=networkdir,
                                 gitdir=gitdir, projectsubdir=projectsubdir, **kwargs)

    def getCommit(self, gitdir):
        """
        Figures out the SHA1 hash commit string for the given gitdir (so gitdir is a git dir).
        (e.g. a 40-character hex string)
        """
        cmd = r"git log -1"
        (retcode, retstdout, retstderr) = self._runAndLog(cmd, gitdir)
        if len(retstdout)<3:
            raise NetworkException("Git log failed; see log file")
        
        m = re.match(git_commit_pattern, retstdout[0])
        if not m:
            raise NetworkException("Didn't understand git log output: [" + retstdout[0] + "]")

        return m.group(1)

    def getTags(self, gitdir, commitstr):
        """
        Returns a list of all tags for this commit
        """
        cmd = r"git tag --contains " + commitstr
        (retcode, retstdout, retstderr) = self._runAndLog(cmd, gitdir)
        if len(retstdout)==0:
            return None
        return retstdout

    def logProject(self, gitdir, projectname, year=None, projectdesc=None, county=None):
        """
        Figures out the commit string and the tag.  Subclass should figure out the rest.
        Returns the SHA1 hash ID of the git commit of the project applied
        """
        commitstr = self.getCommit(gitdir)
        tag       = self.getTags(gitdir, commitstr)

        if year:
            yearstr = "%4d" % year
        else:
            yearstr = "    "

        WranglerLogger.info("%-4s | %-5s | %-40s | %-40s | %-10s | %s" %
                            (yearstr,
                             tag if tag else "notag",
                             commitstr if commitstr else "",
                             string.lstrip(projectname) if projectname else "",
                             string.lstrip(county) if county else "",
                             string.lstrip(projectdesc) if projectdesc else ""
                             )
                            )
        self.appliedProjects[projectname] = tag if tag else commitstr
        
        return commitstr
                
    def write(self, path='.', name='network', writeEmptyFiles=True, suppressQuery=False, suppressValidation=False):
        """
        Implemented by subclass
        """
        pass