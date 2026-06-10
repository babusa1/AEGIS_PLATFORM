# Profile Page

This directory contains the Profile page components and related files for the patient portal application.

## Structure

```
ProfilePage/
├── components/
│   ├── ProfileHeader.tsx      # Profile image, name, email, and edit button
│   ├── PersonalInformation.tsx # Form fields in 3-column grid layout
│   └── index.ts              # Component exports
├── ProfilePage.tsx           # Main profile page component
├── ProfilePage.styles.ts     # Styled components for the profile page
├── types.ts                  # TypeScript interfaces and types
├── index.tsx                 # Default export
└── README.md                 # This file
```

## Components

### ProfilePage.tsx
The main component that orchestrates the profile page functionality:
- Manages state for profile data, form data, editing mode, loading, and errors
- Handles API calls (currently using mock data)
- Renders the profile header and personal information sections
- Provides error and loading states

### ProfileHeader.tsx
Displays the profile section header with:
- Circular profile image with edit button overlay
- User's full name
- Email address with mail icon
- "Edit Profile" button

### PersonalInformation.tsx
Renders the personal information form in a 3-column grid:
- **Column 1**: First Name, Phone Number, Chemotherapy Day
- **Column 2**: Last Name, Date of Birth, Reminder Time
- **Column 3**: Email, Doctor, Clinic
- Save/Cancel buttons when in editing mode

## Features

- **Responsive Design**: Grid layout adapts to different screen sizes
- **Edit Mode**: Toggle between view and edit modes
- **Form Validation**: Input fields with proper types and validation
- **Loading States**: Shows loading spinner while fetching data
- **Error Handling**: Displays error messages for failed operations
- **Image Upload**: Support for profile image upload (TODO: implement)

## Styling

The profile page uses styled-components with:
- Clean, modern design matching the application theme
- Consistent spacing and typography
- Hover effects and transitions
- Responsive breakpoints for mobile and tablet

## API Integration

The profile page is designed to work with RESTful APIs:
- `GET /profile` - Fetch user profile data
- `PUT /profile` - Update profile information
- `POST /profile/image` - Upload profile image

## Usage

```tsx
import ProfilePage from './pages/ProfilePage';

// In your router or app
<Route path="/profile" element={<ProfilePage />} />
```

## Future Enhancements

- [ ] Implement actual API integration
- [ ] Add image upload functionality
- [ ] Add form validation
- [ ] Add profile image cropping
- [ ] Add change password functionality
- [ ] Add notification preferences 