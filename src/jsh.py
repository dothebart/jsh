#!/usr/bin/python3
import sys, os, re, json, yaml, signal

from jenkinsapi.jenkins import Jenkins

from jenkinsapi.utils.crumb_requester import CrumbRequester


config = {
    'server' : [{
        'name': 'myServerName',
        'url': 'http://127.0.0.1:8080/',
        'user': 'test',
        'password': 'test'

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
        
def JenkinsFromConfig(serverName):
    for server in config['server']:
        if server['name'] == serverName: 
            return Jenkins(server['url'], username=server['user'], password=server['password'])
    print("no server by name '%s' found!" % serverName)
    raise

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

    serverName=sys.argv[1]
    command=sys.argv[2]
    jobName = sys.argv[3]

    jenkins = JenkinsFromConfig(serverName)

    signal.signal(signal.SIGINT, signal_handler)

    print(jenkins.items())
    print(jenkins[jobName].has_params())
    print(jenkins[jobName].get_params_list())

    params = GetParamsFromArgv(4, jobName)

    job = jenkins[jobName]

    qi = job.invoke(build_params=params)

    print('waiting for build to start')
    qi.block_until_building()
    # Block this script until build is finished
    print('now running')
    thisBuild=job.get_build(qi.get_build_number())

    pollJob(thisBuild.baseurl, sys.stdout)
    thisBuild.block_until_complete()
