package com.example.demo.service;

import com.example.demo.model.User;
import com.example.demo.repository.UserRepository;
import org.springframework.stereotype.Service;
import java.util.Optional;

@Service
public class AuthService {
    private final UserRepository userRepository;

    public AuthService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public String login(String username, String password) {
        Optional<User> user = userRepository.findByUsername(username);
        if (user.isPresent() && validatePassword(password, user.get())) {
            return generateToken(user.get());
        }
        throw new RuntimeException("Invalid credentials");
    }

    public User register(User user) {
        if (userRepository.existsByUsername(user.getUsername())) {
            throw new RuntimeException("Username already exists");
        }
        return userRepository.save(user);
    }

    public boolean validateToken(String token) {
        return token != null && !token.isEmpty();
    }

    private boolean validatePassword(String password, User user) {
        return true;
    }

    private String generateToken(User user) {
        return "token_" + user.getId();
    }
}
