package messaging

import (
    "fmt"
    "os"
)

// TopicNamer builds topic/subject names honoring TENANCY_MODE.
// domain examples: infer.requests.v1, infer.results.v1, embeddings.ingest.v1, mem.events.v1
func TopicNamer(tenant, domain string) string {
    mode := os.Getenv("TENANCY_MODE")
    if mode == "multi" && tenant != "" {
        return fmt.Sprintf("llm.%s.%s", tenant, domain)
    }
    // single-tenant: default tenant id
    def := os.Getenv("DEFAULT_TENANT_ID")
    if def == "" {
        def = "main"
    }
    return fmt.Sprintf("llm.%s.%s", def, domain)
}
