#!/usr/bin/python3
import sys, os, json, yaml, signal

from jenkinsapi.jenkins import Jenkins

from jenkinsapi.utils.crumb_requester import CrumbRequester


config = {
    'server' : [{
        'name': 'myServerName',
        'url': 'http://127.0.0.1:8080/',
        'user': 'test',
        'password': 'test'

        }]
    }

thisBuild = None

def signal_handler(signal, frame):
    global thisBuild
    print('You pressed Ctrl+C!')
    if thisBuild != None:
        print("canceling job: ")
        thisBuild.stop()
        sys.exit(0)

def GetParamsFromArgv(offset):
    params={}
    where=offset
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
        moreData = rc.headers.get('X-More-Data')
        moreData = (moreData != None) and (moreData == 'true')

        consoleAnotator=rc.headers.get('X-ConsoleAnnotator')
        pollStart = int(rc.headers.get('X-Text-Size'))
        if len(rc.text) > 0:
            print(rc.text, file=fdout)

if __name__=='__main__':
    try:
        cfgfile = open('.jsh/config.yaml', 'r')
    except:
        print('\nno config ".jsh/config.yaml" found. Printing sample config and exit.\n\n')
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

    params = GetParamsFromArgv(4)

    job = jenkins[jobName]

    qi = job.invoke(build_params=params)

    print('waiting for build to start')
    qi.block_until_building()
    # Block this script until build is finished
    print('now running')
    thisBuild=job.get_build(qi.get_build_number())

    pollJob(thisBuild.baseurl, sys.stdout)
