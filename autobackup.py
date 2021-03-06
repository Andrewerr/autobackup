import os
import sys
import logging
import datetime

import paramiko
#TODO:Improve parsing!
logging.basicConfig(filename="autobackup.log", level=logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger=logging.getLogger(__name__)
logger.addHandler(ch)

#TODO:def argcount(fn):
#    def wrapped(self, context, *args, **kwargs):
#        if len(self.args)
class Command:
    def __init__(self, cmdline):
        cmd=cmdline.split(":")
        self.name=cmd[0]
        args=cmd[1:]
        for i,arg in enumerate(args):
            if arg[0]=='!':
                cmd=commands[arg[1:]](arg[1:])
                result=cmd.run(dict())
                args[i]=result["result"]
        self.args=args
                
    def run(self, context, *args, **kwargs):
        pass

class Script:
    commands=[]
    def __init__(self,context):
        self.data=context
    def run(self):
        for command in self.commands:
            try:
                self.data.update(command.run(self.data))
            except Exception as e:
                logging.exception("Failed to run command:"+command.name+":"+str(e))
###ALL COMMANDS###
class ConnectCommand(Command):
    def run(self, context, *args, **kwargs):
        if len(self.args)>=4:
            username=self.args[0]
            password=self.args[1]
            host=self.args[2]
            port=int(self.args[3])
        else:
            host=context["HOST"]
            port=int(context["PORT"])
            username=context["USERNAME"]
            password=context["PASSWORD"]
        client=paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host,username=username,password=password,port=port)
        return {"client":client}

class CloseCommand(Command):
    def run(self, context, *args, **kwargs):
        if "client" in context:
            context["client"].close()
        else:
            logger.error("Could not close connection.No open connections right now.")
        return dict() #Empty dict

class ExecCommand(Command):
    def __init__(self, line):
        self.args=[line]
    def run(self, context, *args, **kwargs):
        #if "client" in context:
        stdin, stdout, stderr = context["client"].exec_command(self.args[0])
        return {"stdin":stdin,"stdout":stdout,"stderr":stderr}

class DumpStdOutCommand(Command):#FIXME:All prechecks
    def run(self, context, *args, **kwargs):
        if len(self.args)<1:
            logger.error("DUMPSTDOUT:requires an argument")
            return dict()
        s=""
        for arg in self.args:
            s+=arg
        with open(self.args[0],"wb") as f:
            f.write(context["stdout"].read())
        logger.info("DUMPSTDOUT:succesfully dumped to file:"+self.args[0])
        return dict()

class TimeCommand(Command):
    def run(self, context, *args, **kwargs):
        return {"result":str(datetime.datetime.now())}

class LogCommand(Command):
    loglevels={"debug":logger.debug,"info":logger.info,"warn":logger.warning,"error":logger.error}
    def run(self, context, *args, **kwargs):
        if len(self.args)<2:
            logger.error("LOG:not enough arguments")
            return dict()
        else:
            level=self.args[0]
            if level not in self.loglevels:
                logger.error("LOG:bad arugment:"+level)
            msg=""
            for i in range(0,len(self.args),1):
                msg+=self.args[i]
            self.loglevels[level](msg)
        return dict()


commands={"CONNECT_SSH":ConnectCommand,"DUMPSTDOUT":DumpStdOutCommand,"CLOSE_SSH":CloseCommand,"LOG":LogCommand,"TIME":TimeCommand}
class Config:
    def __init__(self,fname):
        context=dict()
        f=open(fname)
        line=f.readline()
        while line:
            line = line.split("#")[0]
            line=line.rstrip("\n")
            if line=="!SCRIPT":
                script=Script(context)
                while line and line!="!END":
                    line=f.readline()
                    line=line.rstrip("\n")
                    if line=="!END":
                        break
                    if line=="":
                        continue
                    if line[0]=="!":
                        line=line[1:]
                        cmdname=line.split(":")[0]
                        cmd=commands[cmdname](line)
                        script.commands.append(cmd)
                    else:
                        script.commands.append(ExecCommand(line))
                script.run()
            if line=="":
                line=f.readline()
                continue
            if line!="!END":
                key, value = line.split(":")
                context.update({key: value})
            line=f.readline()
        f.close()

def main():
    for config in os.listdir("/etc/autobackup"):
        Config("/etc/autobackup/"+config)

if __name__=='__main__':
    main()
