package messaging

import (
    "time"
    nats "github.com/nats-io/nats.go"
)

type ControlPlane struct {
    nc *nats.Conn
    js nats.JetStreamContext
}

func NewControlPlane(url string, opts ...nats.Option) (*ControlPlane, error) {
    nc, err := nats.Connect(url, opts...)
    if err != nil { return nil, err }
    js, err := nc.JetStream()
    if err != nil { nc.Close(); return nil, err }
    return &ControlPlane{nc: nc, js: js}, nil
}

func (cp *ControlPlane) Heartbeat(tenant string) error {
    subj := "ctrl." + tenant + ".workers.heartbeat"
    _, err := cp.nc.Request(subj, []byte("{}"), time.Second)
    return err
}

func (cp *ControlPlane) Publish(tenant, subject string, payload []byte) error {
    subj := "ctrl." + tenant + "." + subject
    _, err := cp.js.Publish(subj, payload)
    return err
}

func (cp *ControlPlane) Close() { cp.nc.Close() }
