// author: jf
package com.resumebuilder.springaibackend.mapper;

import com.resumebuilder.springaibackend.entity.UserResumeEntity;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface UserResumeMapper {

    String lockUser(@Param("userId") String userId);

    List<UserResumeEntity> selectByUserId(@Param("userId") String userId);

    UserResumeEntity selectOwnedById(@Param("userId") String userId, @Param("resumeId") String resumeId);

    int countByUserId(@Param("userId") String userId);

    int insert(UserResumeEntity entity);

    int updateOwned(UserResumeEntity entity);

    int deactivateAll(@Param("userId") String userId);

    int activateOwned(@Param("userId") String userId, @Param("resumeId") String resumeId);

    int deleteOwned(@Param("userId") String userId, @Param("resumeId") String resumeId);
}
