# Testing (End-to-End)

This document contains screenshots demonstrating the end-to-end testing of the service registry, two service instances, and the client-based discovery + load balancing.

## Screenshots

### Health checks and discovery (registry + instances)

![Registry and services health + discover output](TestCase%20Screenshots/Health%20checks%20and%20discovery%20%28registry%20%2B%20instances%29.png)
### Negative test (unknown service returns 503)

![Unknown service returns 503](TestCase%20Screenshots/Negative%20test%20%28unknown%20services%20returns%20503%29.png)

### Failure / resilience test (stop one instance, TTL expiry)

![Stopping one instance and registry count drops](TestCase%20Screenshots/Failure%20%3A%20resilience%20test%20%28stop%20one%20instance%2C%20TTL%20expiry.png%29)

### Registry heartbeats / runtime logs

![Docker compose logs with register + heartbeat](TestCase%20Screenshots/Registry%20heartbeats%3A%20runtime%20logs.png)

