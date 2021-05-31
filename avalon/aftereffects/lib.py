import os
import sys
import contextlib
import subprocess
import importlib
import traceback
import logging
import functools

from wsrpc_aiohttp import (
    WebSocketRoute,
    WebSocketAsync
)

from Qt import QtWidgets, QtCore, QtGui

from avalon.tools.webserver.app import WebServerTool

from openpype.tools import workfiles
from openpype.tools.tray_app.app import ConsoleTrayApp

from .ws_stub import AfterEffectsServerStub

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def show(module_name):
    """Call show on "module_name".

    This allows to make a QApplication ahead of time and always "exec_" to
    prevent crashing.

    Args:
        module_name (str): Name of module to call "show" on.
    """
    # Import and show tool.
    if module_name == "workfiles":
        # Use OpenPype's workfiles tool
        tool_module = workfiles
    else:
        tool_module = importlib.import_module("avalon.tools." + module_name)

    if "loader" in module_name:
        tool_module.show(use_context=True)
    else:
        tool_module.show()


class ConnectionNotEstablishedYet(Exception):
    pass


class AfterEffectsRoute(WebSocketRoute):
    """
        One route, mimicking external application (like Harmony, etc).
        All functions could be called from client.
        'do_notify' function calls function on the client - mimicking
            notification after long running job on the server or similar
    """
    instance = None

    def init(self, **kwargs):
        # Python __init__ must be return "self".
        # This method might return anything.
        log.debug("someone called AfterEffects route")
        self.instance = self
        return kwargs

    # server functions
    async def ping(self):
        log.debug("someone called AfterEffects route ping")

    # This method calls function on the client side
    # client functions

    async def read(self):
        log.debug("aftereffects.read client calls server server calls "
                  "aftereffects client")
        return await self.socket.call('aftereffects.read')

    # panel routes for tools
    async def creator_route(self):
        self._tool_route("creator")

    async def workfiles_route(self):
        self._tool_route("workfiles")

    async def loader_route(self):
        self._tool_route("loader")

    async def publish_route(self):
        self._tool_route("publish")

    async def sceneinventory_route(self):
        self._tool_route("sceneinventory")

    async def subsetmanager_route(self):
        self._tool_route("subsetmanager")

    def _tool_route(self, tool_name):
        """The address accessed when clicking on the buttons."""
        partial_method = functools.partial(show, tool_name)

        ConsoleTrayApp.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"


def stub():
    """
        Convenience function to get server RPC stub to call methods directed
        for host (Photoshop).
        It expects already created connection, started from client.
        Currently created when panel is opened (PS: Window>Extensions>Avalon)
    :return: <PhotoshopClientStub> where functions could be called from
    """
    stub = AfterEffectsServerStub()
    if not stub.client:
        raise ConnectionNotEstablishedYet("Connection is not created yet")

    return stub


def safe_excepthook(*args):
    traceback.print_exception(*args)


def main(*subprocess_args):
    from avalon import aftereffects

    def is_host_connected():
        """Returns True if connected, False if app is not running at all."""
        if ConsoleTrayApp.process.poll() is not None:
            return False
        try:
            _stub = aftereffects.stub()

            if _stub:
                return True
        except Exception:
            pass

        return None

    # coloring in ConsoleTrayApp
    os.environ["OPENPYPE_LOG_NO_COLORS"] = "False"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)

    console_app = ConsoleTrayApp('aftereffects', launch,
                                 subprocess_args, is_host_connected)

    sys.exit(app.exec_())


def launch(*subprocess_args):
    """Starts the websocket server that will be hosted
       in the AfterEffects extension.
    """
    from avalon import api, aftereffects

    api.install(aftereffects)
    sys.excepthook = safe_excepthook

    # Launch aftereffects and the websocket server.
    ConsoleTrayApp.process = subprocess.Popen(subprocess_args,
                                               stdout=subprocess.PIPE)

    websocket_server = WebServerTool()
    # Add Websocket route
    websocket_server.add_route("*", "/ws/", WebSocketAsync)
    # Add after effects route to websocket handler
    route_name = 'AfterEffects'
    print("Adding {} route".format(route_name))
    WebSocketAsync.add_route(
        route_name, AfterEffectsRoute
    )
    websocket_server.start_server()

    ConsoleTrayApp.websocket_server = websocket_server

    if os.environ.get("AVALON_PHOTOSHOP_WORKFILES_ON_LAUNCH", True):
        save = False
        if os.getenv("WORKFILES_SAVE_AS"):
            save = True

        ConsoleTrayApp.execute_in_main_thread(lambda: workfiles.show(save))


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context."""
    selection = stub().get_selected_items(True, False, False)
    try:
        yield selection
    finally:
        pass
