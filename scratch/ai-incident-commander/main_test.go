package main

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestWebhookHandler(t *testing.T) {
	tests := []struct {
		name           string
		method         string
		payload        string
		expectedStatus int
	}{
		{
			name:           "Valid New Alert",
			method:         "POST",
			payload:        `{"status":"firing","alerts":[{"status":"firing","labels":{"alertname":"HighCPUUsage"},"annotations":{"description":"CPU is over 90%"}}]}`,
			expectedStatus: http.StatusOK,
		},
		{
			name:           "Valid Resolved Alert",
			method:         "POST",
			payload:        `{"status":"resolved","alerts":[{"status":"resolved","labels":{"alertname":"HighCPUUsage"},"annotations":{"description":"CPU returned to normal"}}]}`,
			expectedStatus: http.StatusOK,
		},
		{
			name:           "Invalid JSON Payload",
			method:         "POST",
			payload:        `{"status":"firing", "alerts": [ bad json }`,
			expectedStatus: http.StatusBadRequest,
		},
		{
			name:           "Multiple Alerts in Payload",
			method:         "POST",
			payload:        `{"status":"firing","alerts":[{"status":"firing","labels":{"alertname":"MemoryLeak"}},{"status":"firing","labels":{"alertname":"DiskSpaceLow"}}]}`,
			expectedStatus: http.StatusOK,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req, err := http.NewRequest(tt.method, "/webhook", bytes.NewBuffer([]byte(tt.payload)))
			if err != nil {
				t.Fatalf("Failed to create request: %v", err)
			}
			req.Header.Set("Content-Type", "application/json")

			rr := httptest.NewRecorder()
			handler := http.HandlerFunc(handleWebhook)

			handler.ServeHTTP(rr, req)

			if status := rr.Code; status != tt.expectedStatus {
				t.Errorf("Handler returned wrong status code: got %v want %v", status, tt.expectedStatus)
			}
		})
	}
}
