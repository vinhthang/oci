# Build stage
FROM golang:alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY main.go ./
# Compile static binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o incident-commander .

# Run stage
FROM alpine:3.19
WORKDIR /app
RUN apk add --no-cache ca-certificates git
# Copy binary from builder
COPY --from=builder /app/incident-commander .
# We will use hostPath to mount the agy binary into /home/opc/.local/bin/agy
EXPOSE 8080
CMD ["./incident-commander"]
