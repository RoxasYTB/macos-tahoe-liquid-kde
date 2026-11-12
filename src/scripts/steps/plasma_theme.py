from localization import tr
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import configparser
from pathlib import Path

from glass_surfaces import apply_plasma_surface_defaults

from steps._helpers import (
    DATA_HOME, fail, info, install_tree, kw_write, offline, ok, remove_tree, temp_dir, warn,
)
from utils import run_user

DEST_DIR = DATA_HOME / "plasma/desktoptheme"
LEGACY = ("MacTahoe-Dark", "MacTahoe-Light")
VARIANTS = ("MacTahoeLiquidKde-Dark", "MacTahoeLiquidKde-Light")
_MENU_STYLE_HOME = DATA_HOME / "mac-tahoe-liquid-kde/plasma-menu-style"
_MENU_STYLE_OVERLAY = _MENU_STYLE_HOME / "qml"
_MENU_STYLE_REFRESH = _MENU_STYLE_HOME / "refresh.py"
_MENU_STYLE_ENV_MARKER = "# Managed by mac-tahoe-liquid-kde: Plasma QML menu styling\n"
_MENU_BLUR_WATCHER = _MENU_STYLE_HOME / "blur_watch.py"
_MENU_BLUR_SERVICE_NAME = "mac-tahoe-plasma-menu-blur.service"
_MENU_BLUR_SERVICE_MARKER = "# Managed by mac-tahoe-liquid-kde: Plasma menu blur watcher\n"
_MENU_BLUR_STATE = _MENU_STYLE_HOME / "blur-plugin-original.json"
_MENU_BLUR_STATE_MARKER = "# Managed by mac-tahoe-liquid-kde: original KWin blur setting\n"


def deps() -> list[str]:
    return ["python-xlib:python-xlib"]


def _menu_style_env_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "plasma-workspace/env/mac-tahoe-plasma-menu-style.sh"


def _menu_blur_service_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "systemd/user" / _MENU_BLUR_SERVICE_NAME


def _menu_blur_service_contents() -> str:
    return (
        _MENU_BLUR_SERVICE_MARKER
        + "[Unit]\n"
        + "Description=Rounded blur for Tahoe Plasma context menus\n"
        + "After=graphical-session.target\n"
        + "PartOf=graphical-session.target\n\n"
        + "[Service]\n"
        + "Type=simple\n"
        + f"ExecStart=/usr/bin/python3 {shlex.quote(str(_MENU_BLUR_WATCHER))}\n"
        + "Restart=on-failure\n"
        + "RestartSec=2\n\n"
        + "[Install]\n"
        + "WantedBy=graphical-session.target\n"
    )


def _kwin_blur_enabled() -> bool | None:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(config_home / "kwinrc", encoding="utf-8")
        return parser.getboolean("Plugins", "blurEnabled", fallback=None)
    except (OSError, configparser.Error, ValueError):
        return None


def _kwin_liquidglass_enabled() -> bool:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(config_home / "kwinrc", encoding="utf-8")
        return parser.getboolean("Plugins", "liquidglassEnabled", fallback=False)
    except (OSError, configparser.Error, ValueError):
        return False


def _capture_original_blur_setting() -> None:
    if _MENU_BLUR_STATE.is_file() and not _MENU_BLUR_STATE.is_symlink():
        try:
            if _MENU_BLUR_STATE.read_text(encoding="utf-8").startswith(_MENU_BLUR_STATE_MARKER):
                return
        except (OSError, UnicodeError):
            pass
    original = _kwin_blur_enabled()
    body = json.dumps({"original": original}, separators=(",", ":"))
    _write_owned_file(_MENU_BLUR_STATE, _MENU_BLUR_STATE_MARKER + body + "\n", _MENU_BLUR_STATE_MARKER)


def _start_blur_watcher() -> None:
    source = offline("plasma-theme", "plasma-menu-overlay", "blur_watch.py")
    try:
        data = source.read_text(encoding="utf-8")
    except OSError as exc:
        warn(tr("Plasma menu blur watcher source unavailable: {value1}", value1=exc))
        return
    if not data.startswith("#!/usr/bin/env python3\n# Managed by mac-tahoe-liquid-kde: Plasma QML menu blur watcher\n"):
        warn(tr("Plasma menu blur watcher source is not recognized"))
        return
    if not _write_owned_file(
        _MENU_BLUR_WATCHER, data,
        "#!/usr/bin/env python3\n# Managed by mac-tahoe-liquid-kde: Plasma QML menu blur watcher\n",
    ):
        warn(tr("Unowned Plasma menu blur watcher preserved: {value1}", value1=_MENU_BLUR_WATCHER))
        return
    service = _menu_blur_service_path()
    if not _write_owned_file(service, _menu_blur_service_contents(), _MENU_BLUR_SERVICE_MARKER):
        warn(tr("Unowned Plasma menu blur service preserved: {value1}", value1=service))
        return

    # Liquid Glass already supplies the menu blur. Enabling KWin's stock blur
    # as well stacks a second darkening layer over the translucent surface.
    if not _kwin_liquidglass_enabled():
        _capture_original_blur_setting()
        if not kw_write("--file", "kwinrc", "--group", "Plugins", "--key", "blurEnabled", "true"):
            warn(tr("KWin blur could not be enabled in kwinrc"))
        run_user(["qdbus6", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects.loadEffect", "blur"],
                 capture_output=True, text=True)
    run_user(["systemctl", "--user", "daemon-reload"], capture_output=True, text=True)
    enabled = run_user(["systemctl", "--user", "reenable", _MENU_BLUR_SERVICE_NAME],
                       capture_output=True, text=True)
    if enabled.returncode:
        enabled = run_user(["systemctl", "--user", "enable", _MENU_BLUR_SERVICE_NAME],
                           capture_output=True, text=True)
    started = run_user(["systemctl", "--user", "restart", _MENU_BLUR_SERVICE_NAME],
                       capture_output=True, text=True)
    if enabled.returncode or started.returncode:
        detail = (started.stderr or enabled.stderr).strip()
        warn(tr("Plasma menu blur watcher did not start: {value1}", value1=detail))


def _write_owned_file(path: Path, data: str, marker: str) -> bool:
    if path.is_symlink():
        return False
    if path.exists():
        try:
            if not path.read_text(encoding="utf-8").startswith(marker):
                return False
        except (OSError, UnicodeError):
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
        os.chmod(temp_name, 0o755 if path.suffix == ".sh" else 0o644)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return True


def _menu_style_env_contents() -> str:
    overlay = shlex.quote(str(_MENU_STYLE_OVERLAY))
    refresh = shlex.quote(str(_MENU_STYLE_REFRESH))
    return (
        _MENU_STYLE_ENV_MARKER
        + f"if /usr/bin/python3 {refresh} >/dev/null; then\n"
        + f"    _tahoe_qml_menu_path={overlay}\n"
        + '    case ":${QML_IMPORT_PATH:-}:" in\n'
        + '        *":${_tahoe_qml_menu_path}:"*) ;;\n'
        + '        *) export QML_IMPORT_PATH="${_tahoe_qml_menu_path}${QML_IMPORT_PATH:+:$QML_IMPORT_PATH}" ;;\n'
        + "    esac\n"
        + '    systemctl --user set-environment "QML_IMPORT_PATH=${QML_IMPORT_PATH}" >/dev/null 2>&1 || true\n'
        + "else\n"
        + f"    _tahoe_qml_menu_path={overlay}\n"
        + f"    _tahoe_clean_qml_path=$(/usr/bin/python3 {refresh} --strip-import-path 2>/dev/null) || _tahoe_clean_qml_path=\n"
        + '    if [ -n "${_tahoe_clean_qml_path}" ]; then\n'
        + '        export QML_IMPORT_PATH="${_tahoe_clean_qml_path}"\n'
        + '        systemctl --user set-environment "QML_IMPORT_PATH=${_tahoe_clean_qml_path}" >/dev/null 2>&1 || true\n'
        + "    else\n"
        + "        unset QML_IMPORT_PATH\n"
        + "        systemctl --user unset-environment QML_IMPORT_PATH >/dev/null 2>&1 || true\n"
        + "    fi\n"
        + "fi\n"
        + "unset _tahoe_qml_menu_path _tahoe_clean_qml_path\n"
    )


def _set_session_qml_import_path(add: bool) -> None:
    """Update systemd's user environment so an immediate Plasma restart uses the overlay."""
    show = run_user(["systemctl", "--user", "show-environment"], capture_output=True, text=True)
    values = {}
    for line in (show.stdout if show.returncode == 0 else "").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    paths = []
    for value in (values.get("QML_IMPORT_PATH", ""), os.environ.get("QML_IMPORT_PATH", "")):
        for part in value.split(":"):
            if part and part not in paths:
                paths.append(part)
    overlay = str(_MENU_STYLE_OVERLAY)
    if add and overlay not in paths:
        paths.insert(0, overlay)
    elif not add:
        paths = [part for part in paths if part != overlay]
    updated = ":".join(paths)
    if updated:
        os.environ["QML_IMPORT_PATH"] = updated
    else:
        os.environ.pop("QML_IMPORT_PATH", None)
    command = ["systemctl", "--user", "set-environment", f"QML_IMPORT_PATH={updated}"] if updated else [
        "systemctl", "--user", "unset-environment", "QML_IMPORT_PATH"
    ]
    run_user(command, capture_output=True, text=True)


def _install_menu_style_overlay() -> None:
    source = offline("plasma-theme", "plasma-menu-overlay", "refresh.py")
    try:
        data = source.read_text(encoding="utf-8")
    except OSError as exc:
        fail(tr("Plasma QML menu overlay source unavailable: {value1}", value1=exc))
        return
    if not data.startswith("#!/usr/bin/env python3\n# Managed by mac-tahoe-liquid-kde: Plasma QML menu overlay\n"):
        fail(tr("Plasma QML menu overlay source is not recognized"))
        return

    if not _write_owned_file(_MENU_STYLE_REFRESH, data, "#!/usr/bin/env python3\n# Managed by mac-tahoe-liquid-kde: Plasma QML menu overlay\n"):
        fail(tr("Unowned Plasma QML menu refresh script preserved: {value1}", value1=_MENU_STYLE_REFRESH))
        return
    env_path = _menu_style_env_path()
    if not _write_owned_file(env_path, _menu_style_env_contents(), _MENU_STYLE_ENV_MARKER):
        fail(tr("Unowned Plasma environment file preserved: {value1}", value1=env_path))
        return

    result = run_user([sys.executable, str(_MENU_STYLE_REFRESH)], capture_output=True, text=True)
    if result.returncode:
        fail(tr("Plasma QML menu overlay could not be prepared: {value1}", value1=result.stderr.strip()))
        return
    _set_session_qml_import_path(True)
    _start_blur_watcher()
    ok(tr("Plasma QML context-menu state styling installed"))


def _uninstall_menu_style_overlay() -> None:
    env_path = _menu_style_env_path()
    if not env_path.is_symlink():
        try:
            if env_path.read_text(encoding="utf-8").startswith(_MENU_STYLE_ENV_MARKER):
                env_path.unlink()
        except (OSError, UnicodeError):
            pass
    _set_session_qml_import_path(False)
    service = _menu_blur_service_path()
    run_user(["systemctl", "--user", "disable", "--now", _MENU_BLUR_SERVICE_NAME],
             capture_output=True, text=True)
    if not service.is_symlink():
        try:
            if service.read_text(encoding="utf-8").startswith(_MENU_BLUR_SERVICE_MARKER):
                service.unlink()
                run_user(["systemctl", "--user", "daemon-reload"], capture_output=True, text=True)
        except (OSError, UnicodeError):
            pass
    if _MENU_BLUR_STATE.is_file() and not _MENU_BLUR_STATE.is_symlink():
        try:
            state_text = _MENU_BLUR_STATE.read_text(encoding="utf-8")
            if state_text.startswith(_MENU_BLUR_STATE_MARKER):
                original = json.loads(state_text[len(_MENU_BLUR_STATE_MARKER):]).get("original")
                current = _kwin_blur_enabled()
                if current is True and original is False:
                    kw_write("--file", "kwinrc", "--group", "Plugins", "--key", "blurEnabled", "false")
                    run_user(["qdbus6", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects.unloadEffect", "blur"],
                             capture_output=True, text=True)
                elif current is True and original is None:
                    kw_write("--file", "kwinrc", "--group", "Plugins", "--key", "blurEnabled", "--delete")
                    run_user(["qdbus6", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects.unloadEffect", "blur"],
                             capture_output=True, text=True)
                _MENU_BLUR_STATE.unlink()
        except (OSError, UnicodeError, ValueError, TypeError):
            pass
    # Keep the generated QML mirror as recoverable data; removing the hook and
    # session import path makes it inert, and reinstall can refresh it in place.

def install() -> None:
    src = offline("plasma-theme")
    if not src.is_dir():
        fail(tr('Plasma theme source not found at {src}', src=src))
        return
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # Purge legacy names from pre-0.6.2 installs.
    for stale in LEGACY:
        shutil.rmtree(DEST_DIR / stale, ignore_errors=True)

    n = 0
    for v in VARIANTS:
        if not (src / v).is_dir():
            continue
        with temp_dir("plasma-surfaces-") as staging:
            source = staging / v
            shutil.copytree(src / v, source)
            apply_plasma_surface_defaults(source)
            if install_tree(source, DEST_DIR / v, v):
                n += 1
    info(tr('{n} Plasma themes installed/reinstalled', n=n))
    _install_menu_style_overlay()


def uninstall() -> None:
    _uninstall_menu_style_overlay()
    n = 0
    for v in VARIANTS:
        remove_tree(DEST_DIR / (v + "-ReducedTransparency"))
        if remove_tree(DEST_DIR / v, v):
            n += 1
    if not kw_write("--file", "plasmarc", "--group", "Theme",
                    "--key", "name", "default"):
        warn(tr("Active Plasma theme not reset to 'default' — kwriteconfig6 unavailable. Files are removed but Plasma will still try to load MacTahoeLiquidKde until you set plasmarc:Theme.name=default manually."))
    info(tr('{n} Plasma themes removed', n=n))
