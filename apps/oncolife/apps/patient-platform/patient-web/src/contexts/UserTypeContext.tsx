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
}

export const UserTypeProvider: React.FC<UserTypeProviderProps> = ({ children }) => {
  const [isDoctor, setIsDoctor] = useState<boolean>(() => {
    const stored = localStorage.getItem('userType');
    return stored === 'doctor';
  });

  const setUserType = (type: UserType) => {
    setIsDoctor(type === 'doctor');
    localStorage.setItem('userType', type);
  };

  const value: UserTypeContextType = {
    isDoctor,
    userType: isDoctor ? 'doctor' : 'patient',
    setUserType,
  };

  return (
    <UserTypeContext.Provider value={value}>
      {children}
    </UserTypeContext.Provider>
  );
}; 