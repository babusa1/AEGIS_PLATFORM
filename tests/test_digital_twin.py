from aegis.digital_twin.twin import DigitalTwin


def test_digital_twin_step_and_snapshot():
    twin = DigitalTwin("patient-001")
    snap1 = twin.snapshot()
    assert snap1["id"] == "patient-001"

    state2 = twin.step(minutes=10)
    assert "last_updated" in state2
    assert state2["vitals"]["hr"] >= snap1["vitals"]["hr"]
