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