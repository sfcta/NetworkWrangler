import copy,datetime,getopt,logging,os,shutil,sys,time

# use Wrangler from the same directory as this build script
sys.path.insert(0, os.path.realpath("."))
sys.path.insert(0, r"Y:\Users\Drew\NetworkWrangler")
import Wrangler
from Wrangler import PlanSpecs


USAGE = """

  python build_network.py [-c configword] [-m test] network_specification.py

  Builds a network using the specifications in network_specification.py, which should
  define the variables listed below (in this script)
  
  If test mode is specified (with -m test), then the following happen:
  
    * networks are built in OUT_DIR\TEST_hwy and OUT_DIR\TEST_trn
    * RTP projects are not applied
    * TAG is not used for TEST_PROJECTS
    
    (Yes, you could just specify "-t" but I want you to spell it out. :)

  The [-c configword] is if you want an optional word for your network_specification.py
  (e.g. to have multiple scenarios in one file).  Access it via CONFIG_WORD.
  
  This script will warn if TAG is behind HEAD or if the project is older than
  two years.  For building non-test networks, the user
  has to explicitly OK this.

"""

###############################################################################
#                                                                             #
#              Define the following in an input configuration file            #
#                                                                             #
###############################################################################
# MANDATORY. Set this to be the Project Name.
# e.g. "19thAve", "CentralCorridor" 
PROJECT = None

# MANDATORY. Set this to be the model year for the model run. e.g. 2012, 2040.
YEAR = None

# MANDATORY. Set this to be the Scenario Name
# e.g. "Base", "Baseline"
SCENARIO = None

# MANDATORY. Set this to be the git tag for checking out network projects.
TAG = None

# OPTIONAL. If you are building on top of a previously built network, this
# should be set to the location of those networks.  This should be a directory
# which has "hwy" and "trn" subdirectories.
PIVOT_DIR = None

# OPTIONAL. If PIVOT_DIR is specified, MANDATORY.  Specifies year for PIVOT_DIR.
PIVOT_YEAR = None

# MANDATORY. Set this to the directory in which to write your outputs. 
# "hwy" and "trn" subdirectories will be created here.
OUT_DIR = None

# MANDATORY. Set this to the directory with initial transit capacity
# configuration. Typically this is Y:\networks\TransitVehicles or PIVOT_DIR\trn
TRANSIT_CAPACITY_DIR = None

# MANDATORY unless YEAR==PIVOT_YEAR.  Location of coded
# Regional Transportation Projects (RTP) in Y:\networks
NONSF_RTPDIR = "2040_Plan_Bay_Area_Outside_SF"
# MANDATORY unless YEAR==PIVOT_YEAR.  Location of RTP configuration
# (Ref#, Corridor, Action, Span, County, RTP YEar, RTP FUNDING, Model Year)
NONSF_RTPCONFIG = "2040_PlanBayArea_specs.csv"

# MANDATORY.  Should be a dictionary with keys "hwy", "muni", "rail", "bus"
# to a list of projects.  A project can either be a simple string, or it can be
# a dictionary with with keys 'name', 'tag' (optional), and 'kwargs' (optional)
# to specify a special tag or special keyword args for the projects apply() call.
# For example:
#     {'name':"Muni_TEP", 'kwargs':{'servicePlan':"'2012oct'"}}
NETWORK_PROJECTS = None

# OPTIONAL. The default route network project directory is Y:\networks.  If
# projects are stored in another directory, then use this variable to specify it.
# For example: Y:\networks\projects
NETWORK_BASE_DIR = None
NETWORK_PROJECT_SUBDIR = None
NETWORK_SEED_SUBDIR = None
NETWORK_PLAN_SUBDIR = None

# OPTIONAL. A list of project names which have been previously applied in the
# PIVOT_DIR network that projects in this project might rely on.  For example
# if DoyleDrive exists, then Muni_TEP gets applied differently so transit lines
# run on the new Doyle Drive alignment
APPLIED_PROJECTS = None

# OPTIONAL.  A list of project names.  For test mode, these projects won't use
# the TAG.  This is meant for developing a network project.
TEST_PROJECTS = None

CHAMPVERSION = 4.3
###############################################################################

if __name__ == '__main__':
    optlist,args    = getopt.getopt(sys.argv[1:],'c:m:')
    NOW = time.strftime("%Y%b%d.%H%M%S")
    
    if len(args) < 1:
        print USAGE
        sys.exit(2)        
    NETWORK_CONFIG  = args[0]
    
    BUILD_MODE  = None # regular
    CONFIG_WORD = None
    TRN_SUBDIR  = "trn"
    HWY_SUBDIR  = "hwy"
    HWY_OUTFILE = "FREEFLOW.NET"

    for o,a in optlist:
        if o=="-m": BUILD_MODE = a
        if o=="-c": CONFIG_WORD = a
        
    if BUILD_MODE not in [None,"test"]:
        print USAGE
        sys.exit(2)
    
    if BUILD_MODE=="test":
        TRN_SUBDIR = "TEST_trn"
        HWY_SUBDIR = "TEST_hwy"        

    # Read the configuration
    execfile(NETWORK_CONFIG)
    
    # Verify mandatory fields are set
    if PROJECT==None:
        print "PROJECT not set in %s" % NETWORK_CONFIG
        sys.exit(2)
    if YEAR==None:
        print "YEAR not set in %s" % NETWORK_CONFIG
        sys.exit(2)
    if SCENARIO==None:
        print "SCENARIO not set in %s" % NETWORK_CONFIG
        sys.exit(2)
    if TAG==None:
        print "TAG not set in %s" % NETWORK_CONFIG
        sys.exit(2)
    if OUT_DIR==None:
        print "OUT_DIR not set in %s" % NETWORK_CONFIG
        sys.exit(2)
    if TRANSIT_CAPACITY_DIR==None:
        print "TRANSIT_CAPACITY_DIR not set in %s" % NETWORK_CONFIG
        sys.exit(2)
    if NETWORK_PROJECTS==None:
        print "NETWORK_PROJECTS not set in %s" % NETWORK_CONFIG
        sys.exit(2)

    # Set up logging
    LOG_FILENAME = "build%snetwork_%s_%d%s_%s.info.LOG" % ("TEST" if BUILD_MODE=="test" else "", PROJECT, YEAR, SCENARIO, NOW)
    Wrangler.setupLogging(LOG_FILENAME, LOG_FILENAME.replace("info", "debug"))
    Wrangler.TransitNetwork.capacity = Wrangler.TransitCapacity(directory=TRANSIT_CAPACITY_DIR)

    # Prepend the RTP roadway projects (if applicable -- not TEST mode and YEAR!=PIVOT_YEAR)
    NONSF_PLANBAYAREA_SPECS = None
    if BUILD_MODE != "test" and YEAR!=PIVOT_YEAR:
        
        NONSF_PLANBAYAREA_SPECS = Wrangler.HwySpecsRTP(NONSF_RTPCONFIG)

        # get the list of projects themselves
        nonsf_projlist = NONSF_PLANBAYAREA_SPECS.listOfProjects(maxYear=YEAR)

        # prepend the appropriate directory
        nonsf_projdirlist = [os.path.join(NONSF_RTPDIR,rtpref) for rtpref in nonsf_projlist]

        # prepend the whole list to the hwy projects
        NETWORK_PROJECTS['hwy'] = nonsf_projdirlist + NETWORK_PROJECTS['hwy']

    # Create a scratch directory to check out project repos into
    SCRATCH_SUBDIR = "scratch"
    TEMP_SUBDIR    = "Wrangler_tmp_" + NOW    
    if not os.path.exists(SCRATCH_SUBDIR): os.mkdir(SCRATCH_SUBDIR)
    os.chdir(SCRATCH_SUBDIR)
    
    # Initialize networks
    networks = {'hwy' :Wrangler.HighwayNetwork(champVersion=CHAMPVERSION,
                                               basenetworkpath=os.path.join(PIVOT_DIR,"hwy") if PIVOT_DIR else "Roads2010",
                                               networkBaseDir=NETWORK_BASE_DIR,
                                               networkProjectSubdir=NETWORK_PROJECT_SUBDIR,
                                               networkSeedSubdir=NETWORK_SEED_SUBDIR,
                                               networkPlanSubdir=NETWORK_PLAN_SUBDIR,
                                               isTiered=True if PIVOT_DIR else False,
                                               tag=TAG,
                                               hwyspecsdir=NONSF_RTPDIR,
                                               hwyspecs=NONSF_PLANBAYAREA_SPECS,
                                               tempdir=TEMP_SUBDIR,
                                               networkName="hwy"),
                'muni':Wrangler.TransitNetwork(champVersion=CHAMPVERSION,
                                               basenetworkpath=os.path.join(PIVOT_DIR,"trn") if PIVOT_DIR else None,
                                               networkBaseDir=NETWORK_BASE_DIR,
                                               networkProjectSubdir=NETWORK_PROJECT_SUBDIR,
                                               networkSeedSubdir=NETWORK_SEED_SUBDIR,
                                               networkPlanSubdir=NETWORK_PLAN_SUBDIR,
                                               isTiered=True if PIVOT_DIR else False,
                                               networkName="muni"),
                'rail':Wrangler.TransitNetwork(champVersion=CHAMPVERSION,
                                               basenetworkpath=os.path.join(PIVOT_DIR,"trn") if PIVOT_DIR else None,
                                               networkBaseDir=NETWORK_BASE_DIR,
                                               networkProjectSubdir=NETWORK_PROJECT_SUBDIR,
                                               networkSeedSubdir=NETWORK_SEED_SUBDIR,
                                               networkPlanSubdir=NETWORK_PLAN_SUBDIR,
                                               isTiered=True if PIVOT_DIR else False,
                                               networkName="rail"),
                'bus' :Wrangler.TransitNetwork(champVersion=CHAMPVERSION,
                                               basenetworkpath=os.path.join(PIVOT_DIR,"trn") if PIVOT_DIR else None,
                                               networkBaseDir=NETWORK_BASE_DIR,
                                               networkProjectSubdir=NETWORK_PROJECT_SUBDIR,
                                               networkSeedSubdir=NETWORK_SEED_SUBDIR,
                                               networkPlanSubdir=NETWORK_PLAN_SUBDIR,
                                               isTiered=True if PIVOT_DIR else False,
                                               networkName="bus")
                }

    # For projects applied in a pivot network (because they won't show up in the current project list)
    if APPLIED_PROJECTS != None:
        for proj in APPLIED_PROJECTS:
            networks['hwy'].appliedProjects[proj]=TAG
            
    # Initialize output subdirectories    
    hwypath=os.path.join(OUT_DIR,HWY_SUBDIR)
    if not os.path.exists(hwypath): os.makedirs(hwypath)
    trnpath = os.path.join(OUT_DIR,TRN_SUBDIR)
    if not os.path.exists(trnpath): os.makedirs(trnpath)

#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
# ---------- New stuff here: iterate through network projects and build full network list.  Once list is build, then check out 
# ---------- projects sequentially and check prereqs.  This goes after networks are initialized because projects are checked-out
# ---------- by networks.
#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
##    for netmode in ['hwy','muni','rail','bus']:
##        #read/gather nework list
##        Wrangler.WranglerLogger.info("Gathering network list for %s" % netmode)
##
##        for project in NETWORK_PROJECT[netmode]:
##            projType    = 'project'
##            tag         = TAG
##            kwargs      = {}
##            
##            # Use project name, tags, kwargs from dictionary
##            if type(project)==type({'this is':'a dictionary'}):
##                project_name = project['name']
##                if 'tag' in project:    tag = project['tag']
##                if 'type' in project:   projType = project['type']
##                if 'kwargs' in project: kwargs = project['kwargs']
##
##                
##            # Use Project name directly
##            elif type(project)==type("string"):
##                project_name = project

#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
# ---------- End new stuff
# ---------- 
#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------

    for netmode in ['hwy','muni', 'rail', 'bus']:
        
        # Build the networks!
        Wrangler.WranglerLogger.info("Building %s networks" % netmode)
        appliedcount = 0
        for project in NETWORK_PROJECTS[netmode]:
            
            # Start with TAG if not build mode, no kwargs
            projType = 'project'
            tag    = TAG
            kwargs = {}

            # Use project name, tags, kwargs from dictionary
            if type(project)==type({'this is':'a dictionary'}):
                project_name = project['name']
                if 'tag' in project:    tag = project['tag']
                if 'type' in project:   projType = project['type']
                if 'kwargs' in project: kwargs = project['kwargs']
                
            # Use Project name directly
            elif type(project)==type("string"):
                project_name = project

            # Other structures not recognized
            else:
                 Wrangler.WranglerLogger.fatal("Don't understand project %s" % str(project))
            
            # test mode - don't use TAG for TEST_PROJECTS
            if BUILD_MODE=="test" and type(TEST_PROJECTS)==type(['List']):
                if project_name in TEST_PROJECTS:
                    Wrangler.WranglerLogger.debug("Skipping tag [%s] because test mode and [%s] is in TEST_PROJECTS" % 
                                                  (TAG, project_name))
                    tag = None                   

            print "Checking projType... %s" % projType
            if projType=='plan':
                #Open specs file and get list of projects
                specFile = os.path.join(project_name,'planSpecs.csv')
                PLAN_SPECS = Wrangler.PlanSpecs.PlanSpecs(basedir=Wrangler.Network.NETWORK_BASE_DIR,
                                                          networkdir=project_name,
                                                          plansubdir=Wrangler.Network.NETWORK_PLAN_SUBDIR,
                                                          projectsubdir=Wrangler.Network.NETWORK_PROJECT_SUBDIR,
                                                          tag=tag,
                                                          tempdir=TEMP_SUBDIR, **kwargs)
                plan_project_list = PLAN_SPECS.listOfProjects(netmode)
                i = NETWORK_PROJECTS[netmode].index(project) + 1
                print "i-value: ", i
                for p in plan_project_list:
                    if type(p) is dict:
                        p['name'] = os.path.join(project_name,p['name'])
                        NETWORK_PROJECTS[netmode].insert(i, p)
                    else:
                        NETWORK_PROJECTS[netmode].insert(i, os.path.join(project_name,p))
                    i+=1
                continue

            Wrangler.WranglerLogger.debug("Project name = %s" % project_name)

            applied_SHA1 = None 
            # if project = "dir1/dir2" assume dir1 is git, dir2 is the projectsubdir
            (head,tail) = os.path.split(project_name)
            if head:
##                applied_SHA1 = networks[netmode].cloneAndApplyProject(networkdir=head, projectsubdir=tail, tag=tag,
##                                                                      projtype=projType, tempdir=TEMP_SUBDIR, **kwargs)
                applied_SHA1 = networks[netmode].cloneProject(networkdir=head, projectsubdir=tail, tag=tag,
                                                              projtype=projType, tempdir=TEMP_SUBDIR, **kwargs)
            else:
##                applied_SHA1 = networks[netmode].cloneAndApplyProject(networkdir=project_name, tag=tag,
##                                                                      projtype=projType, tempdir=TEMP_SUBDIR, **kwargs)
                applied_SHA1 = networks[netmode].cloneProject(networkdir=project_name, tag=tag,
                                                              projtype=projType, tempdir=TEMP_SUBDIR, **kwargs)

            # get any 
            # find out if the applied project is behind HEAD
            # get the HEAD SHA1
            cmd = r"git show-ref --head master"
            if projType=='project':
                join_subdir = Wrangler.Network.NETWORK_PROJECT_SUBDIR
            if projType=='seed':
                join_subdir = Wrangler.Network.NETWORK_SEED_SUBDIR
                
            cmd_dir = os.path.join(Wrangler.Network.NETWORK_BASE_DIR, join_subdir, project_name)
            (retcode, retStdout, retStderr) = networks[netmode]._runAndLog(cmd, run_dir = cmd_dir)
            # Wrangler.WranglerLogger.debug("results of [%s]: %s %s %s" % (cmd, str(retcode), str(retStdout), str(retStderr)))
            if retcode != 0: # this shouldn't happen -- wouldn't cloneAndApply have failed?
                Wrangler.WranglerLogger.fatal("Couldn't run cmd [%s] in [%s]: stdout=[%s] stderr=[%s]" % \
                                              (cmd, cmd_dir, str(retStdout), str(retStderr)))
                sys.exit(2)
            head_SHA1 = retStdout[0].split()[0]
            
            # if they're different, log more information and get approval (if not in test mode)
            if applied_SHA1 != head_SHA1:
                Wrangler.WranglerLogger.warn("Using non-head version of project of %s" % project_name)
                Wrangler.WranglerLogger.warn("  Applying version [%s], Head is [%s]" % (applied_SHA1, head_SHA1))
                
                cmd = "git log %s..%s" % (applied_SHA1, head_SHA1)
                (retcode, retStdout, retStderr) = networks[netmode]._runAndLog(cmd, run_dir = cmd_dir)
                Wrangler.WranglerLogger.warn("  The following commits are not included:") 
                for line in retStdout:
                    Wrangler.WranglerLogger.warn("    %s" % line)

                # test mode => warn is sufficient
                # non-test mode => get explicit approval                    
                if BUILD_MODE !="test":
                    Wrangler.WranglerLogger.warn("  Is this ok? (y/n) ")
                    response = raw_input("")
                    Wrangler.WranglerLogger.debug("  response = [%s]" % response)
                    if response.strip().lower()[0] != "y":
                        sys.exit(2)
            
            # find out if the project is stale
            else:
                cmd = 'git show -s --format="%%ct" %s' % applied_SHA1
                (retcode, retStdout, retStderr) = networks[netmode]._runAndLog(cmd, run_dir = cmd_dir)
                applied_commit_date = datetime.datetime.fromtimestamp(int(retStdout[0]))
                applied_commit_age = datetime.datetime.now() - applied_commit_date
                
                # if older than one year, holler
                STALE_YEARS = 2
                if applied_commit_age > datetime.timedelta(days=365*STALE_YEARS):
                    Wrangler.WranglerLogger.warn("  This project was last updated %.1f years ago (over %d), on %s" % \
                                                 (applied_commit_age.days/365.0, 
                                                  STALE_YEARS, applied_commit_date.strftime("%x"))) 
                    if BUILD_MODE !="test":
                        Wrangler.WranglerLogger.warn("  Is this ok? (y/n) ")
                        response = raw_input("")
                        Wrangler.WranglerLogger.debug("  response = [%s]" % response)
                        if response.strip().lower() not in ["y", "yes"]:
                            sys.exit(2)
                
            appliedcount += 1
        
        # Write the networks! 
        if netmode == 'hwy':
            networks[netmode].write(path=hwypath,name=HWY_OUTFILE,suppressQuery=True)
        else:
            networks[netmode].write(path=trnpath, 
                                    name=netmode,
                                    suppressQuery = True if BUILD_MODE=="test" else False,
                                    suppressValidation = False, cubeNetFileForValidation = os.path.join(hwypath, HWY_OUTFILE))

    # Write the transit capacity configuration
    Wrangler.TransitNetwork.capacity.writeTransitVehicleToCapacity(directory = trnpath)
    Wrangler.TransitNetwork.capacity.writeTransitLineToVehicle(directory = trnpath)
    Wrangler.TransitNetwork.capacity.writeTransitPrefixToVehicle(directory = trnpath)

    # build transit report
    transit_freqs_by_line = {}  # line name => [freq_am,  freq_md,  freq_pm,  freq_ev,  freq_ea ] as strings
    transit_vtypes_by_line = {} # line name => (vtype_am, vtype_md, vtype_pm, vtype_ev, vtype_ea)
    for netmode in ['muni', 'rail', 'bus']:
        for line in networks[netmode]:
            transit_freqs_by_line[line.name] = line.getFreqs()
            transit_vtypes_by_line[line.name] = (Wrangler.TransitNetwork.capacity.getSystemAndVehicleType(line.name, "AM")[1],
                                                 Wrangler.TransitNetwork.capacity.getSystemAndVehicleType(line.name, "MD")[1],
                                                 Wrangler.TransitNetwork.capacity.getSystemAndVehicleType(line.name, "PM")[1],
                                                 Wrangler.TransitNetwork.capacity.getSystemAndVehicleType(line.name, "EV")[1],
                                                 Wrangler.TransitNetwork.capacity.getSystemAndVehicleType(line.name, "EA")[1])
    # print it
    os.chdir("..")  # get out of the scratch subdir
    transit_report_filename = 'transitreport_%s_%s_%d%s_%s.csv' % \
                            ("TEST" if BUILD_MODE=="test" else "", PROJECT, YEAR, SCENARIO, NOW)
    transit_report = open(transit_report_filename, 'w')
    transit_report.write("Source: %s\n" % transit_report_filename)
    transit_report.write(",Headways,,,,,,TransitVehicles\n")
    transit_report.write("Line Name,AM,MD,PM,EV,EA,,AM,MD,PM,EV,EA\n")
    for line_name in sorted(transit_freqs_by_line.keys()):
        transit_report.write("%s,%s,%s,%s,%s,%s,,%s,%s,%s,%s,%s\n" %
                             (line_name,
                              transit_freqs_by_line[line_name][0],
                              transit_freqs_by_line[line_name][1],
                              transit_freqs_by_line[line_name][2],
                              transit_freqs_by_line[line_name][3],
                              transit_freqs_by_line[line_name][4],
                              transit_vtypes_by_line[line_name][0],
                              transit_vtypes_by_line[line_name][1],
                              transit_vtypes_by_line[line_name][2],
                              transit_vtypes_by_line[line_name][3],
                              transit_vtypes_by_line[line_name][4]))
    transit_report.close()
    Wrangler.WranglerLogger.debug("Wrote transit report to %s" % transit_report_filename)

    # special!
    Wrangler.WranglerLogger.debug("Successfully completed running %s" % os.path.abspath(__file__))
    print "Remember to copy MissionLocalDelay.csv from the Muni_2011Oct dir!"
