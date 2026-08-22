// author: jf
package com.resumebuilder.springaibackend.dto;

public record RagUploadProgressEvent(
        String event,
        String traceId,
        Integer fileIndex,
        Integer totalFiles,
        String fileName,
        String stage,
        String status,
        String message,
        Integer progressPercent,
        Integer fileProgressPercent,
        RagUploadFileResult result,
        RagUploadResponse summary
) {
    public static RagUploadProgressEvent batchStart(String traceId, int totalFiles) {
        return new RagUploadProgressEvent(
                "batch-start",
                traceId,
                null,
                totalFiles,
                null,
                "开始",
                "uploading",
                "开始处理批量上传",
                0,
                null,
                null,
                null
        );
    }

    public static RagUploadProgressEvent batchStage(String traceId, int totalFiles, String stage, String message) {
        return new RagUploadProgressEvent(
                "batch-stage",
                traceId,
                null,
                totalFiles,
                null,
                stage,
                "uploading",
                message,
                resolveBatchProgressPercent(stage),
                null,
                null,
                null
        );
    }

    public static RagUploadProgressEvent fileStart(
            String traceId,
            int fileIndex,
            int totalFiles,
            String fileName,
            String stage,
            String message
    ) {
        return new RagUploadProgressEvent(
                "file-start",
                traceId,
                fileIndex,
                totalFiles,
                fileName,
                stage,
                "uploading",
                message,
                resolveOverallProgressPercent(fileIndex, totalFiles, resolveFileStageProgress(stage)),
                resolveFileStageProgressPercent(stage),
                null,
                null
        );
    }

    public static RagUploadProgressEvent fileStage(
            String traceId,
            int fileIndex,
            int totalFiles,
            String fileName,
            String stage,
            String message
    ) {
        return new RagUploadProgressEvent(
                "file-stage",
                traceId,
                fileIndex,
                totalFiles,
                fileName,
                stage,
                "uploading",
                message,
                resolveOverallProgressPercent(fileIndex, totalFiles, resolveFileStageProgress(stage)),
                resolveFileStageProgressPercent(stage),
                null,
                null
        );
    }

    public static RagUploadProgressEvent fileResult(
            String traceId,
            int fileIndex,
            int totalFiles,
            String stage,
            RagUploadFileResult result
    ) {
        return new RagUploadProgressEvent(
                "file-result",
                traceId,
                fileIndex,
                totalFiles,
                result.fileName(),
                stage,
                result.status(),
                "success".equals(result.status()) ? "文件处理成功" : result.errorMessage(),
                resolveOverallProgressPercent(fileIndex, totalFiles, 1.0),
                100,
                result,
                null
        );
    }

    public static RagUploadProgressEvent batchComplete(String traceId, RagUploadResponse summary) {
        return new RagUploadProgressEvent(
                "batch-complete",
                traceId,
                null,
                summary.totalFiles(),
                null,
                "完成",
                summary.failedFiles() == 0 ? "success" : "failed",
                "上传请求处理结束",
                100,
                null,
                null,
                summary
        );
    }

    public static RagUploadProgressEvent error(String traceId, String message) {
        return new RagUploadProgressEvent(
                "error",
                traceId,
                null,
                null,
                null,
                "异常",
                "failed",
                message,
                0,
                null,
                null,
                null
        );
    }

    private static int resolveBatchProgressPercent(String stage) {
        if ("校验".equals(stage)) {
            return 1;
        }
        if ("初始化".equals(stage)) {
            return 2;
        }
        if ("处理".equals(stage)) {
            return 3;
        }
        return 0;
    }

    private static int resolveFileStageProgressPercent(String stage) {
        return clampPercent((int) Math.round(resolveFileStageProgress(stage) * 100));
    }

    private static double resolveFileStageProgress(String stage) {
        if ("读取".equals(stage) || "开始".equals(stage)) {
            return 0.16;
        }
        if ("校验".equals(stage)) {
            return 0.25;
        }
        if ("解析".equals(stage)) {
            return 0.38;
        }
        if ("规范化".equals(stage)) {
            return 0.50;
        }
        if ("逻辑文档拆分".equals(stage) || "拆分".equals(stage)) {
            return 0.60;
        }
        if ("切块".equals(stage)) {
            return 0.72;
        }
        if ("Embedding".equals(stage)) {
            return 0.84;
        }
        if ("入库".equals(stage)) {
            return 0.94;
        }
        if ("完成".equals(stage)) {
            return 1.0;
        }
        return 0.35;
    }

    private static int resolveOverallProgressPercent(int fileIndex, int totalFiles, double fileProgress) {
        if (totalFiles <= 0) {
            return 0;
        }
        int safeFileIndex = Math.max(fileIndex, 1);
        int progress = (int) Math.round(((safeFileIndex - 1) + fileProgress) / totalFiles * 100);
        return Math.min(99, Math.max(1, clampPercent(progress)));
    }

    private static int clampPercent(int value) {
        return Math.min(100, Math.max(0, value));
    }
}
