def test_beacon_functions_thresholds():
    from llm_server.housekeeper import _beacon_ram, _beacon_ssd

    # RAM: critical <= 0, hot <= 2, warn <= 6, ok otherwise
    assert _beacon_ram(-1.0) == 'critical'
    assert _beacon_ram(0.0) == 'critical'
    assert _beacon_ram(1.0) == 'hot'
    assert _beacon_ram(2.0) == 'hot'
    assert _beacon_ram(3.0) == 'warn'
    assert _beacon_ram(6.0) == 'warn'
    assert _beacon_ram(7.0) == 'ok'

    # SSD: based on pressure vs soft/hard and very low free
    soft, hard = 0.75, 0.85
    assert _beacon_ssd(0.50, 500.0, soft, hard) == 'ok'
    assert _beacon_ssd(0.80, 500.0, soft, hard) == 'warn'
    assert _beacon_ssd(0.88, 500.0, soft, hard) == 'hot'
    # critical by free space
    assert _beacon_ssd(0.50, 1.5, soft, hard) == 'critical'

