#!/usr/bin/env python

import bin.path_util        # noqa: F401
import asyncio
import errno
import socket
from typing import (
    List,
    Coroutine
)

from hummingbot.client.hummingbot_application import HummingbotApplication
from hummingbot.client.config.global_config_map import global_config_map
from hummingbot.client.config.config_helpers import (
    create_yml_files,
    read_configs_from_yml
)
from hummingbot import (
    init_logging,
    check_dev_mode,
    chdir_to_data_directory
)
from hummingbot.client.ui.stdout_redirection import patch_stdout
from hummingbot.core.utils.async_utils import safe_gather
from hummingbot.core.utils.exchange_rate_conversion import ExchangeRateConversion
from prompt_toolkit.shortcuts import input_dialog, message_dialog
from prompt_toolkit.styles import Style
from hummingbot.client.config.security import Security


def detect_available_port(starting_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        current_port: int = starting_port
        while current_port < 65535:
            try:
                s.bind(("127.0.0.1", current_port))
                break
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    current_port += 1
                    continue
        return current_port


async def main():
    chdir_to_data_directory()

    await create_yml_files()

    # This init_logging() call is important, to skip over the missing config warnings.
    init_logging("hummingbot_logs.yml")

    read_configs_from_yml()
    ExchangeRateConversion.get_instance().start()

    hb = HummingbotApplication.main_application()

    with patch_stdout(log_field=hb.app.log_field):
        dev_mode = check_dev_mode()
        if dev_mode:
            hb.app.log("Running from dev branches. Full remote logging will be enabled.")
        init_logging("hummingbot_logs.yml",
                     override_log_level=global_config_map.get("log_level").value,
                     dev_mode=dev_mode)
        tasks: List[Coroutine] = [hb.run()]
        if global_config_map.get("debug_console").value:
            if not hasattr(__builtins__, "help"):
                import _sitebuiltins
                __builtins__.help = _sitebuiltins._Helper()

            from hummingbot.core.management.console import start_management_console
            management_port: int = detect_available_port(8211)
            tasks.append(start_management_console(locals(), host="localhost", port=management_port))
        await safe_gather(*tasks)

dialog_style = Style.from_dict({
    'dialog': 'bg:#171E2B',
    'dialog frame.label': 'bg:#ffffff #000000',
    'dialog.body': 'bg:#000000 #1CD085',
    'dialog shadow': 'bg:#171E2B',
    'button': 'bg:#000000',
    'text-area': 'bg:#000000 #1CD085',
})

logo = """

    ██╗  ██╗██╗   ██╗███╗   ███╗███╗   ███╗██╗███╗   ██╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██║  ██║██║   ██║████╗ ████║████╗ ████║██║████╗  ██║██╔════╝ ██╔══██╗██╔═══██╗╚══██╔══╝
    ███████║██║   ██║██╔████╔██║██╔████╔██║██║██╔██╗ ██║██║  ███╗██████╔╝██║   ██║   ██║
    ██╔══██║██║   ██║██║╚██╔╝██║██║╚██╔╝██║██║██║╚██╗██║██║   ██║██╔══██╗██║   ██║   ██║
    ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║██║██║ ╚████║╚██████╔╝██████╔╝╚██████╔╝   ██║
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝

    =======================================================================================

    Version:  [version number]
    Codebase: https://github.com/coinalpha/hummingbot


"""


def login(welcome_msg=True):
    err_msg = None
    if Security.new_password_required():
        if welcome_msg:
            message_dialog(
                title='Welcome to Hummingbot',
                text=logo,
                style=dialog_style).run()
        password = input_dialog(
            title="Security",
            text="Set a password to protect your sensitive data. This password is not shared with us nor with anyone else, so please store it in a safe place.\n\nEnter your new password:",
            password=True,
            style=dialog_style).run()
        re_password = input_dialog(
            title="Security",
            text="Please re-enter your password:",
            password=True,
            style=dialog_style).run()
        if password != re_password:
            err_msg = "Passwords entered do not match, please try again."
        else:
            Security.login(password)
    else:
        if welcome_msg:
            message_dialog(
                title='Welcome to Hummingbot',
                text=logo,
                style=dialog_style).run()
        password = input_dialog(
            title="Security",
            text="Enter your password:",
            password=True,
            style=dialog_style).run()
        if not Security.login(password):
            err_msg = "Invalid password - please try again."
    if err_msg is not None:
        message_dialog(
            title='Error',
            text=err_msg,
            style=dialog_style).run()
        login(welcome_msg=False)


if __name__ == "__main__":
    login()
    ev_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    ev_loop.run_until_complete(main())
