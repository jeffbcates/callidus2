import time 
import random
import multiprocessing
from multiprocessing import shared_memory

class Signaling:

    #our reference to sharable communication buffer
    #and our identity (if we are a slave process)
    buffer = None
    identity = None
    name = None
    master = False
    slaves = None
    registers = 0

    #return the status of slaves (are they alive or dead)
    def GetStatuses(self):

        #reading the buffer occasionally fails (perhaps if reads and writes are simulatneous?)
        #so retry a couple times
        attempts = 0
        while attempts < 5:

            #try this - because sometimes the buffer is unavailable?
            try:

                #internally 1 means a slave is dead, so reverse that
                return [1 - status for status in list(self.buffer)[(-1 * (2 + self.slaves )):-2]]

            except:

                #wait just a split second (10th of a second)
                time.sleep(0.1)

                #add to attempts
                attempts += 1

        #if we got here then we tried 5 times and the buffer never became available
        return [0 for i in range(self.slaves)]

    #how many slaves are alive?
    def GetActive(self):
        return sum(self.GetStatuses())

    #how many slaves are alive?
    def GetInActive(self):
        return self.slaves - sum(self.GetStatuses())

    #how many slaves are there
    def GetTotal(self):
        return self.slaves

    #wait for a signal (as a master wait for all slaves, and as a slave, just wait for the master)
    def WaitWhileSignal(self, signal):

        #if we are master, wait for all slaves to report this signal
        if self.master:

            #wait until all have the same signal (at least for the active ones)
            while self.CountSignal(signal) > self.GetInactive(): time.sleep(1)

        else:

            #wait for a specific signal from the parent
            while self.GetSignal() == signal: time.sleep(1)


    #wait for a signal (as a master wait for all slaves, and as a slave, just wait for the master)
    def WaitForSignal(self, signal):

        #if we are master, wait for all slaves to report this signal
        if self.master:

            #wait until all have the same signal (at least for the active ones)
            while self.CountSignal(signal) < self.GetActive(): time.sleep(1)

        else:

            #wait for a specific signal from the parent
            while self.GetSignal() != signal: time.sleep(1)

    #count how many slaves are at a signal
    def CountSignal(self, signal):

        #if we are master, wait for all slaves to report this signal
        if self.master:
            return len([self.buffer[i] for i in range(0,self.slaves*2) if i % 2 == 1 and self.buffer[i] == signal])
            
    #get a register value -> the slaves will use this for 1-way communication of other values from master
    #like -> for multi-core ML training, the epoch # and overall step #
    def GetRegister(self, register):

        #if this is a valid register, return its value
        if register < self.registers and register >= 0:
            return self.buffer[(-1 * (2 + self.registers - register))]

    #sets a register value (as the master) that can be read by the slaves
    def SetRegister(self, register, value):

        #if this is a valid register, return its value
        if register < self.registers and register >= 0 and self.master:
            self.buffer[(-1 * (2 + self.registers - register))] = value

    #as a master only - > return all signals as an array
    def GetSignals(self):

        #as a master, we can either return the sum of all signals, or an array of signals
        #we use the signal "getsignal" to return the sum, and we use "getsignals" to return the array
        if self.master: return [self.buffer[i] for i in range(0,self.slaves*2) if i % 2 == 1]
        else: return None

    #get a signal value -> either as the master or one of the slaves
    def GetSignal(self):

        #as a master, we can either return the sum of all signals, or an array of signals
        #we use the signal "getsignal" to return the sum, and we use "getsignals" to return the array
        if self.master:  return sum(self.GetSignals())

        #as a slave - only return the master signal for your identity
        else: return self.buffer[self.identity*2]

    #set a signal value -> either as the master or one of the slaves
    def SetSignal(self, signal):

        #the master only sets signal for all slaves        
        if self.master: 
            for i in range(0,self.slaves*2,2): self.buffer[i] = signal
        
        #the slave can only set the signal for itself
        else: self.buffer[self.identity*2 + 1] = signal

    #reset signaling - only the master can do this
    def Reset(self):

        #if we are the master, reset
        if self.master: 
            for i in range(0,self.slaves*2):    
                self.buffer[i] = 0

    #return our buffer name -> which we will need to tell slave processes
    def Name(self):
        return self.name

    #initialize signaling -> if a size is passed, we are the master process
    def __init__(self, slaves=None, name=None, identity=None, registers=0):

        #if we have a # of slaves, we are the master
        if slaves != None:

            #in addition to the regular registers, add 1 register per slave
            #to track if that slave is dead or not
            registers += slaves

            #save slaves and name
            self.slaves = slaves
            self.name = hex(hash(time.time()))
            self.master = True
            self.registers = registers

            #create a buffer for our communication, 2 entries per slave (1 incomm and 1 outcomm + # of registers from master)
            #note that we internally have a register for each slave to track if that slave is alive or not
            self.buffer = shared_memory.ShareableList([0] * ( slaves * 2 + registers + 2), name=self.name)

            #last value is slaves, second to last is registers
            self.buffer[-1] = slaves
            self.buffer[-2] = registers

        else:

            #we are a slave process
            self.master = False
            self.identity = identity
            self.name = name

            #connect to master buffer   
            self.buffer = shared_memory.ShareableList(name=self.name)

            #get the # of slaves and number of registers from the buffer
            self.slaves = self.buffer[-1]
            self.registers = self.buffer[-2]

    #destructor logic
    def __del__(self):

        #we only need to do something when we are the master
        if self.master:

            #destroy the shared memory buffer
            self.buffer.shm.close()
            del self.buffer

        else:

            #flag the slave as dead in our register
            self.buffer[(-1 * (2 + self.slaves - self.identity))] = 1
            self.SetSignal(0)