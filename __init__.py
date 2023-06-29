# -*- coding:UTF-8 -*-
# __author__ = "KenLee"
# __email__ = "hellokenlee@163.com"

from qrenderdoc import CaptureContext, WindowMenu

from .common.debug import *
from .unrealdoc_window import UnrealDocViewerManager
from .tools.struct_buffer_viewer_mgr import StructBufferViewerManager
from .tools.utils import PipelineStateUtils

DEBUG = True


def register(version: str, context: CaptureContext):
    #
    connect_debug_server(DEBUG)
    #
    PipelineStateUtils().register(context)
    StructBufferViewerManager().register(context)
    #
    UnrealDocViewerManager.version = version
    UnrealDocViewerManager.context = context
    context.Extensions().RegisterWindowMenu(WindowMenu.Window, ["UnrealDoc"], UnrealDocViewerManager.open_window)
    context.Extensions().RegisterWindowMenu(WindowMenu.Tools, ["Settings", "UnrealDoc"], UnrealDocViewerManager.open_settings_json)
    UnrealDocViewerManager.on_app_start()
    pass


def unregister():
    #
    disconnect_debug_server(DEBUG)
    #
    UnrealDocViewerManager.close_window()
    #
    PipelineStateUtils().unregister()
    StructBufferViewerManager().unregister()
    pass
