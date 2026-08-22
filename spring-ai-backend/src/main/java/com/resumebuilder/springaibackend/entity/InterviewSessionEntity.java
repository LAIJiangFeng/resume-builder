// author: jf
package com.resumebuilder.springaibackend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.LocalDateTime;

@TableName("interview_sessions")
public class InterviewSessionEntity {

    @TableId(value = "session_id", type = IdType.INPUT)
    private String sessionId;

    @TableField("user_id")
    private String userId;

    @TableField("mode")
    private String mode;

    @TableField("status")
    private String status;

    @TableField("duration_minutes")
    private Integer durationMinutes;

    @TableField("elapsed_seconds")
    private Integer elapsedSeconds;

    @TableField("memory_summary")
    private String memorySummary;

    @TableField("final_evaluation_json")
    private String finalEvaluationJson;

    @TableField("resume_snapshot_json")
    private String resumeSnapshotJson;

    @TableField("total_score")
    private Integer totalScore;

    @TableField("passed")
    private Integer passed;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getDurationMinutes() {
        return durationMinutes;
    }

    public void setDurationMinutes(Integer durationMinutes) {
        this.durationMinutes = durationMinutes;
    }

    public Integer getElapsedSeconds() {
        return elapsedSeconds;
    }

    public void setElapsedSeconds(Integer elapsedSeconds) {
        this.elapsedSeconds = elapsedSeconds;
    }

    public String getMemorySummary() {
        return memorySummary;
    }

    public void setMemorySummary(String memorySummary) {
        this.memorySummary = memorySummary;
    }

    public String getFinalEvaluationJson() {
        return finalEvaluationJson;
    }

    public void setFinalEvaluationJson(String finalEvaluationJson) {
        this.finalEvaluationJson = finalEvaluationJson;
    }

    public String getResumeSnapshotJson() {
        return resumeSnapshotJson;
    }

    public void setResumeSnapshotJson(String resumeSnapshotJson) {
        this.resumeSnapshotJson = resumeSnapshotJson;
    }

    public Integer getTotalScore() {
        return totalScore;
    }

    public void setTotalScore(Integer totalScore) {
        this.totalScore = totalScore;
    }

    public Integer getPassed() {
        return passed;
    }

    public void setPassed(Integer passed) {
        this.passed = passed;
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
