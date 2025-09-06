package messaging

import (
    "errors"
    "os"
)

type TenantContext struct {
    ID     string            `json:"id"`
    Plan   string            `json:"plan"`
    Quotas map[string]int64  `json:"quotas"`
}

func RequireTenantHeader(mode string, header string) (string, error) {
    if mode == "multi" {
        if header == "" {
            return "", errors.New("missing X-Tenant-Id header in multi-tenant mode")
        }
        return header, nil
    }
    def := os.Getenv("DEFAULT_TENANT_ID")
    if def == "" { def = "main" }
    return def, nil
}
