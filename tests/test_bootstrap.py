import importlib


def test_python_app_entrypoints_can_be_imported():
    main_module = importlib.import_module("pyapp.main")
    app_module = importlib.import_module("pyapp.app")

    assert callable(main_module.main)
    assert callable(app_module.create_app)
