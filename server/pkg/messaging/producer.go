package messaging

import (
    "context"
    "crypto/sha1"
    "encoding/hex"
    "time"

    kafka "github.com/segmentio/kafka-go"
)

type ProducerOpts struct {
    Brokers    []string
    Linger     time.Duration
    BatchBytes int
    Compression kafka.Compression
    Idempotent bool
}

type Producer struct {
    w *kafka.Writer
}

func NewProducer(opts ProducerOpts) *Producer {
    return &Producer{w: &kafka.Writer{
        Addr:         kafka.TCP(opts.Brokers...),
        BatchTimeout: opts.Linger,
        BatchBytes:   opts.BatchBytes,
        RequiredAcks: kafka.RequireAll,
        Compression:  opts.Compression,
        // segmentio/kafka-go idempotence is limited; rely on key-based dedupe downstream
    }}
}

func keyFor(tenant, model, priority string) []byte {
    h := sha1.Sum([]byte(tenant + "|" + model + "|" + priority))
    b := make([]byte, hex.EncodedLen(len(h)))
    hex.Encode(b, h[:])
    return b
}

func (p *Producer) Write(ctx context.Context, topic string, key []byte, headers map[string]string, payload []byte) error {
    hdrs := make([]kafka.Header, 0, len(headers))
    for k, v := range headers {
        hdrs = append(hdrs, kafka.Header{Key: k, Value: []byte(v)})
    }
    return p.w.WriteMessages(ctx, kafka.Message{Topic: topic, Key: key, Headers: hdrs, Value: payload})
}

func (p *Producer) Close() error { return p.w.Close() }
