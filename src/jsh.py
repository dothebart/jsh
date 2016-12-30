#!/usr/bin/python3
import sys, os, re, json, yaml, signal

from jenkinsapi.jenkins import Jenkins

from jenkinsapi.utils.crumb_requester import CrumbRequester

# testfd=open('/tmp/test.txt', 'a+')
config = {
    'server' : [{
        'name': 'myServerName',
        'url': 'http://127.0.0.1:8080/',
        'user': 'test',
        'password': 'test',
        'default': True
        }],
    'jobParameters' : {
        'someJobName': {
            'testParam': 'default value',
            'anotherParam': 'other value'

            }
        }
    }

thisBuild = None

def signal_handler(signal, frame):
    global thisBuild
    print('You pressed Ctrl+C!')
    if thisBuild != None:
        print("canceling job: ")
        thisBuild.stop()
        sys.exit(0)

def GetParamsFromArgv(offset, jobName):
    params={}
    where=offset
    if jobName in config['jobParameters']:
        params = config['jobParameters'][jobName]
    while where < len(sys.argv):
        kv=sys.argv[where].split('=')
        params[kv[0]] = kv[1]
        where += 1
    return params

def getServerConfig():
    retServer = None
    defServerName = ""
    for nArg in range(0, len(sys.argv)-1):
        if sys.argv[nArg] == '--server':
            defServerName = sys.argv[nArg + 1]
    
    for server in config['server']:
        if server['default'] == True:
            retServer = server        
        if server['name'] == serverName: 
            retServer = server
            break
    return retServer

def JenkinsFromConfig(serverName):
    retServer = getServerConfig()
    if (retServer == None):
        print("no server by name '%s' found!" % serverName)
        raise
    return (retServer['name'],
            Jenkins(retServer['url'],
                    username=retServer['user'],
                    password=retServer['password'],
                    requester=CrumbRequester(baseurl=retServer['url'],
                                             username=retServer['user'],
                                            password=retServer['password']
                                             )
                    )
            )

proceedRX = re.compile(".*'([/a-zA-Z0-9]*proceedEmpty).*'([/a-zA-Z0-9]*abort).*")

def pollJob(url, fdout):
    pollStart=0
    consoleAnotator=''
    moreData = True
    while moreData:
        postHttpHeaders= {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        if (consoleAnotator != None) and len(consoleAnotator) > 0:
            postHttpHeaders['X-ConsoleAnnotator']=consoleAnotator
        
        rc = jenkins.requester.post_and_confirm_status(
            url + '/logText/progressiveText',
            #url + '/logText/progressiveHtml',
            data={
                'start': pollStart
            },
            headers=postHttpHeaders
        )
        if len(rc.text) > 0:
            print(rc.text, file=fdout)

            if rc.text.find('Proceed or Abort') >= 0:
                # for now: auto-approve. TODO: user input.
                searchrc = jenkins.requester.post_and_confirm_status(
                    url + '/logText/progressiveHtml',
                    data={
                        'start': 0
                    },
                    headers=postHttpHeaders
                )
                foundUrls = proceedRX.search(searchrc.text)
                proceedUrl = foundUrls.group(1)
                
                AbortUrl = foundUrls.group(2)
                proceedRc = jenkins.requester.post_and_confirm_status(
                    jenkins.baseurl + proceedUrl,
                    data = {'foo': 'bar'}
                )

        moreData = rc.headers.get('X-More-Data')
        moreData = (moreData != None) and (moreData == 'true')

        consoleAnotator=rc.headers.get('X-ConsoleAnnotator')
        pollStart = int(rc.headers.get('X-Text-Size'))

def startJob(job):
    qi = job.invoke(build_params=params)

    print('waiting for build to start')
    qi.block_until_building()
    # Block this script until build is finished
    print('now running')

    return job.get_build(qi.get_build_number())

def getCompleteState():
    connectString=' '
    escapeBlanks = str.maketrans({" ":  r"\ "})
    if len(sys.argv) < 5:
        print("autocompletion failed", file=sys.stderr)
        return

    copleteType = int(sys.argv[2])
    completeIndex = int(sys.argv[3])
    
    if len(sys.argv) < 6 or (len(sys.argv) == 6 and completeIndex == 1):
        print("COMPREPLY=(run get scan)")
        return

    serverCfg = getServerConfig()
    if serverCfg == None:
        print("unable to detect server to autocomplete against, define default or specify one.")
        return
    
    ServerName = serverCfg['name']
    cacheFile = open(os.environ['HOME'] + '/.jsh/' + ServerName + '.json', 'r')
    jobs = json.load(cacheFile)
    command = sys.argv[5]
    orgArgv = sys.argv[6:]

    if command == 'run':
        if len(orgArgv) == 0 or (len(orgArgv) == 1 and completeIndex == 2):
            matchingJobStrings=[]
            if len(orgArgv) == 0:
                matchingJobStrings = jobs.keys()
            else: # we need to filter:
                matchStr = orgArgv[0]
                for hint in jobs.keys():
                    if hint.startswith(matchStr): 
                        matchingJobStrings.append(hint)
            completionString = (connectString.join('"' + hint.translate(escapeBlanks)  + '"' for hint in matchingJobStrings))
            print("COMPREPLY=(" + completionString + ')')
            return

        jobName = orgArgv[0]
        if jobName in jobs and jobs[jobName]['hasParams']:
            params = jobs[jobName]
            defaultParams=[]
            if jobName in config['jobParameters']:
                defaultParams = config['jobParameters'][jobName]
            paramHints=[]
            paramDocu='\n'
            for paramName in params['params'].keys():
                param = params['params'][paramName]
                if param['type'] == 'BooleanParameterDefinition':
                    if param['defaultParameterValue']:
                        paramHints.append(paramName + '=True')
                        paramHints.append(paramName + '=False')
                    else:
                        paramHints.append(paramName + '=False')
                        paramHints.append(paramName + '=True')
                    paramDocu += "%s: (Boolean) %s\n" % (paramName, param['description'])
                elif param['type'] == 'StringParameterDefinition':
                    paramDocu += "%s: (%s) %s\n" % (paramName, param['type'], param['description'])
                    if param['defaultParameterValue'] != '':
                        paramHints.append(paramName + "=" + param['defaultParameterValue'])
                else:
                    paramHints.append(paramName + "='" + param['defaultParameterValue'].replace('\n', r'\n') + "'")
                    
                    paramDocu += "%s: (%s No auto suggestions) %s\n" % (paramName, param['type'], param['description'])

            matchingParams=[]
            if len(orgArgv) + 1 < completeIndex:
                matchingParams = paramHints
            else: # we need to filter:
                matchStr = orgArgv[completeIndex - 2]
                for hint in paramHints:
                    if hint.startswith(matchStr): 
                        matchingParams.append(hint)
            
            if copleteType == 63 and len(matchingParams) > 1:
                print(paramDocu, file=sys.stderr)

            completionString = (connectString.join('"' + hint.translate(escapeBlanks)  + '"' for hint in matchingParams))
            
            print("COMPREPLY=(" + completionString + ')')
        return
    print("failed")
    
def ScanServer(jenkins, ServerName):
    cacheFile = open(os.environ['HOME'] + '/.jsh/' + ServerName + '.json', 'w')
    Jobs = {}
    for (jobName, job) in jenkins.items():
        thisJob = {}
        thisJob['hasParams'] = job.has_params()
        thisJob['params'] = {}
        for param in job.get_params():
            thisJob['params'][param['name']] = {
                'type': param['type'],
                'description': param['description'],
                'defaultParameterValue': param['defaultParameterValue']['value'],
            }
            
        Jobs[jobName] = thisJob
    print(json.dumps(Jobs), file=cacheFile)
    
if __name__=='__main__':
    try:
        cfgfile = open(os.environ['HOME'] + '/.jsh/config.yaml', 'r')
    except:
        print('\nno config "%s/.jsh/config.yaml" found. Printing sample config and exit.\n\n' % os.environ['HOME'])
        print(yaml.safe_dump(config, default_flow_style=False))
        
        exit(1)

    confstr = cfgfile.read()
    cfgfile.close()
    config = yaml.safe_load(confstr)

    serverName = None # sys.argv[1]
    command = sys.argv[1]
    if command == 'complete':
        getCompleteState()
        sys.exit(0)

    (ServerName, jenkins) = JenkinsFromConfig(serverName)

    signal.signal(signal.SIGINT, signal_handler)

    #print(jenkins.items())
    #print(jenkins[jobName].has_params())
    #print(jenkins[jobName].get_params_list())

    if command == 'run':
        jobName = sys.argv[2]
        params = GetParamsFromArgv(3, jobName)
        thisBuild = startJob(jenkins[jobName])
        pollJob(thisBuild.baseurl, sys.stdout)
        thisBuild.block_until_complete()
    elif command == 'get':
        pollJob(thisBuild.baseurl, sys.stdout)
    elif command == 'scan':
        ScanServer(jenkins, ServerName)
