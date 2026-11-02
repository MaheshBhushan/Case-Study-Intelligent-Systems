import numpy as np

from moulding_sim.risk import RiskModel, engineer


def test_engineered_features_are_physical():
    x = np.array([[1, 300.0, 310.0, 1500.0, 40.0, 100.0]])
    _, dt, power, strain = engineer(x)[0, 5:]
    assert dt == 10.0
    assert power == np.float64(40.0 * 1500.0 * 2 * np.pi / 60)
    assert strain == 4000.0


def test_risk_ranks_failure_conditions_above_healthy():
    rm = RiskModel()
    healthy = [1, 300.0, 310.0, 1500.0, 40.0, 50.0]
    hdf = [1, 300.0, 308.2, 1330.0, 48.0, 50.0]
    overload = [1, 300.0, 310.0, 1300.0, 70.0, 50.0]
    r = rm.predict(np.array([healthy, hdf, overload]))
    assert r[0] < 0.1
    assert r[1] > 0.3 and r[2] > 0.3
