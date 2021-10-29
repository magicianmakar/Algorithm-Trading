#!/usr/bin/env python

import asyncio
import threading
from typing import Callable, Optional, Dict, Any, TYPE_CHECKING
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.document import Document
from prompt_toolkit.layout.processors import BeforeInput, PasswordProcessor
from prompt_toolkit.completion import Completer

from hummingbot.client.ui.layout import (
    create_input_field,
    create_log_field,
    create_log_toggle,
    create_output_field,
    create_search_field,
    generate_layout,
    create_timer,
    create_process_monitor,
    create_trade_monitor,
    create_live_field,
    create_button,
)
from hummingbot.client.ui.interface_utils import start_timer, start_process_monitor, start_trade_monitor
from hummingbot.client.ui.style import load_style
from hummingbot.client.tab.data_types import CommandTab
if TYPE_CHECKING:
    from hummingbot.client.hummingbot_application import HummingbotApplication
from hummingbot.core.utils.async_utils import safe_ensure_future
import logging


# Monkey patching here as _handle_exception gets the UI hanged into Press ENTER screen mode
def _handle_exception_patch(self, loop, context):
    if "exception" in context:
        logging.getLogger(__name__).error(f"Unhandled error in prompt_toolkit: {context.get('exception')}",
                                          exc_info=True)


Application._handle_exception = _handle_exception_patch


class HummingbotCLI:
    def __init__(self,
                 input_handler: Callable,
                 bindings: KeyBindings,
                 completer: Completer,
                 command_tabs: Dict[str, CommandTab]):
        self.command_tabs = command_tabs
        self.search_field = create_search_field()
        self.input_field = create_input_field(completer=completer)
        self.output_field = create_output_field()
        self.log_field = create_log_field(self.search_field)
        self.right_pane_toggle = create_log_toggle(self.toggle_right_pane)
        self.live_field = create_live_field()
        self.log_field_toggle = create_button("Running Logs", self.log_button_clicked)
        self.timer = create_timer()
        self.process_usage = create_process_monitor()
        self.trade_monitor = create_trade_monitor()
        self.layout, self.layout_components = generate_layout(self.input_field, self.output_field, self.log_field,
                                                              self.right_pane_toggle, self.log_field_toggle,
                                                              self.search_field, self.timer,
                                                              self.process_usage, self.trade_monitor,
                                                              self.command_tabs)
        # add self.to_stop_config to know if cancel is triggered
        self.to_stop_config: bool = False

        self.live_updates = False
        self.bindings = bindings
        self.input_handler = input_handler
        self.input_field.accept_handler = self.accept
        self.app: Optional[Application] = None

        # settings
        self.prompt_text = ">>> "
        self.pending_input = None
        self.input_event = None
        self.hide_input = False

        # start ui tasks
        loop = asyncio.get_event_loop()
        loop.create_task(start_timer(self.timer))
        loop.create_task(start_process_monitor(self.process_usage))
        loop.create_task(start_trade_monitor(self.trade_monitor))

    async def run(self):
        self.app = Application(layout=self.layout, full_screen=True, key_bindings=self.bindings, style=load_style(),
                               mouse_support=True, clipboard=PyperclipClipboard())
        await self.app.run_async()

    def accept(self, buff):
        self.pending_input = self.input_field.text.strip()

        if self.input_event:
            self.input_event.set()

        try:
            if self.hide_input:
                output = ''
            else:
                output = '\n>>>  {}'.format(self.input_field.text,)
                self.input_field.buffer.append_to_history()
        except BaseException as e:
            output = str(e)

        self.log(output)
        self.input_handler(self.input_field.text)

    def clear_input(self):
        self.pending_input = None

    def log(self, text: str, save_log: bool = True):
        if save_log:
            if self.live_updates:
                self.output_field.log(text, silent=True)
            else:
                self.output_field.log(text)
        else:
            self.output_field.log(text, save_log=False)

    def change_prompt(self, prompt: str, is_password: bool = False):
        self.prompt_text = prompt
        processors = []
        if is_password:
            processors.append(PasswordProcessor())
        processors.append(BeforeInput(prompt))
        self.input_field.control.input_processors = processors

    async def prompt(self, prompt: str, is_password: bool = False) -> str:
        self.change_prompt(prompt, is_password)
        self.app.invalidate()
        self.input_event = asyncio.Event()
        await self.input_event.wait()

        temp = self.pending_input
        self.clear_input()
        self.input_event = None

        if is_password:
            masked_string = "*" * len(temp)
            self.log(f"{prompt}{masked_string}")
        else:
            self.log(f"{prompt}{temp}")
        return temp

    def set_text(self, new_text: str):
        self.input_field.document = Document(text=new_text, cursor_position=len(new_text))

    def toggle_hide_input(self):
        self.hide_input = not self.hide_input

    def toggle_right_pane(self):
        if self.layout_components["pane_right"].width.weight == 1:
            self.layout_components["pane_right"].width.weight = 0
            self.layout_components["item_top_toggle"].text = '< log pane'
        else:
            self.layout_components["pane_right"].width.weight = 1
            self.layout_components["item_top_toggle"].text = '> log pane'

    def log_button_clicked(self):
        for tab in self.command_tabs.values():
            tab.is_focus = False
        self.redraw_app()
        # self.log_field.width.weight = 1
        # self.live_field.width.weight = 0
        # self.log_field.is_visible = True
        # self.live_field.is_visible = False

    def tab_button_clicked(self, command_name: str):
        # live_2 = create_live_field()
        # self.layout_components["pane_right_middle"].children.append(live_2)
        # self.log_field.width.weight = 0
        # self.live_field.width.weight = 0
        # live_2.width.weight = 1
        # self.log_field.is_visible = False
        # self.live_field.is_visible = True
        # live_2.log("live live")
        self.command_tabs[command_name].is_focus = True
        self.redraw_app()

    def exit(self):
        self.app.exit()

    def redraw_app(self):
        self.layout, self.layout_components = generate_layout(self.input_field, self.output_field, self.log_field,
                                                              self.right_pane_toggle, self.log_field_toggle,
                                                              self.search_field, self.timer,
                                                              self.process_usage, self.trade_monitor, self.command_tabs)
        self.app.layout = self.layout
        self.app.invalidate()

    def close_buton_clicked(self, command_name: str):
        self.command_tabs[command_name].button = None
        self.command_tabs[command_name].close_button = None
        self.command_tabs[command_name].output_field = None
        self.command_tabs[command_name].is_focus = False

    def handle_tab_command(self, hummingbot: "HummingbotApplication", command_name: str, kwargs: Dict[str, Any]):
        if command_name not in self.command_tabs:
            return
        cmd_tab = self.command_tabs[command_name]
        if cmd_tab.button is None:
            cmd_tab.button = create_button(command_name, lambda: self.tab_button_clicked(command_name))
            cmd_tab.close_button = create_button("x", lambda: self.tab_button_clicked(command_name))
            cmd_tab.output_field = create_live_field()
        self.tab_button_clicked(command_name)
        self.display_tab_output(cmd_tab, hummingbot, kwargs)

    def display_tab_output(self,
                           command_tab: CommandTab,
                           hummingbot: "HummingbotApplication",
                           kwargs: Dict[Any, Any]):
        if threading.current_thread() != threading.main_thread():
            hummingbot.ev_loop.call_soon_threadsafe(self.display_tab_output, command_tab, hummingbot, kwargs)
            return
        safe_ensure_future(command_tab.tab_class.display(command_tab.output_field, hummingbot, **kwargs))
