import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import multiprocessing as mp
import time
import socket
import argparse
from collections import OrderedDict

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

    def __init__(self, id, clock_period, diff_mode, clock_queue, diff_queue):
        super(ClockPlotter, self).__init__(daemon=True)
        self.id = id
        self.clock_period = clock_period
        self.diff_mode = diff_mode
        self.clock_queue = clock_queue
        self.diff_queue = diff_queue
        self.known_ips = OrderedDict()

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
        self.ax2.set_title('Average Difference to Other Clocks')
        self.ax2.grid(True)
        self.ax2.xaxis.set_tick_params(rotation=45)

        self.fig.tight_layout()

    def run(self):

        start = time.time()

        anim = animation.FuncAnimation(self.fig, self.animate, fargs=(start,), interval = 100, blit=False, cache_frame_data=False)

        plt.show()

    def animate(self, frames, start):

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
                self.known_ips[clock_time_stamp[0]] = 0
                self.ax1.step([], [], where='pre')
                self.ax2.plot([], [])

        for ip in list(self.known_ips.keys()):
            if ip not in [clock_time_stamp[0] for clock_time_stamp in clock_time_stamps]:
                self.known_ips[ip] = self.known_ips[ip] + 1
            if self.known_ips[ip] > 40:
                line_index = list(self.known_ips.keys()).index(ip)
                del self.known_ips[ip]
                self.ax1.get_lines()[line_index].remove()
                self.ax2.get_lines()[line_index].remove()
                if len(self.ax2.get_lines()) == 1:
                    self.ax2.get_lines()[0].set_data([], [])

        for clock_time_stamp in clock_time_stamps:
            line = self.ax1.get_lines()[list(self.known_ips.keys()).index(clock_time_stamp[0])]
            xdata, ydata = line.get_data()
            for i in range(len(xdata)):
                xdata[i] = xdata[i] - self.clock_period
            xdata = np.append(xdata, clock_time_stamp[1] % self.clock_period + 9 * self.clock_period)
            ydata = np.append(ydata, 0)
            xdata = np.append(xdata, clock_time_stamp[1] % self.clock_period + 9 * self.clock_period + self.clock_period / 2)
            ydata = np.append(ydata, 1)
            if len(xdata) > 20:
                xdata = xdata[2:]
                ydata = ydata[2:]
            line.set_data(xdata, ydata)
            self.ax1.set_xlim(0, self.clock_period * 10)

        for diff_time_stamp in diff_time_stamps:
            try:
                line = self.ax2.get_lines()[list(self.known_ips.keys()).index(diff_time_stamp[0])]
                xdata, ydata = line.get_data()
                xdata = np.append(xdata, time.time() - start)
                if self.diff_mode == 'rel':
                    ydata = np.append(ydata, (diff_time_stamp[1] / self.clock_period * 100))
                    self.ax2.set_ylabel('% of Clock Period')
                elif self.diff_mode == 'abs':
                    ydata = np.append(ydata, diff_time_stamp[1])
                    self.ax2.set_ylabel('Seconds (s)')
                if len(xdata) > int(45 / self.clock_period):
                    xdata = xdata[1:]
                    ydata = ydata[1:]
                line.set_data(xdata, ydata)
                self.ax2.set_xlim(xdata[-1] - 45, xdata[-1] + 5)
                min = 0
                max = 0
                for line in self.ax2.get_lines():
                    _, limit_ydata = line.get_data()
                    if (len(limit_ydata) > 0) and (np.min(limit_ydata) < min):
                        min = np.min(limit_ydata)
                    if (len(limit_ydata) > 0) and (np.max(limit_ydata) > max):
                        max = np.max(limit_ydata)
                if self.diff_mode == 'rel':
                    self.ax2.set_ylim(min - 10, max + 10)
                elif self.diff_mode == 'abs':
                    ydata = np.append(ydata, diff_time_stamp[1])
                    self.ax2.set_ylim(min - abs(min) / 5, max  + abs(max) / 5)
            except Exception as e:
                print(e)
                pass

        self.ax1.legend(self.known_ips, loc='upper left')
        self.ax2.legend(self.known_ips, loc='upper left')

if __name__ == '__main__':

    clock_port = 16321
    diff_port = 16322

    parser = argparse.ArgumentParser()

    parser.add_argument('--clockperiod', '-clkp', type=float, help='Clock period in seconds', default=1.0)
    parser.add_argument('--diffmode', '-dm', type=str, help='Diff mode', default='rel', choices=['rel', 'abs'])
    args = parser.parse_args()
    clock_period = args.clockperiod
    diff_mode = args.diffmode

    clock_queue = mp.Queue()
    diff_queue = mp.Queue()

    clock_listener = Listener(0, clock_queue, clock_port)
    diff_listener = Listener(1, diff_queue, diff_port)

    clock_plotter = ClockPlotter(0, clock_period, diff_mode, clock_queue, diff_queue)

    clock_listener.start()
    diff_listener.start()
    clock_plotter.start()

    clock_listener.join()
    diff_listener.join()
    clock_plotter.join()
