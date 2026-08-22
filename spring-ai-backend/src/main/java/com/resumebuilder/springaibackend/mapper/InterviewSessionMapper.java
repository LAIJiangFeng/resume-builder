// author: jf
package com.resumebuilder.springaibackend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.resumebuilder.springaibackend.entity.InterviewSessionEntity;
import com.resumebuilder.springaibackend.entity.InterviewSessionSummaryRow;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface InterviewSessionMapper extends BaseMapper<InterviewSessionEntity> {

    List<InterviewSessionSummaryRow> selectSessionSummaries(@Param("userId") String userId, @Param("limit") int limit);
}
