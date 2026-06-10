import React from 'react';
import { Mail, Edit } from 'lucide-react';
import {
  ProfileInfoHeader,
  ProfileImageContainer,
  ProfileImage,
  EditImageButton,
  ProfileInfo,
  ProfileName,
  ProfileEmail,
  EditProfileButton,
} from '../ProfilePage.styles';
import type { ProfileData } from '../types';

interface ProfileHeaderProps {
  profile: ProfileData;
  onEditProfile: () => void;
  onEditImage: () => void;
}

const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  profile,
  onEditProfile,
  onEditImage,
}) => {
  const getInitials = (first_name: string, last_name: string) => {
    return `${(first_name?.charAt(0) || '')}${(last_name?.charAt(0) || '')}`.toUpperCase();
  };

  return (
    <ProfileInfoHeader>
      <ProfileImageContainer>
        <ProfileImage imageUrl={undefined}>
          {getInitials(profile.first_name, profile.last_name)}
        </ProfileImage>
        <EditImageButton onClick={onEditImage}>
          <Edit />
        </EditImageButton>
      </ProfileImageContainer>
      
      <ProfileInfo>
        <ProfileName>{`${profile.first_name || ''} ${profile.last_name || ''}`}</ProfileName>
        <ProfileEmail>
          <Mail />
          {profile.email_address || ''}
        </ProfileEmail>
      </ProfileInfo>
      
      <EditProfileButton onClick={onEditProfile}>
        Edit Profile
      </EditProfileButton>
    </ProfileInfoHeader>
  );
};

export default ProfileHeader; 