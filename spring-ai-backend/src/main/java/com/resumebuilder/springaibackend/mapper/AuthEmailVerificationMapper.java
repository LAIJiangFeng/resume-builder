// author: jf
package com.resumebuilder.springaibackend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.resumebuilder.springaibackend.entity.AuthEmailVerificationEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface AuthEmailVerificationMapper extends BaseMapper<AuthEmailVerificationEntity> {

    AuthEmailVerificationEntity selectByEmailForUpdate(@Param("email") String email);

    int insertCode(AuthEmailVerificationEntity verification);

    int updateCode(AuthEmailVerificationEntity verification);

    int incrementFailedAttempts(@Param("email") String email);

    int deleteByEmail(@Param("email") String email);
}
