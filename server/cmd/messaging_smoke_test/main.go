package main

import (
    "context"
    "encoding/json"
    "flag"
    "fmt"
    "os"
    "sync"
    "time"

    msg "github.com/Ruben-Alvarez-Dev/LLM-server/server/pkg/messaging"
)

type InferRequestV1 struct {
    RequestID   string                 `json:"request_id"`
    TenantID    string                 `json:"tenant_id"`
    Model       string                 `json:"model"`
    Priority    string                 `json:"priority"`
    Prompt      string                 `json:"prompt"`
    Params      map[string]interface{} `json:"params"`
    TimestampMs int64                  `json:"timestamp_ms"`
}

func main() {
    tenant := flag.String("tenant", "main", "tenant id")
    count := flag.Int("count", 10, "messages to send")
    conc := flag.Int("concurrency", 4, "concurrency")
    brokers := flag.String("brokers", os.Getenv("KAFKA_BROKERS"), "kafka brokers")
    model := flag.String("model", "phi-4-mini-instruct", "model name")
    prompt := flag.String("prompt", "Hello", "prompt text")
    flag.Parse()

    if *brokers == "" { *brokers = "localhost:9092" }

    prod := msg.NewProducer(msg.ProducerOpts{
        Brokers:    []string{*brokers},
        Linger:     10 * time.Millisecond,
        BatchBytes: 128 << 10,
    })
    defer prod.Close()

    topic := msg.TopicNamer(*tenant, "infer.requests.v1")
    fmt.Println("Producing to:", topic)

    wg := sync.WaitGroup{}
    sem := make(chan struct{}, *conc)
    ctx := context.Background()
    errs := 0

    for i := 0; i < *count; i++ {
        wg.Add(1)
        sem <- struct{}{}
        go func(i int) {
            defer wg.Done(); defer func(){<-sem}()
            req := InferRequestV1{
                RequestID:   fmt.Sprintf("test-%d", i),
                TenantID:    *tenant,
                Model:       *model,
                Priority:    "normal",
                Prompt:      *prompt,
                Params:      map[string]interface{}{"temperature":0.2},
                TimestampMs: time.Now().UnixMilli(),
            }
            b, _ := json.Marshal(req)
            if err := prod.Write(ctx, topic, []byte(req.RequestID), map[string]string{"tenant":*tenant}, b); err != nil {
                fmt.Println("produce error:", err)
                errs++
            }
        }(i)
    }
    wg.Wait()
    if errs > 0 { os.Exit(1) }
    fmt.Println("Produced", *count, "messages successfully")
}
