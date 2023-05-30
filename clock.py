import time
import argparse
import multiprocessing as mp
from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
import random

class Clock(mp.Process):

    def __init__(self, id, clock_period, broadcast_number, alpha, precision, clock_queue, receive_clock_queue, broadcast_clock_queue, diff_queue):
        super(Clock, self).__init__()
        self.id = id
        self.clock_period = clock_period
        self.broadcast_number = broadcast_number
        self.alpha = alpha
        self.precision = precision
        self.clock_queue = clock_queue
        self.receive_clock_queue = receive_clock_queue
        self.broadcast_clock_queue = broadcast_clock_queue
        self.diff_queue = diff_queue

    def run(self):
        start = time.time()
        shift = 0
        diff = 0
        i = 0
        while True:
            rising_edge = time.time()
            self.clock_queue.put(rising_edge)
            if i % self.broadcast_number == 0:
                self.broadcast_clock_queue.put(rising_edge)
            if not self.receive_clock_queue.empty():
                self.receive_clock_queue.put(None)
                time_stamps = list(iter(self.receive_clock_queue.get, None))
                diff = sum([(((time_stamp - rising_edge) % self.clock_period) - self.clock_period) if abs(((time_stamp - rising_edge) % self.clock_period) - self.clock_period) < self.clock_period / 2 else ((time_stamp - rising_edge) % self.clock_period) for time_stamp in time_stamps]) / len(time_stamps)
                self.diff_queue.put(diff / (self.clock_period / 2))
                shift = self.alpha * diff
                if abs(diff) < self.precision * self.clock_period:
                    shift = 0
            i = i + 1
            time.sleep(((rising_edge - time.time()) % self.clock_period) + shift)
            
class Communicator(mp.Process):

    def __init__(self, id, receive_clock_queues, broadcast_clock_queue):
        super(Communicator, self).__init__()
        self.id = id
        self.receive_clock_queues = receive_clock_queues
        self.broadcast_clock_queue = broadcast_clock_queue

    def run(self):
        while True:
            s = self.broadcast_clock_queue.get()
            for receive_clock_queue in self.receive_clock_queues:
                if receive_clock_queues.index(receive_clock_queue) != self.id:
                    receive_clock_queue.put(s)

def update_plot(frames, ax1, ax2, clock_queues, diff_queues, start, clock_period):

    for clock_queue in clock_queues:
        line = ax1.lines[clock_queues.index(clock_queue)]
        xdata, ydata = line.get_data()
        if not clock_queue.empty():
            t = clock_queue.get()
            xdata = np.append(xdata, t - start)
            ydata = np.append(ydata, 1)
            xdata = np.append(xdata, t - start + (clock_period / 2))
            ydata = np.append(ydata, 0)
            line.set_data(xdata, ydata)
            ax1.set_xlim(xdata[-1] - 4.5 * clock_period, xdata[-1] + clock_period / 2)

    for diff_queue in diff_queues:
        line = ax2.lines[diff_queues.index(diff_queue)]
        xdata, ydata = line.get_data()
        if not diff_queue.empty():
            diff = diff_queue.get()
            xdata = np.append(xdata, time.time() - start)
            ydata = np.append(ydata, diff * 100)
            line.set_data(xdata, ydata)
            ax2.set_xlim(xdata[-1] - 90 * clock_period, xdata[-1] + 10 * clock_period)


def plot(clock_period, clock_queues, diff_queues):

    fig = plt.figure()
    ax1 = fig.add_subplot(2,1,1)
    ax2 = fig.add_subplot(2,1,2)

    ax1.set_ylim(-0.1, 1.1)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Value')
    ax1.set_title('Clocks')
    ax1.grid(True)
    ax1.xaxis.set_tick_params(rotation=45)

    ax2.set_ylim(-110, 110)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('% of clock period')
    ax2.set_title('Average Difference')
    ax2.grid(True)
    ax2.xaxis.set_tick_params(rotation=45)

    fig.tight_layout()

    for _ in range(len(clock_queues)):
        ax1.step([], [], lw=2, where='post')[0]

    for _ in range(len(diff_queues)):
        ax2.plot([], [], lw=2)[0]

    start = time.time()

    anim = animation.FuncAnimation(fig, update_plot, fargs=(ax1, ax2, clock_queues, diff_queues, start, clock_period), interval=clock_period/4, blit=False, cache_frame_data=False)

    plt.show()
    
if __name__ == '__main__':

    n = 4

    parser = argparse.ArgumentParser()
    parser.add_argument('--clockperiod', '-clkp', type=float, help='Clock period in seconds', default=1.0)
    parser.add_argument('--broadcastnumber', '-bn', type=float, help='Broadcast period in number of clock cycles', default=1.0)
    parser.add_argument('--alpha', '-a', type=float, help='Clock skew', default=1.0)
    parser.add_argument('--precision', '-p', type=float, help='Synchonization precision', default=0.01)
    args = parser.parse_args()

    clock_period = args.clockperiod
    broadcast_number = args.broadcastnumber
    alpha = args.alpha
    precision = args.precision

    clock_queues = []
    for i in range(n):
        clock_queues.append(mp.Queue())

    broadcast_clock_queues = []
    for i in range(n):
        broadcast_clock_queues.append(mp.Queue())

    receive_clock_queues = []
    for i in range(n):
        receive_clock_queues.append(mp.Queue())

    diff_queues = []
    for i in range(n):
        diff_queues.append(mp.Queue())

    clocks = []
    for i in range(n):
        clocks.append(Clock(i, clock_period, broadcast_number, alpha, precision, clock_queues[i], receive_clock_queues[i], broadcast_clock_queues[i], diff_queues[i]))

    communicators = []
    for i in range(n):
        communicators.append(Communicator(i, receive_clock_queues, broadcast_clock_queues[i]))

    plotter = mp.Process(target=plot, args=(clock_period, clock_queues, diff_queues))

    plotter.start()
    for clock in clocks:
        clock.start()
        time.sleep(random.random() * clock_period)
    for communicator in communicators:
        communicator.start()
    plotter.join()
    for clock in clocks:
        clock.join()
    for communicator in communicators:
        communicator.join()