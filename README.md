# Robot_controller

Backend service for the robot controller.

## Runtime port configuration (AWS ECS friendly)

The API listens on a dynamic runtime port using the first available environment variable in this order:

1. `PORT`
2. `APP_PORT`
3. `ECS_PORT`
4. fallback: `8080`

This allows the same container image to run locally and in ECS task definitions that inject a port value through environment variables.
