#imports
import sys
import browser

#run our process
if __name__ == "__main__":
    
    #run browser with parameters
    rb = browser.Browser().browse([s.upper() for s in sys.argv[1:]])
