import time
import argparse
import multiprocessing as mp
import socket

class Clock(mp.Process):

    def __init__(self, id, clock_period, broadcast_number, alpha, clock_queue, receive_clock_queue, broadcast_clock_queue, diff_queue):
        super(Clock, self).__init__(daemon=True)
        self.id = id
        self.clock_period = clock_period
        self.broadcast_number = broadcast_number
        self.alpha = alpha
        self.clock_queue = clock_queue
        self.receive_clock_queue = receive_clock_queue
        self.broadcast_clock_queue = broadcast_clock_queue
        self.diff_queue = diff_queue

    def run(self):
        rising_edge = time.time()
        shift = 0
        diff = 0
        i = 0
        while True:
            op_start = time.perf_counter()
            self.clock_queue.put(rising_edge)
            if not self.receive_clock_queue.empty():
                self.receive_clock_queue.put(None)
                time_stamps = list(iter(self.receive_clock_queue.get, None))
                diff = sum([(((time_stamp - rising_edge) % self.clock_period) - self.clock_period) if abs(((time_stamp - rising_edge) % self.clock_period) - self.clock_period) < self.clock_period / 2 else ((time_stamp - rising_edge) % self.clock_period) for time_stamp in time_stamps]) / len(time_stamps)
                self.diff_queue.put(diff / (self.clock_period / 2))
                shift = self.alpha * diff
            i = i + 1
            time.sleep((op_start - time.perf_counter()) % self.clock_period + shift)
            rising_edge = rising_edge + time.perf_counter() - op_start
            if i % self.broadcast_number == 0:
                self.broadcast_clock_queue.put(rising_edge)
                i = 0
            
class Listener(mp.Process):

    def __init__(self, ip, port, queue):
        super(Listener, self).__init__(daemon=True)
        self.ip = ip
        self.port = port
        self.queue = queue
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))

    def run(self):

        while True:
            data, addr = self.sock.recvfrom(1024)
            data = float(data.decode('utf-8'))
            if self.ip != addr[0]:
                self.queue.put(data)

class Sender(mp.Process):

    def __init__(self, ip, port, queue):
        super(Sender, self).__init__(daemon=True)
        self.ip = ip
        self.port = port
        self.queue = queue
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, 0))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def run(self):
        while True:
            data = self.queue.get()
            while not self.queue.empty():
                pass
            self.sock.sendto(str(data).encode('utf-8'), ('<broadcast>', self.port))
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--clockperiod', '-clkp', type=float, help='Clock period in seconds', default=1.0)
    parser.add_argument('--broadcastnumber', '-bn', type=float, help='Broadcast period in number of clock cycles', default=1.0)
    parser.add_argument('--alpha', '-a', type=float, help='Clock skew', default=1.0)
    args = parser.parse_args()

    clock_period = args.clockperiod
    broadcast_number = args.broadcastnumber
    alpha = args.alpha

    host = socket.gethostname()
    ip = socket.gethostbyname(host)

    clock_queue = mp.Queue()
    diff_queue = mp.Queue()
    broadcast_queue = mp.Queue()
    receive_queue = mp.Queue()

    clock = Clock(ip, clock_period, broadcast_number, alpha, clock_queue, receive_queue, broadcast_queue, diff_queue)
    broadcast_listener = Listener(ip, receive_queue, 16320)
    broadcast_sender = Sender(ip, broadcast_queue, 16320)
    clock_sender = Sender(ip, clock_queue, 16321)
    diff_sender = Sender(ip, diff_queue, 16322)


    clock.start()
    broadcast_listener.start()
    broadcast_sender.start()
    clock_sender.start()
    diff_sender.start()

    clock.join()
    broadcast_listener.join()
    broadcast_sender.join()
    clock_sender.join()
    diff_sender.join()
