package com.example.demo.controller;

import com.example.demo.service.OrderService;
import com.example.demo.service.ProductService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/reports")
public class ReportController {
    private final OrderService orderService;
    private final ProductService productService;

    public ReportController(OrderService orderService, ProductService productService) {
        this.orderService = orderService;
        this.productService = productService;
    }

    @GetMapping("/sales")
    public ResponseEntity<Map<String, Object>> getSalesReport(@RequestParam String period) {
        Map<String, Object> report = new HashMap<>();
        report.put("period", period);
        report.put("totalSales", 1000);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/inventory")
    public ResponseEntity<Map<String, Object>> getInventoryReport() {
        Map<String, Object> report = new HashMap<>();
        report.put("totalProducts", productService.getAllProducts().size());
        return ResponseEntity.ok(report);
    }

    @GetMapping("/users/activity")
    public ResponseEntity<Map<String, Object>> getUserActivityReport(@RequestParam(required = false) String startDate) {
        Map<String, Object> report = new HashMap<>();
        report.put("activeUsers", 50);
        report.put("startDate", startDate);
        return ResponseEntity.ok(report);
    }
}
