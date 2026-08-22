// author: jf
package com.resumebuilder.springaibackend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.resumebuilder.springaibackend.entity.AuthUserEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface AuthUserMapper extends BaseMapper<AuthUserEntity> {

    AuthUserEntity selectByUsername(@Param("username") String username);

    AuthUserEntity selectEnabledByUsername(@Param("username") String username);

    int insertUser(AuthUserEntity account);

    int updatePasswordHash(@Param("userId") String userId, @Param("passwordHash") String passwordHash);
}
