// author: jf
package com.resumebuilder.springaibackend.entity;

import java.time.LocalDateTime;

public class UserResumeEntity {

    private String resumeId;
    private String userId;
    private String resumeName;
    private String resumeDataJson;
    private Integer active;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public String getResumeId() {
        return resumeId;
    }

    public void setResumeId(String resumeId) {
        this.resumeId = resumeId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getResumeName() {
        return resumeName;
    }

    public void setResumeName(String resumeName) {
        this.resumeName = resumeName;
    }

    public String getResumeDataJson() {
        return resumeDataJson;
    }

    public void setResumeDataJson(String resumeDataJson) {
        this.resumeDataJson = resumeDataJson;
    }

    public Integer getActive() {
        return active;
    }

    public void setActive(Integer active) {
        this.active = active;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
