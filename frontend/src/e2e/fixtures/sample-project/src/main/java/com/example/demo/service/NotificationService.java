package com.example.demo.service;

import com.example.demo.model.Order;
import com.example.demo.model.User;
import org.springframework.stereotype.Service;

@Service
public class NotificationService {

    public NotificationService() {
    }

    public void sendOrderConfirmation(Order order) {
        String message = "Order #" + order.getId() + " confirmed";
        sendEmail(order.getUser(), message);
    }

    public void sendWelcomeEmail(User user) {
        String message = "Welcome " + user.getUsername();
        sendEmail(user, message);
    }

    public void sendPasswordReset(User user, String resetToken) {
        String message = "Reset your password: " + resetToken;
        sendEmail(user, message);
    }

    private void sendEmail(User user, String message) {
        System.out.println("Sending email to " + user.getEmail() + ": " + message);
    }
}
