package middleware

import "context"

// Tracing stubs; integrate OpenTelemetry SDK if available.
type Tracer interface{ Start(ctx context.Context, name string) (context.Context, func()) }

type noopTracer struct{}
func (noopTracer) Start(ctx context.Context, name string) (context.Context, func()) { return ctx, func(){} }

func NoopTracer() Tracer { return noopTracer{} }
