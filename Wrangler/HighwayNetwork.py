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

    def validateTurnPens(self, CubeNetFile, turnPenReportFile=None, suggestCorrectLink=True):
        import Cube
        turnpens_files = ['turnsam.pen','turnsop.pen','turnspm.pen']
        pen_regex = r'^\s*(?P<frnode>\d+)\s+(?P<thnode>\d+)\s+(?P<tonode>\d+)\s+\d+\s+(?P<pen>-[\d+])'
        if turnPenReportFile:
            outfile = open(turnPenReportFile,'w')
            outfile.write('file,old_from,old_through,old_to,on_street,at_street,new_from,new_through,new_to,note\n')
            
        (nodes_dict, links_dict) = Cube.import_cube_nodes_links_from_csvs(CubeNetFile,
                                                                          extra_link_vars=['LANE_AM', 'LANE_OP','LANE_PM',
                                                                                           'BUSLANE_AM', 'BUSLANE_OP', 'BUSLANE_PM'],
                                                                          extra_node_vars=[],
                                                                          links_csv=os.path.join(os.getcwd(),"cubenet_validate_links.csv"),
                                                                          nodes_csv=os.path.join(os.getcwd(),"cubenet_validate_nodes.csv"),
                                                                          exportIfExists=True)
        found_matches = {}
        
        for file_name in turnpens_files:
            f = open(file_name,'r')
            for line in f:
                text = line.split(';')[0]
                m = re.match(pen_regex, text)
                if m:
                    new_fr = None
                    new_th = None
                    new_to = None
                    from_street = 'missing'
                    to_street = 'missing'
                    fr_node = int(m.groupdict()['frnode'])
                    th_node = int(m.groupdict()['thnode'])
                    to_node = int(m.groupdict()['tonode'])
                    pen     = int(m.groupdict()['pen'])
                    if not (fr_node,th_node) in links_dict:
                        WranglerLogger.debug("HighwayNetwork.validateTurnPens: (%d, %d) not in the roadway network for %s (%d, %d, %d)" % (fr_node,th_node,file_name,fr_node,th_node,to_node))
                        
                        if suggestCorrectLink:
                            new_fr = -1
                            new_th = th_node
                            match_links_fr = []
                            match_links_th = []
                            # if we already found a match for this, don't keep looking.
                            if (fr_node,th_node) in found_matches.keys():
                                match = found_matches[(fr_node,th_node)]
                                new_fr = match[0][1]
                            else:
                                #catch the links matching fr_node on the from end
                                for (a,b) in links_dict.keys():
                                    if a == fr_node:
                                        match_links_fr.append((a,b))
                                    # and links matching th_node on the to end
                                    if b == th_node:
                                        match_links_th.append((a,b))
                                # now take matched links and look for match_links_fr node b to match match_links_th node a
                                for (a1,b1) in match_links_fr:
                                    for (a2,b2) in match_links_th:
                                        if b1 == a2:
                                            #WranglerLogger.info("For link1 (%d, %d) and link2 (%d, %d): %d == %d" % (a1,b1,a2,b2,b1,a2))
                                            found_matches[(fr_node,th_node)] = [(a1,b1),(a2,b2)]
                                            new_fr = a2
                                            # index 1 is streetname
                                            from_street = links_dict[(a2,b2)][1]
                                            break
                    else:
                        new_fr = fr_node
                        from_street = links_dict[(fr_node,th_node)][1]
        
                            
                    if not (th_node,to_node) in links_dict:
                        WranglerLogger.debug("HighwayNetwork.validateTurnPens: (%d, %d) not in the roadway network for %s (%d, %d, %d)" % (th_node,to_node,file_name,fr_node,th_node,to_node))
                        #if turnPenReportFile: outfile.write("%s,%d,%d,outbound link missing from, %d, %d, %d\n" %(file_name,th_node,to_node,fr_node,th_node,to_node))
                        if suggestCorrectLink:
                            new_th = th_node
                            new_to = -1
                            match_links_th = []
                            match_links_to = []
                            # if we already found a match for this, don't keep looking.
                            if (th_node,to_node) in found_matches.keys():
                                match = found_matches[(th_node,to_node)]
                                new_to = match[0][1]
                            else:
                                #catch the links matching fr_node on the from end
                                for (a,b) in links_dict.keys():
                                    if a == th_node:
                                        match_links_th.append((a,b))
                                    # and links matching th_node on the to end
                                    if b == to_node:
                                        match_links_to.append((a,b))
                                # now take matched links and look for match_links_fr node b to match match_links_th node a
                                for (a1,b1) in match_links_th:
                                    for (a2,b2) in match_links_to:
                                        if b1 == a2:
                                            #WranglerLogger.info("For link1 (%d, %d) and link2 (%d, %d): %d == %d" % (a1,b1,a2,b2,b1,a2))
                                            found_matches[(th_node,to_node)] = [(a1,b1),(a2,b2)]
                                            new_to = a2
                                            to_street = links_dict[(a2,b2)][1]
                                            break
                    else:
                        new_to = to_node
                        to_street = links_dict[(th_node,to_node)][1]
                    
                    if new_th != None:
                        #outfile.write('file,old_from,old_through,old_to,on_street,at_street,new_from,new_through,new_to,note\n')
                        print file_name,fr_node,th_node,to_node,from_street,to_street,new_fr,new_th,new_to
                        outfile.write('%s,%d,%d,%d,%s,%s,%d,%d,%d,note\n' % (file_name,fr_node,th_node,to_node,from_street,to_street,new_fr if new_fr else -1,new_th,new_to if new_to else -1))
                
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
            
        if not suppressValidation: self.validateTurnPens(netfile,'turnPenValidations.csv')