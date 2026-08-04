from app.core.llm_classify_circuit import LlmClassifyCircuit


def test_circuit_trips_and_blocks_until_reset():
    LlmClassifyCircuit.reset()
    assert LlmClassifyCircuit.is_open() is False
    LlmClassifyCircuit.trip(cooldown_seconds=30.0)
    assert LlmClassifyCircuit.is_open() is True
    LlmClassifyCircuit.reset()
    assert LlmClassifyCircuit.is_open() is False
