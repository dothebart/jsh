# jsh
Shell to manage Jenkins jobs

Browser clickediclick in jenkins may become cumbersome if you frequently test/trigger jobs.
This is intended to become the `<cursor up><enter>` for:
- click on job
- click run (with params)
- edit parameters (once more if the defaults weren't right...)
- click 'run'
- wait for the job to start
- click on job in jobs list
- click on 'console output'
...


instead do:

```
jsh.py myServerName run testJob testparam=True
````

And it gets better;
 - copy src/jsh_complete.bash to your bash settings (`/etc/bash_completion.d/`)
 - install jsh.py plus symlink to jsh to your path

and once you've started a fresh shell you will be able to tab expand:

 - jobs
 - parameters to these jobs.


#Dependencies

- jenkinsapi python library `pip3 install jenkinsapi`
- pyYaml

# known issues
- Currently doesn't support jenkins with enabled CSRF-protection
- will auto-continue waiting jobs
- no paralell pipeline and sub jobs support yet