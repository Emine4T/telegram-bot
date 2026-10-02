import importlib


def test_bot_module_imports_from_package_context():
    module = importlib.import_module('ehd_shope.bot')
    assert hasattr(module, 'main')
