package middleware

import (
    "sync/atomic"
    "time"
)

type Metrics struct {
    Produced uint64
    Consumed uint64
    Errors   uint64
    P50      time.Duration
    P95      time.Duration
    P99      time.Duration
}

func (m *Metrics) IncProduced() { atomic.AddUint64(&m.Produced, 1) }
func (m *Metrics) IncConsumed() { atomic.AddUint64(&m.Consumed, 1) }
func (m *Metrics) IncErrors()   { atomic.AddUint64(&m.Errors, 1) }
