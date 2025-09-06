package middleware

import (
    "sync"
    "time"
)

type Dedupe struct {
    mu sync.Mutex
    seen map[string]time.Time
    ttl time.Duration
}

func NewDedupe(ttl time.Duration) *Dedupe {
    return &Dedupe{seen: map[string]time.Time{}, ttl: ttl}
}

func (d *Dedupe) Allow(key string) bool {
    d.mu.Lock(); defer d.mu.Unlock()
    now := time.Now()
    // cleanup
    for k, t := range d.seen { if now.Sub(t) > d.ttl { delete(d.seen, k) } }
    if _, ok := d.seen[key]; ok { return false }
    d.seen[key] = now
    return true
}
