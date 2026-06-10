// User types
export interface User {
    uuid: string;
    email: string;
    firstName: string;
    lastName: string;
    role?: 'patient' | 'doctor' | 'admin';
}

// Auth types
export interface AuthTokens {
    accessToken: string;
    refreshToken: string;
    idToken: string;
    tokenType: string;
}

// Chat types
export interface Message {
    id: number;
    chatUuid: string;
    sender: 'user' | 'assistant' | 'system';
    messageType: string;
    content: string;
    structuredData?: any;
    createdAt: string;
}

// Add more shared types
export * from './patient.types';
export * from './doctor.types';
export * from './api.types';