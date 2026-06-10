/**
 * OncoLife Global Styles - Lovable-Inspired Warm Design
 * 
 * Includes:
 * - CSS Reset
 * - DM Sans (body) + Fraunces (headings) fonts
 * - Warm cream backgrounds
 * - Left-border card pattern
 * - Severity color system (green/amber/red)
 * - Animation keyframes
 * - Dark mode support
 */

import { createGlobalStyle } from 'styled-components';
import styled, { css } from 'styled-components';
import { sharedTokens, cardBorderColors } from './theme';

// =============================================================================
// GLOBAL STYLES
// =============================================================================

export const GlobalStyles = createGlobalStyle`
  /* Note: Fonts (DM Sans + Fraunces) are loaded via <link> tags in index.html */
  
  /* CSS Reset */
  *, *::before, *::after {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  /* Root Variables - Warm Cream Theme */
  :root {
    /* Warm Background Colors */
    --background: #FAF8F5;
    --background-paper: #FFFFFF;
    --foreground: #3D3A35;
    
    /* Warm Gray Scale */
    --warm-50: ${sharedTokens.warmLight[50]};
    --warm-100: ${sharedTokens.warmLight[100]};
    --warm-200: ${sharedTokens.warmLight[200]};
    --warm-300: ${sharedTokens.warmLight[300]};
    --warm-400: ${sharedTokens.warmLight[400]};
    --warm-500: ${sharedTokens.warmLight[500]};
    --warm-600: ${sharedTokens.warmLight[600]};
    --warm-700: ${sharedTokens.warmLight[700]};
    --warm-800: ${sharedTokens.warmLight[800]};
    --warm-900: ${sharedTokens.warmLight[900]};
    
    /* Primary Colors */
    --primary: #4F7CAC;
    --primary-light: #7BA3C9;
    --primary-dark: #3B5F8A;
    --primary-foreground: #FFFFFF;
    
    /* Secondary / Accent */
    --secondary: #D4A574;
    --accent: #4F7CAC;
    
    /* Severity Colors (Lovable-style consistent system) */
    --severity-emergency: ${sharedTokens.severity.emergency};
    --severity-urgent: ${sharedTokens.severity.urgent};
    --severity-moderate: ${sharedTokens.severity.moderate};
    --severity-mild: ${sharedTokens.severity.mild};
    
    /* Severity Background Colors */
    --severity-bg-emergency: ${sharedTokens.severityBg.emergency};
    --severity-bg-urgent: ${sharedTokens.severityBg.urgent};
    --severity-bg-moderate: ${sharedTokens.severityBg.moderate};
    --severity-bg-mild: ${sharedTokens.severityBg.mild};
    
    /* Card Colors */
    --card: #FFFFFF;
    --card-foreground: #3D3A35;
    --card-border: #E8E4DD;
    
    /* Text Colors */
    --muted: #8A847A;
    --muted-foreground: #5C574F;
    
    /* Shadows - Soft, warm */
    --shadow-soft: ${sharedTokens.shadows.soft};
    --shadow-warm: ${sharedTokens.shadows.warm};
    --shadow-card: ${sharedTokens.shadows.card};
    --shadow-hover: ${sharedTokens.shadows.hover};
    --shadow-sm: ${sharedTokens.shadows.sm};
    --shadow-md: ${sharedTokens.shadows.md};
    --shadow-lg: ${sharedTokens.shadows.lg};
    
    /* Border Radius (larger for Lovable style) */
    --radius-xs: ${sharedTokens.borderRadius.xs}px;
    --radius-sm: ${sharedTokens.borderRadius.sm}px;
    --radius-md: ${sharedTokens.borderRadius.md}px;
    --radius-lg: ${sharedTokens.borderRadius.lg}px;
    --radius-xl: ${sharedTokens.borderRadius.xl}px;
    --radius-2xl: ${sharedTokens.borderRadius['2xl']}px;
    --radius-full: ${sharedTokens.borderRadius.full}px;
    
    /* Transitions */
    --transition-fast: ${sharedTokens.transitions.fast};
    --transition-normal: ${sharedTokens.transitions.normal};
    --transition-slow: ${sharedTokens.transitions.slow};
    --transition-page-enter: ${sharedTokens.transitions.pageEnter};
    --transition-page-exit: ${sharedTokens.transitions.pageExit};
    
    /* Card Left Border Colors */
    --card-border-primary: ${cardBorderColors.primary};
    --card-border-shared: ${cardBorderColors.shared};
    --card-border-severe: ${cardBorderColors.severe};
    --card-border-moderate: ${cardBorderColors.moderate};
    --card-border-mild: ${cardBorderColors.mild};
    --card-border-new: ${cardBorderColors.new};
    
    /* Safe Areas */
    --safe-area-inset-top: env(safe-area-inset-top, 0px);
    --safe-area-inset-bottom: env(safe-area-inset-bottom, 0px);
    --safe-area-inset-left: env(safe-area-inset-left, 0px);
    --safe-area-inset-right: env(safe-area-inset-right, 0px);
  }

  /* Dark Mode Variables */
  [data-theme="dark"] {
    --background: #1A1917;
    --background-paper: #252320;
    --foreground: #F5F3EE;
    
    --warm-50: ${sharedTokens.warmDark[50]};
    --warm-100: ${sharedTokens.warmDark[100]};
    --warm-200: ${sharedTokens.warmDark[200]};
    --warm-300: ${sharedTokens.warmDark[300]};
    --warm-400: ${sharedTokens.warmDark[400]};
    --warm-500: ${sharedTokens.warmDark[500]};
    --warm-600: ${sharedTokens.warmDark[600]};
    --warm-700: ${sharedTokens.warmDark[700]};
    --warm-800: ${sharedTokens.warmDark[800]};
    --warm-900: ${sharedTokens.warmDark[900]};
    
    --primary: #7BA3C9;
    --primary-light: #A5C4DE;
    --primary-dark: #4F7CAC;
    --primary-foreground: #1A1917;
    
    --card: #252320;
    --card-foreground: #F5F3EE;
    --card-border: #3D3A35;
    
    --muted: #5C574F;
    --muted-foreground: #B8B3A8;
    
    --shadow-soft: ${sharedTokens.shadowsDark.soft};
    --shadow-warm: ${sharedTokens.shadowsDark.warm};
    --shadow-card: ${sharedTokens.shadowsDark.card};
    --shadow-hover: ${sharedTokens.shadowsDark.hover};
    --shadow-sm: ${sharedTokens.shadowsDark.sm};
    --shadow-md: ${sharedTokens.shadowsDark.md};
    --shadow-lg: ${sharedTokens.shadowsDark.lg};
  }

  /* ==========================================================================
     ANIMATION KEYFRAMES
     ========================================================================== */

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes fadeInDown {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slideInLeft {
    from {
      opacity: 0;
      transform: translateX(-30px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes slideInRight {
    from {
      opacity: 0;
      transform: translateX(30px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes scaleIn {
    from {
      opacity: 0;
      transform: scale(0.95);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(100%);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  /* ==========================================================================
     ANIMATION UTILITY CLASSES
     ========================================================================== */

  .animate-fadeIn {
    animation: fadeIn var(--transition-page-enter) forwards;
  }

  .animate-fadeInUp {
    animation: fadeInUp var(--transition-page-enter) forwards;
  }

  .animate-fadeInDown {
    animation: fadeInDown var(--transition-page-enter) forwards;
  }

  .animate-slideInLeft {
    animation: slideInLeft var(--transition-page-enter) forwards;
  }

  .animate-slideInRight {
    animation: slideInRight var(--transition-page-enter) forwards;
  }

  .animate-scaleIn {
    animation: scaleIn var(--transition-page-enter) forwards;
  }

  .animate-slideUp {
    animation: slideUp var(--transition-page-enter) forwards;
  }

  .animate-pulse {
    animation: pulse 2s infinite;
  }

  .animate-spin {
    animation: spin 1s linear infinite;
  }

  /* Staggered children animations */
  .animate-stagger > * {
    opacity: 0;
    animation: fadeInUp var(--transition-page-enter) forwards;
  }

  .animate-stagger > *:nth-child(1) { animation-delay: 0ms; }
  .animate-stagger > *:nth-child(2) { animation-delay: 50ms; }
  .animate-stagger > *:nth-child(3) { animation-delay: 100ms; }
  .animate-stagger > *:nth-child(4) { animation-delay: 150ms; }
  .animate-stagger > *:nth-child(5) { animation-delay: 200ms; }
  .animate-stagger > *:nth-child(6) { animation-delay: 250ms; }
  .animate-stagger > *:nth-child(7) { animation-delay: 300ms; }
  .animate-stagger > *:nth-child(8) { animation-delay: 350ms; }

  /* ==========================================================================
     BASE STYLES - Warm, Lovable-inspired
     ========================================================================== */

  html {
    font-size: 16px;
    scroll-behavior: smooth;
    height: 100%;
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
  }

  body {
    margin: 0;
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 1rem;
    font-weight: 400;
    line-height: 1.6;
    color: var(--foreground);
    background-color: var(--background);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    height: 100%;
    overflow-x: hidden;
    transition: background-color var(--transition-normal), color var(--transition-normal);
  }

  #root {
    height: 100%;
    min-height: 100vh;
  }

  /* Typography - Serif headings for emotional warmth */
  h1, h2, h3, h4 {
    font-family: 'Fraunces', Georgia, serif;
    font-weight: 600;
    line-height: 1.3;
    margin-bottom: 0.5em;
    color: var(--warm-800);
    transition: color var(--transition-normal);
  }
  
  h5, h6 {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    line-height: 1.4;
    margin-bottom: 0.5em;
    color: var(--warm-700);
    transition: color var(--transition-normal);
  }

  h1 { font-size: 2rem; font-weight: 600; }
  h2 { font-size: 1.5rem; font-weight: 600; }
  h3 { font-size: 1.25rem; font-weight: 500; }
  h4 { font-size: 1.125rem; font-weight: 500; }
  h5 { font-size: 1rem; }
  h6 { font-size: 0.875rem; }

  p {
    margin-bottom: 1rem;
    color: var(--warm-600);
    transition: color var(--transition-normal);
  }

  a {
    color: var(--primary);
    text-decoration: none;
    transition: color var(--transition-fast);
    
    &:hover {
      color: var(--primary-dark);
    }
  }

  /* Interactive Elements */
  button, input, select, textarea {
    font-family: inherit;
    font-size: inherit;
  }

  button {
    cursor: pointer;
    border: none;
    outline: none;
    background: transparent;
    transition: all var(--transition-fast);
  }

  /* Touch-friendly targets */
  button, a, input, select, textarea, [role="button"] {
    min-height: 44px;
    
    @media (min-width: 900px) {
      min-height: 36px;
    }
  }

  /* Images */
  img, svg {
    max-width: 100%;
    height: auto;
    display: block;
  }

  /* Lists */
  ul, ol {
    list-style: none;
  }

  /* Focus Styles (Accessibility) */
  :focus-visible {
    outline: 2px solid var(--primary);
    outline-offset: 2px;
  }

  /* Selection */
  ::selection {
    background-color: rgba(79, 124, 172, 0.2);
    color: inherit;
  }

  [data-theme="dark"] ::selection {
    background-color: rgba(123, 163, 201, 0.3);
  }

  /* Scrollbar Styling - Subtle, warm */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: var(--warm-100);
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb {
    background: var(--warm-300);
    border-radius: 4px;
    
    &:hover {
      background: var(--warm-400);
    }
  }

  /* ==========================================================================
     LOVABLE-STYLE UTILITY CLASSES
     ========================================================================== */

  /* Left-border card styles */
  .card-border-primary {
    border-left: 4px solid var(--card-border-primary) !important;
  }
  
  .card-border-shared {
    border-left: 4px solid var(--card-border-shared) !important;
    background-color: rgba(79, 124, 172, 0.05) !important;
  }
  
  .card-border-severe {
    border-left: 4px solid var(--card-border-severe) !important;
  }
  
  .card-border-moderate {
    border-left: 4px solid var(--card-border-moderate) !important;
  }
  
  .card-border-mild {
    border-left: 4px solid var(--card-border-mild) !important;
  }
  
  .card-border-new {
    border-left: 4px solid var(--card-border-new) !important;
  }

  /* Severity badge styles */
  .severity-emergency {
    background-color: var(--severity-bg-emergency);
    color: var(--severity-emergency);
    border: 1px solid currentColor;
  }
  
  .severity-severe,
  .severity-urgent {
    background-color: var(--severity-bg-urgent);
    color: var(--severity-urgent);
    border: 1px solid currentColor;
  }
  
  .severity-moderate {
    background-color: var(--severity-bg-moderate);
    color: #92400E;
    border: 1px solid var(--severity-moderate);
  }
  
  .severity-mild {
    background-color: var(--severity-bg-mild);
    color: #166534;
    border: 1px solid var(--severity-mild);
  }

  /* Glass card effect */
  .glass-card {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(8px);
    border: 1px solid var(--card-border);
    box-shadow: var(--shadow-soft);
    
    [data-theme="dark"] & {
      background: rgba(37, 35, 32, 0.8);
    }
  }

  /* Soft shadow utility */
  .shadow-soft {
    box-shadow: var(--shadow-soft);
  }
  
  .shadow-warm {
    box-shadow: var(--shadow-warm);
  }

  /* Visually hidden */
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .truncate {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Line clamp utilities */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* Responsive Visibility */
  .hide-mobile {
    @media (max-width: 599px) {
      display: none !important;
    }
  }

  .hide-desktop {
    @media (min-width: 900px) {
      display: none !important;
    }
  }

  .show-mobile-only {
    @media (min-width: 600px) {
      display: none !important;
    }
  }

  .show-desktop-only {
    @media (max-width: 899px) {
      display: none !important;
    }
  }

  /* Skeleton Loading */
  .skeleton {
    background: linear-gradient(
      90deg,
      var(--warm-200) 25%,
      var(--warm-100) 50%,
      var(--warm-200) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius-sm);
  }

  /* Reduced Motion */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
`;

// =============================================================================
// STYLED COMPONENTS - Lovable-inspired
// =============================================================================

export const Container = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  height: 100vh;
  min-height: 0;
  background-color: var(--background);
  transition: background-color var(--transition-normal);
`;

export const Content = styled.main`
  display: flex;
  flex-direction: column;
  padding: 1rem;
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  overflow-y: auto;
  
  @media (min-width: 600px) {
    padding: 1.5rem;
  }
  
  @media (min-width: 900px) {
    padding: 2rem;
  }
`;

export const PageHeader = styled.div`
  margin-bottom: 1.5rem;
  animation: fadeInDown var(--transition-page-enter) forwards;
  
  @media (min-width: 600px) {
    margin-bottom: 2rem;
  }
`;

export const PageTitle = styled.h1`
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--foreground);
  margin: 0 0 0.5rem 0;
  
  @media (min-width: 600px) {
    font-size: 1.75rem;
  }
  
  @media (min-width: 900px) {
    font-size: 2rem;
  }
`;

export const PageSubtitle = styled.p`
  font-size: 0.875rem;
  color: var(--muted);
  margin: 0;
  
  @media (min-width: 600px) {
    font-size: 1rem;
  }
`;

// =============================================================================
// LEFT-BORDER CARD (Lovable pattern)
// =============================================================================

export interface CardWithBorderProps {
  borderColor?: 'primary' | 'shared' | 'severe' | 'moderate' | 'mild' | 'new';
  isShared?: boolean;
}

export const CardWithBorder = styled.div<CardWithBorderProps>`
  background: var(--card);
  border: 1px solid var(--card-border);
  border-left: 4px solid ${props => {
    switch (props.borderColor) {
      case 'shared': return 'var(--card-border-shared)';
      case 'severe': return 'var(--card-border-severe)';
      case 'moderate': return 'var(--card-border-moderate)';
      case 'mild': return 'var(--card-border-mild)';
      case 'new': return 'var(--card-border-new)';
      default: return 'var(--card-border-primary)';
    }
  }};
  border-radius: var(--radius-xl);
  padding: 1.25rem;
  box-shadow: var(--shadow-soft);
  transition: all var(--transition-normal);
  
  ${props => props.isShared && css`
    background: rgba(79, 124, 172, 0.05);
    
    [data-theme="dark"] & {
      background: rgba(123, 163, 201, 0.1);
    }
  `}
  
  &:hover {
    box-shadow: var(--shadow-hover);
  }
  
  @media (min-width: 600px) {
    padding: 1.5rem;
  }
`;

// =============================================================================
// SEVERITY BADGE
// =============================================================================

export interface SeverityBadgeProps {
  severity: 'emergency' | 'urgent' | 'severe' | 'moderate' | 'mild';
}

export const SeverityBadge = styled.span<SeverityBadgeProps>`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
  
  ${props => {
    switch (props.severity) {
      case 'emergency':
        return css`
          background: var(--severity-bg-emergency);
          color: var(--severity-emergency);
          border: 1px solid var(--severity-emergency);
        `;
      case 'urgent':
      case 'severe':
        return css`
          background: var(--severity-bg-urgent);
          color: var(--severity-urgent);
          border: 1px solid var(--severity-urgent);
        `;
      case 'moderate':
        return css`
          background: var(--severity-bg-moderate);
          color: #92400E;
          border: 1px solid var(--severity-moderate);
        `;
      case 'mild':
      default:
        return css`
          background: var(--severity-bg-mild);
          color: #166534;
          border: 1px solid var(--severity-mild);
        `;
    }
  }}
`;

// =============================================================================
// FOR DOCTOR BADGE (Lovable pattern)
// =============================================================================

export const ForDoctorBadge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.75rem;
  background: rgba(79, 124, 172, 0.1);
  color: var(--primary);
  border: 1px solid rgba(79, 124, 172, 0.3);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  
  svg {
    width: 12px;
    height: 12px;
  }
  
  [data-theme="dark"] & {
    background: rgba(123, 163, 201, 0.15);
    border-color: rgba(123, 163, 201, 0.4);
  }
`;

// =============================================================================
// SYMPTOM TAG (Lovable style)
// =============================================================================

export const SymptomTag = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  background: var(--warm-100);
  color: var(--warm-600);
  border-radius: var(--radius-lg);
  font-size: 0.75rem;
  font-weight: 500;
  
  [data-theme="dark"] & {
    background: var(--warm-200);
    color: var(--warm-600);
  }
`;

// =============================================================================
// SEARCH INPUT (Lovable style)
// =============================================================================

export const SearchInput = styled.div`
  position: relative;
  flex: 1;
  
  input {
    width: 100%;
    padding: 0.75rem 1rem 0.75rem 2.5rem;
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    color: var(--foreground);
    transition: all var(--transition-fast);
    
    &::placeholder {
      color: var(--muted);
    }
    
    &:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(79, 124, 172, 0.1);
    }
  }
  
  svg {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    width: 18px;
    height: 18px;
    color: var(--muted);
    pointer-events: none;
  }
`;

// =============================================================================
// ANIMATED CONTAINERS
// =============================================================================

export const AnimatedPage = styled.div<{ delay?: number }>`
  animation: fadeInUp var(--transition-page-enter) forwards;
  animation-delay: ${props => props.delay || 0}ms;
  opacity: 0;
`;

export const StaggeredList = styled.div`
  & > * {
    opacity: 0;
    animation: fadeInUp var(--transition-page-enter) forwards;
  }
  
  & > *:nth-child(1) { animation-delay: 0ms; }
  & > *:nth-child(2) { animation-delay: 50ms; }
  & > *:nth-child(3) { animation-delay: 100ms; }
  & > *:nth-child(4) { animation-delay: 150ms; }
  & > *:nth-child(5) { animation-delay: 200ms; }
  & > *:nth-child(6) { animation-delay: 250ms; }
`;

// =============================================================================
// LEGACY EXPORTS (backward compatibility)
// =============================================================================

export const Background = styled.div`
  min-height: 100vh;
  width: 100%;
  background: var(--background);
  padding: 10px 20px;
  
  @media (max-width: 600px) {
    padding: 8px 12px;
  }
`;

export const WrapperStyle = styled.div`
  border: 5px solid var(--card);
  border-radius: 30px;
  height: calc(100vh - 20px);
  display: flex;
  flex-direction: column;
  position: relative;
  
  @media (max-width: 600px) {
    border-width: 3px;
    border-radius: 20px;
    height: calc(100vh - 16px);
  }
`;

export const Header = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background-color: var(--card);
  border-bottom: 1px solid var(--card-border);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-normal);
  
  @media (min-width: 900px) {
    padding: 1.25rem 2rem;
  }
`;

export const Title = styled.h1`
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--foreground);
  margin: 0;
  
  @media (min-width: 900px) {
    font-size: 2rem;
  }
`;

interface CardProps {
  width?: string;
}

export const Card = styled.div<CardProps>`
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-soft);
  border: 1px solid var(--card-border);
  padding: 1.25rem;
  max-width: ${(props) => props.width || '100%'};
  width: 100%;
  display: flex;
  flex-direction: column;
  animation: scaleIn var(--transition-page-enter) forwards;
  transition: all var(--transition-normal);
  
  @media (min-width: 600px) {
    padding: 1.5rem;
    max-width: ${(props) => props.width || '490px'};
  }
`;

export const Subtitle = styled.p`
  font-size: 0.875rem;
  color: var(--muted);
  margin-bottom: 1.5rem;
  text-align: center;
  
  @media (min-width: 600px) {
    font-size: 1rem;
  }
`;

export const Logo = styled.img`
  width: 40px;
  height: 40px;
  
  @media (min-width: 900px) {
    width: 56px;
    height: 56px;
  }
`;

// Grid and Flex utilities
export const Grid = styled.div<{ columns?: number; gap?: string }>`
  display: grid;
  grid-template-columns: 1fr;
  gap: ${props => props.gap || '1rem'};
  
  @media (min-width: 600px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (min-width: 900px) {
    grid-template-columns: repeat(${props => props.columns || 3}, 1fr);
  }
`;

export const Flex = styled.div<{
  direction?: 'row' | 'column';
  align?: string;
  justify?: string;
  gap?: string;
  wrap?: boolean;
}>`
  display: flex;
  flex-direction: ${props => props.direction || 'row'};
  align-items: ${props => props.align || 'stretch'};
  justify-content: ${props => props.justify || 'flex-start'};
  gap: ${props => props.gap || '0'};
  flex-wrap: ${props => props.wrap ? 'wrap' : 'nowrap'};
`;

export const Stack = styled(Flex)`
  flex-direction: column;
`;

export const Row = styled(Flex)`
  flex-direction: row;
`;
