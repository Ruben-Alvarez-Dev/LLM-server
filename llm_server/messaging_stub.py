from __future__ import annotations

import os
from typing import Dict, Optional


class KafkaProducerStub:
    def __init__(self) -> None:
        self._impl = None
        try:
            # Attempt to load confluent_kafka if available
            from confluent_kafka import Producer  # type: ignore

            brokers = os.getenv("KAFKA_BROKERS", "")
            if brokers:
                self._impl = Producer({"bootstrap.servers": brokers})
        except Exception:
            self._impl = None

    def available(self) -> bool:
        return self._impl is not None

    def produce(self, topic: str, key: Optional[bytes], headers: Optional[Dict[str, str]], value: bytes) -> None:
        if not self._impl:
            return
        hdrs = [(k, v) for k, v in (headers or {}).items()]
        self._impl.produce(topic=topic, key=key, headers=hdrs, value=value)
        self._impl.poll(0)

