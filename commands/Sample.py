#imports
import commands as broker
import console
import time
import copy

_dispatcher = {}

def _copy_list(l, dispatch):
    ret = l.copy()
    for idx, item in enumerate(ret):
        cp = dispatch.get(type(item))
        if cp is not None:
            ret[idx] = cp(item, dispatch)
    return ret

def _copy_dict(d, dispatch):
    ret = d.copy()
    for key, value in ret.items():
        cp = dispatch.get(type(value))
        if cp is not None:
            ret[key] = cp(value, dispatch)

    return ret

_dispatcher[list] = _copy_list
_dispatcher[dict] = _copy_dict

def deepcopy(sth):
    cp = _dispatcher.get(type(sth))
    if cp is None:
        return sth
    else:
        return cp(sth, _dispatcher)


#a sample command group with some sample commands
class Sample(broker.CommandGroup):

    #a simple test command
    def timetrial(self,parameters):

        #get a sample dictionary (use regretman settings)
        r = broker.state["regretman"]
        sample = r.settings
        count = 100000
        console.writeline("Deep Copying {} Times...".format(count))
        start = time.time()
        for c in range(1,count):
            x = deepcopy(sample)
        end = time.time()
        print("Total Time: {}, c/s = {:.2f}".format(end-start,count/(end-start)))

    #a simple test command
    def test(self,parameters):

        #get a sample dictionary (use regretman settings)
        r = broker.state["regretman"]
        sample = r.settings
        count = 100000
        console.writeline("Deep Copying {} Times...".format(count))
        start = time.time()
        for c in range(1,count):
            x = deepcopy(sample)
        end = time.time()
        print("Total Time: {}, c/s = {:.2f}".format(end-start,count/(end-start)))


    #we implement a register method
    def registerCommands(self):

        #add our commands to the broker
        broker.registerCommand("test",self.test,0,"Tests commands",["this","is","a","test"])

#register our command group
broker.registerCommandGroup("Sample", Sample())

