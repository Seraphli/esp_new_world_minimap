from appdirs import user_data_dir
import codecs
import json
import asyncio
import socketio
import uuid
import win32gui


APP_NAME = "electron-spirit"
PLUGIN_NAME = "ES NWMP"
PLUGIN_SETTING = "plugin.setting.json"
NWMP_URL = "https://www.newworldminimap.com/map"


class PluginApi(socketio.AsyncClientNamespace):
    def __init__(self, parent):
        super().__init__()
        self.elem_count = 0
        self.parent = parent
        self.lock_flag = True
        self.move_flag = False
        self.dev_flag = False

    def on_connect(self):
        print("Connected")

    def on_disconnect(self):
        print("Disconnected")

    def on_echo(self, data):
        print("Echo:", data)

    def on_register_topic(self, data):
        print("Register topic:", data)

    def on_hook_input(self, data):
        print("Hook input:", data)

    def on_insert_css(self, data):
        print("Insert css:", data)

    def on_remove_css(self, data):
        print("Remove css:", data)

    def on_update_elem(self, data):
        print("Update elem:", data)
        self.elem_count += 1

    def on_remove_elem(self, data):
        print("Remove elem:", data)
        self.elem_count -= 1

    def on_show_view(self, data):
        print("Show view:", data)

    def on_hide_view(self, data):
        print("Hide view:", data)

    def on_exec_js_in_elem(self, data):
        print("Exec js in elem:", data)

    def on_notify(self, data):
        print("Notify:", data)

    def on_update_bound(self, key, _type, bound):
        print("Update bound:", key, _type, bound)
        self.parent.update_bound(bound)

    def on_process_content(self, content):
        print("Process content:", content)

    def on_mode_flag(self, lock_flag, move_flag, dev_flag):
        print("Mode flag:", lock_flag, move_flag, dev_flag)
        self.lock_flag = lock_flag
        self.move_flag = move_flag
        self.dev_flag = dev_flag


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
        except:
            self.cfg = {"x": 100, "y": 100, "w": 300, "h": 300}
        self.save_cfg()

    def save_cfg(self):
        with codecs.open(PLUGIN_SETTING, "w") as f:
            json.dump(self.cfg, f)

    def update_bound(self, bound):
        self.view_elem["bound"] = bound
        self.cfg = bound
        self.save_cfg()

    def check_front_win_name(self):
        w = win32gui
        name = w.GetWindowText(w.GetForegroundWindow())
        if name == "New World":
            return True
        return False

    async def register(self):
        # Create a context for registering plugins
        # You can either use sample password or use complex password
        # You can also register multiple topic
        ctx = {"topic": "nwmp", "pwd": str(uuid.uuid4())}
        await sio.emit("register_topic", ctx)
        self.ctx = ctx

    async def wait_for_elem(self):
        while self.api.elem_count < 1:
            await sio.sleep(0.1)

    async def visible(self):
        self.show = True
        while True:
            if self.check_front_win_name() and not self.show:
                await sio.emit(
                    "show_view",
                    data=(
                        self.ctx,
                        self.view_elem,
                    ),
                )
                self.show = True
            if (
                not self.check_front_win_name()
                and self.show
                and self.api.lock_flag
                and not self.api.move_flag
                and not self.api.dev_flag
            ):
                await sio.emit(
                    "hide_view",
                    data=(
                        self.ctx,
                        self.view_elem,
                    ),
                )
                self.show = False
            await sio.sleep(0.1)

    async def main(self):
        self.view_elem = {
            "key": "view-1",
            "type": 1,
            "bound": self.cfg,
            "content": NWMP_URL,
        }
        await sio.emit(
            "update_elem",
            data=(
                self.ctx,
                self.view_elem,
            ),
        )
        await sio.start_background_task(self.wait_for_elem)
        await sio.start_background_task(self.visible)

    async def loop(self):
        await sio.connect(f"http://localhost:{self.port}")
        await sio.emit("echo", "Hello World!")
        await self.register()
        await self.main()


if __name__ == "__main__":
    # asyncio
    sio = socketio.AsyncClient()
    p = Plugin()
    sio.register_namespace(p.api)
    asyncio.run(p.loop())
