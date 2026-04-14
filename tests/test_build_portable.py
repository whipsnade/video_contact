from importlib import util
from pathlib import Path


def _load_build_portable_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "build_portable.py"
    spec = util.spec_from_file_location("build_portable", module_path)
    module = util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_portable_sets_pyinstaller_config_dir_inside_project_root(tmp_path):
    module = _load_build_portable_module()

    env = module._build_pyinstaller_env(tmp_path)

    assert env["PYINSTALLER_CONFIG_DIR"] == str(tmp_path / ".pyinstaller-config")


def test_build_portable_prepares_output_tree_by_removing_old_bundle(tmp_path):
    module = _load_build_portable_module()

    distpath = tmp_path / "dist"
    old_bundle = distpath / "Video Grid Compositor"
    old_app = distpath / "Video Grid Compositor.app"
    old_exe = distpath / "Video Grid Compositor.exe"
    old_bundle.mkdir(parents=True)
    old_app.mkdir(parents=True)
    old_exe.write_text("exe", encoding="utf-8")
    (old_bundle / "marker.txt").write_text("bundle", encoding="utf-8")
    (old_app / "marker.txt").write_text("app", encoding="utf-8")

    module._prepare_output_tree(distpath, "Video Grid Compositor")

    assert not old_bundle.exists()
    assert not old_app.exists()
    assert not old_exe.exists()


def test_build_portable_finds_onefile_executable(tmp_path):
    module = _load_build_portable_module()

    distpath = tmp_path / "dist"
    distpath.mkdir()
    exe_path = distpath / "Video Grid Compositor.exe"
    exe_path.write_text("exe", encoding="utf-8")

    found = module._find_bundle_path(distpath, "Video Grid Compositor", onefile=True)

    assert found == exe_path
