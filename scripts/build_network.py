import copy,datetime,getopt,logging,os,shutil,sys,time

# use Wrangler from the same directory as this build script
sys.path.insert(0, os.path.join(os.path.dirname(__file__),".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..\_static"))
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

CHAMPVERSION = 5.0
CHAMP_NODE_NAMES = r'Y:\champ\util\nodes.xls'
###############################################################################

###############################################################################
#                                                                             #
#              Helper functions                                               #
#                                                                             #
###############################################################################
def getProjectNameAndDir(project):
    if type(project) == type({'this is':'a dict'}):
        name = project['name']
    else:
        name = project
    (path,name) = os.path.split(name)
    return (path,name)

def getNetworkListIndex(project, networks):
    for proj in networks:
        (path,name) = getProjectNameAndDir(proj)
        if project == name or project == os.path.join(path,name):
            return networks.index(proj)
    return None

def getProjectMatchLevel(left, right):
    (left_path,left_name)   = getProjectNameAndDir(left)
    (right_path,right_name) = getProjectNameAndDir(right)
    match = 0
    if os.path.join(left_path,left_name) == os.path.join(right_path,right_name):
        match = 2
    elif left_name == right_name:
        match = 1
    #Wrangler.WranglerLogger.debug("Match level %d for %s and %s" % (match, os.path.join(left_path,left_name), os.path.join(right_path,right_name)))
    return match

def checkRequirements(REQUIREMENTS, PROJECTS, req_type='prereq', mode='all'):
    if req_type not in ('prereq','coreq','conflict') or mode not in ('any','all'):
        return (None, None)

    if mode=='all':
        found = True
    if mode=='any':
        found = False

    for netmode in REQUIREMENTS.keys():
        for project in REQUIREMENTS[netmode].keys():
            Wrangler.WranglerLogger.info('Checking project %s for %s' %(project,req_type))
            i = getNetworkListIndex(project,PROJECTS[netmode]) if req_type == 'prereq' else len(NETWORK_PROJECTS[netmode]) - 1
            if i == None:
                Wrangler.WranglerLogger.warn('Cannot find the project %s to check its requirements' % project)
                continue

            # check prereqs in the current net type first
            for req in REQUIREMENTS[netmode][project]:
                match_records = []
                (path,name) = getProjectNameAndDir(req)
                if req_type=='conflict':
                    for n in ['hwy','muni','bus','rail']:
                        for possible_match in PROJECTS[n]:
                            match_level = getProjectMatchLevel(possible_match, req)
                            if match_level > 0:
                                (match_path,match_name) = getProjectNameAndDir(possible_match)
                                match_record = {'name':os.path.join(match_path,match_name),'level':match_level,'net_type':n}
                                match_records.append(match_record)
                    REQUIREMENTS[netmode][project][req] = match_records
                else:
                    for possible_match in PROJECTS[netmode][0:i+1]:
                        match_level = getProjectMatchLevel(possible_match, req)
                        if match_level > 0:
                            (match_path,match_name) = getProjectNameAndDir(possible_match)
                            match_record = {'name':os.path.join(match_path,match_name),'level':match_level,'net_type':netmode}
                            match_records.append(match_record)
                    REQUIREMENTS[netmode][project][req] = match_records

                    # if prereqs not found in current net type, check the others
                    if match_records == []:
                        Wrangler.WranglerLogger.debug('No records found for primary network type %s for project %s with prereq %s'
                                                     % (netmode, project, req))
                        other_netmodes = ['muni','rail','bus','hwy']
                        other_netmodes.remove(netmode)
                        Wrangler.WranglerLogger.debug('Checking other modes: %s' % str(other_netmodes))
                        for n in other_netmodes:
                            for possible_match in PROJECTS[n]:
                                match_level = getProjectMatchLevel(possible_match, req)
                                if match_level > 0:
                                    Wrangler.WranglerLogger.debug("OTHER NETS: comparing 'possible_match' %s to 'req' %s" % (possible_match,req))
                                    match_record = {'name':os.path.join(path,name),'level':match_level,'net_type':n}
                                    match_records.append(match_record)
                        REQUIREMENTS[netmode][project][req] = match_records
                if mode == 'all' and REQUIREMENTS[netmode][project][req] == []:
                    found = False
                if mode == 'any' and REQUIREMENTS[netmode][project][req] != []:
                    found = True
                        
    return (REQUIREMENTS, found)

def writeRequirementsToFile(REQUIREMENTS,filename):
    report = open(filename,'w')    
    report.write('project,net_type,prereq,possible_match,match_level,match_type\n')
    for net in REQUIREMENTS.keys():
        for proj in REQUIREMENTS[net].keys():
            for req in REQUIREMENTS[net][proj].keys():
                if REQUIREMENTS[net][proj][req] != []:
                    for match in REQUIREMENTS[net][proj][req]:
                        report.write(proj+','+net+','+req+','+match['name']+','+str(match['level'])+','+match['net_type']+'\n')
                else:
                    report.write(proj+','+net+','+req+',Missing,\n')    

def writeRequirementsToScreen(REQUIREMENTS, req_type='prereq'):
    if req_type=='prereq':
        print_req = 'pre-requisite'
    elif req_type=='coreq':
        print_req = 'co-requisite'
    elif req_type=='conflict':
        print_req = 'conflict'
    else:
        return None

    print "Match type 2:   Perfect match    "
    print "Match type 1:   Possible match   "
    print "Match type 0:   No match         "
    print "------------------------------   "
    
    for net in REQUIREMENTS.keys():
        proj_name_max_width = 22
        print "--------------------------------------------------------------------------------------------"
        print "%s" % net.upper()
        print "--------------------------------------------------------------------------------------------"
        print "                       REQ    NET                          MATCH POSSIBLE               NET "
        print "PROJECT                TYPE   TYPE  %-23sLEVEL %-23sTYPE" % (print_req.upper(), print_req.upper()+' MATCH')
        print "---------------------- ------ ----- ---------------------- ----- ---------------------- ----"
        if REQUIREMENTS[net].keys() == []:
            print "NO %sS FOUND FOR %s NETWORK TYPE" % (print_req.upper(), net.upper())
            
        for proj in REQUIREMENTS[net].keys():
            for req in REQUIREMENTS[net][proj].keys():
                line_to_print = ""
                i = 0
                left_to_get = 0
                while i == 0 or left_to_get > 0:
                    line = ""
                    if i == 0:
                        line_part_one = "%-23s%-7s%-6s%-23s" %(proj[0:proj_name_max_width],req_type[0:6].upper(),
                                                               net, req[0:proj_name_max_width])
                    else:
                        line_part_one = "%-23s%-13s%-23s" % (proj[i*proj_name_max_width:(i+1)*proj_name_max_width],
                                                             "",req[i*proj_name_max_width:(i+1)*proj_name_max_width])

                    left_to_get = max(0, len(proj) - (i+1) * proj_name_max_width)
                    if REQUIREMENTS[net][proj][req] != []:
                        for match in REQUIREMENTS[net][proj][req]:
                            if i == 0:
                                line = line_part_one + "%-6s%-23s%-4s" %(str(match['level']),
                                                                         match['name'][0:proj_name_max_width],match['net_type'])
                            else:
                                line = line_part_one + "%-6s%-23s%-4s" %("",
                                                                         match['name'][i*proj_name_max_width:(i+1)*proj_name_max_width],"")

                            left_to_get = max(left_to_get, len(match['name']) - (i+1) * proj_name_max_width)
                            if line_to_print.isspace():
                                line_to_print = line_to_print + line
                            else:
                                line_to_print = line_to_print + '\n' + line
                            line = "%-59s" % ""
                    else:
                        if line_to_print.isspace():
                            line_to_print = line_part_one + "%-6s%-23s%-4s\n" %("NA","MISSING","NA")
                        else:
                            line_to_print = line_to_print + '\n' + line_part_one + "%-6s%-23s%-4s\n" %("NA","MISSING","NA")
                    i += 1
                print line_to_print
        print '\n'

def getProjectAttributes(project):
    # Start with TAG if not build mode, no kwargs
    project_type    = 'project'
    tag             = None
    kwargs          = {}

    # Use project name, tags, kwargs from dictionary
    if type(project)==type({'this is':'a dictionary'}):
        project_name = project['name']
        if 'tag' in project:    tag = project['tag']
        if 'type' in project:   project_type = project['type']
        if 'kwargs' in project: kwargs = project['kwargs']
        
    # Use Project name directly
    elif type(project)==type("string"):
        project_name = project

    # Other structures not recognized
    else:
         Wrangler.WranglerLogger.fatal("Don't understand project %s" % str(project))

    return (project_name, project_type, tag, kwargs)
###############################################################################

if __name__ == '__main__':
    os.system('mode con:cols=100')
    optlist,args    = getopt.getopt(sys.argv[1:],'c:m:')
    NOW = time.strftime("%Y%b%d.%H%M%S")
    os.environ['CHAMP_NODE_NAMES'] = CHAMP_NODE_NAMES
    
    if len(args) < 1:
        print USAGE
        sys.exit(2)        
    NETWORK_CONFIG  = args[0]
    
    BUILD_MODE  = None # regular
    CONFIG_WORD = None
    TRN_SUBDIR  = "trn"
    HWY_SUBDIR  = "hwy"
    HWY_OUTFILE = "FREEFLOW.NET"

    PRE_REQS = {'hwy':{},'muni':{},'rail':{},'bus':{}}
    CO_REQS = {'hwy':{},'muni':{},'rail':{},'bus':{}}
    CONFLICTS = {'hwy':{},'muni':{},'rail':{},'bus':{}}

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

    # Network Loop #1: check out all the projects, check if they're stale, check if they're the head repository.  Build completed
    # project list so we can check pre-reqs, etc, in loop #2.
    for netmode in ['hwy','muni', 'rail', 'bus']:
        # Build the networks!
        Wrangler.WranglerLogger.info("Checking out %s networks" % netmode)
        clonedcount = 0
        for project in NETWORK_PROJECTS[netmode]:
            (project_name, projType, tag, kwargs) = getProjectAttributes(project)          
##            Wrangler.WranglerLogger.debug('PROJECT ATTRIBUTES--- project_name: %s -- project_type: %s -- tag: %s -- kwargs: %s' % (project_name, projType, tag, str(kwargs)))
            if tag == None: tag = TAG
            
            # test mode - don't use TAG for TEST_PROJECTS
            if BUILD_MODE=="test" and type(TEST_PROJECTS)==type(['List']):
                if project_name in TEST_PROJECTS:
                    Wrangler.WranglerLogger.debug("Skipping tag [%s] because test mode and [%s] is in TEST_PROJECTS" % 
                                                  (TAG, project_name))
                    tag = None                   

            Wrangler.WranglerLogger.debug("Project name = %s" % project_name)

            cloned_SHA1 = None 
            # if project = "dir1/dir2" assume dir1 is git, dir2 is the projectsubdir
            (head,tail) = os.path.split(project_name)
            if head:
                cloned_SHA1 = networks[netmode].cloneProject(networkdir=head, projectsubdir=tail, tag=tag,
                                                              projtype=projType, tempdir=TEMP_SUBDIR, **kwargs)
                (prereqs, coreqs, conflicts) = networks[netmode].getReqs(networkdir=head, projectsubdir=tail, tag=tag,
                                                                         projtype=projType, tempdir=TEMP_SUBDIR)
            else:
                cloned_SHA1 = networks[netmode].cloneProject(networkdir=project_name, tag=tag,
                                                              projtype=projType, tempdir=TEMP_SUBDIR, **kwargs)
                (prereqs, coreqs, conflicts) = networks[netmode].getReqs(networkdir=project_name, projectsubdir=tail, tag=tag,
                                                                         projtype=projType, tempdir=TEMP_SUBDIR)                

            print "Checking projType... %s" % projType
            if projType=='plan':
                #Open specs file and get list of projects
                specFile = os.path.join(TEMP_SUBDIR,NETWORK_PLAN_SUBDIR,'planSpecs.csv')
                PLAN_SPECS = Wrangler.PlanSpecs.PlanSpecs(champVersion=CHAMPVERSION,basedir=Wrangler.Network.NETWORK_BASE_DIR,
                                                          networkdir=project_name,
                                                          plansubdir=Wrangler.Network.NETWORK_PLAN_SUBDIR,
                                                          projectsubdir=Wrangler.Network.NETWORK_PROJECT_SUBDIR,
                                                          tag=tag,
                                                          tempdir=TEMP_SUBDIR, **kwargs)
                plan_project_list = PLAN_SPECS.listOfProjects(netmode)
                i = NETWORK_PROJECTS[netmode].index(project) + 1
                #print "i-value: ", i
                for p in plan_project_list:
                    NETWORK_PROJECTS[netmode].insert(i, p)
                    i+=1
                continue

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
            if cloned_SHA1 != head_SHA1:
                Wrangler.WranglerLogger.warn("Using non-head version of project of %s" % project_name)
                Wrangler.WranglerLogger.warn("  Applying version [%s], Head is [%s]" % (cloned_SHA1, head_SHA1))
                
                cmd = "git log %s..%s" % (cloned_SHA1, head_SHA1)
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
                cmd = 'git show -s --format="%%ct" %s' % cloned_SHA1
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
                
            clonedcount += 1

            if prereqs != []:
                PRE_REQS[netmode][project_name] = {}
                for prereq in prereqs:
                    PRE_REQS[netmode][project_name][prereq] = None
                    
            if coreqs != []:
                CO_REQS[netmode][project_name] = {}
                for coreq in coreqs:
                    CO_REQS[netmode][project_name][coreq] = None
                    
            if conflicts != []:
                CONFLICTS[netmode][project_name] = {}
                for conflict in conflicts:
                    CONFLICTS[netmode][project_name][conflict] = None

    # Check requirements
    prFile = 'prereqs.csv'
    crFile = 'coreqs.csv'
    cfFile = 'conflicts.csv'

    # Check prereqs
    (PRE_REQS, allPrereqsFound) = checkRequirements(PRE_REQS, NETWORK_PROJECTS, req_type='prereq', mode='all')
    writeRequirementsToFile(PRE_REQS,prFile)
    writeRequirementsToScreen(PRE_REQS, req_type='prereq')
    if allPrereqsFound:
        Wrangler.WranglerLogger.debug('All PRE-REQUISITES were found. Are the PRE-REQUISITES matches correct? (y/n)')
    else:
        Wrangler.WranglerLogger.debug('!!!WARNING!!! Some PRE-REQUISITES were not found.  Continue anyway? (y/n)')
    response = raw_input("")
    Wrangler.WranglerLogger.debug("  response = [%s]" % response)
    if response.strip().lower() not in ["y", "yes"]:
        sys.exit(2)
    
    # Check coreqs
    (CO_REQS, allCoreqsFound) = checkRequirements(CO_REQS, NETWORK_PROJECTS, req_type='coreq', mode='all')
    writeRequirementsToFile(CO_REQS,crFile)
    writeRequirementsToScreen(CO_REQS, req_type='coreq')
    if allCoreqsFound:
        Wrangler.WranglerLogger.debug('All CO-REQUISITES were found. Are the CO-REQUISITE matches correct? (y/n)')
    else:
        Wrangler.WranglerLogger.debug('!!!WARNING!!! Some CO-REQUISITES were not found.  Continue anyway? (y/n)')
    response = raw_input("")
    Wrangler.WranglerLogger.debug("  response = [%s]" % response)
    if response.strip().lower() not in ["y", "yes"]:
        sys.exit(2)
        
    # Check conflicts
    (CONFLICTS, anyConflictFound) = checkRequirements(CONFLICTS, NETWORK_PROJECTS, req_type='conflict', mode='any')
    writeRequirementsToFile(CONFLICTS,cfFile)
    writeRequirementsToScreen(CONFLICTS, 'conflict')
    if anyConflictFound:
        Wrangler.WranglerLogger.debug('!!!WARNING!!! Conflicting projects were found.  Continue anyway? (y/n)')
    else:
        Wrangler.WranglerLogger.debug('No conflicting projects were found. Enter \'y\' to continue.')
    response = raw_input("")
    Wrangler.WranglerLogger.debug("  response = [%s]" % response)
    if response.strip().lower() not in ["y", "yes"]:
        sys.exit(2)

    # Network Loop #2: Now that everything has been checked, build the networks.
    for netmode in ['hwy','muni', 'rail', 'bus']:
        Wrangler.WranglerLogger.info("Building %s networks" % netmode)
        appliedcount = 0
        for project in NETWORK_PROJECTS[netmode]:
            (project_name, projType, tag, kwargs) = getProjectAttributes(project)
            if tag == None: tag = TAG

            if projType=='plan':
                continue

            applied_SHA1 = None 
            (head,tail) = os.path.split(project_name)
            if head:
                (parentdir, networkdir, gitdir, projectsubdir) = networks[netmode].getClonedProjectArgs(head, tail, projType, TEMP_SUBDIR)
            else:
                (parentdir, networkdir, gitdir, projectsubdir) = networks[netmode].getClonedProjectArgs(project_name, None, projType, TEMP_SUBDIR)

            applied_SHA1 = networks[netmode].applyProject(parentdir, networkdir, gitdir, projectsubdir)
            appliedcount += 1

    # Network Loop #3: write the networks.
    for netmode in ['hwy','muni', 'rail', 'bus']:
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
    Wrangler.WranglerLogger.debug("Successfully completed running %s" % os.path.abspath(__file__))
    print "Remember to copy MissionLocalDelay.csv from the Muni_2011Oct dir!"
