import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

type UserType = 'doctor' | 'patient';

interface UserTypeContextType {
  isDoctor: boolean;
  userType: UserType;
  setUserType: (type: UserType) => void;
}

const UserTypeContext = createContext<UserTypeContextType | undefined>(undefined);

export const useUserType = () => {
  const context = useContext(UserTypeContext);
  if (context === undefined) {
    throw new Error('useUserType must be used within a UserTypeProvider');
  }
  return context;
};

interface UserTypeProviderProps {
  children: ReactNode;
  userType?: UserType;
}

export const UserTypeProvider: React.FC<UserTypeProviderProps> = ({ 
  children, 
  userType = 'doctor' // Default to doctor for doctor-web app
}) => {
  // For doctor-web app, always set as doctor
  const [currentUserType, setCurrentUserType] = useState<UserType>(userType);
  
  const setUserType = (type: UserType) => {
    setCurrentUserType(type);
    localStorage.setItem('userType', type);
  };

  const value: UserTypeContextType = {
    isDoctor: currentUserType === 'doctor',
    userType: currentUserType,
    setUserType,
  };

  return (
    <UserTypeContext.Provider value={value}>
      {children}
    </UserTypeContext.Provider>
  );
}; 