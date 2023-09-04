import os
import subprocess
import logging
import argparse

from ublue_update.update_checks.system import system_update_check
from ublue_update.update_checks.wait import transaction_wait
from ublue_update.update_inhibitors.hardware import check_hardware_inhibitors
from ublue_update.config import load_value


def notify(title: str, body: str, actions: list = [], urgency: str = "normal"):
    if not dbus_notify:
        return
    args = [
        "/usr/bin/notify-send",
        title,
        body,
        "--app-name=Universal Blue Updater",
        "--icon=software-update-available-symbolic",
        f"--urgency=${urgency}",
    ]
    if actions != []:
        for action in actions:
            args.append(f"--action={action}")
    out = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return out


def ask_for_updates():
    if not dbus_notify:
        return
    out = notify(
        "System Updater",
        "Update available, but system checks failed. Update now?",
        ["universal-blue-update-confirm=Confirm"],
        "critical"
    )
    # if the user has confirmed
    if "universal-blue-update-confirm" in out.stdout.decode("utf-8"):
        run_updates()


def check_for_updates(checks_failed: bool) -> bool:
    """Tracks whether any updates are available"""
    update_available: bool = False
    system_update_available: bool = system_update_check()
    if system_update_available:
        update_available = True
    if update_available:
        return True
    log.info("No updates are available.")
    return False


def hardware_inhibitor_checks_failed(
    hardware_checks_failed: bool, failures: list, hardware_check: bool
):
    # ask if an update can be performed through dbus notifications
    if check_for_updates(hardware_checks_failed) and not hardware_check:
        log.info("Harware checks failed, but update is available")
        ask_for_updates()
    # notify systemd that the checks have failed,
    # systemd will try to rerun the unit
    exception_log = "\n - ".join(failures)
    raise Exception(f"update failed to pass checks: \n - {exception_log}")


def run_updates():
    root_dir = "/etc/ublue-update.d/"

    log.info("Running system update")

    """Wait on any existing transactions to complete before updating"""
    transaction_wait()

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            full_path = root_dir + str(file)

            executable = os.access(full_path, os.X_OK)
            if executable:
                log.info(f"Running update script: {full_path}")
                out = subprocess.run(
                    [full_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )

                if out.returncode != 0:
                    log.info(f"{full_path} returned error code: {out.returncode}")
                    log.info(f"Program output: \n {out.stdout}")
                    notify(
                        "System Updater",
                        f"Error in update script: {file}, check logs for more info",
                    )
            else:
                log.info(f"could not execute file {full_path}")
    notify(
        "System Updater",
        "System update complete, reboot for changes to take effect",
    )
    log.info("System update complete")
    os._exit(0)


dbus_notify: bool = load_value("notify", "dbus_notify")

# setup logging
logging.basicConfig(
    format="[%(asctime)s] %(name)s:%(levelname)s | %(message)s",
    level=os.getenv("UBLUE_LOG", default=logging.INFO),
)
log = logging.getLogger(__name__)


def main():

    # setup argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force manual update, skipping update checks",
    )
    parser.add_argument(
        "-c", "--check", action="store_true", help="run update checks and exit"
    )
    parser.add_argument(
        "-u",
        "--updatecheck",
        action="store_true",
        help="check for updates and exit",
    )
    parser.add_argument(
        "-w",
        "--wait",
        action="store_true",
        help="wait for transactions to complete and exit",
    )
    args = parser.parse_args()
    hardware_checks_failed = False

    if args.wait:
        transaction_wait()
        os._exit(0)

    if not args.force and not args.updatecheck:
        hardware_checks_failed, failures = check_hardware_inhibitors()
        if hardware_checks_failed:
            hardware_inhibitor_checks_failed(
                hardware_checks_failed,
                failures,
                args.check,
            )
        if args.check:
            os._exit(0)

    if args.updatecheck:
        update_available = check_for_updates(False)
        if not update_available:
            raise Exception("Update not available")
        os._exit(0)

    # system checks passed
    log.info("System passed all update checks")
    notify(
        "System Updater",
        "System passed checks, updating ...",
    )
    run_updates()
