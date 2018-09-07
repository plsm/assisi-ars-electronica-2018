'''
listen out for messages from the bee arena's master nodes

load config file, open several sockets for connecting
use timeout as per cmd-line switch interval
optionally log data as well
'''
import yaml, json
import zmq
import time, os, argparse
from collections import deque
import threading


#{{{ colors
# equivalent to import, but keep the present code more independent
#from inter_domset.iface import clrs
class clrs(object):
    _C_OKBLUE =  '\033[94m'
    _C_OKGREEN = '\033[92m'
    _C_ENDC = '\033[0m'
    END     = '\033[0m'
    _C_WARNING = '\033[93m'
    _C_FAIL = '\033[91m'
    _C_TEST = '\033[2;32;40m'
    _C_ERR  = '\033[1;31m'
#}}}

#{{{ convenience functions
def parse_payload(payload):
    ''' given a message payload with the formatting
    "key1:value; key2:value; ..."
    extract the info and return a map
    '''
    newdat = {}
    for elem in payload.strip().split(";"):
        if not len(elem): continue
        parts = elem.split(':')
        if len(parts) >= 2:
            field, val = parts[0:2]
            newdat[field.strip()] = val
    return newdat
#}}}
#{{{ BeeArenaListener
class BeeArenaListener(object):

    #{{{ initialisation
    def __init__(self, proj_conf, pth, name='bee_relay', logfile=None,
                 verb=False, buflen=15):
        self.iface_name = name
        self._proj_conf_file = proj_conf
        self.pth = pth

        self.verb = verb
        self.stop = True
        self.init_log(logfile)

        self.load_config()
        self.load_subscribe_list()

        self.context = zmq.Context(1)
        self._incoming_data = {
            k:deque(maxlen=buflen) for k in self.dsnode_to_masters }

        # now establish sockets in each direction
        self.init_listen_socket()
    #}}}

    #{{{ log handling.
    def init_log(self, logfile):
        self.logging = False
        if logfile is not None:
            self.logfile_name = logfile
            self.logging = True
        if not self.logging:
            return

        # this one is different because it needs to be WRITE not APPEND
        with open(self.logfile_name, "w") as lf:
            lf.write("# Started logging data BeeArena -> ISI at {}\n".format(
                time.time()) )


    def justlog(self, msg, isdata=True):
        '''
        silently writes log msg to file; IF logging is already launched
        '''
        if self.logging:
            t = time.time()
            cmt = ""
            if isdata is False:
                cmt = "#"
            with open(self.logfile_name, "a") as lf:
                lf.write("{}{}| {} \n".format(cmt, t, msg))

    def displog(self, msg, isdata=True, clr=""):
        '''
        prints with color to terminal and logs message to file without

        if isdata is False, add comment char at start

        '''
        print(clr+msg+clrs.END)
        t = time.time()
        cmt = ""
        if isdata is False:
            cmt = "#"

        if self.logging:
            with open(self.logfile_name, "a") as lf:
                lf.write("{}{}| {} \n".format(cmt, t, msg))
    #}}}




    #{{{ input config parsing
    def load_config(self):
        self.proj_conf = os.path.expanduser(os.path.join(self.pth, self._proj_conf_file))
        with open(self.proj_conf) as _f:
            self.cfg = yaml.safe_load(_f)
            setup = self.cfg.get('problem_setup')
            if setup is None:
                raise

            self.dbfile = os.path.join(self.pth, setup['dbfile'])
            self.allocfile = os.path.join(self.pth, setup['allocfile'])
            self.graphfile = os.path.join(self.pth, setup['graphfile'])

    def load_subscribe_list(self, ):
        '''
        given the master nodes in the allocfile, and the port/addr data for
        all casus in the dbfile, get the relevant tcp ports to subsrcribe to
        listen whole arena.

        '''
        with open(self.dbfile) as _f:
            self._casu_info = yaml.safe_load(_f)
        with open(self.allocfile) as _f:
            self.alloc = yaml.safe_load(_f)

        # look up all of the required physical info based on the
        # casus in the problem definition
        self.subscribe_list = []
        # check wheterh the config expects us to do a substitution.
        # of addresses (when simulator is run on different machine
        # than the db info has)
        repl_addr = False
        if "subscriber_repl_addr" in self.cfg["interfaces"]["BEE_ARENA"]:
            repl_addr = True
            orig_addr, repl_addr = self.cfg["interfaces"]["BEE_ARENA"].get("subscriber_repl_addr")


        self._sub_labels = [] # keep a note of some debug info.
        for node, mcasu in self.alloc['master_casus'].items():
            if mcasu not in self._casu_info.keys():
                raise RuntimeError, "[F] no port info for {}".format(mcasu)

            addr = self._casu_info[mcasu].get("msg_addr")
            if addr is None:
                raise RuntimeError, "[F] no msg port info for {}".format(mcasu)

            if repl_addr:
                addr = addr.replace(orig_addr, repl_addr)
            self.subscribe_list.append(addr)
            self._sub_labels.append((node, mcasu))
        #
        self.dsnode_to_masters = {
            k:v for k, v in self.alloc['master_casus'].items() }
        self.masters_to_dsnode = {
            v:k for k, v in self.alloc['master_casus'].items() }

    #}}}

    #{{{ comms setup/shutdown
    def start_rx(self):
        self.incoming_thread = threading.Thread(target = self.recieve_from_bee_arena)
        self.justlog("started listen thread", isdata=False)

        self.stop = False
        self.incoming_thread.start()

    def closedown(self):
        # not sure how this interacts with the thread being stopped exogeneously?
        print "closing down... bee-arena/ISI relay ..."
        self.stop = True
        self.justlog("waiting for incoming thread to join", isdata=False)
        self.incoming_thread.join()
        self.justlog("incoming thread joined. done", isdata=False)


    def init_listen_socket(self, timeout=1000):
        self.sub_to_beearena = self.context.socket(zmq.SUB)

        self.sub_to_beearena.setsockopt(zmq.SUBSCRIBE,'') # listen to EVERYthing
        self.sub_to_beearena.setsockopt(zmq.RCVTIMEO, timeout) # timeout in msec

        for i, addr in  enumerate(self.subscribe_list):
            try:
                self.sub_to_beearena.connect(addr)
                msg = "[I] listening on {} (node : {}, {})".format(
                    addr, *self._sub_labels[i])
                self.displog(msg, isdata=False)
            except Exception as e:
                msg = "Exception in connection to {}! Error {} {}".format(
                    addr, e.errno, e.strerror)
                self.displog(msg, isdata=False, clr=clrs._C_ERR)
                msg = "[W] NOT listening on {} (node : {}, {})".format(
                    addr, *self._sub_labels[i])
                self.displog(msg, isdata=False, clr=clrs._C_WARNING)


    #}}}

    #{{{ main listener function, recieve_from_bee_arena
    def recieve_from_bee_arena(self, verb=False):
        '''
        this buffers messages that can be absorbed by other code when requested

        this is unlike the plain 'relay', which always forwards data to
        some other translated port.

        '''
        while not self.stop:
            try:
                [towho, msgtype, fromwho, payload] = \
                    self.sub_to_beearena.recv_multipart()
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    # listening timeout
                    continue
            now = time.time()
            # translate message
            dsnode = self.masters_to_dsnode.get(fromwho, None)
            if dsnode is None:
                # drop message
                self.displog("[W] unrecognised message sender -- {}.".format(fromwho), isdata=False, clr=clrs._C_WARNING)
                msg = "    " + "".join(str(e) for e in [towho, msgtype, fromwho, payload])
                self.displog(msg, isdata=False)
                continue

            if towho in ["iface", "cats"]: # depends on whether the spec was followed; cats also generalises for consensus-type expts
                # buffer into relevant queue
                self._incoming_data[dsnode].append([now, towho, msgtype, fromwho, payload])
                msg = "[I] buffered for node {}, recv {} {} {} {} {}".format(
                    dsnode, *self._incoming_data[dsnode][-1])
                if self.verb: self.displog(msg)
                else: self.justlog(msg)

    #}}}

    #{{{ buffer interrogation (not really needed in this code)
    def get_latest_inval(self, node, maxage=None, fifo=False, debug=False):
        '''
        yield most recent value recvd for the domset node `node`. Optionally
        if `fifo` is True, yield the oldest value.
        only returns data if it is less than `maxage` secs old

        if no (valid) data is available, including if node is not found, return None

        '''
        if node not in self._incoming_data:
            print "[W] requested inval for node {} but not recognised.".format(node)
            return None

        if not len( self._incoming_data[node] ):
            # we don't have any data available (they are rolling buffers)
            return None

        if fifo is False: # oldest data first
            elem = self._incoming_data[node].pop() # HMM, SHOULD IT CONSUME THE OTHERSIDE?
        else: # most recent data first
            elem = self._incoming_data[node].popleft()

        if maxage is not None:
            # not as simple as testing whether packet `elem` is legitimte, because
            # of `fifo`
            raise NotImplementedError

        #when, towho, msgtype, fromwho, payload = elem
        if debug: return elem
        else:     return elem[-1]

    def process_all_input(self, node, stdstr=True, verb=False):
        '''
        consume ALL packets that came in for a specific node, and yield a dict
        with data from the most recent one.
        expecting a string but sometimes sent as a json dict. select the parser this way
        '''
        pkt = None
        while len (self._incoming_data[node]):
            # consume all the packets, exit loop on final one (which is newest)
            pkt = self.get_latest_inval(node, fifo=False, debug=True)

        # didn't find anything in this buffer, return false
        if pkt is None:
            return False, None

        payload = pkt[-1]
        if stdstr:
            newdat = parse_payload(payload)
        else:
            newdat = json.loads(payload)

        if verb: print "[D] recent state is : ", newdat

        return True, newdat
    #}}}

#}}}

if __name__ == "__main__": #noqa
    #{{{ handle arguments and load config file
    parser = argparse.ArgumentParser()
    parser.add_argument('-pth', '--pth', type=str, default=".")
    parser.add_argument('-pc', '--proj_conf', type=str, required=True)
    parser.add_argument('-i', '--ival', type=float, default=1.0)
    parser.add_argument('--logfile', type=str, default=None)
    parser.add_argument('--quiet', action="store_true")
    parser.add_argument('-m', '--manual_close', action="store_true")
    args = parser.parse_args()
    #proj_conf = os.path.join(args.pth, args.proj_conf)
    #}}}

    I_B = BeeArenaListener(args.proj_conf, args.pth, verb=not(args.quiet),
                           logfile=args.logfile)

    try:
        I_B.start_rx()
        while True:
            time.sleep(1.0) # don't spin 100% busy
    except KeyboardInterrupt:
        print "[I] done. Closing sockets."

    if not args.manual_close:
        I_B.closedown()
