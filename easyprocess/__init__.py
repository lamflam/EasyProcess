'''
Easy to use python subprocess interface.
'''

import ConfigParser
import logging
import os.path
import platform
import shlex
import subprocess
import tempfile
import time
import unicodedata
import threading


__version__ = '0.0.7'

log = logging.getLogger(__name__)
#log=logging

log.debug('version=' + __version__)

# deadlock test fails if USE_FILES=0
USE_FILES = 1

CONFIG_FILE = '.easyprocess.cfg'
SECTION_LINK = 'link'

class EasyProcessError(Exception):
    """  
    """
    def __init__(self, easy_process, msg=''):
        self.easy_process = easy_process
        self.msg = msg
    def __str__(self):
        return self.msg + ' ' + repr(self.easy_process)
    
template = '''cmd={cmd}
OSError={oserror}  
Program install error! '''
class EasyProcessCheckInstalledError(Exception):
    """This exception is raised when a process run by check() returns
    a non-zero exit status or OSError is raised.  
    """
    def __init__(self, easy_process):
        self.easy_process = easy_process
    def __str__(self):
        msg = template.format(cmd=self.easy_process.cmd,
                          oserror=self.easy_process.oserror,
                          )
        if self.easy_process.url:
            msg += '\nhome page: ' + self.easy_process.url
        if platform.dist()[0].lower() == 'ubuntu':
            if self.easy_process.ubuntu_package:
                msg += '\nYou can install it in terminal:\n'
                msg += 'sudo apt-get install %s' % self.easy_process.ubuntu_package
        return msg

class Proc():
    '''
    simple interface for :mod:`subprocess` 

    shell is not supported (shell=False)
    
    '''
    config = None
    
    def __init__(self, cmd, ubuntu_package=None, url=None, max_bytes_to_log=200):
        '''
        :param cmd: string ('ls -l') or list of strings (['ls','-l']) 
        :param max_bytes_to_log: logging of stdout and stderr is limited by this value
        '''
        self.popen = None
        self.stdout = None
        self.stderr = None
        self._stdout_file = None
        self._stderr_file = None
        self.url = url
        self.ubuntu_package = ubuntu_package
        self.is_started = False
        self.oserror = None
        self.cmd_param = cmd
        self._thread = None
        self.max_bytes_to_log = max_bytes_to_log

        if hasattr(cmd, '__iter__'):
            # cmd is string list
            self.cmd = cmd
        else:
            # cmd is string 
            # The shlex module currently does not support Unicode input!
            if  isinstance(cmd, unicode):
                log.debug('unicode is normalized')
                cmd = unicodedata.normalize('NFKD', cmd).encode('ascii', 'ignore')
            self.cmd = shlex.split(cmd)
        self.cmd_as_string = ' '.join(self.cmd) # TODO: not perfect
        
        log.debug('param: "%s" command: %s ("%s")' % (str(self.cmd_param), str(self.cmd), self.cmd_as_string))
        
        if not len(cmd):
            raise EasyProcessError(self, 'empty command!')
        
        if not Proc.config:
            conf_file = os.path.join(os.path.expanduser('~'), CONFIG_FILE)
            log.debug('reading config: %s' % (conf_file))
            Proc.config = ConfigParser.RawConfigParser()
            Proc.config.read(conf_file)
        
        self.alias = None
        try:
            self.alias = Proc.config.get(SECTION_LINK, self.cmd[0])
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        
        if self.alias:
            log.debug('alias found: %s' % (self.alias))
            self.cmd[0] = self.alias

    def __repr__(self):
        msg = '<{cls} cmd_param={cmd_param} alias={alias} cmd={cmd} ({scmd}) oserror={oserror} returncode={return_code} stdout="{stdout}" stderr="{stderr}">'.format(
                            cls=self.__class__.__name__,
                            cmd_param=self.cmd_param,
                            cmd=self.cmd,
                            oserror=self.oserror,
                            alias=self.alias,
                            return_code=self.return_code,
                            stderr=self.stderr,
                            stdout=self.stdout,
                            scmd=' '.join(self.cmd),
                            )
        return msg
        
    @property
    def pid(self):
        '''
        PID (subprocess.Popen.pid)

        :rtype: int
        '''
        if self.popen:
            return self.popen.pid
        
    @property
    def return_code(self):
        '''
        returncode (``subprocess.Popen.returncode``)

        :rtype: int
        '''
        if self.popen:
            return self.popen.returncode

    def check(self, return_code=0):
        '''
        Run command with arguments. Wait for command to complete.
        If the exit code was as expected and there is no exception then return, 
        otherwise raise EasyProcessError.
        
        :param return_code: int, expected return code
        :rtype: self
        '''
#        try:
#            ret = self.call().return_code
#            ok = ret == return_code
#        except Exception as e:
#            log.debug('OSError exception:' + str(oserror))
#            ok = False
#            self.oserror = oserror

        ret = self.call().return_code
        ok = ret == return_code
        if not ok:
            raise EasyProcessError(self, 'check error, return code is not zero!')
        return self

    def check_installed(self):
        '''
        Used for testing if program is installed.
        
        Run command with arguments. Wait for command to complete.
        If OSError raised, then raise :class:`EasyProcessCheckInstalledError`
        with information about program installation
        
        :param return_code: int, expected return code
        :rtype: self
        '''
        try:
            self.call()
        except Exception as e:
            #log.debug('exception:' + str(e))
            #self.oserror = oserror
            raise EasyProcessCheckInstalledError(self)
        return self
    
    def call(self, timeout=None):
        '''
        Run command with arguments. Wait for command to complete.
        
        :rtype: self
        '''
        self.start().wait(timeout=timeout)
        if self.is_alive():
            self.stop()
        return self

    def start(self):
        '''
        start command in background and does not wait for it
        
        :rtype: self
        '''
        if self.is_started:
            raise EasyProcessError(self, 'process was started twice!')

        if USE_FILES:
            self._stdout_file = tempfile.NamedTemporaryFile(prefix='stdout')
            self._stderr_file = tempfile.NamedTemporaryFile(prefix='stderr')
            stdout = self._stdout_file
            stderr = self._stderr_file
            
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE
            
        try:     
            self.popen = subprocess.Popen(self.cmd,
                                  stdout=stdout,
                                  stderr=stderr,
                                  #shell=1,
                                  )
        except OSError, oserror:
            log.debug('OSError exception:' + str(oserror))
            self.oserror = oserror
            raise EasyProcessError(self, 'start error')
        self.is_started = True
        log.debug('process was started (pid=%s)' % (str(self.pid),))

        def target():
            log.debug('Thread started')        
            self._wait4process()
            log.debug('Thread finished')
        
        # original idea from here: 
        # http://stackoverflow.com/questions/1191374/subprocess-with-timeout
        self._thread = threading.Thread(target=target)
        self._thread.start()
        
        return self


    def is_alive(self):
        '''
        poll process (:func:`subprocess.Popen.poll`)
        
        :rtype: bool
        '''
        if self.popen:
            return self.popen.poll() is None
        else:
            return False
        
    def wait(self, timeout=None):
        '''
        Wait for command to complete.
        
        :rtype: self
        '''

        if self._thread:
            self._thread.join(timeout=timeout)
        return self

    def _wait4process(self):
        def remove_ending_lf(s):
            if s.endswith('\n'):
                return s[:-1]
            else:
                return s
            
        def read_output(f):
            half_size = int(self.max_bytes_to_log / 2.0 + 0.5)
            size = 2 * half_size
            # -1 for LF
            if os.path.getsize(f.name) - 1 > size:
                data = f.read(half_size)
                f.seek(-half_size - 1, 2)
                data += '..'
                data += f.read(half_size)
            else:
                data = f.read()
            return data
        
        if self.popen:
            if USE_FILES:    
                self.popen.wait()
                self._stdout_file.seek(0)            
                self._stderr_file.seek(0)            
                self.stdout = read_output(self._stdout_file)
                self.stderr = read_output(self._stderr_file)
            else:
                # This will deadlock when using stdout=PIPE and/or stderr=PIPE 
                # and the child process generates enough output to a pipe such 
                # that it blocks waiting for the OS pipe buffer to accept more data. 
                # Use communicate() to avoid that.
                #self.popen.wait()
                #self.stdout = self.popen.stdout.read()
                #self.stderr = self.popen.stderr.read()
                (self.stdout, self.stderr) = self.popen.communicate()
            log.debug('process has ended')
            self.stdout = remove_ending_lf(self.stdout)
            self.stderr = remove_ending_lf(self.stderr)
            
            log.debug('return code=' + str(self.return_code))
            log.debug('stdout=' + self.stdout)
            log.debug('stderr=' + self.stderr)
        #self.is_started = False
        return self
            
    def stop(self):
        '''
        Kill process by sending SIGTERM.
        and wait for command to complete.
        
        same as ``sendstop().wait()``
        
        :rtype: self
        '''
        return self.sendstop().wait()

    def sendstop(self):
        '''
        Kill process by sending SIGTERM.
        Do not wait for command to complete.
        
        :rtype: self
        '''
        if not self.is_started:
            raise EasyProcessError(self, 'process was not started!')
        
        log.debug('stopping process (pid=%s cmd="%s")' % (str(self.pid), self.cmd))
        if self.popen:
            if self.is_alive():
                log.debug('process is active -> sending SIGTERM')

                #os.kill(self.popen.pid, signal.SIGKILL)
                self.popen.terminate()
            else:
                log.debug('process was already stopped')
        else:
            log.debug('process was not started')

        return self
    
    def sleep(self, sec):
        '''
        sleeping (same as :func:`time.sleep`)

        :rtype: self
        '''
        time.sleep(sec)

        return self

    def wrap(self, callable, delay=0):
        '''
        returns a function which:
        1. start process
        2. call callable, save result
        3. stop process
        4. returns result
        
        :rtype: 
        '''
        def wrapped():
            self.start()   
            if delay:
                self.sleep(delay)
            x = None
            try:     
                x = callable()
            except OSError, oserror:
                log.debug('OSError exception:' + str(oserror))
                self.oserror = oserror
                raise EasyProcessError(self, 'wrap error!')
            finally:
                self.stop()
            return x
        return wrapped

EasyProcess = Proc
