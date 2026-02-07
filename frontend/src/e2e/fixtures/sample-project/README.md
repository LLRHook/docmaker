# Sample Spring Boot Project - E2E Test Fixture

This is a realistic Spring Boot project structure created as a test fixture for Docmaker's E2E tests.

## Project Statistics

- **Total Files**: 20 Java files
- **Controllers**: 5 (UserController, OrderController, ProductController, AuthController, ReportController)
- **Services**: 5 (UserService, OrderService, ProductService, AuthService, NotificationService)
- **Models**: 5 (User, Order, Product, OrderItem, Address)
- **Repositories**: 3 (UserRepository, OrderRepository, ProductRepository)
- **Config**: 2 (SecurityConfig, AppConfig)

## REST Endpoints

### UserController (`/api/users`)
- `GET /api/users` - Get all users
- `GET /api/users/{id}` - Get user by ID
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### OrderController (`/api/orders`)
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Get order by ID
- `GET /api/orders/user/{userId}` - Get orders by user
- `PUT /api/orders/{id}/status` - Update order status
- `DELETE /api/orders/{id}` - Cancel order

### ProductController (`/api/products`)
- `GET /api/products` - Get all products
- `GET /api/products/{id}` - Get product by ID
- `GET /api/products/search` - Search products
- `POST /api/products` - Create product
- `PUT /api/products/{id}/stock` - Update stock
- `DELETE /api/products/{id}` - Delete product

### AuthController (`/api/auth`)
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register
- `GET /api/auth/validate` - Validate token

### ReportController (`/api/reports`)
- `GET /api/reports/sales` - Get sales report
- `GET /api/reports/inventory` - Get inventory report
- `GET /api/reports/users/activity` - Get user activity report

## Dependency Graph

The project has a realistic dependency structure:

```
Controllers → Services → Repositories
     ↓           ↓
  Models  ←  Models
```

### Key Dependencies
- `UserController` → `UserService` → `UserRepository` → `User`
- `OrderController` → `OrderService` → `OrderRepository` → `Order`, `User`
- `OrderService` → `NotificationService` (service-to-service)
- `ProductController` → `ProductService` → `ProductRepository` → `Product`
- `AuthController` → `AuthService` → `UserRepository`
- `ReportController` → `OrderService`, `ProductService`

### Model Relationships
- `Order` → `User` (ManyToOne)
- `Order` → `OrderItem` (OneToMany)
- `OrderItem` → `Product` (ManyToOne)
- `Order` → `Address` (Embedded)

## Expected Graph Metrics

When processed by Docmaker, this fixture should produce:

- **Nodes**: ~20 (one per file)
- **Edges**: ~40-50 (based on imports and dependencies)
- **Classes**: ~22 (including inner classes in config files)
- **Methods**: ~80-100 (across all services, controllers, and models)
- **REST Endpoints**: 21 total endpoints

## Usage

This fixture is designed to be processed by Docmaker's Java parser for E2E testing. It contains:

- Valid Java syntax (parseable by tree-sitter)
- Realistic Spring Boot annotations
- Multiple types of relationships (composition, inheritance, dependency injection)
- Various REST endpoint patterns (@PathVariable, @RequestParam, @RequestBody)
- Service layer with business logic
- Repository layer with JPA
- Configuration classes with @Bean methods

The code is intentionally simplified (methods don't need real implementations) but maintains proper structure for parsing and graph generation.
