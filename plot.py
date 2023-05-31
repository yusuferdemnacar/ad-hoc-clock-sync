import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import multiprocessing as mp
import time
import socket
import argparse

class Listener(mp.Process):

    def __init__(self, id, queue, port):
        super(Listener, self).__init__(daemon=True)
        self.id = id
        self.queue = queue
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))
        print('Listening on port {}'.format(self.port))

    def run(self):

        while True:
            t, addr = self.sock.recvfrom(1024)
            t = float(t.decode('utf-8'))
            self.queue.put((addr[0], t))

class ClockPlotter(mp.Process):

    def __init__(self, id, clock_period, clock_queue, diff_queue):
        super(ClockPlotter, self).__init__(daemon=True)
        self.id = id
        self.clock_period = clock_period
        self.clock_queue = clock_queue
        self.diff_queue = diff_queue
        self.known_ips = []

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(2,1,1)
        self.ax2 = self.fig.add_subplot(2,1,2)

        self.ax1.set_ylim(-0.1, 1.1)
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Value')
        self.ax1.set_title('Clocks')
        self.ax1.grid(True)
        self.ax1.xaxis.set_tick_params(rotation=45)

        self.ax2.set_ylim(-110, 110)
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('% of clock period')
        self.ax2.set_title('Average Difference')
        self.ax2.grid(True)
        self.ax2.xaxis.set_tick_params(rotation=45)

        self.fig.tight_layout()

    def run(self):

        anim = animation.FuncAnimation(self.fig, self.animate, interval = 100, blit=False, cache_frame_data=False)

        plt.show()

    def animate(self, frames):

        clock_time_stamps = []
        diff_time_stamps = []

        if not self.clock_queue.empty():
            self.clock_queue.put(None)
            clock_time_stamps = list(iter(self.clock_queue.get, None))

        if not self.diff_queue.empty():
            self.diff_queue.put(None)
            diff_time_stamps = list(iter(self.diff_queue.get, None))

        for clock_time_stamp in clock_time_stamps:
            if clock_time_stamp[0] not in self.known_ips:
                self.known_ips.append(clock_time_stamp[0])
                self.ax1.step([], [], where='pre')
                self.ax2.plot([], [])

        for clock_time_stamp in clock_time_stamps:
            line = self.ax1.lines[self.known_ips.index(clock_time_stamp[0])]
            xdata, ydata = line.get_data()
            xdata = np.append(xdata, clock_time_stamp[1])
            ydata = np.append(ydata, 0)
            xdata = np.append(xdata, clock_time_stamp[1] + self.clock_period / 2)
            ydata = np.append(ydata, 1)
            line.set_data(xdata, ydata)
            self.ax1.set_xlim(xdata[-1] - 4.5 * self.clock_period, xdata[-1] + 0.5 * self.clock_period)

        for diff_time_stamp in diff_time_stamps:
            try:
                line = self.ax2.lines[self.known_ips.index(diff_time_stamp[0])]
                xdata, ydata = line.get_data()
                xdata = np.append(xdata, time.time())
                ydata = np.append(ydata, diff_time_stamp[1] * 100)
                line.set_data(xdata, ydata)
                self.ax2.set_xlim(xdata[-1] - 45, xdata[-1] + 5)
            except:
                pass

        self.ax1.legend(self.known_ips, loc='upper left')
        self.ax2.legend(self.known_ips, loc='upper left')

if __name__ == '__main__':

    clock_port = 16321
    diff_port = 16322

    parser = argparse.ArgumentParser()

    parser.add_argument('--clockperiod', '-clkp', type=float, help='Clock period in seconds', default=1.0)
    args = parser.parse_args()
    clock_period = args.clockperiod

    clock_queue = mp.Queue()
    diff_queue = mp.Queue()

    clock_listener = Listener(0, clock_queue, clock_port)
    diff_listener = Listener(1, diff_queue, diff_port)

    clock_plotter = ClockPlotter(0, clock_period, clock_queue, diff_queue)

    clock_listener.start()
    diff_listener.start()
    clock_plotter.start()

    clock_listener.join()
    diff_listener.join()
    clock_plotter.join()
