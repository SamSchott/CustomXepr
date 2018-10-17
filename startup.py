"""
Created on Tue Aug 23 11:03:57 2016

@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

To Do:

* See GitHub issues list at https://github.com/OE-FET/CustomXepr

New in v2.1.0:
    * Removed dark theme: code is easier to maintain.
    * Split off mercury_gui and keithley_gui as separate packages.

New in v2.0.0:

    * Moved driver backends from NI-VISA to pyvisa-py. It is no longer
      necessary to install NI-VISA from National Instruments on your system.
    * Moved drivers to external packages. Install with pip before first use.
    * Improved data plotting in Mercury user interface:
        - heater output and gasflow are plotted alongside the temperature
        - major speedups in plotting framerate by relying on numpy for updating
          the data, redrawing only changed elements of plot widget
        - allow real-time panning and zooming of plots
    * Started working on Python 3.6 compatability.

"""
import sys
import os
import logging
from qtpy import QtCore, QtWidgets, QtGui
from keithley2600 import Keithley2600
from mercuryitc import MercuryITC
from mercurygui import MercuryFeed, MercuryMonitorApp
from keithleygui import KeithleyGuiApp
from mercurygui import CONF as M_CONF
from keithleygui import CONF as K_CONF

# local imports
from xeprtools.customxepr import CustomXepr, __version__, __author__, __year__
from xeprtools.customxper_ui import JobStatusApp

from utils.misc import patch_excepthook
from utils.internal_ipkernel import InternalIPKernel


# if we are running from IPython:
# disable autoreload, start integrated Qt event loop
try:
    from IPython import get_ipython
    ipython = get_ipython()
    ipython.magic('%gui qt')
    ipython.magic('%autoreload 0')
    app = QtWidgets.QApplication([' '])
except:
    pass

try:
    sys.path.insert(0, os.popen("Xepr --apipath").read())
    import XeprAPI
except ImportError:
    logging.info('XeprAPI could not be located. Please make sure that it' +
                 ' is installed on your system.')

KEITHLEY_ADDRESS = K_CONF.get('Connection', 'KEITHLEY_ADDRESS')
MERCURY_ADDRESS = M_CONF.get('Connection', 'MERCURY_ADDRESS')


# =============================================================================
# Set up Qt event loop and console if necessary
# =============================================================================

def get_qt_app(*args, **kwargs):
    """
    Create a new Qt app or return an existing one.
    """
    created = False
    app = QtCore.QCoreApplication.instance()

    if not app:
        if not args:
            args = ([''],)
        app = QtWidgets.QApplication(*args, **kwargs)
        created = True

    return app, created


# =============================================================================
# Create splash screen
# =============================================================================

def show_splash_screen(app):
    """ Shows a splash screen from file."""
    direct = os.path.dirname(os.path.realpath(__file__))
    image = QtGui.QPixmap(os.path.join(direct, 'images', 'splash.png'))
    image.setDevicePixelRatio(3)
    splash = QtWidgets.QSplashScreen(image)
    splash.show()
    app.processEvents()

    return splash


# =============================================================================
# Connect to instruments: Bruker Xepr, Keithley and MercuryiTC.
# =============================================================================

def connect_to_instruments(keithley_address=KEITHLEY_ADDRESS,
                           mercury_address=MERCURY_ADDRESS):
    """Tries to connect to Keithley, Mercury and Xepr."""

    keithley = Keithley2600(keithley_address)
    mercury = MercuryITC(mercury_address)
    mercuryFeed = MercuryFeed(mercury)

    try:
        xepr = XeprAPI.Xepr()
    except NameError:
        xepr = None
    except IOError:
        logging.info('No running Xepr instance could be found.')
        xepr = None

    customXepr = CustomXepr(xepr, mercuryFeed, keithley)

    return customXepr, xepr, keithley, mercury, mercuryFeed


# =============================================================================
# Start CustomXepr and user interfaces
# =============================================================================

def start_gui(customXepr, mercuryFeed, keithley):
    """Starts GUIs for Keithley, Mercury and CustomXepr."""

    customXeprGUI = JobStatusApp(customXepr)
    mercuryGUI = MercuryMonitorApp(mercuryFeed)
    keithleyGUI = KeithleyGuiApp(keithley)

    customXeprGUI.show()
    mercuryGUI.show()
    keithleyGUI.show()

    return customXeprGUI, keithleyGUI, mercuryGUI


if __name__ == '__main__':

    # create a new Qt app or return an existing one
    app, CREATED = get_qt_app()

    # create and show splash screen
    splash_screen = show_splash_screen(app)

    # connect to instruments
    customXepr, xepr, keithley, mercury, mercuryFeed = connect_to_instruments()
    # start user interfaces
    customXeprGUI, keithleyGUI, mercuryGUI = start_gui(customXepr, mercuryFeed,
                                                       keithley)

    BANNER = ('Welcome to CustomXepr %s. ' % __version__ +
              'You can access connected instruments through "customXepr" ' +
              'or directly as "xepr", "keithley" and "mercury".\n\n' +
              'Use "%run path/to/file.py" to run a python script such as a ' +
              'measurement routine.\n'
              'Type "exit" to gracefully exit ' +
              'CustomXepr.\n\n(c) 2016 - %s, %s.' % (__year__, __author__))

    if CREATED:

        # start event loop and console if run as standalone app
        kernel_window = InternalIPKernel()
        kernel_window.init_ipkernel(banner=BANNER)
        kernel_window.new_qt_console()

        var_dict = {'customXepr': customXepr, 'xepr': xepr,
                    'customXeprGUI': customXeprGUI,
                    'mercuryFeed': mercuryFeed, 'mercuryGUI': mercuryGUI,
                    'keithley': keithley, 'keithleyGUI': keithleyGUI}

        kernel_window.send_to_namespace(var_dict)
        app.aboutToQuit.connect(kernel_window.cleanup_consoles)
        # remove splash screen
        splash_screen.finish(keithleyGUI)
        # start event loop
        kernel_window.ipkernel.start()

    else:
        # print banner
        print(BANNER)
        # remove splash screen
        splash_screen.finish(customXeprGUI)
        # patch exception hook to display errors from Qt event loop
        patch_excepthook()
