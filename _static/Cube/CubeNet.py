# -*- coding: utf-8 -*-
"""

 This is based on scripts/walkSkims/gothroughme/cube/cubeNet.py
 But I left the original in place because of the dependency on the network object, which I didn't want
 to bring in here (as the functionality we want is more simplistic).
  -Lisa 2012.03.12

"""
import copy, os
from socket import gethostname

CUBE_COMPUTER = "vanness"

def getCubeHostnames():
    """
    Cube hostnames in Y:\COMMPATH\HostnamesWithCube.txt
    """
    hostnames = []
    f = open(r"Y:\COMMPATH\HostnamesWithCube.txt")
    for line in f:
        if line[0] == "#": continue
        hostnames.append(line.split()[0])  # use the first token of non-comment lines
    f.close()
    return hostnames
    
def export_cubenet_to_csvs(file, extra_link_vars=[], extra_node_vars=[], 
                              links_csv=None, nodes_csv=None):
    """
    Export cube network to csv files
    If *links_csv* and *nodes_csv* filenames passed, will use those.
    Otherwise, will output into %TEMP%\link.csv and %TEMP%\node.csv
    
    options:
        extra_link_vars, extra_node_vars: list extra variables to export
    """
    import subprocess
    script   = os.path.join(os.path.dirname(os.path.abspath(__file__)),"exportHwyfromPy.s")
    
    #set environment variables
    env = copy.copy(os.environ)
    
    env['CUBENET']=file 
    env['PATH'] = os.environ['PATH'] # inherit this
    
    if links_csv:
        env["CUBELINK_CSV"] = links_csv
    else:
        env["CUBELINK_CSV"] = os.path.join(os.environ["TEMP"], "link.csv")
    if nodes_csv:
        env["CUBENODE_CSV"] = nodes_csv
    else:
        env["CUBENODE_CSV"] = os.path.join(os.environ["TEMP"], "node.csv")
        
    if len(extra_link_vars)>0:
        extra_vars_str=","
        extra_vars_str+=extra_vars_str.join(extra_link_vars)
        env['XTRALINKVAR']=extra_vars_str
    else:
        env['XTRALINKVAR']=''

    if len(extra_node_vars)>0:
        extra_vars_str=","
        extra_vars_str+=extra_vars_str.join(extra_node_vars)
        env['XTRANODEVAR']=extra_vars_str
    else:
        env['XTRANODEVAR']=' '    
    
    #run it on CUBE_COMPUTER; cube is installed there
    filedir = os.path.dirname(os.path.abspath(file))
    hostname = gethostname().lower()
    if hostname not in getCubeHostnames():
        if links_csv == None or nodes_csv == None:
            print "export_cubenet_to_csvs requires a links_csv and nodes_csv output file if dispatching to %s (temp won't work)" % CUBE_COMPUTER
            sys.exit(2)
             
        env["MACHINES"] = CUBE_COMPUTER
        
        cmd = r'y:\champ\util\bin\dispatch-one.bat "runtpp ' + script + '"'
        print cmd
        proc = subprocess.Popen( cmd, cwd = filedir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        for line in proc.stdout:
            line = line.strip('\r\n')
            print "stdout: " + line
    else:
        cmd = 'runtpp.exe ' + script 
        print cmd
        print filedir
        
        proc = subprocess.Popen( cmd, cwd = filedir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        for line in proc.stdout:
            line = line.strip('\r\n')
            print "stdout: " + line
            
     
    print "EXPORTING CUBE NETWORK: ",env['CUBENET']
    print "...adding variables %s, %s:" % (env['XTRALINKVAR'], env['XTRANODEVAR'])
    print "...running script: \n      %s" % (script)
    


    retStderr = []
    for line in proc.stderr:
        line = line.strip('\r\n')
        print "stderr: " + line
    retcode  = proc.wait()
    if retcode != 0: raise


    print "Received %d from [%s]" % (retcode, cmd)
    print "Exported network to: %s, %s" % (env["CUBELINK_CSV"], env["CUBENODE_CSV"])

    
def import_cube_nodes_links_from_csvs(cubeNetFile,
                                          extra_link_vars=[], extra_node_vars=[],
                                          links_csv=None, nodes_csv=None,
                                          exportIfExists=True):
    """
    Imports cube network from network file and returns (nodes_dict, links_dict).
    
    Nodes_dict maps node numbers to [X, Y, vars given by *extra_node_vars*]
    
    Links_dict maps (a,b) to [DISTANCE, STREETNAME, *extra_link_vars*]
    """

    if not links_csv:
        links_csv=os.path.join(os.environ['TEMP'],"link.csv")
    if not nodes_csv:
        nodes_csv=os.path.join(os.environ['TEMP'],"node.csv")

    # don't export if
    if (not exportIfExists and links_csv and nodes_csv and 
        os.path.exists(links_csv) and os.path.exists(nodes_csv)):
        pass # don't need to do anything
    else:
        export_cubenet_to_csvs(cubeNetFile,extra_link_vars, extra_node_vars, links_csv=links_csv, nodes_csv=nodes_csv)

    
    # Open node file and read nodes
    nodes_dict = {}    
    F=open(nodes_csv,mode='r')
    for rec in F:
        r=rec.strip().split(',')
        n=int(r[0])
        x=float(r[1])
        y=float(r[2])
        node_array = [x,y]
        node_array.extend(r[3:])
        
        nodes_dict[n] = node_array
    F.close()
    
    # Open link file and read links
    links_dict = {}
    F=open(links_csv,mode='r')
    for rec in F:
        r=rec.strip().split(',')
        
        #add standard fields
        a=int(r[0])
        b=int(r[1])
        dist=float(r[2])
        streetname=str(r[3])

        #add additional fields        
        link_array = [dist, streetname]
        link_array.extend(r[4:])
        
        links_dict[(a,b)] = link_array
    F.close()

    return (nodes_dict, links_dict)


