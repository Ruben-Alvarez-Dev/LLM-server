package messaging

import (
    "context"
    "time"

    kafka "github.com/segmentio/kafka-go"
)

type ConsumerOpts struct {
    Brokers []string
    GroupID string
    Topic   string
    MinBytes int
    MaxBytes int
}

type Consumer struct {
    r *kafka.Reader
}

func NewConsumer(opts ConsumerOpts) *Consumer {
    return &Consumer{r: kafka.NewReader(kafka.ReaderConfig{
        Brokers: opts.Brokers,
        GroupID: opts.GroupID,
        Topic:   opts.Topic,
        MinBytes: opts.MinBytes,
        MaxBytes: opts.MaxBytes,
        StartOffset: kafka.FirstOffset,
        WatchPartitionChanges: true,
        ReadLagInterval: time.Second,
    })}
}

type Message struct {
    Key     []byte
    Value   []byte
    Headers map[string]string
}

func (c *Consumer) Fetch(ctx context.Context) (Message, error) {
    m, err := c.r.ReadMessage(ctx)
    if err != nil { return Message{}, err }
    hs := map[string]string{}
    for _, h := range m.Headers { hs[h.Key] = string(h.Value) }
    return Message{Key: m.Key, Value: m.Value, Headers: hs}, nil
}

func (c *Consumer) Close() error { return c.r.Close() }
