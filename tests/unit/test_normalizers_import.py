def test_normalizers_module_imports():
    """Smoke-test: модуль должен импортироваться без ошибок."""
    import src.utils.normalizers as normalizers
    assert hasattr(normalizers, "__doc__")
