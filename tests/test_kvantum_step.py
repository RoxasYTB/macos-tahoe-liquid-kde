"""Bundled Qt 6 Kvantum engine fallback for Debian-family hosts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def isolate_session_environment_commands(monkeypatch):
    """Installer unit tests must not mutate the maintainer's session manager."""
    from steps import kvantum

    monkeypatch.delenv("QT_PLUGIN_PATH", raising=False)
    monkeypatch.delenv("QML_IMPORT_PATH", raising=False)
    monkeypatch.setattr(
        kvantum, "run_user",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=""),
    )


def _neon(monkeypatch, kvantum, destination):
    monkeypatch.setattr(kvantum, "is_debian_family", lambda: True)
    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)


def test_neon_uses_build_deps_when_qt6_engine_is_missing(monkeypatch, tmp_path):
    from steps import kvantum

    _neon(monkeypatch, kvantum, tmp_path / "plugins/styles/libkvantum.so")

    deps = set(kvantum.deps())

    assert "qt6-svg-cmake:qt6-svg" in deps
    assert "xext-cmake:libxext" in deps
    assert "kvantummanager:kvantum" not in deps


def test_neon_builds_user_overlay_for_unmarked_distro_qt6_engine(monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"distro-owned")
    _neon(monkeypatch, kvantum, destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", tmp_path / "missing-marker")
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", tmp_path / "missing-marker")

    assert kvantum._user_overlay_required() is True
    assert "qt6-svg-cmake:qt6-svg" in kvantum.deps()
    assert kvantum.build_artifacts() == [kvantum.ENGINE_BUILD / "style/libkvantum.so"]


def test_distro_overlay_installs_user_plugin_without_replacing_system_engine(
        monkeypatch, tmp_path):
    from steps import kvantum
    import shutil

    system_plugin = tmp_path / "system/plugins/styles/libkvantum.so"
    system_plugin.parent.mkdir(parents=True)
    system_plugin.write_bytes(b"distro plugin")
    artifact = tmp_path / "build/style/libkvantum.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"tahoe patched plugin")
    source = tmp_path / "source"
    license_source = source / "Kvantum/COPYING"
    license_source.parent.mkdir(parents=True)
    license_source.write_text("GPL-3.0\n")
    overlay_root = tmp_path / "data/mac-tahoe/qt6/plugins"
    overlay_plugin = overlay_root / "styles/libkvantum.so"
    marker = tmp_path / "data/mac-tahoe/kvantum-engine-overlay.json"
    license_dest = tmp_path / "data/mac-tahoe/licenses/Kvantum.txt"
    env = tmp_path / "config/plasma-workspace/env/mac-tahoe-kvantum-style.sh"
    work = tmp_path / "build-stage"
    calls = []
    session_calls = []

    monkeypatch.setattr(kvantum, "_bundled_engine_required", lambda: False)
    monkeypatch.setattr(kvantum, "_user_overlay_required", lambda: True)
    monkeypatch.setattr(kvantum, "ENGINE_BUILD", tmp_path / "build")
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", source)
    monkeypatch.setattr(kvantum, "ENGINE_WORK", work)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_ROOT", overlay_root)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_PLUGIN", overlay_plugin)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_LICENSE", license_dest)
    monkeypatch.setattr(kvantum, "_engine_overlay_env_path", lambda: env)
    monkeypatch.setenv("QT_PLUGIN_PATH", "/system/qt6/plugins")
    monkeypatch.setattr(
        kvantum,
        "run_user",
        lambda command, **_kwargs: session_calls.append(command)
        or SimpleNamespace(returncode=0, stdout="QT_PLUGIN_PATH=/system/qt6/plugins\n"),
    )

    def install_file(src, dest, label, *, user_owned=False):
        calls.append((Path(dest), user_owned))
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return True

    monkeypatch.setattr(kvantum, "sudo_install_file", install_file)

    assert kvantum._install_bundled_engine() is True
    assert system_plugin.read_bytes() == b"distro plugin"
    assert overlay_plugin.read_bytes() == b"tahoe patched plugin"
    assert json.loads(marker.read_text())["plugin_sha256"] == hashlib.sha256(
        b"tahoe patched plugin"
    ).hexdigest()
    assert str(overlay_root) in env.read_text()
    assert "${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}" in env.read_text()
    assert "systemctl --user set-environment" in env.read_text()
    assert "dbus-update-activation-environment --systemd QT_PLUGIN_PATH" in env.read_text()
    assert len(calls) == 5 and all(user_owned for _dest, user_owned in calls)
    assert os.environ["QT_PLUGIN_PATH"].startswith(f"{overlay_root}:")
    assert session_calls[-1][2] == "set-environment"
    assert session_calls[-1][3].startswith(f"QT_PLUGIN_PATH={overlay_root}:")


def test_session_qt_plugin_path_reaches_plasma_restart_and_is_removed(
        monkeypatch, tmp_path):
    from steps import kvantum

    overlay = tmp_path / "qt6/plugins"
    manager_environment = {"QT_PLUGIN_PATH": "/system/qt6/plugins:/other/plugins"}

    def run_user(command, **_kwargs):
        if command[2] == "show-environment":
            stdout = "".join(f"{key}={value}\n" for key, value in manager_environment.items())
            return SimpleNamespace(returncode=0, stdout=stdout)
        if command[2] == "set-environment":
            key, _, value = command[3].partition("=")
            manager_environment[key] = value
        elif command[2] == "unset-environment":
            manager_environment.pop(command[3], None)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_ROOT", overlay)
    monkeypatch.setattr(kvantum, "run_user", run_user)
    monkeypatch.delenv("QT_PLUGIN_PATH", raising=False)

    assert kvantum._set_session_qt_plugin_path(True) is True
    expected = f"{overlay}:/system/qt6/plugins:/other/plugins"
    assert os.environ["QT_PLUGIN_PATH"] == expected
    assert manager_environment["QT_PLUGIN_PATH"] == expected

    assert kvantum._set_session_qt_plugin_path(False) is True
    assert os.environ["QT_PLUGIN_PATH"] == "/system/qt6/plugins:/other/plugins"
    assert manager_environment["QT_PLUGIN_PATH"] == "/system/qt6/plugins:/other/plugins"


def test_distro_overlay_preserves_unmanaged_plasma_environment_file(
        monkeypatch, tmp_path):
    from steps import kvantum

    env = tmp_path / "config/plasma-workspace/env/mac-tahoe-kvantum-style.sh"
    env.parent.mkdir(parents=True)
    env.write_text("# user-owned settings\nexport QT_PLUGIN_PATH=/custom\n")
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_MARKER", tmp_path / "overlay.json")
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_PLUGIN", tmp_path / "plugins/libkvantum.so")
    monkeypatch.setattr(kvantum, "_engine_overlay_env_path", lambda: env)
    artifact = tmp_path / "build/style/libkvantum.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"plugin")
    source = tmp_path / "source/Kvantum/COPYING"
    source.parent.mkdir(parents=True)
    source.write_text("GPL-3.0\n")
    monkeypatch.setattr(kvantum, "ENGINE_BUILD", tmp_path / "build")
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", tmp_path / "source")
    monkeypatch.setattr(kvantum, "ENGINE_WORK", tmp_path / "stage")
    failures = []
    monkeypatch.setattr(kvantum, "fail", failures.append)

    assert kvantum._install_user_overlay_engine() is False
    assert env.read_text().startswith("# user-owned settings")
    assert not (tmp_path / "plugins/libkvantum.so").exists()
    assert failures


def test_distro_overlay_recovers_after_pending_marker_before_plugin_copy(
        monkeypatch, tmp_path):
    from steps import kvantum
    import shutil

    artifact = tmp_path / "build/style/libkvantum.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"patched plugin")
    license_source = tmp_path / "source/Kvantum/COPYING"
    license_source.parent.mkdir(parents=True)
    license_source.write_text("GPL-3.0\n")
    overlay_plugin = tmp_path / "overlay/styles/libkvantum.so"
    marker = tmp_path / "overlay/kvantum-engine-overlay.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({
        "state": "pending",
        "plugin_sha256": hashlib.sha256(b"patched plugin").hexdigest(),
    }))
    env = tmp_path / "config/plasma-workspace/env/mac-tahoe-kvantum-style.sh"
    env.parent.mkdir(parents=True)
    env.write_text(kvantum.ENGINE_OVERLAY_ENV_MARKER + "export QT_PLUGIN_PATH=/old\n")

    monkeypatch.setattr(kvantum, "ENGINE_BUILD", tmp_path / "build")
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", tmp_path / "source")
    monkeypatch.setattr(kvantum, "ENGINE_WORK", tmp_path / "stage")
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_ROOT", tmp_path / "overlay")
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_PLUGIN", overlay_plugin)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_LICENSE", tmp_path / "overlay/licenses/Kvantum.txt")
    monkeypatch.setattr(kvantum, "_engine_overlay_env_path", lambda: env)
    monkeypatch.setattr(
        kvantum,
        "run_user",
        lambda command, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="QT_PLUGIN_PATH=/old\n" if command[2] == "show-environment" else "",
        ),
    )

    def install_file(src, dest, _label, *, user_owned=False):
        assert user_owned is True
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return True

    monkeypatch.setattr(kvantum, "sudo_install_file", install_file)
    warnings = []
    monkeypatch.setattr(kvantum, "warn", warnings.append)

    assert kvantum._install_user_overlay_engine() is True
    assert overlay_plugin.read_bytes() == b"patched plugin"
    assert json.loads(marker.read_text()).get("state") is None
    assert warnings


def test_uninstall_removes_owned_overlay_but_preserves_distro_plugin(
        monkeypatch, tmp_path):
    from steps import kvantum

    system_plugin = tmp_path / "system/libkvantum.so"
    system_plugin.parent.mkdir(parents=True)
    system_plugin.write_bytes(b"distro plugin")
    overlay = tmp_path / "overlay/styles/libkvantum.so"
    overlay.parent.mkdir(parents=True)
    overlay.write_bytes(b"tahoe plugin")
    marker = tmp_path / "overlay/kvantum-engine-overlay.json"
    marker.write_text(json.dumps({
        "plugin_sha256": hashlib.sha256(b"tahoe plugin").hexdigest(),
        "license_sha256": hashlib.sha256(b"GPL-3.0\n").hexdigest(),
        "version": kvantum.ENGINE_VERSION,
    }))
    license_file = tmp_path / "overlay/licenses/Kvantum.txt"
    license_file.parent.mkdir()
    license_file.write_text("GPL-3.0\n")
    env = tmp_path / "config/plasma-workspace/env/mac-tahoe-kvantum-style.sh"
    env.parent.mkdir(parents=True)
    env.write_text(kvantum.ENGINE_OVERLAY_ENV_MARKER + "export QT_PLUGIN_PATH=/overlay\n")
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_PLUGIN", overlay)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_LICENSE", license_file)
    monkeypatch.setattr(kvantum, "_engine_overlay_env_path", lambda: env)
    monkeypatch.setattr(
        kvantum, "sudo_remove",
        lambda path, _label=None: Path(path).unlink(missing_ok=True) or True,
    )

    kvantum._remove_user_overlay_engine()

    assert system_plugin.read_bytes() == b"distro plugin"
    assert not overlay.exists()
    assert not marker.exists()
    assert not license_file.exists()
    assert not env.exists()


def test_uninstall_retains_overlay_when_environment_is_unmanaged(
        monkeypatch, tmp_path):
    from steps import kvantum

    overlay = tmp_path / "overlay/styles/libkvantum.so"
    overlay.parent.mkdir(parents=True)
    overlay.write_bytes(b"tahoe plugin")
    marker = tmp_path / "overlay/kvantum-engine-overlay.json"
    marker.write_text(json.dumps({
        "plugin_sha256": hashlib.sha256(b"tahoe plugin").hexdigest(),
    }))
    env = tmp_path / "config/plasma-workspace/env/mac-tahoe-kvantum-style.sh"
    env.parent.mkdir(parents=True)
    env.write_text("# custom\nexport QT_PLUGIN_PATH=/custom\n")
    warnings = []
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_PLUGIN", overlay)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_OVERLAY_LICENSE", tmp_path / "license")
    monkeypatch.setattr(kvantum, "_engine_overlay_env_path", lambda: env)
    monkeypatch.setattr(kvantum, "warn", warnings.append)
    monkeypatch.setattr(kvantum, "sudo_remove", lambda *_args: pytest.fail("unexpected removal"))

    kvantum._remove_user_overlay_engine()

    assert overlay.is_file()
    assert marker.is_file()
    assert env.read_text().startswith("# custom")
    assert warnings


def test_bundled_archive_extracts_only_after_digest_check(monkeypatch, tmp_path):
    from steps import kvantum

    work = tmp_path / "work"
    source = work / f"Kvantum-{kvantum.ENGINE_VERSION}"
    monkeypatch.setattr(kvantum, "ENGINE_WORK", work)
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", source)

    assert kvantum._extract_bundled_engine() is True
    assert (source / "Kvantum/CMakeLists.txt").is_file()
    assert (source / "Kvantum/COPYING").is_file()
    patched_style = (source / "Kvantum/style/Kvantum.cpp").read_text()
    assert "tahoeNativeSelection" in patched_style
    assert "pointerHover" in patched_style
    assert "menu->menuAction()->associatedObjects()" in patched_style
    assert "QColor(85, 119, 214)" in patched_style

    corrupt = tmp_path / "Kvantum-corrupt.tar.xz"
    corrupt.write_bytes(kvantum.ENGINE_ARCHIVE.read_bytes() + b"corrupt")
    monkeypatch.setattr(kvantum, "ENGINE_ARCHIVE", corrupt)
    failures = []
    monkeypatch.setattr(kvantum, "fail", failures.append)

    assert kvantum._extract_bundled_engine() is False
    assert any("checksum mismatch" in message for message in failures)


def test_build_compiles_only_the_qt6_style_target(monkeypatch, tmp_path):
    from steps import kvantum

    calls = []
    monkeypatch.setattr(kvantum, "_bundled_engine_required", lambda: True)
    monkeypatch.setattr(kvantum, "_extract_bundled_engine", lambda: True)
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", tmp_path / "source")
    monkeypatch.setattr(kvantum, "ENGINE_BUILD", tmp_path / "build")
    monkeypatch.setattr(
        kvantum,
        "cmake_build",
        lambda *args, **kwargs: calls.append((args, kwargs)) or True,
    )

    kvantum.build()

    assert calls[0][1]["targets"] == ("kvantum",)


def test_marker_is_prepared_before_any_system_install(monkeypatch, tmp_path):
    from steps import kvantum

    build = tmp_path / "build"
    artifact = build / "style/libkvantum.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"plugin")
    source = tmp_path / "source"
    license_source = source / "Kvantum/COPYING"
    license_source.parent.mkdir(parents=True)
    license_source.write_text("GPL-3.0\n")
    work = tmp_path / "work"
    installs: list[tuple] = []
    failures: list[str] = []

    monkeypatch.setattr(kvantum, "_bundled_engine_required", lambda: True)
    monkeypatch.setattr(kvantum, "ENGINE_BUILD", build)
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", source)
    monkeypatch.setattr(kvantum, "ENGINE_WORK", work)
    monkeypatch.setattr(
        kvantum, "_engine_destination",
        lambda: tmp_path / "plugins/styles/libkvantum.so",
    )
    monkeypatch.setattr(
        kvantum, "sudo_install_file",
        lambda *args: installs.append(args) or True,
    )
    monkeypatch.setattr(kvantum, "fail", failures.append)

    real_write_text = Path.write_text

    def fail_marker_write(path, *args, **kwargs):
        if path == work / "kvantum-engine.json":
            raise OSError("disk full")
        return real_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_marker_write)

    assert kvantum._install_bundled_engine() is False
    assert installs == []
    assert any("marker could not be prepared" in message for message in failures)


def test_non_object_ownership_marker_is_not_trusted(monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"plugin")
    marker = tmp_path / "kvantum-engine.json"
    marker.write_text("[]\n")
    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)

    assert kvantum._engine_matches_ownership_marker() is False


def test_pending_marker_owns_old_and_new_plugin_during_reinstall(
        monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old plugin")
    marker = tmp_path / "share/kvantum-engine.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({
        "version": "old",
        "plugin_sha256": hashlib.sha256(b"old plugin").hexdigest(),
    }))
    license_dest = tmp_path / "share/Kvantum.txt"
    build = tmp_path / "build"
    artifact = build / "style/libkvantum.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"new plugin")
    source = tmp_path / "source"
    license_source = source / "Kvantum/COPYING"
    license_source.parent.mkdir(parents=True)
    license_source.write_text("GPL-3.0\n")
    calls: list[Path] = []

    monkeypatch.setattr(kvantum, "_bundled_engine_required", lambda: True)
    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", license_dest)
    monkeypatch.setattr(kvantum, "ENGINE_BUILD", build)
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", source)
    monkeypatch.setattr(kvantum, "ENGINE_WORK", tmp_path / "work")

    def install_file(src, dest, _label):
        calls.append(dest)
        # The marker published before replacement must recognize the old file.
        if dest == destination:
            assert kvantum._engine_matches_ownership_marker() is True
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(src).read_bytes())
        # It must also recognize the new file immediately after replacement.
        if dest == destination:
            assert kvantum._engine_matches_ownership_marker() is True
        return True

    monkeypatch.setattr(kvantum, "sudo_install_file", install_file)

    assert kvantum._install_bundled_engine() is True
    assert calls == [marker, destination, license_dest, marker]
    final = json.loads(marker.read_text())
    assert final["plugin_sha256"] == hashlib.sha256(b"new plugin").hexdigest()
    assert "state" not in final
    assert "previous_plugin_sha256" not in final


def test_failed_reinstall_leaves_pending_marker_owning_previous_plugin(
        monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old plugin")
    marker = tmp_path / "share/kvantum-engine.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({
        "plugin_sha256": hashlib.sha256(b"old plugin").hexdigest(),
    }))
    build = tmp_path / "build"
    artifact = build / "style/libkvantum.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"new plugin")
    source = tmp_path / "source"
    license_source = source / "Kvantum/COPYING"
    license_source.parent.mkdir(parents=True)
    license_source.write_text("GPL-3.0\n")

    monkeypatch.setattr(kvantum, "_bundled_engine_required", lambda: True)
    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", tmp_path / "share/Kvantum.txt")
    monkeypatch.setattr(kvantum, "ENGINE_BUILD", build)
    monkeypatch.setattr(kvantum, "ENGINE_SOURCE", source)
    monkeypatch.setattr(kvantum, "ENGINE_WORK", tmp_path / "work")

    def fail_plugin(src, dest, _label):
        if dest == marker:
            dest.write_bytes(Path(src).read_bytes())
            return True
        return False

    monkeypatch.setattr(kvantum, "sudo_install_file", fail_plugin)

    assert kvantum._install_bundled_engine() is False
    pending = json.loads(marker.read_text())
    assert pending["state"] == "pending"
    assert kvantum._engine_matches_ownership_marker() is True
    assert destination.read_bytes() == b"old plugin"


def test_uninstall_removes_only_the_digest_owned_engine(monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"ours")
    marker = tmp_path / "share/kvantum-engine.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({
        "version": kvantum.ENGINE_VERSION,
        "plugin_sha256": hashlib.sha256(b"ours").hexdigest(),
    }))
    license_file = tmp_path / "share/Kvantum.txt"
    license_file.write_text("GPL-3.0")

    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", license_file)
    monkeypatch.setattr(
        kvantum,
        "sudo_remove",
        lambda path, _label=None: path.unlink(missing_ok=True) or True,
    )

    kvantum._remove_bundled_engine()

    assert not destination.exists()
    assert not marker.exists()
    assert not license_file.exists()


def test_uninstall_preserves_engine_replaced_by_distro(monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"distro replacement")
    marker = tmp_path / "kvantum-engine.json"
    marker.write_text(json.dumps({
        "version": kvantum.ENGINE_VERSION,
        "plugin_sha256": hashlib.sha256(b"old project build").hexdigest(),
    }))
    license_file = tmp_path / "Kvantum.txt"
    license_file.write_text("GPL-3.0")
    warnings = []

    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", license_file)
    monkeypatch.setattr(kvantum, "warn", warnings.append)
    monkeypatch.setattr(
        kvantum,
        "sudo_remove",
        lambda path, _label=None: path.unlink(missing_ok=True) or True,
    )

    kvantum._remove_bundled_engine()

    assert destination.read_bytes() == b"distro replacement"
    assert not marker.exists()
    assert warnings and "leaving" in warnings[0]


def test_uninstall_retains_recovery_marker_when_owned_engine_remove_fails(
        monkeypatch, tmp_path):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"ours")
    marker = tmp_path / "share/kvantum-engine.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({
        "plugin_sha256": hashlib.sha256(b"ours").hexdigest(),
    }))
    license_file = tmp_path / "share/Kvantum.txt"
    license_file.write_text("GPL-3.0")
    failures: list[str] = []

    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", license_file)
    monkeypatch.setattr(kvantum, "fail", failures.append)
    monkeypatch.setattr(kvantum, "sudo_remove", lambda *_args: False)

    kvantum._remove_bundled_engine()

    assert destination.is_file()
    assert marker.is_file()
    assert license_file.is_file()
    assert any("retaining" in failure for failure in failures)


@pytest.mark.parametrize("unreadable", ["marker", "plugin"])
def test_uninstall_retains_recovery_when_ownership_cannot_be_read(
        monkeypatch, tmp_path, unreadable):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"ours")
    marker = tmp_path / "share/kvantum-engine.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({
        "plugin_sha256": hashlib.sha256(b"ours").hexdigest(),
    }))
    license_file = tmp_path / "share/Kvantum.txt"
    license_file.write_text("GPL-3.0")
    failures: list[str] = []

    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", license_file)
    monkeypatch.setattr(kvantum, "fail", failures.append)
    monkeypatch.setattr(
        kvantum, "sudo_remove",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("cleanup must not run without ownership proof")
        ),
    )

    if unreadable == "marker":
        real_read_text = Path.read_text

        def fail_marker_read(path, *args, **kwargs):
            if path == marker:
                raise OSError("transient read failure")
            return real_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fail_marker_read)
    else:
        monkeypatch.setattr(
            kvantum, "_sha256",
            lambda _path: (_ for _ in ()).throw(OSError("transient read failure")),
        )

    kvantum._remove_bundled_engine()

    assert destination.is_file()
    assert marker.is_file()
    assert license_file.is_file()
    assert failures and "retaining" in failures[0]


@pytest.mark.parametrize("payload", ["{not-json}\n", "[]\n", '{"plugin_sha256":"nope"}\n'])
def test_uninstall_retains_invalid_ownership_marker_for_recovery(
        monkeypatch, tmp_path, payload):
    from steps import kvantum

    destination = tmp_path / "plugins/styles/libkvantum.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"possibly ours")
    marker = tmp_path / "share/kvantum-engine.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(payload)
    license_file = tmp_path / "share/Kvantum.txt"
    license_file.write_text("GPL-3.0")
    failures: list[str] = []

    monkeypatch.setattr(kvantum, "_engine_destination", lambda: destination)
    monkeypatch.setattr(kvantum, "ENGINE_MARKER", marker)
    monkeypatch.setattr(kvantum, "ENGINE_LICENSE", license_file)
    monkeypatch.setattr(kvantum, "fail", failures.append)
    monkeypatch.setattr(
        kvantum, "sudo_remove",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("invalid ownership proof must not remove anything")
        ),
    )

    kvantum._remove_bundled_engine()

    assert destination.is_file()
    assert marker.is_file()
    assert license_file.is_file()
    assert failures and "retaining" in failures[0]
