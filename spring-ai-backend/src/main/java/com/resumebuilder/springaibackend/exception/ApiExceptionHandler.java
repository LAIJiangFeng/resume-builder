// author: jf
package com.resumebuilder.springaibackend.exception;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler({MethodArgumentNotValidException.class, BindException.class})
    public ResponseEntity<Map<String, Object>> handleValidation(Exception ex) {
        String message = "请求参数不合法";

        if (ex instanceof MethodArgumentNotValidException methodEx && !methodEx.getBindingResult().getFieldErrors().isEmpty()) {
            var fieldError = methodEx.getBindingResult().getFieldErrors().getFirst();
            message = resolveValidationMessage(fieldError.getDefaultMessage());
        } else if (ex instanceof BindException bindEx && !bindEx.getBindingResult().getFieldErrors().isEmpty()) {
            var fieldError = bindEx.getBindingResult().getFieldErrors().getFirst();
            message = resolveValidationMessage(fieldError.getDefaultMessage());
        }

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("error", "validation_failed");
        payload.put("message", message);

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(payload);
    }


    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, Object>> handleResponseStatus(ResponseStatusException ex) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("error", "request_failed");
        payload.put("message", safeStatusMessage(ex));
        return ResponseEntity.status(ex.getStatusCode()).body(payload);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException ex) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("error", "bad_request");
        payload.put("message", ex.getMessage() == null ? "请求参数不合法" : ex.getMessage().trim());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(payload);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleUnexpected(Exception ex) {
        log.error("未处理的服务异常", ex);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("error", "internal_error");
        payload.put("message", buildDetailedMessage(ex));
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(payload);
    }


    private String safeStatusMessage(ResponseStatusException ex) {
        String reason = ex.getReason();
        if (reason == null || reason.isBlank()) {
            return ex.getStatusCode().toString();
        }
        return reason.trim();
    }

    private String resolveValidationMessage(String message) {
        if (message == null || message.isBlank()) {
            return "请求参数不合法";
        }
        return message.trim();
    }

    private String buildDetailedMessage(Throwable ex) {
        if (ex == null) {
            return "未知服务异常";
        }

        List<String> causes = new ArrayList<>();
        Throwable current = ex;
        int depth = 0;

        while (current != null && depth < 6) {
            String className = current.getClass().getSimpleName();
            String message = current.getMessage();
            if (message == null || message.isBlank()) {
                causes.add(className);
            } else {
                causes.add(className + ": " + message.trim());
            }
            current = current.getCause();
            depth++;
        }

        return String.join(" | caused by -> ", causes);
    }
}
