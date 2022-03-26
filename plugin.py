from appdirs import user_data_dir
import codecs
import json
import asyncio
import socketio
import uuid
import win32gui
import sys


APP_NAME = "electron-spirit"
PLUGIN_NAME = "ES NWMP"
PLUGIN_VERSION = "0.4.0"
PLUGIN_SETTING = "plugin.setting.json"
NWMP_URL = ["https://www.newworldminimap.com/map", "https://www.newworld-map.com/#/"]
DEFAULT_CONFIG = {
    "x": 100,
    "y": 100,
    "w": 450,
    "h": 300,
    "debug": True,
    "url": NWMP_URL,
    "index": 0,
    "opacity": 1.0,
}


class PluginApi(socketio.AsyncClientNamespace):
    def __init__(self, parent):
        super().__init__()
        self.elem_count = 0
        self.parent = parent
        self.lock_flag = True
        self.move_flag = False
        self.dev_flag = False

    async def on_connect(self):
        print("Connected")
        await self.parent.setup_connect()

    def on_disconnect(self):
        print("Disconnected")

    def on_echo(self, data):
        print("Echo:", data)

    def on_addInputHook(self, data):
        print("Add input hook:", data)

    def on_delInputHook(self, data):
        print("Del input hook:", data)

    def on_insertCSS(self, data):
        print("Insert css:", data)

    def on_removeCSS(self, data):
        print("Remove css:", data)

    def on_addElem(self, data):
        print("Add elem:", data)
        self.elem_count += 1

    def on_delElem(self, data):
        print("Remove elem:", data)
        self.elem_count -= 1

    def on_showElem(self, data):
        print("Show view:", data)

    def on_hideElem(self, data):
        print("Hide view:", data)

    def on_setBound(self, data):
        print("Set bound:", data)

    def on_setContent(self, data):
        print("Set content:", data)

    def on_setOpacity(self, data):
        print("Set opacity:", data)

    def on_execJSInElem(self, data):
        print("Exec js in elem:", data)

    def on_notify(self, data):
        print("Notify:", data)

    def on_updateBound(self, key, bound):
        print("Update bound:", key, bound)
        self.parent.update_bound(bound)

    def on_updateOpacity(self, key, opacity):
        print("Update opacity:", key, opacity)
        self.parent.set_opacity(opacity)

    def on_processContent(self, content):
        print("Process content:", content)

    def on_modeFlag(self, flags):
        print("Mode flag:", flags)
        self.lock_flag = flags["lock"]
        self.move_flag = flags["move"]
        self.dev_flag = flags["dev"]

    def on_elemRemove(self, key):
        print("Elem remove:", key)
        # prevent remove elem
        return True

    def on_elemRefresh(self, key):
        print("Elem refresh:", key)
        # prevent refresh elem
        return True


class Plugin(object):
    def __init__(self) -> None:
        self.load_config()
        self.api = PluginApi(self)

    def load_config(self):
        path = user_data_dir(APP_NAME, False, roaming=True)
        with codecs.open(path + "/api.json") as f:
            config = json.load(f)
        self.port = config["apiPort"]
        try:
            with codecs.open(PLUGIN_SETTING) as f:
                self.cfg = json.load(f)
            for k in DEFAULT_CONFIG:
                if k not in self.cfg or (
                    k in self.cfg and type(self.cfg[k]) != type(DEFAULT_CONFIG[k])
                ):
                    self.cfg[k] = DEFAULT_CONFIG[k]
        except:
            self.cfg = DEFAULT_CONFIG
        self.save_cfg()

    def save_cfg(self):
        with codecs.open(PLUGIN_SETTING, "w") as f:
            json.dump(self.cfg, f)

    def update_bound(self, bound):
        self.view_elem["bound"] = bound
        self.cfg = {**self.cfg, **bound}
        self.save_cfg()

    def set_opacity(self, opacity):
        self.cfg["opacity"] = opacity
        print("Set opacity:", opacity)
        self.save_cfg()

    def check_front_win_name(self):
        w = win32gui
        name = w.GetWindowText(w.GetForegroundWindow())
        if name == "New World":
            return True
        return False

    async def wait_for_elem(self):
        while self.api.elem_count < 1:
            await sio.sleep(0.1)
        
        await sio.emit("setOpacity", data=(self.catKey, self.cfg["opacity"]))
        print("Set opacity:", self.cfg["opacity"])

    async def visible(self):
        self.show = True
        while True:
            if self.check_front_win_name() and not self.show:
                await sio.emit(
                    "showElem",
                    data=(self.catKey,),
                )
                self.show = True
            if (
                not self.check_front_win_name()
                and self.show
                and self.api.lock_flag
                and not self.api.move_flag
                and not self.api.dev_flag
                and not self.cfg["debug"]
            ):
                await sio.emit(
                    "hideElem",
                    data=(self.catKey,),
                )
                self.show = False
            await sio.sleep(0.1)

    async def setup_connect(self):
        self.catKey = "nwmp"
        self.view_elem = {
            "type": 1,
            "bound": {
                "x": self.cfg["x"],
                "y": self.cfg["y"],
                "w": self.cfg["w"],
                "h": self.cfg["h"],
            },
            "content": self.cfg["url"][self.cfg["index"]],
        }
        await sio.emit(
            "addElem",
            data=(
                self.catKey,
                self.view_elem,
            ),
        )
        await sio.start_background_task(self.wait_for_elem)
        await sio.start_background_task(self.visible)

    async def loop(self):
        await sio.connect(f"http://localhost:{self.port}")
        await sio.wait()


if __name__ == "__main__":
    print(f"Start {PLUGIN_NAME} {PLUGIN_VERSION}")
    # asyncio
    try:
        sio = socketio.AsyncClient()
        p = Plugin()
        sio.register_namespace(p.api)
        asyncio.run(p.loop())
    except KeyboardInterrupt:
        print("Bye!")
        sys.exit(0)
    except Exception as e:
        import traceback

        traceback.print_exc()
        input()
        sys.exit(0)
