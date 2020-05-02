EasyProcess is an easy to use python subprocess interface.

Links:
 * home: https://github.com/ponty/EasyProcess
 * PYPI: https://pypi.python.org/pypi/EasyProcess

[![Build Status](https://travis-ci.org/ponty/EasyProcess.svg?branch=master)](https://travis-ci.org/ponty/EasyProcess)

Features:
 - layer on top of [subprocess](http://docs.python.org/library/subprocess.html) module
 - easy to start, stop programs
 - easy to get standard output/error, return code of programs
 - command can be list (preferred) or string (command string is converted to list using shlex.split)
 - logging
 - timeout
 - shell is not supported
 - pipes are not supported
 - stdout/stderr is set only after the subprocess has finished
 - stop() does not kill whole subprocess tree
 - unicode support
 - supported python versions: 2.7, 3.6, 3.7, 3.8
 - [Method chaining](https://en.wikipedia.org/wiki/Method_chaining)
 
Basic usage
===========

    >>> from easyprocess import EasyProcess
    >>> EasyProcess('python --version').call().stderr
    'Python 2.7.17'

Installation
============

install:

    pip3 install EasyProcess


Usage
=====

Simple example
--------------

Example program:

    #-- include('examples/hello.py')--#
    from easyprocess import EasyProcess
    import sys

    s = EasyProcess([sys.executable, '-c', 'print "hello"']).call().stdout
    print(s)
    #-#

Output:

    #-- sh('python -m easyprocess.examples.hello')--#
    hello
    #-#


General
-------

The command can be a string list or a concatenated string:
    
    #-- include('examples/cmd.py')--#
    from easyprocess import EasyProcess

    print('-- Run program, wait for it to complete, get stdout (command is string):')
    s=EasyProcess('python -c "print 3"').call().stdout
    print(s)

    print('-- Run program, wait for it to complete, get stdout (command is list):')
    s=EasyProcess(['python','-c','print 3']).call().stdout
    print(s)

    print('-- Run program, wait for it to complete, get stderr:')
    s=EasyProcess('python --version').call().stderr
    print(s)

    print('-- Run program, wait for it to complete, get return code:')
    s=EasyProcess('python --version').call().return_code
    print(s)

    print('-- Run program, wait 1 second, stop it, get stdout:')
    s=EasyProcess('ping localhost').start().sleep(1).stop().stdout
    print(s)

    #-#

Output:

    #-- sh('python -m easyprocess.examples.cmd')--#
    -- Run program, wait for it to complete, get stdout (command is string):
    3
    -- Run program, wait for it to complete, get stdout (command is list):
    3
    -- Run program, wait for it to complete, get stderr:
    Python 2.7.6
    -- Run program, wait for it to complete, get return code:
    0
    -- Run program, wait 1 second, stop it, get stdout:
    PING localhost (127.0.0.1) 56(84) bytes of data.
    64 bytes from localhost (127.0.0.1): icmp_seq=1 ttl=64 time=0.017 ms
    64 bytes from localhost (127.0.0.1): icmp_seq=2 ttl=64 time=0.034 ms
    #-#

Shell commands
--------------

Shell commands are not supported.

.. warning:

  ``echo`` is a shell command on Windows (there is no echo.exe),
  but it is a program on Linux.

return_code
-----------

`EasyProcess.return_code` is None until
`EasyProcess.stop` or `EasyProcess.wait` is called.

With
----

By using `with` statement the process is started
and stopped automatically:
    
    from easyprocess import EasyProcess
    with EasyProcess('ping 127.0.0.1') as proc: # start()
        # communicate with proc
        pass
    # stopped
    
Equivalent with:
    
    from easyprocess import EasyProcess
    proc = EasyProcess('ping 127.0.0.1').start()
    try:
        # communicate with proc
        pass
    finally:
        proc.stop()


Timeout
-------

This was implemented with "daemon thread".

"The entire Python program exits when only daemon threads are left."
http://docs.python.org/library/threading.html:

    #-- include('examples/timeout.py')--#
    from easyprocess import EasyProcess

    s = EasyProcess('ping localhost').call(timeout=2).stdout
    print(s)
    #-#

Output:

    #-- sh('python -m easyprocess.examples.timeout')--#
    PING localhost (127.0.0.1) 56(84) bytes of data.
    64 bytes from localhost (127.0.0.1): icmp_seq=1 ttl=64 time=0.018 ms
    64 bytes from localhost (127.0.0.1): icmp_seq=2 ttl=64 time=0.037 ms
    64 bytes from localhost (127.0.0.1): icmp_seq=3 ttl=64 time=0.025 ms
    #-#


Replacing existing functions
----------------------------

Replacing os.system:

    retcode = os.system("ls -l")
    ==>
    p = EasyProcess("ls -l").call()
    retcode = p.return_code
    print(p.stdout)

Replacing subprocess.call:

    retcode = subprocess.call(["ls", "-l"])
    ==>
    p = EasyProcess(["ls", "-l"]).call()
    retcode = p.return_code
    print(p.stdout)




     

   
