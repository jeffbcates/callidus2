import time
import multiprocessing
import random
import console
import games
from engine.Regrets import RegretManager
from engine.Signaling import Signaling
from multiprocessing import shared_memory


#some signals
SIGNAL_EPOCH_READY = 0
SIGNAL_SLAVE_READY = 0
SIGNAL_SLAVE_DONE = 5
SIGNAL_EPOCH_START = 1
SIGNAL_EPOCH_STOP = 2
SIGNAL_TRAINING_STOP = 3

class Test:

    RegretMan:RegretManager

    #does this work?
    def multifunc(self, identity, buffer, steps, settings):

        self.RegretMan = RegretManager()
        self.RegretMan.configure("commregrets",games.registeredGames)
        self.RegretMan.open("commregrets")

        #as a test - print settings

        console.writeline("{} testval={} settings = {}".format(identity,self.testvalue, settings))
        console.writeline("{} set={}".format(identity,self.RegretMan.settings["game"]))

        #create a new signaling object as a slave
        signaling = Signaling(name=buffer,identity=identity)

        #continue to process until we receive the stop incom
        signal = SIGNAL_EPOCH_READY
        done = False
        while not done:

            #get the siginal
            signal = signaling.GetSignal()

            #if the end of game signal was received, we are done
            if signal == SIGNAL_TRAINING_STOP:
                print("SLAVE {}: received game end signal".format(identity))
                done = True

            #if the end of epoch signal was reeived
            if signal == SIGNAL_EPOCH_STOP:
                print("SLAVE {}: received end of epoch {} signal, steps = {}".format(identity,signaling.GetRegister(0),signaling.GetRegister(1)))

                #reset our step
                signaling.SetSignal(SIGNAL_SLAVE_READY)

                #wait while our signal value is 2
                signaling.WaitWhileSignal(SIGNAL_EPOCH_STOP)
                print("SLAVE {}: received acknowledgement from master".format(identity))

            #if the start of epoch signal was received
            if signal == SIGNAL_EPOCH_START:
                #acknowledge epoch start signal
                #print("SLAVE {}: received epoch start signal".format(identity))

                #continue for our specified number of work units
                for s in range(1,steps+1):

                    #simulate a variable speed work unit
                    #time.sleep(2 + random.randrange(1,5))
                    time.sleep(1)

                    #signal step
                    signaling.SetSignal(s)

                #as a test - what happens when one slave process dies?
                if identity == 0:
                    x = 1 / 0

                #communicate that we are done with all work units
                signaling.SetSignal(SIGNAL_SLAVE_DONE)

                #wait until signal of completion was received by master
                signaling.WaitForSignal(SIGNAL_EPOCH_STOP)

            #if we received a wait for start signal
            if signal == SIGNAL_EPOCH_READY:

                #wait until we get a new signal (besides zero - which is to wait)
                print("SLAVE {}: waiting for epoch start signal".format(identity))
                signaling.WaitWhileSignal(SIGNAL_EPOCH_READY)

        #end of slave
        print("SLAVE {}: ending workload".format(signal))

    #a sample multiprocessing commmand
    def multi(self):
        #how many cores do we have?
        cores = multiprocessing.cpu_count()
        print("Testing multi-process logic on {} cores".format(cores))
        self.testvalue = 999

        #create our signaling object
        signaling = Signaling(slaves=cores, registers=2)

        #reset signaling (this is actually not needed)
        signaling.Reset()

        #create our processes
        print("Registering Processes",end="",flush=True)
        processes = []
        workunits = 5

        #test passing dict to child process
        settings = {"game":"Commodity","regrets":"commregrets","history":[1,23,4]}

        for c in range(0,cores):
            print(".",end="",flush=True)
            p = multiprocessing.Process(target=self.multifunc, args=(c,signaling.Name(),workunits,settings,))
            p.start()
            processes.append(p)

        #after connecting processes, can we start regret man?
        #self.RegretMan = RegretManager()
        #self.RegretMan.configure("commregrets",games.registeredGames)
        #self.RegretMan.open("commregrets")


        #we are done registering
        print("Done!")

        #simulate epochs and steps
        epochs = 5
        epoch = 1
        steps = workunits * cores

        #keep control of processing and report back to console
        done = False
        while epoch <= epochs:

            #signal the start of the next epoch by passing 1
            signaling.SetRegister(0,epoch)
            signaling.SetSignal(SIGNAL_EPOCH_START)

            #now wait for each process to finish
            running = cores
            while running > 0:

                #the step is actually the sum of all signals from slaves
                #and we know we are running when not all slaves have signal 5
                step = signaling.GetSignal()
                running = signaling.GetActive() - signaling.CountSignal(SIGNAL_SLAVE_DONE)
                signaling.SetRegister(1,step)

                #write out our progress                
                console.progress("Epoch {}".format(epoch),step,steps," {:.0f}% Active".format(signaling.GetActive() / cores * 100))

                #we still have something going on
                time.sleep(1)

            #now that we are done with the epoch, make some updates
            console.writeline()
            epoch += 1

            #acknowledge that we've reveived the end of steps from each slave
            console.writeline("MASTER: Acknowledging Epoch Completion")
            signaling.SetSignal(SIGNAL_EPOCH_STOP)

            #now, wait for all OUTCOMM buffers to be reset to 0
            console.writeline("MASTER: waiting for slaves to reset")
            signaling.WaitForSignal(SIGNAL_SLAVE_READY)

            console.writeline("MASTER: reseting epoch for all slaves")
            signaling.SetSignal(SIGNAL_EPOCH_READY)

        #end all processes
        print("Ending Processes",end="",flush=True)
        signaling.SetSignal(SIGNAL_TRAINING_STOP)

        #wait for them to actually end
        active = cores
        while active > 0:
            active = sum([1 for p in processes if p.is_alive() == True])
            print(".",end="",flush=True)
            time.sleep(1)

        #can we restart the process?
        print("")
        print("All Done!")

        #we are done
        print("From the mothership... we are done!")

