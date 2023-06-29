# RenderDoc Python console, powered by python 3.6.4.
# The 'pyrenderdoc' object is the current CaptureContext instance.
# The 'renderdoc' and 'qrenderdoc' modules are available.
# Documentation is available: https://renderdoc.org/docs/python_api/index.html

# Used to open exist rdc file
RDC_FILE = ""
CONTROL_RDC_FILE = ""  # CompareFilePath
ROOT_NAME = "Scene"  # ROOT_NAME =""  =>  all passes in the same level of "Capture Start"
FOCUS_EVENTS_IN_PASS = ["PrePass DDM_AllOpaque (Forced by DBuffer)", "CompositionBeforeBasePass", "BasePass",  "Translucency"] #"Lights",
IS_X20 = False

g_absoulte = None
g_assets_folder = None
g_current_controller = None
g_drawcall_dict = {}
g_drawcall_dict_control = {}
g_drawcall_common = []
from pathlib import WindowsPath
import sys

# Import renderdoc if not already imported (e.g. in the UI)
if 'renderdoc' not in sys.modules and '_renderdoc' not in sys.modules:
    import renderdoc

# Alias renderdoc for legibility
# rd = renderdoc
rd = sys.modules["renderdoc"]


class DrawCall:
    def __init__(self, draw, pass_name):
        self.draw = draw
        self.pass_name = pass_name
        self.parent = self.draw.parent
        self.eventId = draw.eventId if draw else 0
        self.numIndices = self.draw.numIndices
        self.numInstances = self.draw.numInstances
        global g_drawcall_dict
        global g_drawcall_dict_control
        if str(g_absoulte) == str(WindowsPath(CONTROL_RDC_FILE).absolute()):
            g_drawcall_dict_control[self.getName()] = self
        elif str(g_absoulte) == str(WindowsPath(RDC_FILE).absolute()):
            g_drawcall_dict[self.getName()] = self

    def getName(self):
        suffix = " " + str(self.numIndices) + " indices"
        prefix = self.pass_name + "    "
        if self.parent:
            name = prefix + self.parent.GetName(g_current_controller.GetStructuredFile()) + suffix
        else:
            name = prefix + self.draw.GetName(g_current_controller.GetStructuredFile()) + suffix
        return name
    pass


def find_events_tree_entry(root):
    name = root.GetName(g_current_controller.GetStructuredFile())
    if str(name) == ROOT_NAME:
        return root
    for child in root.children:
        entry = find_events_tree_entry(child)
        if entry:
            return entry


def collect_frame_events_internal(action, pass_name, fwrite):
    if action.flags & rd.ActionFlags.Drawcall:
        new_draw_call = DrawCall(action, pass_name)
        content = new_draw_call.getName()
        fwrite.write(content)
        fwrite.write("\n")
    else:
        for child in action.children:
            collect_frame_events_internal(child, pass_name, fwrite)


# Write variable htmls
def collect_frame_events(controller):
    global g_current_controller
    g_current_controller = controller
    root_actions = g_current_controller.GetRootActions()
    if ROOT_NAME == "":
        pass_list = root_actions
    else:
        entry = "None"
        for item in root_actions:
            entry = find_events_tree_entry(item)
            if entry:
                break
        if str(entry) == 'None':
            print("[Error] ROOT_FRAME: '%s' do not exist!Please ensure!\n" % ROOT_NAME)
            return
        pass_list = entry.children

    filename = "Origin_" + str(g_absoulte.stem) + ".txt"
    filepath = g_assets_folder / filename
    txt_write = open(str(filepath), 'w', encoding='utf-8')

    for item in pass_list:
        pass_name = item.GetName(g_current_controller.GetStructuredFile())
        if IS_X20:
            if pass_name in FOCUS_EVENTS_IN_PASS:
                for child in item.children:
                    collect_frame_events_internal(child, pass_name, txt_write)
        else:
            collect_frame_events_internal(item, pass_name, txt_write)

    txt_write.close()
    print("Finished!")


def write_processed_events(frame_path):
    filename = "Processed_" + WindowsPath(frame_path).absolute().stem + ".txt"
    filepath = g_assets_folder / filename
    txt_write = open(str(filepath), 'w', encoding='utf-8')

    # Remove duplicate elements
    if frame_path is RDC_FILE:
        for element in g_drawcall_common:
            txt_write.write("%d    %s\n" % (g_drawcall_dict[element].eventId, element))
            g_drawcall_dict.pop(element)
        txt_write.write("\nDiff:\n")
        for i, j in g_drawcall_dict.items():
            txt_write.write("%d    %s\n" % (j.eventId, i))
    elif frame_path is CONTROL_RDC_FILE:
        for element in g_drawcall_common:
            txt_write.write("%d    %s\n" % (g_drawcall_dict_control[element].eventId, element))
            g_drawcall_dict_control.pop(element)
        txt_write.write("\nDiff:\n")
        for i, j in g_drawcall_dict_control.items():
            txt_write.write("%d    %s\n" % (j.eventId, i))
    txt_write.close()
    pass


def handle_events_order(controller):
    global g_drawcall_dict_control
    global g_drawcall_common

    # Find common elements
    for item_key in g_drawcall_dict.keys():
        if item_key in g_drawcall_dict_control.keys() and \
                g_drawcall_dict[item_key].pass_name == g_drawcall_dict_control[item_key].pass_name:
            g_drawcall_common.append(item_key)

    write_processed_events(RDC_FILE)
    write_processed_events(CONTROL_RDC_FILE)
    print("Finished2!")
    pass


def reset_data_container():
    global g_drawcall_dict
    global g_drawcall_dict_control
    global g_drawcall_common
    g_drawcall_dict.clear()
    g_drawcall_dict_control.clear()
    g_drawcall_common.clear()


def create_result_folder():
    global g_absoulte
    global g_assets_folder
    g_absoulte = WindowsPath(RDC_FILE).absolute()
    file_name = g_absoulte.stem + "_CompareResult"
    g_assets_folder = g_absoulte.parent / file_name
    g_assets_folder.mkdir(parents=True, exist_ok=True)


def load_capture(filename):
    rd.InitialiseReplay(rd.GlobalEnvironment(), [])
    # Open a capture file handle
    cap = rd.OpenCaptureFile()
    # Open a particular file - see also OpenBuffer to load from memory
    result = cap.OpenFile(filename, '', None)
    # Make sure the file opened successfully
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError("Couldn't open file: " + str(result))
    # Make sure we can replay
    if not cap.LocalReplaySupport():
        raise RuntimeError("Capture cannot be replayed")
    # Initialise the replay
    result, controller = cap.OpenCapture(rd.ReplayOptions(), None)
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError("Couldn't initialise replay: " + str(result))
    return cap, controller


def main():
    global RDC_FILE
    global g_current_controller
    global g_absoulte
    if 'pyrenderdoc' in globals():
        if RDC_FILE == "":
            RDC_FILE = pyrenderdoc.GetCaptureFilename()

        if CONTROL_RDC_FILE == "":
            pyrenderdoc.Extensions().MessageDialog(
                "Frame of control group is null, please enter value of 'CompareFilePath'", "Error")
            return
        # Reset
        reset_data_container()
        create_result_folder()

        # RDC frame of control group
        g_absoulte = WindowsPath(CONTROL_RDC_FILE).absolute()
        pyrenderdoc.LoadCapture(CONTROL_RDC_FILE, rd.ReplayOptions(), CONTROL_RDC_FILE, False, True)
        pyrenderdoc.Replay().BlockInvoke(collect_frame_events)

        # Another rdc file : RDC frame of experimental group
        g_absoulte = WindowsPath(RDC_FILE).absolute()
        pyrenderdoc.LoadCapture(RDC_FILE, rd.ReplayOptions(), RDC_FILE, False, True)
        pyrenderdoc.Replay().BlockInvoke(collect_frame_events)

        pyrenderdoc.Replay().BlockInvoke(handle_events_order)
    else:
        if len(sys.argv) <= 1:
            print('Usage: python3 {} filename.rdc'.format(sys.argv[0]))
            sys.exit(0)
        # Reset
        reset_data_container()
        create_result_folder()

        # RDC frame of control group
        cap0, g_current_controller = load_capture(CONTROL_RDC_FILE)
        g_absoulte = WindowsPath(CONTROL_RDC_FILE).absolute()
        collect_frame_events(g_current_controller)
        g_current_controller.Shutdown()

        # Another rdc file : RDC frame of experimental group
        cap1, g_current_controller = load_capture(RDC_FILE)
        g_absoulte = WindowsPath(RDC_FILE).absolute()
        collect_frame_events(g_current_controller)

        handle_events_order(g_current_controller)

        g_current_controller.Shutdown()
        cap0.Shutdown()
        cap1.Shutdown()
        rd.ShutdownReplay()


if __name__ == "__main__":
    main()
    pass
