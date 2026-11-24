"""Import smoke test: the public API the web backend relies on exists. No Earth Engine calls."""

import pytest

from agriculture_monitoring_model import gee, paddy, palm

PALM_API = ["palm_cover", "palm_age", "palm_condition", "palm_nutrient", "palm_waterlogging",
            "palm_productivity", "productivity_covers", "RUNNERS", "PRODUCTIVITY_YEAR", "palm_data_dir"]
PADDY_API = ["productivity", "vhi", "growth_phase", "add_months", "RUNNERS", "VHI_FIRST_YEAR"]


@pytest.mark.parametrize(("module", "names"), [(palm, PALM_API), (paddy, PADDY_API)])
def test_public_names(module, names):
    missing = [n for n in names if not hasattr(module, n)]
    assert not missing, missing
    assert all(callable(f) for f in module.RUNNERS.values())


def test_palm_data_dir_reads_env(monkeypatch, tmp_path):
    monkeypatch.delenv("PALM_DATA_DIR", raising=False)
    with pytest.raises(RuntimeError, match="PALM_DATA_DIR"):
        palm.palm_data_dir()
    monkeypatch.setenv("PALM_DATA_DIR", str(tmp_path))
    assert palm.palm_data_dir() == tmp_path


def test_utm_epsg():
    assert gee.utm_epsg(101.5, 0.9) == 32647  # Siak, north of the equator
    assert gee.utm_epsg(112.4, -7.1) == 32749  # Lamongan, south
