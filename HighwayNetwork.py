import os, re, shutil, subprocess
from socket         import gethostname

from .HwySpecsRTP import HwySpecsRTP
from .Logger import WranglerLogger
from .Network import Network
from .NetworkException import NetworkException

__all__ = ['HighwayNetwork']

class HighwayNetwork(Network):
    """
    Representation of a roadway network.
    """
    cube_hostnames = None

    @staticmethod
    def getCubeHostnames():
        """
        Cube hostnames in Y:\COMMPATH\HostnamesWithCube.txt
        """
        # got them already
        if HighwayNetwork.cube_hostnames: return HighwayNetwork.cube_hostnames
        
        # read them
        HighwayNetwork.cube_hostnames = []
        f = open(r"Y:\COMMPATH\HostnamesWithCube.txt")
        for line in f:
            if line[0] == "#": continue
            HighwayNetwork.cube_hostnames.append(line.split()[0])  # use the first token of non-comment lines
        f.close()
        return HighwayNetwork.cube_hostnames

    def __init__(self, champVersion, basenetworkpath, networkBaseDir=None, networkProjectSubdir=None,
                 networkSeedSubdir=None, networkPlanSubdir=None, isTiered=False, tag=None,
                 hwyspecsdir=None, hwyspecs=None, tempdir=None, networkName=None, tierNetworkName=None):
        """
        *basenetworkpath* should be a starting point for this network, and include a ``FREEFLOW.net``,
        as well as ``turns[am,pm,op].pen`` files.  
        Also a shapefile export: FREEFLOW.[dbf,prj,shp] and FREEFLOW_nodes.[dbf,prj,shp]

        *isTiered*: when False, checks out the *basenetworkpath* from Y:\networks.  When True,
        expects the basenetwork path to be a fullpath and uses that.  Can optionally specify tierNetworkName
        (an alternative to `FREEFLOW.net`.)

        *tag*: when not *isTiered*, a tag can optionally be used for cloning the base network
        
        *hwyspecs*, if passed in, should be an instance of :py:class:`HwySpecsRTP`.  It
        is only used for logging.
        """
        Network.__init__(self, champVersion, networkBaseDir, networkProjectSubdir, networkSeedSubdir,
                         networkPlanSubdir, networkName)
        
        if isTiered:
            (head,tail) = os.path.split(basenetworkpath)
            self.applyBasenetwork(head,tail,None, tierNetworkName)
        else:
            self.applyingBasenetwork = True
            self.cloneAndApplyProject(networkdir=basenetworkpath,tempdir=tempdir, projtype='seed', tag=tag)

        # keep a reference of the hwyspecsrtp for logging
        self.hwyspecsdir = hwyspecsdir
        self.hwyspecs = hwyspecs
        
    def applyBasenetwork(self, parentdir, networkdir, gitdir, tierNetworkName):
        
        # copy the base network file to my workspace
        tierNetwork = os.path.join(parentdir,networkdir,tierNetworkName if tierNetworkName else "FREEFLOW.net")
        WranglerLogger.debug("Using tier network %s" % tierNetwork)
        shutil.copyfile(tierNetwork,"FREEFLOW.BLD")
        for filename in ["turnsam.pen",         "turnspm.pen",          "turnsop.pen"]:
            shutil.copyfile(os.path.join(parentdir,networkdir,filename), filename)

        # done
        self.applyingBasenetwork = False

    def applyProject(self, parentdir, networkdir, gitdir, projectsubdir=None, **kwargs):
        """
        Applies a roadway project by calling ``runtpp`` on the ``apply.s`` script.
        By convention, the input to ``apply.s`` is ``FREEFLOW.BLD`` and the output is 
        ``FREEFLOW.BLDOUT`` which is copied to ``FREEFLOW.BLD`` at the end of ``apply.s``

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        # special case: base network
        if self.applyingBasenetwork:
            self.applyBasenetwork(parentdir, networkdir, gitdir, tierNetworkName=None)
            self.logProject(gitdir=gitdir,
                            projectname=(networkdir + "\\" + projectsubdir if projectsubdir else networkdir),
                            projectdesc="Base network")            
            return
        
        if projectsubdir:
            applyDir = os.path.join(parentdir, networkdir, projectsubdir)
            applyScript = "apply.s"
            descfilename = os.path.join(parentdir, networkdir, projectsubdir,"desc.txt")
            turnsfilename = os.path.join(parentdir, networkdir, projectsubdir, "turns.pen")
        else:
            applyDir = os.path.join(parentdir, networkdir)
            applyScript = "apply.s"
            descfilename = os.path.join(parentdir, networkdir,'desc.txt')
            turnsfilename = os.path.join(parentdir, networkdir, "turns.pen")

        # read the description
        desc = None
        try:
            desc = open(descfilename,'r').read()
        except:
            pass
        
        # move the FREEFLOW.BLD into place
        shutil.move("FREEFLOW.BLD", os.path.join(applyDir,"FREEFLOW.BLD"))

        # dispatch it, cube license
        hostname = gethostname().lower()
        if hostname not in HighwayNetwork.getCubeHostnames():
            print "Dispatching cube script to taraval from %s" % hostname 
            f = open(os.path.join(applyDir,'runtpp_dispatch.tmp'), 'w')
            f.write("runtpp " + applyScript + "\n")
            f.close()
            (cuberet, cubeStdout, cubeStderr) = self._runAndLog("Y:/champ/util/bin/dispatch.bat runtpp_dispatch.tmp taraval", run_dir=applyDir, logStdoutAndStderr=True) 
        else:
            (cuberet, cubeStdout, cubeStderr) = self._runAndLog(cmd="runtpp "+applyScript, run_dir=applyDir)
            

        nodemerge = re.compile("NODEMERGE: \d+")
        linkmerge = re.compile("LINKMERGE: \d+-\d+")
        for line in cubeStdout:
            line = line.rstrip()
            if re.match(nodemerge,line): continue
            if re.match(linkmerge,line): continue
            WranglerLogger.debug(line)
        
        if cuberet != 0 and cuberet != 1:
            WranglerLogger.fatal("FAIL! Project: "+applyScript)
            raise NetworkException("HighwayNetwork applyProject failed; see log file")

        # move it back
        shutil.move(os.path.join(applyDir,"FREEFLOW.BLD"), "FREEFLOW.BLD")

        # append new turn penalty file to mine
        if os.path.exists(turnsfilename):
            for filename in ["turnsam.pen", "turnspm.pen", "turnsop.pen"]:
                newturnpens = open(turnsfilename, 'r').read()
                turnfile = open(filename, 'a')
                turnfile.write(newturnpens)
                turnfile.close()
                WranglerLogger.debug("Appending turn penalties from "+turnsfilename)

        WranglerLogger.debug("")
        WranglerLogger.debug("")

        year    = None
        county  = None
        if (networkdir==self.hwyspecsdir and
            self.hwyspecs and
            projectsubdir in self.hwyspecs.projectdict):
            year    = self.hwyspecs.projectdict[projectsubdir]["MOD YEAR"]
            county  = self.hwyspecs.projectdict[projectsubdir]["County"]
            desc    = (self.hwyspecs.projectdict[projectsubdir]["Facility"] + ", " +
                       self.hwyspecs.projectdict[projectsubdir]["Action"] + ", " +
                       self.hwyspecs.projectdict[projectsubdir]["Span"])

        return self.logProject(gitdir=gitdir,
                               projectname=(networkdir + "\\" + projectsubdir if projectsubdir else networkdir),
                               year=year, projectdesc=desc, county=county)

    def write(self, path='.', name='FREEFLOW.NET', writeEmptyFiles=True, suppressQuery=False, suppressValidation=False):
        if not os.path.exists(path):
            WranglerLogger.debug("\nPath [%s] doesn't exist; creating." % path)
            os.mkdir(path)

        else:
            netfile = os.path.join(path,"FREEFLOW.net")
            if os.path.exists(netfile) and not suppressQuery:
                print "File [%s] exists already.  Overwrite contents? (y/n/s) " % netfile
                response = raw_input("")
                WranglerLogger.debug("response = [%s]" % response)
                if response == "s" or response == "S":
                    WranglerLogger.debug("Skipping!")
                    return

                if response != "Y" and response != "y":
                    exit(0)

        shutil.copyfile("FREEFLOW.BLD",os.path.join(path,name))
        WranglerLogger.info("Writing into %s\\%s" % (path, name))
        WranglerLogger.info("")

        for filename in ["turnsam.pen",         "turnspm.pen",          "turnsop.pen"]:
            shutil.copyfile(filename, os.path.join(path, filename))
