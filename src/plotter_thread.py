# plotter_thread.py

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from collections import deque
import math
import time
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pyqtgraph as pg
import threading
from pyqtgraph.graphicsItems.GraphicsLayout import GraphicsLayout

class myGraphics(GraphicsLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_Space:
            self.sweep.flip_direction()
        elif key == QtCore.Qt.Key_Escape:
            self.sweep.stop()
        elif key == QtCore.Qt.Key_Enter:
            self.sweep.resume()


class pyqtgraphPlotter(QObject):

    def __init__(self, sweep, plot_bin=1):
        QObject.__init__(self)

        self.sweep = sweep
        self.data_queue = deque([])
        self.finished = False
        self.last_pass = False
        self.figs_set = False
        self.kill_flag = False
        self.plot_bin = plot_bin

        self.set_plot = None
        self.follow_plots = []
        self.view = None
        self.win = None

        self.set_lines = {'fwd': [], 'bwd': []}
        self.follow_lines = {}

    def __del__(self):
        """
        Standard destructor.
        """
        self.clear()
        #self.wait()

    def handle_close(self, evt):
        self.clear()

    @pyqtSlot(int)
    def add_break(self, direction):
        d = ''
        if direction == 0:
            d = 'fwd'
        else:
            d = 'bwd'
        if self.set_plot is not None:
            x = self.set_lines[d].xData
            y = self.set_lines[d].yData
            if x is None:
                x = np.array([])
            if y is None:
                y = np.array([])
            self.set_lines[d].setData(np.append(x, np.nan), np.append(y, np.nan))
        for p, lines in self.follow_lines.items():
            x = lines[d].xData
            y = lines[d].yData
            if x is None:
                x = np.array([])
            if y is None:
                y = np.array([])
            lines[d].setData(np.append(x, np.nan), np.append(y, np.nan))

    @pyqtSlot(list, int)
    def add_data_to_queue(self, data, direction):
        """
        Grabs the data to plot.

        Arguments:
            data - list of tuples to plot
            direction - int (0 or 1) determining forward or backward
        """
        print('add data', threading.get_ident(), QThread.currentThreadId())
        self.data_queue.append((data, direction))
        self.update_plots(force=False)

    def create_figs(self):
        """
        Creates default figures for each of the parameters. Plots them in a new, separate window.
        """
        if self.figs_set is True:
            print("figs already set. returning.")
            return
        print('a')
        self.view = pg.GraphicsView()
        print('a')
        self.win = myGraphics()
        print('a')
        self.view.setCentralItem(self.win)
        print('a')
        self.view.setWindowTitle('MeasureIt Plots')
        print('test 1')
        pg.setConfigOptions(antialias=True)
        self.figs_set = True
        print('test 2')
        num_plots = len(self.sweep._params)
        if self.sweep.set_param is not None:
            num_plots += 1

        columns = math.ceil(math.sqrt(num_plots))
        rows = math.ceil(num_plots / columns)

        # Create the on-screen instructions
        text = """
        <h2 style="text-align:center">Keyboard Shortcuts</h2>
        <h3 style="text-align:center">esc: stop&emsp;enter: resume&emsp;spacebar: flip direction</h3>
        """
        self.win.addLabel(text, colspan=columns)
        self.win.nextRow()
        print('test 3')
        n = 0
        if self.sweep.set_param is not None:
            self.set_plot = self.win.addPlot(title=self.sweep.set_param.label)
            self.set_plot.setLabel('left', self.sweep.set_param.label, units=self.sweep.set_param.unit)
            self.set_plot.setLabel('bottom', 'time', units='s')
            self.set_plot.showGrid(x=True, y=True)
            self.set_plot.enableAutoRange()
            self.set_lines['fwd'] = self.set_plot.plot(pen=(255, 0, 0))
            self.set_lines['bwd'] = self.set_plot.plot(pen=(0, 0, 255))
            n += 1

        self.follow_plots = []
        for p in self.sweep._params:
            plot = self.win.addPlot(title=p.label)
            plot.setLabel('left', p.label, units=p.unit)
            plot.showGrid(x=True, y=True)
            plot.enableAutoRange()
            if self.sweep.set_param is not None:
                plot.setLabel('bottom', self.sweep.set_param.label, units=self.sweep.set_param.unit)
            else:
                plot.setLabel('bottom', 'time', units='s')
            self.follow_plots.append(plot)
            self.follow_lines[p] = {}
            self.follow_lines[p]['fwd'] = plot.plot(pen=(255, 0, 0))
            self.follow_lines[p]['bwd'] = plot.plot(pen=(0, 0, 255))
            n += 1
            if n % columns == 0:
                self.win.nextRow()
        self.view.show()

    def update_plots(self, force=False):
        # Remove all the data points from the deque
        updates = 0
        if (len(self.data_queue) >= self.plot_bin or force is True) and self.figs_set is True:
            while len(self.data_queue) > 0:
                temp = self.data_queue.popleft()
                data = deque(temp[0])
                direction = ''
                if temp[1] == 0:
                    direction = 'fwd'
                else:
                    direction = 'bwd'
                updates += 1

                # Grab the time data
                time_data = data.popleft()

                print('attempting to update setparam plot', threading.get_ident(), QThread.currentThreadId())
                # Grab and plot the set_param if we are driving one
                if self.sweep.set_param is not None:
                    set_param_data = data.popleft()

                    x, y = self.set_lines[direction].getData()
                    if x is None:
                        x = np.array([])
                    if y is None:
                        y = np.array([])
                    # Plot as a function of time
                    self.set_lines[direction].setData(np.append(x, time_data[1]), np.append(y, set_param_data[1]))

                x_data = 0
                if self.sweep.x_axis == 1:
                    x_data = time_data[1]
                elif self.sweep.x_axis == 0:
                    x_data = set_param_data[1]

                # Now, grab the rest of the following param data
                for (p, val) in data:
                    print(f'attempting to update {p.label} plot {threading.get_ident()}')
                    line = self.follow_lines[p][direction]
                    x, y = line.getData()
                    if x is None:
                        x = np.array([])
                    if y is None:
                        y = np.array([])
                    line.setData(np.append(x, x_data), np.append(y, val))
                self.win.update()

    @pyqtSlot()
    def run(self):
        """
        Actual function to run, that controls the plotting of the data.
        """
        print('plotter b4 figs', threading.get_ident(), QThread.currentThreadId())

#        if __name__ == '__main__':
#            import sys
#            if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):

        if self.figs_set is False:
            self.create_figs()
        print('plotter after figs', threading.get_ident())
        #QtGui.QApplication.instance().exec_()
        # Run while the sweep is running
        #while self.kill_flag is False:
        #    t = time.monotonic()
        #    print('about to call update plots')
        #    # Update our plots!
        #    self.update_plots()

            # Smart sleep, by checking if the whole process has taken longer than
            # our sleep time
        #    sleep_time = self.sweep.inter_delay / 2 - (time.monotonic() - t)
        #    if sleep_time > 0:
        #        time.sleep(sleep_time)

        #    if self.sweep.is_running is False:
        #        # If we're done, update our plots one last time to ensure all data is flushed
        #        self.update_plots(force=True)

        # if self.kill_flag == True:
        #    self.clear()

    def reset(self):
        """
        Resets all the plots
        """
        if self.figs_set is True:
            if self.set_plot is not None:
                self.set_lines['fwd'].setData(np.array([]))
                self.set_lines['bwd'].setData(np.array([]))
            for p, lines in self.follow_lines.items():
                lines['fwd'].setData(np.array([]))
                lines['bwd'].setData(np.array([]))

    def clear(self):
        self.reset()
        self.view.close()
        self.figs_set = False


class PlotterThread(QThread):
    """
    Thread to control the plotting of a sweep of class BaseSweep. Gets the data
    from the RunnerThread to plot.
    """
    def __init__(self, sweep, plot_bin=1, setaxline=None, setax=None, axesline=None, axes=[]):
        """
        Initializes the thread. Takes in the parent sweep and the figure information if you want
        to use an already-created plot.
        
        Arguments:
            sweep - the parent sweep object
            setaxline - optional argument (Line2D) for a plot that already exists that you want to use
            setax - optional argument of type subplot for the setaxes
            axesline - same as above for following params
            axes - same as above for following params
        """
        self.sweep = sweep
        self.data_queue = deque([])
        self.setaxline = setaxline
        self.setax = setax
        self.axesline = axesline
        self.axes = axes
        self.finished = False
        self.last_pass = False
        self.figs_set = False
        self.kill_flag = False
        self.plot_bin = plot_bin
        
        QThread.__init__(self)
        
        
    def __del__(self):
        """
        Standard destructor.
        """
        self.wait()
    
    def handle_close(self, evt):
        self.clear()
    
    def key_pressed(self, event):
        key = event.key

        if key == " ":
            self.sweep.flip_direction()
        elif key == "escape":
            self.sweep.stop()
        elif key == "enter":
            self.sweep.resume()
            
    def add_break(self, direction):
        self.setaxline.set_xdata(np.append(self.setaxline.get_xdata(), np.nan))
        self.setaxline.set_ydata(np.append(self.setaxline.get_ydata(), np.nan))
        for i,p in enumerate(self.sweep._params):                
            self.axesline[i][direction].set_xdata(np.append(self.axesline[i][direction].get_xdata(), np.nan))
            self.axesline[i][direction].set_ydata(np.append(self.axesline[i][direction].get_ydata(), np.nan))
            
    def create_figs(self):
        """
        Creates default figures for each of the parameters. Plots them in a new, separate window.
        """        
        if self.figs_set == True:
            print("figs already set. returning.")
            return
        
        #print("creating figures")
        self.figs_set = True
        num_plots = len(self.sweep._params)
        if self.sweep.set_param is not None:
            num_plots += 1

        columns = math.ceil(math.sqrt(num_plots))
        rows = math.ceil(num_plots/columns)
        
        existing_fignums = plt.get_fignums()
        if len(existing_fignums) == 0:
            best_fignum = 1
        else:
            best_fignum = max(existing_fignums)+1
        self.fig = plt.figure(num=best_fignum, figsize=(4*columns+1,4*rows+1))        
        self.fig.canvas.mpl_connect('close_event', self.handle_close)
        self.grid = plt.GridSpec(4*rows+1, columns, hspace=0.15)
        self.axes = []
        self.axesline=[]
        
        # Creating the on-screen text for keyboard shortcuts
        text_ax = self.fig.add_subplot(self.grid[0,:])
        text_ax.axis('off')
        #text_ax.axes.get_xaxis().set_visible(False)
        #text_ax.axes.get_yaxis().set_visible(False)
        plt.text(0.5, 1, 'Keyboard Shortcuts', fontsize=20, ha='center')
        plt.text(0.5, 0.5, "esc: stop\tenter: resume\tspacebar: flip direction".replace("\t", "      "), fontsize=14, ha='center')
        
        # Create the set_param plots 
        if self.sweep.set_param is not None:
            self.setax = self.fig.add_subplot(self.grid[1:4,0])
            self.setax.set_xlabel('Time (s)')
            self.setax.set_ylabel(f'{self.sweep.set_param.label} ({self.sweep.set_param.unit})')
            self.setaxline = self.setax.plot([], [])[0]
            plt.grid(b=True, which='major', color='0.5', linestyle='-')
            
        # Create the following params plots
        for i, p in enumerate(self.sweep._params):
            pos = i
            if self.sweep.set_param is not None:
                pos += 1
            
            row = int(pos/columns)
            col = pos%columns
                
            self.axes.append(self.fig.add_subplot(self.grid[4*row+1:4*(row+1), col]))
            # Create a plot of the sweeping parameters value against time
            if self.sweep.x_axis:
                self.axes[i].set_xlabel('Time (s)')
            else:
                self.axes[i].set_xlabel(f'{self.sweep.set_param.label} ({self.sweep.set_param.unit})')
            self.axes[i].set_ylabel(f'{p.label} ({p.unit})')
            forward_line = matplotlib.lines.Line2D([],[])
            forward_line.set_color('b')
            backward_line = matplotlib.lines.Line2D([],[])
            backward_line.set_color('r')
            self.axes[i].add_line(forward_line)
            self.axes[i].add_line(backward_line)
            self.axesline.append((forward_line, backward_line))
            plt.grid(b=True, which='major', color='0.5', linestyle='-')
            
        plt.subplots_adjust(left=0.2, right=0.9, bottom=0.1, top=0.9, wspace=0.4, hspace=0.4)
        
        self.cid = self.fig.canvas.mpl_connect('key_press_event', self.key_pressed)

        plt.show(block=False)


            
    def add_data_to_queue(self, data, direction):
        """
        Grabs the data to plot.
        
        Arguments:
            data - list of tuples to plot
        """
        self.data_queue.append((data,direction))
        
        
    def update_plots(self, force=False):
        # Remove all the data points from the deque
        updates = 0
        if (len(self.data_queue) >= self.plot_bin or force is True) and self.figs_set == True:
            while len(self.data_queue) > 0:
                temp = self.data_queue.popleft()
                data = deque(temp[0])
                direction = temp[1]
                updates += 1
            
                # Grab the time data 
                time_data = data.popleft()
            
                # Grab and plot the set_param if we are driving one
                if self.sweep.set_param is not None:
                    set_param_data = data.popleft()
                    # Plot as a function of time
                    self.setaxline.set_xdata(np.append(self.setaxline.get_xdata(), time_data[1]))
                    self.setaxline.set_ydata(np.append(self.setaxline.get_ydata(), set_param_data[1]))
                    self.setax.relim()
                    self.setax.autoscale()
                
                x_data=0
                if self.sweep.x_axis == 1:
                    x_data = time_data[1]
                elif self.sweep.x_axis == 0:
                    x_data = set_param_data[1]
                
                # Now, grab the rest of the following param data
                for i,data_pair in enumerate(data):                
                    self.axesline[i][direction].set_xdata(np.append(self.axesline[i][direction].get_xdata(), x_data))
                    self.axesline[i][direction].set_ydata(np.append(self.axesline[i][direction].get_ydata(), data_pair[1]))
                    self.axes[i].relim()
                    self.axes[i].autoscale()
        
            self.fig.canvas.draw()
            
            
    def run(self):
        """
        Actual function to run, that controls the plotting of the data.
        """
        if self.figs_set is False:
            self.create_figs()
        
        
        # Run while the sweep is running
        while self.kill_flag is False:
            t = time.monotonic()
            
            # Update our plots!
            self.update_plots()
            
            # Smart sleep, by checking if the whole process has taken longer than
            # our sleep time
            sleep_time = self.sweep.inter_delay/2 - (time.monotonic() - t)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
            if self.sweep.is_running is False:
                # If we're done, update our plots one last time to ensure all data is flushed
                self.update_plots(force=True)
                
        #if self.kill_flag == True:
        #    self.clear()


    def reset(self):
        """
        Resets all the plots
        """
        if self.sweep.set_param is not None:
            self.setaxline.set_xdata(np.array([]))
            self.setaxline.set_ydata(np.array([]))
            self.setax.relim()
            self.setax.autoscale()
        
        for i,p in enumerate(self.axesline):
            self.axesline[i][0].set_xdata(np.array([]))
            self.axesline[i][0].set_ydata(np.array([]))
            self.axesline[i][1].set_xdata(np.array([]))
            self.axesline[i][1].set_ydata(np.array([]))
            self.axes[i].relim()
            self.axes[i].autoscale()
            
    def clear(self):
        self.reset()
        matplotlib.pyplot.close(self.fig)
        self.figs_set = False